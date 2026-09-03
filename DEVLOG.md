# MatrixVision 开发日志

## v0.2.0

### 新增
- 终端数字雨 + 摄像头亮度实时驱动
- 两层亮度分离：雨痕衰减层 + 摄像头背景层
- 反色固定开启（摄像头级灰度反转）
- 对比度调节：CLAHE，支持 0-3 档位
- 轮廓调节：Sobel 边缘，支持 0-3 档位
- 设置页菜单：CONTRAST / EDGE / AUDIO / CAMERA / AUDIO_QUERY / SAVE / QUIT
- 环境变量支持：MATRIXMIX_FPS、MATRIXMIX_SPEED、MATRIXMIX_INVERT、MATRIXMIX_CONTRAST、MATRIXMIX_EDGE、MATRIXMIX_AUDIO、MATRIXMIX_QUERY
- 启动时整屏预填充随机低亮度字符，避免黑屏
- 背景字符在亮度变化时随机换字，静止时稳定
- 自动备份到 `src/backups/`（最多 20 个）
- 在线音乐播放：yt-dlp + ffmpeg + ffplay，音频能量驱动雨流速度/拖尾/生成概率
- 设置页 AUDIO 开关：ON/OFF，关闭时停止音频并停止驱动
- 设置页 CAMERA 开关：ON/OFF，关闭时停止摄像头采集，数字雨动画继续运行
- 设置页 AUDIO_QUERY 预设电台：DEFAULT / LOFI 1 / JAZZ / AMBIENT / SYNTH / PIANO，左右键切换
- 音频状态实时显示在菜单 AUDIO_QUERY 行：♪ connecting... / ♪ ready
- 空格和回车键均可用于菜单确认

### 修复
- 修复启动黑屏：预跑填充 + 启动提示
- 修复雨头亮度被摄像头压制：改用 max() 混合
- 修复摄像头背景太暗：提升摄像头权重至 0.7
- 修复摄像头背景带拖影：两层亮度分离，摄像头层直接跟踪无衰减
- 修复画面比例：cover 裁剪 + cell_aspect=1.2 保守补偿
- 修复方向键误触设置面板：ESC 序列解析逻辑修正
- 修复方向键误触：ESC 序列解析修正
- 修复关闭 CAMERA 后数字雨消失：摄像头层关闭后继续纯雨滴动画
- 修复切换电台后音频状态显示滞后：后台线程事件通知主循环即时刷新
- 修复切换电台后回音/多进程残留：序列号校验 + 切换前停止旧引擎

### 变更
- 字符集保持片假名 + ASCII，与 MatrixMix 一致
- 设置页保存后显示绿色“✔ Saved”提示 1.5 秒自动消失
- 设置页顶部显示“MatrixVision v0.2.0”
- 统一快捷键入口：SAVE/QUIT 移至菜单，不再独立快捷键触发
- 对比度和轮廓独立调节，各支持 0-3 档

### 待实现
- 截图保存
- 录制 GIF/MP4
