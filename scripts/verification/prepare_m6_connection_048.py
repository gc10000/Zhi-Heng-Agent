"""零调用准备新连接048 catalog；缺省路径由程序确定，不读.env。"""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from app.evaluation.connection_048_preflight import main

if __name__=='__main__':
    main()
