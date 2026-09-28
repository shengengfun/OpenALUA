"""Does the F3009 firmware accept speed values above the official maximum of 2?

The official UI resource (`uires/xml/dlg_main.xml`) declares the speed slider as
`min=0 max=2`, and every captured frame has speed in 0..=2. That is what the
*UI* allows -- it says nothing about what the firmware does with a larger byte.

This script walks speed 0..=8 on the breathing effect, holding each value long
enough to judge the period by eye. Watch the keyboard and note which values
actually differ.

Usage:
    python tools/probe_speed_range.py              # 2.4G / dongle, if present
    python tools/probe_speed_range.py --wired      # force the USB wired path
    python tools/probe_speed_range.py --effect 13  # use 跑马灯效 instead
    python tools/probe_speed_range.py --hold 4     # seconds per step

Nothing here is destructive: it only writes the same lighting command the
official tool writes, with a different speed byte.
"""
import argparse
import sys
import time

import hid

WIRED_VID = 0x1A2C
WIRED_PIDS = (0x7F05, 0x7F07)
DONGLE_VID = 0x1A2C
DONGLE_PID = 0x7FFF
VENDOR_PAGE = 0xFF01
VENDOR_USAGE = 0x0001
# 4 bytes only — the 0xAA that follows is the command discriminator, NOT a
# fifth magic byte. Folding them into one constant is exactly what made the
# Rust port shift the payload and silently stop working.
MAGIC = bytes.fromhex("bbaa9988")
CMD_LIGHTING = 0xAA  # offset 5


def open_vendor(vid, pids):
    for pid in pids:
        for d in hid.enumerate(vid, pid):
            if d.get("usage_page") == VENDOR_PAGE and d.get("usage") == VENDOR_USAGE:
                dev = hid.device()
                dev.open_path(d["path"])
                return dev, pid
    return None, None


def wired_frame(effect, brightness, speed):
    return bytes([0x07, 0xFF, 0xFF, effect & 0xFF,
                  brightness & 0xFF, speed & 0xFF, 0, 0])


def dongle_frame(effect, brightness, speed):
    body = bytes([effect & 0xFF, brightness & 0xFF, speed & 0xFF, 0, 0])
    frame = bytes([0x00]) + MAGIC + bytes([CMD_LIGHTING]) + body
    return frame + bytes(65 - len(frame))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wired", action="store_true", help="use the USB feature-report path")
    ap.add_argument("--effect", type=int, default=2, help="effect index (default 2 = 呼吸)")
    ap.add_argument("--brightness", type=int, default=5)
    ap.add_argument("--hold", type=float, default=2.5, help="seconds per speed step")
    ap.add_argument("--from", dest="lo", type=int, default=0)
    ap.add_argument("--to", dest="hi", type=int, default=8)
    args = ap.parse_args()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.wired:
        dev, pid = open_vendor(WIRED_VID, WIRED_PIDS)
        label, build, send = "USB 有线", wired_frame, "feature"
        if not dev:
            raise SystemExit("找不到有线键盘（1A2C:7F05 / 1A2C:7F07）")
    else:
        dev, pid = open_vendor(DONGLE_VID, (DONGLE_PID,))
        label, build, send = "2.4G 接收器", dongle_frame, "output"
        if not dev:
            raise SystemExit("找不到 2.4G 接收器（1A2C:7FFF）—— 确认键盘在 2.4G 档")

    if args.wired:
        # official tool also pushes these four output reports on open
        for i in range(4):
            f = bytearray(64)
            f[0], f[1] = 0x05, i + 1
            dev.write(bytes(f))
        time.sleep(0.2)

    print(f"链路：{label} (pid={pid:#06x})   灯效 {args.effect}，亮度 {args.brightness}")
    print(f"每档停留 {args.hold}s，共 {args.hi - args.lo + 1} 档。盯着键盘看节奏变化。\n")

    try:
        for speed in range(args.lo, args.hi + 1):
            frame = build(args.effect, args.brightness, speed)
            n = dev.write(frame)
            head = " ".join(f"{b:02x}" for b in frame[:10])
            print(f"  速度 {speed:>2}  →  发送 {n:>2} 字节: {head} …")
            time.sleep(args.hold)
    finally:
        # leave the keyboard somewhere sane
        dev.write(build(args.effect, args.brightness, 2))
        dev.close()

    print("\n完成。请回答：哪几个速度值看起来真的不一样？"
          "（比如「0/1/2 三档都有差别，3 以后完全没反应」）")
    print("如果 3..8 和 2 看起来一模一样 —— 说明固件自己就把上限卡在 2 了。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
