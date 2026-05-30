#!/bin/bash
# 同时启动 API(8000) + Web(5173)
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

echo "=========================================="
echo "  茅台抢单 · Web + API"
echo "  API:  http://127.0.0.1:8000/docs"
echo "  Web:  http://127.0.0.1:5173"
echo "  账号: admin / admin123"
echo "=========================================="

if [ -d "$ROOT/.venv" ]; then
  source "$ROOT/.venv/bin/activate"
fi

pip install -q -r requirements.txt -r backend/requirements.txt 2>/dev/null

export PYTHONPATH="$ROOT"
python backend/run.py &
API_PID=$!

cleanup() {
  kill "$API_PID" 2>/dev/null
  exit 0
}
trap cleanup INT TERM

echo "等待 API 启动..."
for i in 1 2 3 4 5 6 7 8 9 10; do
  if python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/ping', timeout=1)" 2>/dev/null; then
    echo "API 已就绪"
    break
  fi
  sleep 1
done

cd "$ROOT/web"
if [ ! -d node_modules ]; then
  npm install
fi
npm run dev

kill "$API_PID" 2>/dev/null
