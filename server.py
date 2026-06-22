#!/usr/bin/env python3
"""꼬미의 부엌 — 로컬 CLI 두뇌 서버.

같은 폴더의 앱(index.html + assets/)을 서빙하고,
꼬미 채팅 요청을 `claude` CLI(=내 구독)로 처리한다. API 키·결제 불필요.

  python3 server.py            # 0.0.0.0:8787 에서 실행
  python3 server.py 9000       # 포트 지정

폰에서: 맥과 같은 와이파이라면  http://<맥의 LAN IP>:8787  로 접속.
"""
import base64, json, os, re, shutil, subprocess, sys, socket, tempfile
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
            stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return None, "claude CLI를 찾을 수 없어요. (설치/PATH 확인)"
    except subprocess.TimeoutExpired:
        return None, "꼬미가 생각하다 시간이 너무 걸렸어요. 다시 시도해줘."
    if r.returncode != 0:
        return None, (r.stderr.strip() or "claude 실행 오류")
    return r.stdout.strip(), None


RECEIPT_PROMPT = (
    "다음 이미지 파일을 읽어줘: {path}\n"
    "이건 장보기 영수증 사진이야. 영수증에 적힌 '먹는 식재료'와 수량만 뽑아서 "
    'JSON 배열로만 답해. 형식: [{{"name":"당근","qty":"3개"}}]. '
    "비닐봉투·일회용품·할인·포인트·봉투·합계·결제수단 등 식재료가 아닌 항목은 제외해. "
    "수량 단위는 영수증대로(개/모/팩/단/g/ml 등), 안 적혀 있으면 \"1개\". "
    "이름은 짧고 일반적인 한국어로 정리해(예: '서울우유 1L'→'우유', '대파 한단'→'대파'). "
    "JSON 외에 다른 말은 절대 하지 마."
)

def extract_receipt(image_path: str):
    """claude CLI(기본 에이전트)로 영수증 이미지를 읽어 식재료 목록을 추출."""
    try:
        r = subprocess.run(
            [CLAUDE, "-p", RECEIPT_PROMPT.format(path=image_path), "--output-format", "text"],
            capture_output=True, text=True, timeout=200, cwd=ROOT,
            stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return None, "claude CLI를 찾을 수 없어요."
    except subprocess.TimeoutExpired:
        return None, "영수증 읽기에 시간이 너무 걸렸어요. 다시 시도해줘."
    if r.returncode != 0:
        return None, (r.stderr.strip() or "claude 실행 오류")
    out = (r.stdout or "").strip()
    m = re.search(r"\[.*\]", out, re.S)   # 코드펜스/설명이 섞여도 JSON 배열만 추출
    if not m:
        return [], None
    try:
        data = json.loads(m.group(0))
    except Exception:
        return [], None
    items = []
    for x in data:
        if isinstance(x, dict) and str(x.get("name", "")).strip():
            items.append({"name": str(x.get("name")).strip(),
                          "qty": str(x.get("qty", "1개")).strip() or "1개"})
    return items, None


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def end_headers(self):
        # 캐시를 끄고 항상 재검증 → 파일만 바꾸면 폰 새로고침 시 바로 최신 버전.
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()

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
        path = self.path
        if not (path.endswith("/api/komi") or path.endswith("/api/receipt")):
            return self._json(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._json(400, {"error": "bad request"})

        if path.endswith("/api/receipt"):
            return self._handle_receipt(data)

        # /api/komi
        system = (data.get("system") or "너는 '꼬미'라는 귀여운 곰돌이 요리 친구야.").strip()
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return self._json(400, {"error": "empty prompt"})
        text, err = call_claude(system, prompt)
        if err:
            return self._json(502, {"error": err})
        return self._json(200, {"text": text})

    def _handle_receipt(self, data):
        img = data.get("image") or ""
        m = re.match(r"data:image/([\w.+-]+);base64,(.*)$", img, re.S)
        if not m:
            return self._json(400, {"error": "이미지 형식을 못 읽었어요."})
        ext = m.group(1).lower()
        ext = "jpg" if ext in ("jpeg", "jpg") else ("png" if ext == "png" else "img")
        try:
            raw = base64.b64decode(m.group(2))
        except Exception:
            return self._json(400, {"error": "이미지 디코딩 실패"})
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(suffix="." + ext, prefix="komi_receipt_", dir="/tmp")
            with os.fdopen(fd, "wb") as f:
                f.write(raw)
            items, err = extract_receipt(tmp)
            if err:
                return self._json(502, {"error": err})
            return self._json(200, {"items": items})
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except Exception:
                    pass

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
