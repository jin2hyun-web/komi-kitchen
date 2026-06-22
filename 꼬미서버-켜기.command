#!/bin/bash
# 더블클릭하면 꼬미의 부엌 로컬 서버가 켜져요. (끄려면 이 창에서 Ctrl+C 또는 창 닫기)
cd "$(dirname "$0")"
clear
echo "🐻🍳  꼬미의 부엌 서버를 켤게요..."
echo
python3 server.py 8787
