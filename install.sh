#!/usr/bin/env bash
set -euo pipefail

# MatrixVision — 一键安装脚本
# 自动检测系统并安装 Python 依赖 + 外部工具
# 支持: Debian/Ubuntu, Arch, macOS
# 用法: bash install.sh

APP_NAME="MatrixVision"
INSTALL_DIR="${HOME}/.local/bin"
PYTHON_MIN_VERSION="3.10"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[info]${NC} $*"; }
warn()  { echo -e "${YELLOW}[warn]${NC} $*"; }
fail()  { echo -e "${RED}[error]${NC} $*" >&2; exit 1; }

# 检测包管理器
detect_pkg_manager() {
  if command -v apt-get &>/dev/null; then
    echo "apt"
  elif command -v pacman &>/dev/null; then
    echo "pacman"
  elif command -v brew &>/dev/null; then
    echo "brew"
  else
    echo "unknown"
  fi
}

# 检测操作系统
detect_os() {
  if [[ "$(uname -s)" == "Darwin" ]]; then
    echo "macos"
  elif [[ -f /etc/os-release ]]; then
    . /etc/os-release
    echo "${ID:-linux}"
  else
    echo "linux"
  fi
}

# 安装系统依赖
install_system_deps() {
  local pkg_manager="$1"
  local os_id="$2"

  info "安装系统依赖..."

  case "$pkg_manager" in
    apt)
      sudo apt-get update -qq
      # Ubuntu 需要 universe 源来装 ffmpeg
      sudo apt-get install -y --no-install-recommends \
        ffmpeg \
        python3-pip \
        python3-venv \
        python3-dev \
        libopencv-dev \
        python3-numpy 2>/dev/null || {
          warn "部分包安装失败，继续尝试..."
        }
      ;;
    pacman)
      sudo pacman -Sy --noconfirm \
        ffmpeg \
        python-pip \
        python-opencv \
        python-numpy
      ;;
    brew)
      brew install ffmpeg
      ;;
    *)
      warn "未知包管理器，跳过系统依赖安装"
      warn "请手动安装: ffmpeg, python3-pip, python3-venv"
      ;;
  esac
}

# 安装 yt-dlp
install_ytdlp() {
  if command -v yt-dlp &>/dev/null; then
    info "yt-dlp 已安装: $(yt-dlp --version | head -1)"
    return
  fi

  info "安装 yt-dlp..."

  # 优先使用 pipx 或 pip 安装
  if command -v pipx &>/dev/null; then
    pipx install yt-dlp || true
  fi

  # 如果还没装好，用 pip 装到用户目录
  if ! command -v yt-dlp &>/dev/null; then
    python3 -m pip install --user --upgrade yt-dlp || fail "yt-dlp 安装失败"
  fi

  # 确保 ~/.local/bin 在 PATH 里
  if [[ ":$PATH:" != *":${HOME}/.local/bin:"* ]]; then
    export PATH="${HOME}/.local/bin:${PATH}"
    # 写入 shell rc 以便持久化
    local shell_rc="${HOME}/.bashrc"
    if [[ -f "${HOME}/.zshrc" ]]; then
      shell_rc="${HOME}/.zshrc"
    fi
    if ! grep -q '\.local/bin' "$shell_rc" 2>/dev/null; then
      echo '' >> "$shell_rc"
      echo '# Added by MatrixVision install' >> "$shell_rc"
      echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$shell_rc"
      info "已将 ~/.local/bin 添加到 $shell_rc"
    fi
  fi

  if ! command -v yt-dlp &>/dev/null; then
    fail "yt-dlp 安装失败，请手动安装: pip install --user yt-dlp"
  fi

  info "yt-dlp 安装成功"
}

