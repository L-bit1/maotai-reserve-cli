#!/usr/bin/env bash
# 发布 Android 新版本到服务器（应用内更新）
#
# 用法:
#   export DEPLOY_HOST=139.155.134.97
#   export DEPLOY_USER=ubuntu
#   export DEPLOY_PASS='SSH密码'
#   export NEW_VERSION_CODE=2
#   export NEW_VERSION_NAME=1.0.1
#   ./scripts/publish-android-update.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

NEW_VERSION_CODE="${NEW_VERSION_CODE:?请设置 NEW_VERSION_CODE}"
NEW_VERSION_NAME="${NEW_VERSION_NAME:-1.0.1}"
DEPLOY_HOST="${DEPLOY_HOST:?请设置 DEPLOY_HOST}"
DEPLOY_USER="${DEPLOY_USER:-ubuntu}"
DEPLOY_PASS="${DEPLOY_PASS:?请设置 DEPLOY_PASS}"
RELEASE_NOTES="${RELEASE_NOTES:-}"
FORCE_UPDATE="${FORCE_UPDATE:-false}"

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  GRADLE_FILE="android-app/app/build.gradle.kts"
  sed -i.bak "s/versionCode = [0-9]*/versionCode = ${NEW_VERSION_CODE}/" "$GRADLE_FILE"
  sed -i.bak "s/versionName = \"[^\"]*\"/versionName = \"${NEW_VERSION_NAME}\"/" "$GRADLE_FILE"
  rm -f "${GRADLE_FILE}.bak"
  cd android-app
  export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
  ./gradlew assembleDebug --no-daemon
  cd "$ROOT"
fi

APK_SRC="${APK_SRC:-android-app/app/build/outputs/apk/debug/app-debug.apk}"
[[ -f "$APK_SRC" ]] || { echo "找不到 APK: $APK_SRC"; exit 1; }
cp "$APK_SRC" "$ROOT/茅台预约助手-${NEW_VERSION_NAME}.apk"

export APK_SRC DEPLOY_HOST DEPLOY_USER DEPLOY_PASS NEW_VERSION_CODE NEW_VERSION_NAME RELEASE_NOTES FORCE_UPDATE
chmod +x "$ROOT/scripts/publish-android-update.py" 2>/dev/null || true

python3 "$ROOT/scripts/publish-android-update.py"
