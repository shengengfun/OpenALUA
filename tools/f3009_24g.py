"""Control the F3009 over the 2.4 GHz dongle.

Wired mode uses an 8-byte feature report:   07 FF FF <e> <b> <s> 00 00
2.4G mode uses a 65-byte output report:      00 BB AA 99 88 AA <e> <b> <s> 00 00 + 补零

`BB AA 99 88` 是 4 字节魔数，紧跟的 `AA` 才是命令判别字节（偏移 [5]），
灯效/亮度/速度在 [6]/[7]/[8]。两者别合并成一个常量 —— 合并过一次，
结果 Rust 移植版多写了一个 AA，整个载荷右移，灯效命令静默失效。

Usage:
    python tools/f3009_24g.py 0 5 0            # 常亮 / 最亮
    python tools/f3009_24g.py 2 5 2            # 呼吸 / 最亮 / 最快
    python tools/f3009_24g.py --tour           # 依次点亮几个效果
"""
import sys
import time

import hid

VID = 0x1A2C
PID = 0x7FFF
VENDOR_PAGE = 0xFF01
MAGIC = bytes.fromhex("bbaa9988")  # 4 字节
CMD_LIGHTING = 0xAA              # 偏移 [5]

TOUR = [
    (0, 5, 0, "常亮 全亮"),
    (2, 5, 2, "呼吸"),
    (5, 5, 2, "流光模式"),
    (19, 5, 2, "正弦光波"),
    (0, 5, 0, "回常亮"),
]


def open_vendor():
    for d in hid.enumerate(VID, PID):
        if d.get("usage_page") == VENDOR_PAGE and d.get("usage") == 0x0001:
            dev = hid.device()
            dev.open_path(d["path"])
            return dev
    raise SystemExit("没找到厂商集合 —— 确认键盘在 2.4G 模式")


def frame(effect, brightness, speed):
    body = bytes([effect & 0xFF, brightness & 0xFF, speed & 0xFF, 0, 0])
    f = bytes([0x00]) + MAGIC + bytes([CMD_LIGHTING]) + body
    return f + bytes(65 - len(f))


def send(dev, effect, brightness, speed):
    f = frame(effect, brightness, speed)
    n = dev.write(f)
    print(f"  已发送 {n} 字节: {' '.join(f'{b:02x}' for b in f[:12])} …"
          f"   效果={effect} 亮度={brightness} 速度={speed}")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    dev = open_vendor()
    try:
        if "--tour" in sys.argv:
            for e, b, s, label in TOUR:
                print(f"→ {label}")
                send(dev, e, b, s)
                time.sleep(2.5)
        else:
            nums = [a for a in sys.argv[1:] if not a.startswith("--")]
            if len(nums) < 3:
                print(__doc__)
                return 2
            send(dev, int(nums[0]), int(nums[1]), int(nums[2]))
    finally:
        dev.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
