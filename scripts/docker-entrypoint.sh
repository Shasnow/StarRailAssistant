#!/bin/sh
# SRA 服务端容器入口。
#
# 首次启动（数据盘里还没有 settings.json）时预置容器默认设置：容器内没有桌面会话，
# 本地模式必然不可用，只能用云游戏，于是把云游戏开关、浏览器与浏览器路径直接指向
# 镜像内的 Chromium 包装脚本，用户拉下来即可用，不必自己去设置页点三下。
#
# 已存在 settings.json 则一律不动，避免覆盖用户自己的设置。
set -eu

cd "${APP_DIR:-/app}"

SETTINGS="${HOME:-/root}/.config/SRA/settings.json"

if [ -f "$SETTINGS" ]; then
    echo "[entrypoint] 已存在 $SETTINGS，跳过默认设置写入"
else
    echo "[entrypoint] 首次启动：写入容器默认设置（云游戏 + 容器内 Chromium）..."
    # SettingsService.save_settings 直接 open(path,'w')，不会创建父目录
    mkdir -p "$(dirname "$SETTINGS")"
    python - <<'PY'
import sys

from SRACore.services.setting_service import SettingsService

# 字段名对齐 SRACore.models.app_settings 的 JSON 别名，section 为小写的 general；
# browser 必须是 "Chrome for Testing"——它在 BrowserType 里对应 webdriver.Chrome 分支，
# path 指向 Dockerfile 里的包装脚本（负责补 --no-sandbox / --disable-dev-shm-usage）
EXPECTED = {
    "cloudGame.enabled": True,
    "cloudGame.browser": "Chrome for Testing",
    "cloudGame.browser.path": "/usr/local/bin/chromium-container",
    "cloudGame.browser.headless": True,
}

updated = SettingsService().patch({"general": EXPECTED})
print("[entrypoint] 已写入:", ", ".join(updated) if updated else "(无)")

missing = [key for key in EXPECTED if f"general.{key}" not in updated]
if missing:
    print(
        f"[entrypoint] 警告：{missing} 未能写入，请在 WebUI 设置里手动配置云游戏",
        file=sys.stderr,
    )
PY
fi

echo "[entrypoint] 启动 SRAServer（${SRA_HOST:-0.0.0.0}:${SRA_PORT:-5073}）..."
exec python -m SRAServer --no-admin