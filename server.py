#!/usr/bin/env python3
"""꼬미의 부엌 — 로컬 CLI 두뇌 서버.

같은 폴더의 앱(index.html + assets/)을 서빙하고,
꼬미 채팅 요청을 `claude` CLI(=내 구독)로 처리한다. API 키·결제 불필요.

  python3 server.py            # 0.0.0.0:8787 에서 실행
  python3 server.py 9000       # 포트 지정

폰에서: 맥과 같은 와이파이라면  http://<맥의 LAN IP>:8787  로 접속.
"""
import json, os, shutil, subprocess, sys, socket
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8787

# claude 실행 파일 찾기 (PATH → homebrew 폴백)
CLAUDE = shutil.which("claude") or "/opt/homebrew/bin/claude"

def call_claude(system: str, prompt: str):
    """claude CLI를 자동 모드로 호출해 꼬미의 답변 텍스트를 반환."""
    try:
        r = subprocess.run(
            [CLAUDE, "-p", prompt,
             "--system-prompt", system,
             "--output-format", "text"],
            capture_output=True, text=True, timeout=180, cwd=ROOT,
        )
    except FileNotFoundError:
        return None, "claude CLI를 찾을 수 없어요. (설치/PATH 확인)"
    except subprocess.TimeoutExpired:
        return None, "꼬미가 생각하다 시간이 너무 걸렸어요. 다시 시도해줘."
    if r.returncode != 0:
        return None, (r.stderr.strip() or "claude 실행 오류")
    return r.stdout.strip(), None


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/") .endswith("/api/health") or self.path == "/api/health":
            return self._json(200, {"ok": True, "mode": "cli"})
        return super().do_GET()

    def do_POST(self):
        if not self.path.endswith("/api/komi"):
            return self._json(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._json(400, {"error": "bad request"})
        system = (data.get("system") or "너는 '꼬미'라는 귀여운 곰돌이 요리 친구야.").strip()
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return self._json(400, {"error": "empty prompt"})
        text, err = call_claude(system, prompt)
        if err:
            return self._json(502, {"error": err})
        return self._json(200, {"text": text})

    def log_message(self, fmt, *args):
        # /api/* 호출만 간단히 로깅, 정적 파일은 조용히
        if "/api/" in (self.path or ""):
            sys.stderr.write("  꼬미 ← %s\n" % (fmt % args))


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    ip = lan_ip()
    print("🐻🍳  꼬미의 부엌 — 로컬 CLI 서버")
    print("    claude:", CLAUDE)
    print(f"    이 맥에서:   http://localhost:{PORT}")
    print(f"    폰(같은 와이파이): http://{ip}:{PORT}")
    print("    (종료: Ctrl+C)")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
