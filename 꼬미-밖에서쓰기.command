#!/bin/bash
# 더블클릭 → 꼬미 서버 + 터널(어디서나 폰 접속) 한 번에 켜기.
# 끄기: 이 창에서 Ctrl+C 또는 창 닫기.
cd "$(dirname "$0")"
clear
echo "🐻 꼬미 서버 + 터널을 켜는 중... (몇 초 걸려요)"

python3 server.py 8787 >/tmp/komi_server.log 2>&1 &
SRV=$!
cloudflared tunnel --url http://localhost:8787 >/tmp/komi_tunnel.log 2>&1 &
TUN=$!
trap "echo; echo '꼬미가 잠들어요... 🐻'; kill $SRV $TUN 2>/dev/null" EXIT

URL=""
for i in $(seq 1 40); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/komi_tunnel.log | head -1)
  [ -n "$URL" ] && break
  sleep 1
done
LAN=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)

clear
echo "================================================"
echo "  🐻🍳  꼬미의 부엌 — 준비 완료!"
echo "================================================"
echo
echo "  📱 밖에서도 (데이터·어디서나):"
echo "     ${URL:-(주소 받는 중 실패 — 잠시 후 /tmp/komi_tunnel.log 확인)}"
echo
echo "  🏠 집에서 (맥과 같은 와이파이):"
echo "     http://${LAN:-localhost}:8787"
echo
echo "  ⚠️  이 창을 열어두세요. 닫으면 꼬미가 잠들어요."
echo "      (끄기: Ctrl+C)"
echo "================================================"
wait
