"""零依赖 HTTP API（标准库 http.server）。

提供健康检查、状态查询、需求生成、回滚等接口，供前端或第三方调用。
默认监听 127.0.0.1:8765。
"""
import json, os, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from .engine import GameForgeEngine

ENGINE = None
ROOT = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 静默，保持演示界面整洁

    def _send(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send({"ok": True})

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send({"ok": True, "service": "创游助手 GameForge", "version": "1.0.0"})
        elif path == "/api/status":
            self._send(ENGINE.status())
        elif path == "/api/memory":
            self._send({"ok": True, "requirements": ENGINE.ledger.all()})
        elif path == "/api/versions":
            self._send({"ok": True, "versions": ENGINE.snaps.all()})
        elif path == "/api/demo.html":
            p = os.path.join(ROOT, "demo.html")
            with open(p, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self._send({"ok": False, "error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            data = {}
        if path == "/api/chat":
            text = data.get("requirement", "").strip()
            if not text:
                self._send({"ok": False, "error": "需求不能为空"}, 400)
            else:
                self._send(ENGINE.run(text))
        elif path == "/api/rollback":
            v = data.get("version")
            if not v:
                self._send({"ok": False, "error": "缺少 version"}, 400)
            else:
                result = ENGINE.rollback(int(v))
                self._send(result, 200 if result.get("ok") else 404)
        else:
            self._send({"ok": False, "error": "not found"}, 404)


def serve(root=".", host="127.0.0.1", port=8765):
    global ENGINE, ROOT
    ROOT = os.path.abspath(root)
    ENGINE = GameForgeEngine(ROOT)
    srv = ThreadingHTTPServer((host, port), Handler)
    print(f"[创游助手] 内核已启动 http://{host}:{port}")
    print(f"[创游助手] 演示界面  http://{host}:{port}/api/demo.html")
    print(f"[创游助手] API 状态  http://{host}:{port}/api/status")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[创游助手] 已停止")
        srv.shutdown()
