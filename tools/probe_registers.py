"""Guided register probe for the AULA F3009.

The official tool only ever uses:

    07 FF FF <effect> <brightness> <speed> 00 00      main lighting
    07 F1 00 00 00 00 00 00                           read device info

and writes config blobs (ledeffect.xml / macro.xml / record.xml) through the
HID output pipe. There is **no** register for sleep timeout, polling rate or
debounce anywhere in the official software (verified by scanning every string
in ShinetekTools.exe and uires/Translator/*.xml).

This script pokes the neighbouring command space to find out whether the
firmware implements any of them anyway. It is deliberately conservative:

  * one frame per step, throttled to the vendor's 110 ms minimum
  * every step is announced on stdout before it is sent
  * --restore always re-sends a known-good lighting frame afterwards
  * the candidate list is small and ordered by plausibility

Run it only with the keyboard in front of you, and watch the LEDs: a change in
behaviour (dimming, blinking, going dark) is the signal we are looking for.

    python tools/probe_registers.py --list
    python tools/probe_registers.py --try 1          # one candidate
    python tools/probe_registers.py --sweep 2        # byte 2 over 0x00..0x0f
"""
import sys
import time

import hidapi

VID = 0x1A2C
WIRED_PIDS = (0x7F05, 0x7F07)
CTRL_USAGE_PAGE = 0xFF01
CTRL_USAGE = 0x0001
THROTTLE = 0.12


def open_ctrl():
    for d in hidapi.enumerate(vendor_id=VID):
        if d.product_id not in WIRED_PIDS:
            continue
        if d.usage_page != CTRL_USAGE_PAGE or d.usage != CTRL_USAGE:
            continue
        return hidapi.Device(path=d.path, blocking=True)
    raise SystemExit("no wired F3009 control collection found — plug in the USB cable")


def send(dev, frame):
    assert len(frame) == 8, "control frames are exactly 8 bytes"
    hexs = " ".join(f"{b:02x}" for b in frame)
    print(f"  -> {hexs}", flush=True)
    dev.send_feature_report(frame)
    time.sleep(THROTTLE)


def restore(dev):
    """Known-good: 常亮, full brightness (effect index 0 since 2026-09)."""
    print("[restore] 07 ff ff 00 05 00 00 00")
    send(dev, [0x07, 0xFF, 0xFF, 0x00, 0x05, 0x00, 0x00, 0x00])


# (label, byte1, byte2, bytes[3:8]) — byte1/byte2 are the command selector
CANDIDATES = [
    ("info read (known good)", 0xF1, 0x00, [0] * 5),
    ("lighting (known good)", 0xFF, 0xFF, [0x00, 0x05, 0x00, 0x00, 0x00]),
    ("cmd f0 sub 0", 0xF0, 0x00, [0] * 5),
    ("cmd f0 sub 1 (sleep?)", 0xF0, 0x01, [0x03, 0, 0, 0, 0]),
    ("cmd f2 sub 0", 0xF2, 0x00, [0] * 5),
    ("cmd f2 sub 1 (poll?)", 0xF2, 0x01, [0x01, 0, 0, 0, 0]),
    ("cmd f3 sub 0", 0xF3, 0x00, [0] * 5),
    ("cmd fe sub 0", 0xFE, 0x00, [0] * 5),
    ("cmd fd sub 0", 0xFD, 0x00, [0] * 5),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]

    if not args or "--list" in args:
        for i, (label, b1, b2, rest) in enumerate(CANDIDATES):
            frame = " ".join(f"{b:02x}" for b in [0x07, b1, b2, *rest])
            print(f"{i:2d}  {label:26s}  {frame}")
        print("\n--try N / --sweep N / --restore")
        return

    dev = open_ctrl()

    if "--restore" in args:
        restore(dev)
        return

    if "--try" in args:
        idx = int(args[args.index("--try") + 1])
        label, b1, b2, rest = CANDIDATES[idx]
        print(f"[try] {label}")
        send(dev, [0x07, b1, b2, *rest])
        print("[done] watch the keyboard, then re-run with --restore")
        return

    if "--sweep" in args:
        which = int(args[args.index("--sweep") + 1])
        for v in range(0x00, 0x10):
            print(f"[sweep] byte{which} = {v:02x}")
            rest = [0] * 5
            rest[which - 3] = v
            send(dev, [0x07, 0xFF, 0xFF, *rest])
            time.sleep(0.6)
        restore(dev)
        print("[done] note which value changed the LED behaviour, then --restore")
        return

    print("nothing to do; see --list")


if __name__ == "__main__":
    main()
