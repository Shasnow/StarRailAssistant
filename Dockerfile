# SRA 服务端镜像（Linux）
#
# 镜像内容全部来自本仓库当前修订版本，启动时不需要下载任何东西：
#   SRACore / SRAServer（pip 安装）、tasks / extensions / resources（任务与图片模板）、
#   SRAServer/static（阶段 1 现场构建的 WebUI）。
#
# 只承载 SRAServer：WebUI 静态托管 + /api REST + /mcp。本地游戏自动化依赖
# pyautogui / pywin32 与真实 1920x1080 游戏窗口，只能在 Windows 宿主上运行；
# 容器内可跑的是「云游戏」——由 Selenium 驱动容器内的 Chromium 访问 sr.mihoyo.com/cloud。
#
# 构建：docker build -t sra-server .
# 运行：docker compose up -d --build（见 docker-compose.yml）


# ── 阶段 1：构建 WebUI（Vue 3 + Vite）──
# Node 版本满足 WebUI 的 engines（^22.18.0 || >=24.12.0），与开发机保持一致取 24.x
FROM node:24-bookworm-slim AS webui

# pnpm 版本由 package.json 的 packageManager 字段锁定（pnpm@12.4.2），交给 corepack 安装
RUN corepack enable

# 保留仓库目录结构：WebUI 的 postbuild 脚本会把 dist/ 复制到 <仓库根>/SRAServer/static，
# 因此产物落在 /build/SRAServer/static，与仓库内布局一致
WORKDIR /build/SRAFrontend/srafrontend-webui
COPY SRAFrontend/srafrontend-webui/package.json SRAFrontend/srafrontend-webui/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY SRAFrontend/srafrontend-webui/ ./
# pnpm build = type-check + vite build + postbuild（产物落到 SRAServer/static）
RUN pnpm build


# ── 阶段 2：运行镜像 ──
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SRA_HOST=0.0.0.0 \
    SRA_PORT=5073

# chromium / chromium-driver：云游戏模式的 Selenium 浏览器与驱动，同源打包版本号天然匹配；
# fonts-noto-cjk：无头 Chromium 渲染中文界面；
# libgl1 / libglib2.0-0 / libgomp1：opencv-python 与 onnxruntime 的运行时依赖，
#   slim 基础镜像不带，缺失时 import cv2 会直接报 libGL.so.1 找不到；
# tini：作为 PID 1 回收僵尸进程（Chromium 会拉起子进程）并转发信号，使 docker stop 优雅退出
RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        fonts-noto-cjk \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        tini \
    && rm -rf /var/lib/apt/lists/*

# 容器内以 root 运行，Chromium 的 setuid 沙箱在此环境不可用，故用包装脚本补齐
# --no-sandbox 与 --disable-dev-shm-usage（SRACore 不提供注入额外 Chromium 参数的口子）。
# 该路径由入口脚本在首次启动时写进设置，用户不需要手动指定。
RUN printf '#!/bin/sh\nexec /usr/bin/chromium --no-sandbox --disable-dev-shm-usage "$@"\n' \
        > /usr/local/bin/chromium-container \
    && chmod +x /usr/local/bin/chromium-container

WORKDIR /app

# 服务端代码与依赖；.dockerignore 已排除 SRAServer/static（改由阶段 1 提供）
COPY pyproject.toml README.md ./
COPY SRACore ./SRACore
COPY SRAServer ./SRAServer
RUN pip install --no-cache-dir ".[server]"

# 任务、扩展与图片模板按 cwd 相对路径解析（tasks/config/*.toml、resources/img/**），
# 因此必须与仓库同层级落在 /app
COPY tasks ./tasks
COPY extensions ./extensions
COPY resources ./resources

# 阶段 1 构建的 WebUI 产物
COPY --from=webui /build/SRAServer/static/ /app/SRAServer/static/

COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 状态盘（settings.json / configs / cache，云游戏的 selenium_profile 登录态在其下）与运行日志
VOLUME ["/root/.config/SRA", "/app/log"]

EXPOSE 5073

# 入口脚本：首次启动预置云游戏设置，然后 exec 启动 SRAServer
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/docker-entrypoint.sh"]