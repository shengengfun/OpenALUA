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

## 9. 2.4G 无线模式

### 之前写错了

早期版本这里是「2.4G 无 feature report，疑似走 65 字节 output report，待逆向」。
前半句对、方向错了——**它确实没有 feature report，但有一条 65 字节的 output 通道，
而且完全可用**。2026-09 实测已在 2.4G 下成功切换灯效。

### 硬件事实（`hid_caps.py`）

```
1A2C:7FFF  iface=2  usage_page=0xFF01 usage=0x0001
  report len: input=65  output=65  feature=0      ← 关键：feature = 0
```

接收器同时暴露 `MI_01 Col04`（`0xFF01:0xFF01`，input=4）和 `MI_02`（`0xFF01:0x0001`）。
真正能用的是 **`MI_02`**，跟有线模式的控制集合（`0xFF01:0x0001`）对齐。

### 信封格式

```text
有线 (8B feature report):   07 FF FF <e> <b> <s> 00 00
2.4G (65B output report):   00 BB AA 99 88 AA <e> <b> <s> 00 00  然后补零到 65
                            └┬┘ └────┬────┘
                          report id  魔数（第 5 字节 0xAA 是命令判别字节）
```

> 注意：早先有一处容易搞混——**命令判别字节在偏移 [5]，紧跟魔数**，
> 灯效/亮度/速度在 [6]/[7]/[8]。别把 [6] 当成判别字节。

实测对照（官方软件操作 → 抓到的帧）：

| 官方 UI 选择 | 2.4G 帧 `[5]` 起 | 有线帧 |
| --- | --- | --- |
| 常亮（第 0 行） | `aa 00 05 00` | `07 FF FF 00 05 00 00 00` |
| 呼吸（第 1 行） | `aa 02 05 02` | `07 FF FF 02 05 02 00 00` |
| 正弦光波（第 18 行） | `aa 13 05 02` | `07 FF FF 13 05 02 00 00` |

### 官方代码自己算的序号

反汇编 `ShinetekTools.exe`（两个通道在同一个函数里分叉）可以看到官方**亲手**做这个变换：

```asm
0x0042155c  mov  byte ptr [ebp - 9], al   ; al = 下拉框行号
0x0042155f  mov  cl, 1
0x00421561  test al, al
0x00421563  je   0x0042156a                ; 行号 0 → 保持 0
0x00421565  add  al, cl                    ; 其他行号 → +1
0x00421567  mov  byte ptr [ebp - 9], al
```

即 `线上序号 = 行号 + 1（行号 0 除外）`——这就是第 2 节里「常亮 = 0」的机器码级证据。

### 信封魔数的三个构造点

`BB AA 99 88` 在 `.text` 里出现 3 次，都是现场拼装的：

| 虚拟地址 | `[5]` 判别字节 | 用途 |
| --- | --- | --- |
| `0x00421423` | `0xAA` + 载荷全 `0xAA` | 官方在灯光命令前后发的形态之一 |
| `0x0042146d` | `0x00` + 载荷全 0 | 形态之二 |
| `0x004215a6` | `0xAA`（载荷 = 效果/亮度/速度） | **灯光命令**，与抓包一致 |

前两个形态夹着 `Sleep(1500)`，怀疑是进出某个模式的握手，尚未确认，**不要贸然发**。

## 10. 电量：拿不到（有据可查的负面结论）

官方软件在 2.4G 下不显示电量，不是 UI 藏了，而是**协议里就没有**：

1. **厂商通道是只写的**
   - `MI_02` 声明了 `input=65`，但 **150 秒被动监听 0 份报告**（期间对键盘断电重启过）
   - 11 条定向查询命令（`probe_24g_status.py`）**全部 0 应答**
2. **官方代码里没有查询电量的逻辑**
   - 反汇编三个信封构造点，只有灯光和那两个握手形态，没有任何状态查询
3. **唯一活着的输入管道是消费者控制集合**（`usage_page=0x000C`），只报旋钮事件 `03 00 00`
4. 两个键盘集合（`iface=0` / `iface=1`，`usage_page=0x0001 usage=0x0006`）
   在 2.4G 下**用户态读不了**（`read error`，Windows 权限）

结论：**在 USB / 2.4G 通道下无法读取电量**。要么厂商固件另有未公开的查询命令（需更大范围探测，
有风险且收益不确定），要么这条路本来就不存在。

> 欢迎有人带着更靠谱的思路来推翻这一节——但请带上复现步骤。
>
> **2026-09-29 更新**：蓝牙模式下**能**拿到电量，走的是操作系统缓存，见 §11。
> §10 的结论对 USB / 2.4G 仍然成立。



