# OpenALUA

> AULA（狼蛛）F3009 / F2087Pro 键盘的 **HID 协议逆向工程**项目。
>
> 这里只有分析、脚本、抓包与结论 —— 不含任何厂商二进制。
> 用这些结论做出来的成品 App 在姊妹项目 **[MiaKeyDrv](https://github.com/shengengfun/MiaKeyDrv)**。

## 一句话结论

官方驱动的全部控制能力都在一条 **8 字节 HID feature report** 上（report id = 7）：

```text
07 FF FF <效果序号> <亮度> <速度> <保留> <保留>
```

- 效果序号 **0 起**，`0` = 常亮，`1` = 指点江山，`2` = 呼吸 … `19` = 正弦光波
- 亮度 `0..5`（**0 即关灯**），速度 `0..2`
- 换灯效、拖亮度、拖速度，官方软件发的就是这一条，没有别的东西

完整结论（初始化序列、读写路径、宏/改键 XML、键盘本地行为、未知项清单、复现步骤）
见 **[docs/PROTOCOL.md](docs/PROTOCOL.md)**。

## 几个值得单独说的发现

### 常亮不是 1，是 0

官方安装目录下 `uires/Translator/lang_cn.xml` 里的效果顺序是：

```
Steady（常亮）→ Gaming Special Key（指点江山）→ Breathing（呼吸）→ …
```

也就是说协议里 `0 = 常亮`、`1 = 指点江山`，UI 行号与 `data` 属性并不是一回事。
按行号发 `1` 当作常亮，实际点亮的是「指点江山」——**只有游戏键那一片会亮**。
这个坑在 MiaKeyDrv 里已经修掉，并在 `protocol.rs` 留了回归断言。

### 宏和改键是 XML，不是二进制

官方软件在写宏/改键时，通过 output report 一次性把整份 XML 推给键盘：

```xml
<?xml version="1.0"?>
<record code="70004" play="2" type="0" repeat="1" name="A" group="Group 0">
        <item code="70004" state="1" delay="110" name="A" />
        <item code="70004" state="0" delay="264" name="A" />
        <item code="70005" state="1" delay="93"  name="B" />
        ...
</record>
<record code="7003a" play="1" type="1" repeat="1" name="F1" group="Q">
        <item code="70014" state="0" delay="0" name="" />
</record>
```

- `code` = `0x70000 | HID 用途码`，例如 `458756 = 0x70004 = A`、`458810 = 0x7003A = F1`
- `state` = 按下(1)/抬起(0)，`delay` = 距上一事件的毫秒数
- `type` = 绑定类型（0 宏 / 1 单键 / 2 媒体键 / 3 功能键），`play` = 播放模式
- `<config type="0..3" …>` 是 4 组配置档，`skcode` 是这套配置绑定的物理键

### 休眠时间 / 回报率 / 去抖：官方真的没有

对 `ShinetekTools.exe` 与全部附属 DLL 做了关键字扫描（`sleep` / `poll` / `debounce` /
`休眠` / `回报率` / `去抖` …），命中的全是 Windows 样板字符串，
`lang_cn.xml` 里也没有任何对应条目 —— **官方软件和对外命令表里都不存在这些设置**。

MiaKeyDrv 的做法：

- 能靠主机侧实现的就自己实现（空闲熄灯、保持唤醒）
- 回报率改为**实测**（直接读键盘输入管道）
- 剩下的需要寄存器探测（有风险，单独工具，见下）

## 工具

| 脚本 | 作用 |
| --- | --- |
| `tools/capture_hid.py` | frida 挂钩 `HidD_SetFeature` / `HidD_GetFeature` / `WriteFile`，抓官方软件真实流量 |
| `tools/analyze_capture.py` | 把抓包日志解码成控制帧序列、output report 直方图、重组的 XML |
| `tools/scan_hidden_opts.py` | 扫描安装目录与二进制，找隐藏选项关键字 |
| `tools/f3009_write_reg.py` | 单帧复放 / 灯效巡检 / 亮度与速度对照测试 |
| `tools/hid_enum.py`、`tools/hid_probe.py` | 只读枚举与探测 |
| `tools/extract_layout.py` | 从官方 `positions.xml` 生成 87 键坐标表 |

### 复现一次抓包

```bash
# 1) 关掉其它占用键盘的程序，然后拉起官方软件并抓 7 分钟
python tools/capture_hid.py research/capture.log 420

# 2) 窗口期内操作官方软件：切灯效 / 拖亮度 / 存一个宏

# 3) 解码
python tools/analyze_capture.py research/capture.log --frames
python tools/analyze_capture.py research/capture.log --xml
```

## 目录

```
docs/PROTOCOL.md        完整协议文档（唯一权威来源）
tools/                  逆向与验证脚本
research/               抓包日志、反汇编文本、扫描结果
```

> `research/` 里**不含**厂商安装包、驱动与提取物 —— 那些只在本机用于分析，已在 `.gitignore` 中排除。

## 已知未解

- `07 FF FF` 帧里 `[6] [7]` 两个字节的确切含义
- 除「亮度 0」之外，是否存在独立的灯效电源开关寄存器
- 2.4G 模式协议（无 feature report，疑似走 65 字节 output report）
- F2087Pro（`0C45:800A`，不同 MCU 厂商）协议
- `05 01 00 10 / 20 / 40` 这几帧的用途（写宏后出现，疑似指示灯心跳）

## 免责声明

本项目仅出于**互操作性研究**目的，对本机自有硬件做被动抓包与协议分析。
仓库内不包含、不分发任何厂商二进制或反编译产物。与东莞市索艾电子科技有限公司无关联。

## 致谢与贡献者

- 上游 / 灵感：AULA 官方 ShinetekTools（协议行为参考）
- [shengengfun](https://github.com/shengengfun) — 项目发起与硬件实测
- **DeepSeek** — AI 协作（逆向分析、协议推理、脚本实现）
- **GitHub Copilot** — AI 协作

## 许可

MIT

