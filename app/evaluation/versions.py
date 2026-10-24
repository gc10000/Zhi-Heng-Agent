"""运行前核对实际源码、prompt及本机模型，而非相信手填版本。"""
import hashlib
from importlib.metadata import version
import os
from pathlib import Path
from .validate_dataset import fingerprint


def streamed_sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def runtime_versions(*, root=None, model_paths=None):
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    code = {p.relative_to(root).as_posix(): streamed_sha(p) for p in sorted((root / 'app').rglob('*.py'))}
    prompts = {p.relative_to(root).as_posix(): streamed_sha(p) for p in sorted((root / 'prompts').rglob('*.prompt'))}
    paths = model_paths if model_paths is not None else {'embedding': os.getenv('BGE_M3_PATH'), 'reranker': os.getenv('BGE_RERANKER_LARGE')}
    models = {}
    for name, path in paths.items():
        directory = Path(path) if path else None
        if directory is None or not directory.is_dir():
            raise ValueError('须配置已存在的本地模型目录；评测不自动下载')
        files = [p for p in sorted(directory.rglob('*')) if p.is_file() and p.suffix in {'.bin', '.safetensors', '.json', '.txt', '.model'}]
        if not any(p.suffix in {'.bin', '.safetensors'} for p in files):
            raise ValueError('本机模型权重缺失，评测拒绝自动下载')
        models[name] = {p.relative_to(directory).as_posix(): streamed_sha(p) for p in files}
    settings = {name: os.getenv(name) for name in ('BGE_DEVICE', 'BGE_FP16', 'BGE_RERANKER_DEVICE', 'BGE_RERANKER_FP16',
                'LLM_DEFAULT_MODEL', 'LLM_DEFAULT_TEMPERATURE', 'LLM_PROVIDER', 'LLM_ENABLE_THINKING', 'MODEL_HOST_URL')
                if os.getenv(name) is not None}
    # 端点只存指纹；模型桥接若启用仍核对本机权重，不把健康响应当模型版本。
    settings['endpoint_sha256'] = fingerprint(os.getenv('OPENAI_BASE_URL', ''))
    settings['packages'] = {name: version(name) for name in ('pymilvus', 'FlagEmbedding', 'langchain-openai', 'openai', 'torch')}
    return {'code': fingerprint(code), 'prompt': fingerprint(prompts), 'model': fingerprint([models, settings])}
