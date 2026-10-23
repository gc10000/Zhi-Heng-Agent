from pathlib import Path
import uuid
import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, Query
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

from app.utils.task_utils import *
from app.utils.sse_utils import create_sse_queue, SSEEvent, sse_generator
from app.clients.mongo_history_utils import *
from app.core.logger import logger
# 导入 API 不编译图或加载模型；首次执行时建立可替换的调用边界。
query_app = None


def get_query_app():
    global query_app
    if query_app is None:
        from app.query_process.agent.main_graph import query_app as compiled_app
        query_app = compiled_app
    return query_app

# 后续导入启动图对象
#from app.query_process.main_graph import query_app


# 定义fastapi对象
app = FastAPI(title="query service",description="掌柜智库查询服务！")
# 跨域问题解决
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 返回chat.html页面
@app.get("/chat.html")  # 对外访问地址
async def chat():
    # 从 api -> query_process
    current_dir_parent_path = Path(__file__).absolute().parent.parent
    # 定义chat.html位置
    chat_html_path = current_dir_parent_path / "page" / "chat.html"
    # 如果不存在，抛出404异常
    if not chat_html_path.exists():
        raise HTTPException(status_code=404, detail=f"没有查询到页面，地址为：{chat_html_path}！")
    return FileResponse(chat_html_path)

# 定义接口接收的数据结构
class QueryRequest(BaseModel):
    """查询请求数据结构"""
    query: str = Field(..., description="查询内容")  # ...必须填写
    session_id: str = Field(None, description="会话ID")
    is_stream: bool = Field(False, description="是否流式返回")



# 证明服务器启动即可
@app.get("/health")
async def health():
    """
    检查服务是否正常
    """
    return {"ok": True}


# 定义查询接口
def run_query_graph(session_id: str, user_query: str, is_stream: bool = True):
    # 旧入口仍按会话保存进程内结果；每次运行清除上一轮结果，防止失败回用旧答案。
    clear_task(session_id)
    update_task_status(session_id, TASK_STATUS_PROCESSING, is_stream)
    default_state = {'original_query': user_query, 'session_id': session_id, 'is_stream': is_stream}
    try:
        result = get_query_app().invoke(default_state)
    except Exception as exc:
        partial = getattr(exc, 'partial_answer', '')
        public_error = '回答生成失败，请稍后重试。'
        set_task_result(session_id, 'partial_answer', partial)
        set_task_result(session_id, 'error', public_error)
        update_task_status(session_id, TASK_STATUS_FAILED, is_stream)
        logger.error('查询失败，session={}，异常类型={}', session_id, type(exc).__name__)
        if is_stream:
            push_to_session(session_id, SSEEvent.ERROR, {'error': public_error, 'status': 'failed', 'partial_answer': partial})
        return
    answer = (result or {}).get('answer', '')
    image_urls = (result or {}).get('image_urls', [])
    set_task_result(session_id, 'answer', answer)
    update_task_status(session_id, TASK_STATUS_COMPLETED, False)
    if is_stream:
        push_to_session(session_id, SSEEvent.FINAL, {'answer': answer, 'status': 'completed', 'image_urls': image_urls})


@app.post("/query")
async def query(background_tasks: BackgroundTasks, request: QueryRequest):
    """
    1 解析参数
    2 更新任务状态
    3 调用处理流程图
    4 返回结果
    :param background_tasks:
    :param request:
    :return:
    """
    user_query = request.query
    session_id = request.session_id if request.session_id else str(uuid.uuid4())

    # 处理是不是流式返回结果
    is_stream = request.is_stream
    if is_stream:
        # 创建一个字典 存储对一个session_id : queue 结果队列
        create_sse_queue(session_id)
    # 更新任务状态
    # 当前会话id作为key! 整体装填处于运行中！
    update_task_status(session_id, TASK_STATUS_PROCESSING,is_stream)

    print("开始处理流程... 是否流式:", is_stream, f"其他参数:{user_query}, session_id:{session_id}")

    if is_stream:
        # 如果是流式，则返回一个流式响应，过程不断地推送
        # 运行执行图对象方法
        background_tasks.add_task(run_query_graph, session_id,user_query,is_stream)
        # 返回结果
        print("开始处理结果....")
        return {
            "message":"结果正在处理中...",
            "session_id":session_id
        }
    else:
        # 同步运行
        run_query_graph(session_id, user_query, is_stream)
        if get_task_status(session_id) == TASK_STATUS_FAILED:
            return JSONResponse(status_code=502, content={
                'message': '处理失败', 'session_id': session_id, 'status': 'failed', 'answer': '',
                'error': get_task_result(session_id, 'error'),
                'partial_answer': get_task_result(session_id, 'partial_answer'),
            })
        answer = get_task_result(session_id,"answer","")
        return {
            "message":"处理完成！",
            "status":"completed",
            "session_id":session_id,
            "answer":answer,
            "done_list":[]
        }



@app.get("/stream/{session_id}")
async def stream(session_id: str, request: Request):
    print("调用流式/stream...")
    """
    sse 实时返回结果
    """
    return StreamingResponse(
        sse_generator(session_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/history/{session_id}")
async def history(session_id: str, limit: int = Query(50, ge=1)):
    """
    查询当前会话历史记录
    """
    try:
        records = get_recent_messages(session_id, limit=limit)
        items = []
        for r in records:
            items.append({
                "_id": str(r.get("_id")) if r.get("_id") is not None else "",
                "session_id": r.get("session_id", ""),
                "role": r.get("role", ""),
                "text": r.get("text", ""),
                "rewritten_query": r.get("rewritten_query", ""),
                "item_names": r.get("item_names", []),
                "ts": r.get("ts")
            })
        return {"session_id": session_id, "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"history error: {e}")


@app.delete("/history/{session_id}")
async def clear_chat_history(session_id: str):
    count = clear_history(session_id)
    return {"message": "History cleared", "deleted_count": count}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
