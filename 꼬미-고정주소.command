#!/bin/bash
# 더블클릭 → 꼬미 서버 + 고정주소(ngrok) 켜기. 아이폰 홈화면 아이콘은 이 주소에 걸어요.
# 끄기: 이 창에서 Ctrl+C 또는 창 닫기.
cd "$(dirname "$0")"
DOMAIN="identity-bling-spirits.ngrok-free.dev"
clear
echo "🐻 꼬미 서버 + 고정주소를 켜는 중... (몇 초)"

python3 server.py 8787 >/tmp/komi_server.log 2>&1 &
SRV=$!
ngrok http --url=$DOMAIN 8787 --log stdout >/tmp/komi_ngrok.log 2>&1 &
NGR=$!
trap "echo; echo '꼬미가 잠들어요... 🐻'; kill $SRV $NGR 2>/dev/null" EXIT

sleep 5
LAN=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
clear
echo "================================================"
echo "  🐻🍳  꼬미의 부엌 — 준비 완료!"
echo "================================================"
echo
echo "  📱 어디서나 (고정 주소 · 홈화면 아이콘용):"
echo "     https://$DOMAIN"
echo
echo "  🏠 집에서 (같은 와이파이, 더 빠름):"
echo "     http://${LAN:-localhost}:8787"
echo
echo "  ⚠️  이 창을 열어두세요. 닫으면 꼬미가 잠들어요."
echo "      (끄기: Ctrl+C)"
echo "================================================"
wait