依赖：`pip install hidapi frida`（见 `tools/` 目录下各脚本头部说明）。


## 11. 蓝牙模式：电量能拿到，但是从系统里拿

§10 的负面结论只适用于**厂商通道**。键盘的蓝牙（BLE HID）走的是**标准协议栈**，
里面本来就有电量服务。

### 11.1 键盘确实实现了标准电量服务

蓝牙下键盘的 HID 接口是 HOG（HID over GATT），枚举出来是：

```
VID:PID   usage_page usage  path
046D:B34C 0x0001   0x0006  HID#{00001812-...}_Dev_VID&02046d_PID&b34c_REV&0014_<ADDR>&Col01  (键盘)
046D:B34C 0x000c   0x0001  ...Col02  (消费者控制)
046D:B34C 0x0001   0x0002  ...Col03  (鼠标)
```

两点差异要注意：

- **VID/PID 完全不同**（`046D:B34C`，不是有线/2.4G 那套 `1A2C:xxxx`）——
  按 VID 白名单认键盘的方案在蓝牙下会失效
- **没有 `0xFF01` 厂商集合**，只有键盘/鼠标/多媒体三个标准集合
  → 蓝牙模式下**只能读状态，控不了灯**，这一点是协议层面的，不是权限问题

设备节点里同时枚举出了标准的 GATT 服务：

| 服务 | UUID | 说明 |
|---|---|---|
| Generic Access | `0x1800` | |
| Generic Attribute | `0x1801` | |
| Device Information | `0x180A` | |
| **Battery Service** | **`0x180F`** | ← 电量就在这 |
| HID Service | `0x1812` | 键盘数据 |

### 11.2 电量值存在哪

Windows 拿到 BLE 电量后，把它缓存在蓝牙设备节点的属性里——**这就是设置页
「蓝牙和其他设备」显示的那个百分比**。属性和类型：

| 属性 | 类型 | 含义 |
|---|---|---|
| `{104EA319-6EE2-4701-BD47-8DDBF425BBE5}, 2` | `DEVPROP_TYPE_BYTE` | 电量百分比（0–100） |
| `{104EA319-6EE2-4701-BD47-8DDBF425BBE5}, 3` | `DEVPROP_TYPE_BYTE` | 观测为 bool：未充电时为 `0`；语义未验证 |

一条命令就能看到：

```powershell
Get-PnpDeviceProperty -InstanceId 'BTHLE\DEV_<ADDR>\...' `
  -KeyName '{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2'
```

### 11.3 怎么读（不依赖任何第三方库）

用 CfgMgr32 三个调用就够，MiaKeyDrv 的实现见 `src-tauri/src/bt.rs`：

1. `CM_Get_Device_ID_List_SizeW` / `CM_Get_Device_ID_ListW`，
   filter = `"BTHLE"`、flags = `CM_GETIDLIST_FILTER_ENUMERATOR (0x1)`
   → 拿到所有 BLE 设备实例 ID（MULTI_SZ，注意按 NUL 切）
2. `CM_Locate_DevNodeW` 把实例 ID 换成 `DEVINST`
3. `CM_Get_DevNode_PropertyW` 读上表那两个 `DEVPKEY`。
   **第一次调用故意用空 buffer**取 size（返回 `CR_BUFFER_SMALL` 是正常的），
   第二次再真正取数据；没有 `2` 号属性的节点直接跳过，继续找下一个

### 11.4 两个坑

- **别硬编码蓝牙地址**。同一个键盘重新配对后地址会变，实测从
  `000029f00000` 变成了 `01e0889a0000`。所以要枚举 + 找带电池属性的节点，
  不能按地址/实例 ID 写死
- **别用「接收器插着」推断键盘在 2.4G**。接收器只要插在 USB 上就会被枚举，
  跟键盘挂在哪条链路无关；反过来，键盘切到蓝牙后，旧的 BLE 节点会被移除、
  新的（新地址）才会出现，中间有几秒**什么都读不到**，这是正常现象不是 bug

### 11.5 复现步骤

1. 键盘切到蓝牙档，与 Windows 配对，确认「蓝牙和其他设备」列表里键盘那行**显示出百分比**
   （不显示就说明这台键盘的固件没实现 `0x180F`，那系统也拿不到，无需继续）
2. `Get-PnpDevice -InstanceId 'BTHLE\*'` 找到 `BTHLE\DEV_<ADDR>\...` 节点
3. 按 §11.2 的命令读 `{104EA319-...} 2`，应当得到和设置页一致的数值

`tools/probe_bt_battery.ps1` 会把上面几步连同注册表一起 dump 出来。
