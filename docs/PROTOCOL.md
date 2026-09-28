# AULA F3009 HID 协议（逆向文档）

本文档记录 AULA F3009 三模机械键盘在 **USB 有线模式**下的控制协议。
内容通过以下手段获得，并已在本机实测验证：

1. 对官方驱动 `ShinetekTools.exe` 做静态反汇编（IAT 调用点 + 帧构造分析）
2. 用 **frida** 挂钩官方进程的 `HidD_SetFeature` / `HidD_GetFeature` / `HidD_SetOutputReport` / `WriteFile`，
   捕获真实流量（脚本：`tools/capture_hid.py`，日志：`research/hid_capture*.log`）
3. 用自研脚本向键盘复放抓到的帧，逐项与键盘实际表现比对

> ⚠️ 非官方文档。厂商固件更新可能改变协议。请自行承担风险。
> 逆向仅针对自有硬件，目的是实现互操作性。

## 1. 设备识别

| 项目 | 值 |
| --- | --- |
| VID | `0x1A2C`（AULA / 东莞市索艾电子） |
| PID（有线） | `0x7F05`、`0x7F07` |
| PID（2.4G 接收器） | `0x7FFF` |
| 固件版本字段 | `bcdDevice = 0x0111` |
| 通信接口 | 接口 1（`MI_01`）的第 7 个集合 |
| 集合标识 | `usage_page = 0xFF01`，`usage = 0x0001` |
| HID 能力 | `FeatureReportByteLength = 8`，`Report ID = 7` |

同一接口下还有若干键盘/消费者/厂商集合（`0xFF00:0x0001`、`0x000C:0x0001` 等），
**只有上面这个集合响应控制命令**。

2.4G 接收器（`7FFF`）暴露的厂商集合只有 input/output report，没有 feature report，
因此当前版本不支持无线配置。

## 2. 控制帧

所有控制都通过 **8 字节 feature report（id = 7）** 下发：

```text
偏移  0    1    2    3        4           5       6    7
     0x07 0xFF 0xFF <效果>  <亮度>     <速度>   0x00 0x00
```

| 字段 | 取值范围 | 说明 |
| --- | --- | --- |
| `[0]` | 恒为 `0x07` | report id |
| `[1]` `[2]` | 恒为 `0xFF 0xFF` | 固定头 |
| `[3]` | `0..=19` | **效果序号**（**0-based**，见下表） |
| `[4]` | `0..=5` | **亮度**，`0` 即关灯 |
| `[5]` | `0..=2` | **速度** |
| `[6]` `[7]` | `0x00` | 官方软件始终写 0，含义未确认 |

写入该帧会**立即切换并应用**对应效果，无需额外的"提交"命令。

### 时序要求

官方驱动在两次写入之间强制 **≥ 100 ms** 间隔（反汇编可见 `cmp eax, 0x64` + `Sleep`）。
间隔过短会导致固件响应迟缓甚至暂时无响应。本项目的 `AulaDevice::send_frame` 已内置该节流。

### 效果序号表

序号就是官方 UI 下拉框里每一项的 `data` 属性，**从 0 开始**：

| # | 中文 | 英文（官方） | # | 中文 | 英文（官方） |
| --- | --- | --- | --- | --- | --- |
| **0** | **常亮** | Steady | 11 | 按键涟漪 | Ripples shining |
| **1** | **指点江山** | Gaming Special Key | 12 | 花开富贵 | Rich and honored |
| 2 | 呼吸 | Breathing | 13 | 跑马灯效 | Marquee effect |
| 3 | 随按随灭 | Press and destroy | 14 | 旋转风暴 | Rotating storm |
| 4 | 随波逐流 | Neon stream | 15 | 蛇形跑马 | Serpentine horse race |
| 5 | 流光模式 | Streamer | 16 | 繁星点点 | Stars twinkle |
| 6 | 流光溢彩 | Flowing light and color | 17 | 川流不息 | Retro snake |
| 7 | 滴水涟漪 | Dripping ripples | 18 | 斜拉变幻 | Diagonal transformation |
| 8 | 点彩夺目 | Brilliant point | 19 | 正弦光波 | Sine wave |
| 9 | 一触即发 | Flash away | | | |
| 10 | 踏雪无痕 | Shadow disappear | | | |

> **`0` 是常亮，不是 `1`。**
>
> 这里曾经弄错过一次：早期版本按"UI 行号 1-based"把常亮写成 `1`，
> 结果点"常亮"实际触发的是序号 `1` 的 **指点江山**（Gaming Special Key）——
> 只有游戏键那一片会亮。
>
> 硬证据有两条：
> 1. 官方安装目录 `uires/Translator/lang_cn.xml` 里效果顺序是
>    `Steady（常亮）→ Gaming Special Key（指点江山）→ Breathing（呼吸）→ …`；
> 2. 在官方软件里选常亮时，抓到的帧是 `07 FF FF 00 <亮度> 00 00 00`。
>
> 官方 UI 的下拉框里 `data="1"` 这一行**被注释掉了**（见 `uires/xml/dlg_main.xml`），
> 但固件完全接受这个值——MiaKeyDrv 把它作为"官方隐藏功能"放了出来。

### 示例

```text
07 FF FF 02 05 02 00 00     呼吸，最亮，最快
07 FF FF 05 05 02 00 00     流光模式，最亮，最快
07 FF FF 00 05 00 00 00     常亮，最亮（注意是 00，不是 01）
07 FF FF 00 00 00 00 00     常亮，亮度 0 → 关灯
07 FF FF 01 05 00 00 00     指点江山（只有游戏键亮）
```

