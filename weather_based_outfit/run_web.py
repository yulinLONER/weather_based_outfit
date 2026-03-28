import os
import sys
import webbrowser
import socket
import argparse
from threading import Timer

# 将项目根目录添加到 python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web.app_web import app

def _is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
        except OSError:
            return False
        return True

def _pick_port(host: str, preferred_port: int, max_tries: int = 20) -> int:
    port = preferred_port
    for _ in range(max_tries):
        if _is_port_available(host, port):
            return port
        port += 1
    raise RuntimeError(f"未找到可用端口：从 {preferred_port} 开始尝试 {max_tries} 次均被占用")

def _open_browser(url: str):
    webbrowser.open_new(url)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "5001")))
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    port = _pick_port(args.host, args.port)
    url = f"http://127.0.0.1:{port}/"

    print("🚀 正在启动 智能穿搭推荐系统 (Web 版)...")
    print(f"📍 访问地址: {url}")
    
    # 延迟 1.5 秒打开浏览器，确保 Flask 已经启动
    if not args.no_browser:
        Timer(1.5, _open_browser, args=(url,)).start()
    
    # 运行 Flask 应用
    # debug=False 避免在生产环境下产生两个进程，从而导致 Timer 运行两次
    app.run(host=args.host, port=port, debug=False)