# 安装 Python 依赖
install_python_deps() {
  info "安装 Python 依赖..."

  local venv_dir=".venv"

  # 检查 Python 版本
  local py_version
  py_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

  # 简单版本检查
  local major minor
  major=$(echo "$py_version" | cut -d. -f1)
  minor=$(echo "$py_version" | cut -d. -f2)

  if [[ "$major" -lt 3 ]] || [[ "$major" -eq 3 && "$minor" -lt 10 ]]; then
    fail "需要 Python ${PYTHON_MIN_VERSION}+，当前版本: ${py_version}"
  fi

  info "Python 版本: ${py_version}"

  # 创建 venv（如果不存在）
  if [[ ! -d "$venv_dir" ]]; then
    info "创建 Python 虚拟环境..."
    python3 -m venv "$venv_dir"
  else
    info "虚拟环境已存在，跳过创建"
  fi

  # 激活 venv 并安装依赖
  # shellcheck disable=SC1091
  source "$venv_dir/bin/activate"

  python -m pip install --upgrade pip setuptools wheel -q
  python -m pip install opencv-python-headless numpy -q

  # 验证安装
  python -c "import cv2; import numpy; print('cv2:', cv2.__version__); print('numpy:', numpy.__version__)" || \
    fail "Python 依赖安装验证失败"

  info "Python 依赖安装完成"

  # 退出 venv
  deactivate
}

# 配置运行脚本
setup_launcher() {
  info "配置启动脚本..."

  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local venv_python="${script_dir}/.venv/bin/python"
  local launcher="${INSTALL_DIR}/${APP_NAME}"

  # 创建启动器
  mkdir -p "${INSTALL_DIR}"

  cat > "${launcher}" << EOF
#!/usr/bin/env bash
# MatrixVision launcher
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")/.." &>/dev/null && pwd)"
exec "\${SCRIPT_DIR}/.venv/bin/python" "\${SCRIPT_DIR}/src/rain.py" "\$@"
EOF

  chmod +x "${launcher}"
  info "启动器已创建: ${launcher}"

  # 确保安装目录在 PATH 中
  if [[ ":$PATH:" != *":${INSTALL_DIR}:"* ]]; then
    local shell_rc="${HOME}/.bashrc"
    if [[ -f "${HOME}/.zshrc" ]]; then
      shell_rc="${HOME}/.zshrc"
    fi
    if ! grep -q "$INSTALL_DIR" "$shell_rc" 2>/dev/null; then
      echo '' >> "$shell_rc"
      echo '# Added by MatrixVision install' >> "$shell_rc"
      echo "export PATH=\"${INSTALL_DIR}:\${PATH}\"" >> "$shell_rc"
      info "已将 ${INSTALL_DIR} 添加到 PATH ($shell_rc)"
    fi
  fi
}

# 主流程
main() {
  echo ""
  info "=== MatrixVision 一键安装 ==="
  echo ""

  local pkg_manager os_id
  pkg_manager=$(detect_pkg_manager)
  os_id=$(detect_os)

  info "操作系统: ${os_id}"
  info "包管理器: ${pkg_manager}"
  echo ""

  # 安装系统依赖
  install_system_deps "$pkg_manager" "$os_id"
  echo ""

  # 安装 yt-dlp
  install_ytdlp
  echo ""

  # 安装 Python 依赖
  install_python_deps
  echo ""

  # 配置启动器
  setup_launcher
  echo ""

  info "=== 安装完成 ==="
  echo ""
  info "运行方式:"
  info "  1. 直接运行: python3 src/rain.py"
  info "  2. 或使用启动器: ${APP_NAME}"
  info "  3. 指定摄像头: ${APP_NAME} 0 1280 720"
  echo ""
  info "环境变量:"
  info "  MATRIXMIX_FPS=24       帧率"
  info "  MATRIXMIX_SPEED=2      速度倍率"
  info "  MATRIXMIX_INVERT=true  反色"
  info "  MATRIXMIX_CONTRAST=2   对比度 0-3"
  info "  MATRIXMIX_EDGE=2       轮廓 0-3"
  info "  MATRIXMIX_AUDIO=1      启用音频"
  info "  MATRIXMIX_QUERY=\"关键词\" 默认音乐查询词"
  echo ""
}

main "$@"