## 3. 官方软件的初始化序列

打开官方工具时可观察到：

```text
output report (64 B) × 4 :  05 01 00… / 05 02 00… / 05 03 00… / 05 04 00…
feature 写 + 读          :  07 F1 00 00 00 00 00 00  →  HidD_GetFeature(7)
feature 写               :  07 FF FF 00 05 00 00 00      （reg=0，疑似全局/默认亮度）
```

- `05 01..04` 是通过 output report 发出的初始化序列（本项目的 `init()` 会在连接后复放，失败不致命）。
- `07 F1 …` 是读取设备信息的命令。

## 4. 关于"读取"

读路径为：先 `HidD_SetFeature(07 F1 …)`，再 `HidD_GetFeature(7)` 取回，官方代码取 `buf[1] << 8 | buf[2]`。

但实测中 **`GetFeature(7)` 恒返回 `07 02 00 00 00 00 00 00`**，
且在官方软件里切换灯效、改动任何设置后都不会变化。

结论：**键盘基本不回读配置**。官方软件自身把状态保存在安装目录的
`ledeffect.xml` 里（`<effect sel="N">`，`sel` 同样是 1-based 行号，
每项 `<item speed brightness deriction selection/>`）。本项目采用同样的策略：
状态由应用侧维护。

## 5. 键盘本地行为（与协议无关，便于对照）

- **M1 / M2** 键只在**无线模式**下有效；有线模式下不产生任何 HID 事件
- **办公模式**下 M1/M2 = 上一曲 / 下一曲（消费者页 `0x0C`，上报 `01 B5` / `01 B6`）
- **游戏模式**下 M1/M2 = 自定义灯光
- **长按多功能旋钮** = 切换 游戏 / 办公 模式
- 旋钮旋转 = 音量加减（`01 E9` / `01 EA`），按下 = 播放/暂停（`01 CD`）
- F3009 **没有侧灯**（官方 UI 中侧灯页被 `visible="0"` 隐藏），也没有方向选项

## 6. 已知未解

- `[6] [7]` 两个字节的确切含义
- 关灯以外的"灯效电源"开关是否存在独立寄存器
- 休眠时间 / 轮询率 / 按键防抖（官方软件未提供；同平台 F2087Pro 驱动存在
  `sleep_time`、`key_respondtime` 配置项，提示硬件可能支持，待定位寄存器）
- 宏录制与按键重映射的写入路径（需抓取一次官方"宏录制"操作）
- 2.4G 模式协议（无 feature report，疑似走 65 字节 output report）
- F2087Pro（`0C45:800A`，不同 MCU 厂商）协议

## 7. 复现方法

```bash
# 1) 抓取官方软件真实流量（无需安装驱动，管理员权限可选）
python tools/capture_hid.py d:/out/hid.log 120

# 2) 复放单帧验证
python tools/f3009_write_reg.py 02 05 02 00 00

# 3) 枚举设备 / 只读探测
python tools/hid_enum.py
python tools/hid_probe.py
```

## 8. 官方界面资源里的硬证据

官方软件用 SOUI 框架，界面定义就在安装目录 `uires/` 下，而且是**明文 XML**。
滑块的量程、下拉框每个选项的序号都能直接读出来，不用猜。

### 滑块量程（`uires/xml/dlg_main.xml`）

| 控件 | min | max | 说明 |
| --- | --- | --- | --- |
| `bar_general_speed_*` | 0 | 2 | **速度，3 档** |
| `bar_const_brightness_*` | 0 | 5 | 主灯亮度，6 档 |
| `bar_side_brightness` | 0 | 7 | 侧灯亮度（F3009 没有侧灯） |

所以 `07 FF FF` 帧里亮度 `0..5`、速度 `0..2` 的量程是硬件侧就定死的，
**主机端没有"更多档位"可以挖**。

### 速度滑块是按灯效分页显示的

`dlg_main.xml` 里 `tab_color_effect` 有 4 个 page，选到不同灯效会切到不同 page：

| page | 内容 |
| --- | --- |
| 0 | Speed + Brightness + **Direction（左/右）** |
| 1 | Speed + Brightness |
| 2 | **只有 Brightness** —— 这类灯效没有速度概念 |
| 3 | Speed（尺寸写成 `0,0`，等于隐藏）+ Brightness + **Loader M1/M2/M3** |

哪个灯效落到哪个 page 是代码里决定的，XML 里看不到。
但 `ledeffect.xml` 里每条灯效的 `speed` 值能当旁证：默认是 2，
而部分条目写的是 0，对应的正是"没有速度滑块"的那类灯效。

> 对照实现：MiaKeyDrv 不做这个限制，**每条灯效都能调速度**
> （官方对部分灯效藏起滑块，导致可调项反而更少）。

### 别的线索

- `lang_cn.xml` 里还有 `Area1..Area6`（区域 1–6）、`P1/P2/P3`（模式一/二/三）、
  `Side LED`（侧灯，F3009 对应页面被 `visible="0"` 隐藏）
- `uires/xml/page_disk.xml` 是个"我的网盘"界面，和键盘毫无关系 ——
  SOUI 自带的示例代码没删干净，读资源文件时别被它带偏
- `uires/xml/macro.xml` 是宏编辑页的界面定义，可以做 UI 参照


依赖：`pip install hidapi frida`（见 `tools/` 目录下各脚本头部说明）。
