# MatrixVision / 终端 Matrix 数字雨

> 在终端里看一场自己房间光照写进代码的雨，同时听一首从 YouTube Live 里捞出来的电台。

---

## 一个纯小白的开发手记

我没有软件开发背景。写这个项目之前，我不会写代码，不懂 Git，也没有接触过 Python 或终端编程。

这个项目完全是我用自然语言向 [Hermes Agent](https://hermes-agent.nousresearch.com/) 描述我想要什么，然后由 AI 一步步帮我写出来的。

整个过程中，我只负责「说人话」——描述我想要的效果、哪里不满意、希望怎么改——Hermes Agent 帮我处理了 rest：代码架构、OpenCV 调用、音频流、终端渲染、Git 提交……甚至还有截图和 DEVLOG。

**一个纯小白 + 一个会写代码的 AI，就是 MatrixVision 的全部阵容。**

我把它开源出来，是想告诉其他没有编程经验的朋友：你也可以用自然语言，从零开始做出自己的东西。

---

## 它是什么

MatrixVision 是一个**终端里的 Matrix 数字雨**体验：摄像头每一帧的亮度会实时改写雨的密度、速度和拖尾。但它不止于此——

> 🎵 **核心特色：在线音乐/直播电台驱动 + 摄像头实景双层驱动**

它可以把 YouTube Live 电台流拉进终端，用**音频能量**控制雨的节奏和生成概率，同时再用**摄像头实景亮度**控制雨的空间分布。两层叠加，就是这款小程序最不一样的地方。

---

## 效果一览

| 特性 | 说明 |
|------|------|
| 🎥 摄像头亮度驱动 | 亮的地方雨更密、更快，暗的地方稀疏 |
| 🎵 在线电台/音乐驱动 | yt-dlp + ffmpeg + ffplay，音频能量驱动全局雨流速度、拖尾、生成概率 |
| 🌧️ 两层亮度分离 | 雨痕衰减层 + 摄像头背景层，互不干扰 |
| 🎛️ 菜单内实时调节 | 对比度 CLAHE（0-3）、边缘 Sobel（0-3） |
| 📻 电台预设 | DEFAULT / LOFI 1 / JAZZ / AMBIENT / SYNTH / PIANO，左右键切换 |
| 🔊 独立开关 | AUDIO / CAMERA 可独立关闭，关掉某一层其余仍正常运行 |
| 📺 竖屏适配 | cover 裁剪 + cell_aspect ≈ 1.2，外接竖屏友好 |
| ⌨️ 字符集切换 | mix（片假名 + ASCII）/ ascii / kana |
| 📦 一键安装 | `bash install.sh`，自动装依赖、yt-dlp、venv、启动器 |
| 🔄 自动备份 | 修改自动存到 `src/backups/`（最多 20 份） |

---

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/ShallowWaterLab/MatrixVision.git
cd MatrixVision

# 2. 一键安装
bash install.sh

# 3. 启动（默认摄像头）
MatrixVision

# 指定摄像头索引和分辨率
MatrixVision 0 1280 720
```

> 安装脚本会自动：装 ffmpeg、yt-dlp、opencv-python-headless、numpy，创建 `.venv`，并在 `~/.local/bin` 生成 `MatrixVision` 启动器。

---

## 使用说明

### 菜单键位

| 按键 | 功能 |
|------|------|
| `↑ ↓ ← →` | 切换菜单项 |
| `Space` / `Enter` | 确认 / 切换开关 |
| `Esc` | 退出菜单（或退出程序） |
| `Q` / `Ctrl+C` | 退出程序 |

### 菜单项说明

| 菜单 | 功能 |
|------|------|
| **CONTRAST** | CLAHE 对比度，0-3 档（0 = 关闭） |
| **EDGE** | Sobel 边缘轮廓，0-3 档（0 = 关闭） |
| **AUDIO** | 音频引擎 ON / OFF，关闭后停止音频并停止驱动 |
| **CAMERA** | 摄像头采集 ON / OFF，关闭后数字雨继续以纯雨滴动画运行 |
| **AUDIO_QUERY** | 电台预设，左右键切换：DEFAULT / LOFI 1 / JAZZ / AMBIENT / SYNTH / PIANO |
| **SAVE** | 保存当前设置，显示 ✔ Saved 提示 |
| **QUIT** | 退出程序 |

> 当前音频状态会实时显示在 `AUDIO_QUERY` 菜单行：`♪ connecting...` / `♪ ready`

---

## 环境变量

可在启动前通过环境变量预配置：

```bash
MATRIXMIX_FPS=24              # 帧率上限
MATRIXMIX_SPEED=2             # 速度倍率
MATRIXMIX_INVERT=true         # 摄像头级灰度反色
MATRIXMIX_CONTRAST=2          # 对比度 0-3
MATRIXMIX_EDGE=2              # 轮廓 0-3
MATRIXMIX_AUDIO=1             # 启用音频引擎
MATRIXMIX_QUERY="lofi hip hop" # 默认音频查询词
```

---

## 架构概览

```
Camera / Mic input
      │
      ▼
  Capture Pipeline
  (resize → grayscale → brightness map)
      │                 │
      ▼                 ▼
 Rain Engine ─────► Terminal I/O
 (column heads,      (ANSI true-color,
  brightness-         cursor-position writes,
  modulated trails)   dirty-rectangle render)
      │
  Audio Engine
  (yt-dlp stream → ffmpeg decode →
   audio energy → rain speed/spawn)
```

- **Camera Manager**：枚举 `/dev/video*`，打开设备并推帧到渲染循环
- **Capture Pipeline**：`cap.read()` → resize 到终端网格 → 灰度 → 每列亮度能量
- **Rain Engine**：每列独立浮点头部 + 速度偏移（0.6x–1.4x）；亮度越高，拖尾越长、下落越快、生成越密
- **Audio Engine**：yt-dlp 拉直播流 → ffmpeg 解码 → 音频能量映射为全局雨速/生成概率
- **Terminal I/O**：隐藏光标、ANSI 真彩色、脏矩形渲染，只重写变化单元格以降低闪烁

---

## 系统依赖

- Python >= 3.10
- OpenCV >= 5.0
- ffmpeg
- yt-dlp
- 支持 ANSI true-color + UTF-8 的终端

---

## 路线图

- [x] 终端数字雨 + 摄像头亮度驱动
- [x] 两层亮度分离（雨痕衰减 + 摄像头背景）
- [x] 在线音乐播放，音频能量驱动雨流
- [x] 对比度 / 边缘实时调节菜单
- [x] 电台预设 + 独立 AUDIO / CAMERA 开关
- [x] 竖屏 cover 适配
- [ ] 截图保存
- [ ] 录制 GIF / MP4

---

## 相关项目

- [MatrixMix](https://github.com/ShallowWaterLab/MatrixMix) — 基础字符集与渲染核心
- [ShallowWaterLab](https://github.com/ShallowWaterLab/) — 更多实验项目

---

## 开源协议

MIT
