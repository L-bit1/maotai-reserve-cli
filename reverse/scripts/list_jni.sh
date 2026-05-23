#!/usr/bin/env bash
# 列出 APK 中所有 JNI 导出（便于定位签名/加密 native）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
UNZIP="${ROOT}/reverse/apk_unzip"
if [[ ! -d "$UNZIP/lib" ]]; then
  mkdir -p "${ROOT}/reverse/apk_unzip"
  unzip -o -q "${ROOT}/base.apk.1.1.1" -d "$UNZIP"
fi
echo "=== arm64-v8a JNI ==="
for so in "$UNZIP"/lib/arm64-v8a/*.so; do
  hits=$(strings "$so" 2>/dev/null | grep '^Java_' || true)
  if [[ -n "$hits" ]]; then
    echo "--- $(basename "$so") ---"
    echo "$hits"
  fi
done
