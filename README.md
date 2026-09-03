# MatrixVision / 终端 Matrix 数字雨

> Watch a rain written in your room's light, while listening to a radio stream pulled from YouTube Live.
>
> 在终端里看一场自己房间光照写进代码的雨，同时听一首从 YouTube Live 里捞出来的电台。

---

## A pure beginner's dev story / 一个纯小白的开发手记

I have no software development background. Before this project, I couldn't code, didn't understand Git, and had never touched Python or terminal programming.

我没有软件开发背景。写这个项目之前，我不会写代码，不懂 Git，也没有接触过 Python 或终端编程。

This project was built entirely by describing what I wanted in plain natural language to [Hermes Agent](https://hermes-agent.nousresearch.com/), and having the AI write it step by step.

整个过程中，我只负责「说人话」——描述我想要的效果、哪里不满意、希望怎么改——Hermes Agent 帮我处理了 rest：代码架构、OpenCV 调用、音频流、终端渲染、Git 提交……甚至还有截图和 DEVLOG。

**One complete beginner + one AI that can code. That's the full MatrixVision team.**

**一个纯小白 + 一个会写代码的 AI，就是 MatrixVision 的全部阵容。**

I'm open-sourcing it to show other non-programmers: you can also build something from scratch using natural language.

我把它开源出来，是想告诉其他没有编程经验的朋友：你也可以用自然语言，从零开始做出自己的东西。

---

## What it is / 它是什么

MatrixVision is a **terminal Matrix rain** experience: live camera brightness reshapes the rain's density, speed, and trails in real time. But that's not all —

MatrixVision 是一个**终端里的 Matrix 数字雨**体验：摄像头每一帧的亮度会实时改写雨的密度、速度和拖尾。但它不止于此——

> 🎵 **Standout feature: online music/live radio driving + live camera dual-layer driving**
>
> 🎵 **核心特色：在线音乐/直播电台驱动 + 摄像头实景双层驱动**

It pulls YouTube Live radio streams into the terminal, using **audio energy** to control the rain's rhythm and spawn rate, while **camera brightness** controls the rain's spatial distribution. Two layers stacked — that's what makes this little app unique.

它可以把 YouTube Live 电台流拉进终端，用**音频能量**控制雨的节奏和生成概率，同时再用**摄像头实景亮度**控制雨的空间分布。两层叠加，就是这款小程序最不一样的地方。

---

## Features / 效果一览

| Feature / 特性 | Description / 说明 |
|----------------|---------------------|
| 🎥 Camera brightness driving / 摄像头亮度驱动 | Brighter areas get denser, faster rain; darker areas get sparser drops / 亮的地方雨更密、更快，暗的地方稀疏 |
| 🎵 Online radio/music driving / 在线电台/音乐驱动 | yt-dlp + ffmpeg + ffplay; audio energy drives global rain speed, trails, and spawn probability / 音频能量驱动全局雨流速度、拖尾、生成概率 |
| 🌧️ Two-layer brightness separation / 两层亮度分离 | Rain trail attenuation layer + camera background layer, independent / 雨痕衰减层 + 摄像头背景层，互不干扰 |
| 🎛️ In-menu real-time tuning / 菜单内实时调节 | CLAHE contrast (0-3), Sobel edge (0-3) / 对比度 CLAHE（0-3）、边缘 Sobel（0-3） |
| 📻 Radio presets / 电台预设 | DEFAULT / LOFI 1 / JAZZ / AMBIENT / SYNTH / PIANO, switch with left/right keys / 左右键切换 |
| 🔊 Independent toggles / 独立开关 | AUDIO / CAMERA can be toggled independently; turning one off leaves the rest running / 可独立关闭，关掉某一层其余仍正常运行 |
| 📺 Vertical screen friendly / 竖屏适配 | Cover crop + cell_aspect ≈ 1.2, optimized for portrait monitors / cover 裁剪 + cell_aspect ≈ 1.2，外接竖屏友好 |
| ⌨️ Charset switching / 字符集切换 | mix (katakana + ASCII) / ascii / kana / mix（片假名 + ASCII）/ ascii / kana |
| 📦 One-command install / 一键安装 | `bash install.sh`, auto-installs deps, yt-dlp, venv, and launcher / 自动装依赖、yt-dlp、venv、启动器 |
| 🔄 Auto backup / 自动备份 | Changes auto-saved to `src/backups/` (up to 20 snapshots) / 修改自动存到 `src/backups/`（最多 20 份） |

---

## Quick Start / 快速开始

```bash
# 1. Clone / 克隆
git clone https://github.com/ShallowWaterLab/MatrixVision.git
cd MatrixVision

# 2. One-command install / 一键安装
bash install.sh

# 3. Run / 启动
MatrixVision

# Specify camera index and resolution / 指定摄像头索引和分辨率
MatrixVision 0 1280 720
```

> 安装脚本会自动：装 ffmpeg、yt-dlp、opencv-python-headless、numpy，创建 `.venv`，并在 `~/.local/bin` 生成 `MatrixVision` 启动器。
>
> The install script handles: ffmpeg, yt-dlp, opencv-python-headless, numpy, `.venv` creation, and a `MatrixVision` launcher in `~/.local/bin`.

---

## Controls / 使用说明

### Menu keys / 菜单键位

| Key / 按键 | Action / 功能 |
|------------|---------------|
| `↑ ↓ ← →` | Navigate menu / 切换菜单项 |
| `Space` / `Enter` | Confirm / toggle switches / 确认 / 切换开关 |
| `Esc` | Exit menu (or quit) / 退出菜单（或退出程序） |
| `Q` / `Ctrl+C` | Quit / 退出程序 |

### Menu items / 菜单项说明

| Menu / 菜单 | Action / 功能 |
|-------------|---------------|
| **CONTRAST** | CLAHE contrast, 0-3 levels (0 = off) / CLAHE 对比度，0-3 档（0 = 关闭） |
| **EDGE** | Sobel edge detection, 0-3 levels (0 = off) / Sobel 边缘轮廓，0-3 档（0 = 关闭） |
| **AUDIO** | Audio engine ON / OFF; stops audio and driving when off / 音频引擎 ON / OFF，关闭后停止音频并停止驱动 |
| **CAMERA** | Camera capture ON / OFF; rain continues as pure drops when off / 摄像头采集 ON / OFF，关闭后数字雨继续以纯雨滴动画运行 |
| **AUDIO_QUERY** | Radio presets, switch with left/right: DEFAULT / LOFI 1 / JAZZ / AMBIENT / SYNTH / PIANO / 电台预设，左右键切换 |
| **SAVE** | Save settings, shows ✔ Saved hint for 1.5s / 保存当前设置，显示 ✔ Saved 提示 |
| **QUIT** | Exit / 退出程序 |

> Audio status shows live on the `AUDIO_QUERY` line: `♪ connecting...` / `♪ ready`
>
> 当前音频状态会实时显示在 `AUDIO_QUERY` 菜单行：`♪ connecting...` / `♪ ready`

---

## Environment Variables / 环境变量

```bash
MATRIXMIX_FPS=24                # Frame rate cap / 帧率上限
MATRIXMIX_SPEED=2               # Speed multiplier / 速度倍率
MATRIXMIX_INVERT=true           # Camera-level grayscale inversion / 摄像头级灰度反色
MATRIXMIX_CONTRAST=2            # Contrast 0-3 / 对比度 0-3
MATRIXMIX_EDGE=2                # Edge 0-3 / 轮廓 0-3
MATRIXMIX_AUDIO=1               # Enable audio engine / 启用音频引擎
MATRIXMIX_QUERY="lofi hip hop"  # Default audio search query / 默认音频查询词
```

---

## Architecture / 架构概览

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

- **Camera Manager**: enumerates `/dev/video*`, opens device and pushes frames to render loop / 枚举 `/dev/video*`，打开设备并推帧到渲染循环
- **Capture Pipeline**: `cap.read()` → resize to terminal grid → grayscale → per-column brightness energy / `cap.read()` → resize 到终端网格 → 灰度 → 每列亮度能量
- **Rain Engine**: per-column float heads with individual speed offset (0.6x–1.4x); brighter = longer trail, faster fall, denser spawn / 每列独立浮点头部 + 速度偏移（0.6x–1.4x）；亮度越高，拖尾越长、下落越快、生成越密
- **Audio Engine**: yt-dlp pulls live stream → ffmpeg decodes → audio energy mapped to global rain speed/spawn probability / yt-dlp 拉直播流 → ffmpeg 解码 → 音频能量映射为全局雨速/生成概率
- **Terminal I/O**: hidden cursor, ANSI true-color, dirty-rectangle render — only changed cells are rewritten to reduce flicker / 隐藏光标、ANSI 真彩色、脏矩形渲染，只重写变化单元格以降低闪烁

---

## Dependencies / 系统依赖

- Python >= 3.10
- OpenCV >= 5.0
- ffmpeg
- yt-dlp
- Terminal supporting ANSI true-color + UTF-8 / 支持 ANSI true-color + UTF-8 的终端

---

## Roadmap / 路线图

- [x] Terminal Matrix rain + camera brightness driving / 终端数字雨 + 摄像头亮度驱动
- [x] Two-layer brightness separation (trail attenuation + camera background) / 两层亮度分离（雨痕衰减 + 摄像头背景）
- [x] Online music playback with audio-energy-driven rain / 在线音乐播放，音频能量驱动雨流
- [x] Contrast / edge real-time adjustment menu / 对比度 / 边缘实时调节菜单
- [x] Radio presets + independent AUDIO / CAMERA switches / 电台预设 + 独立 AUDIO / CAMERA 开关
- [x] Vertical screen cover adaptation / 竖屏 cover 适配
- [ ] Screenshot save / 截图保存
- [ ] GIF / MP4 recording / 录制 GIF / MP4

---

## Related Projects / 相关项目

- [MatrixMix](https://github.com/ShallowWaterLab/MatrixMix) — Base charset and rendering core / 基础字符集与渲染核心
- [ShallowWaterLab](https://github.com/ShallowWaterLab/) — More experimental projects / 更多实验项目

---

## License / 开源协议

MIT
