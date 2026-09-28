# research/ — 分析产物

本目录只保存**纯文本**的分析结果，方便复现与交叉验证。
厂商的安装包、驱动、以及从里面提取出来的文件**都不在这里**（见 `.gitignore`），
它们只在本地用于分析，不随仓库分发。

| 文件 | 说明 |
| --- | --- |
| `hid_capture.log` | 第一次抓包：官方软件切换到 呼吸 / 随按随灭 / 随波逐流，含亮度与速度全程扫描 |
| `capture_steady_macro.log` | 第二次抓包：宏录制与改键全过程，含官方下发的完整 XML |
| `capture_v2.log` | 第三次抓包：灯光页拖亮度（`07 FF FF 00 <亮度> …`） |
| `hid_capture2.log` | 早期较短的一次抓包，仅含初始化序列 |
| `decoded_xml.txt` | `analyze_capture.py --xml` 的输出，宏/配置 XML 全文 |
| `hidden_opts.txt` | `scan_hidden_opts.py` 的输出，官方软件里所有可疑关键字的命中情况 |
| `dump_fn.txt`、`dump_va*.txt` | 对官方 EXE 的反汇编摘录 |
| `hidcall_xref.txt`、`hidcall_callers.txt` | HID 调用点的交叉引用 |
| `swift_syms.txt` | macOS 版驱动里的符号 |

## 重新生成

```bash
python tools/analyze_capture.py research/capture_v2.log --frames
python tools/analyze_capture.py research/capture_steady_macro.log --xml
python tools/scan_hidden_opts.py "C:\Program Files (x86)\AULA"
```

## 本地需要自备的（不上传）

为了复现抓包，你需要在**自己机器上**安装官方驱动，然后用 `tools/capture_hid.py` 挂钩：

- `ShinetekTools.exe`（F3009 官方驱动，安装目录一般含 `ledeffect.xml` / `macro.xml` / `record.xml`）
- F2087Pro 的 `DeviceDriver.exe`（不同 MCU，协议尚未逆向）

本仓库不提供这些文件的下载地址，也不包含它们。
