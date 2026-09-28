"""F3009 wired register write (8-byte feature report id=7).

Frame layout (reverse-engineered from ShinetekTools.exe):
    07 FF FF <reg> <v0> <v1> <v2> <v3>

Usage:
    python f3009_write_reg.py 20 00        # reg=0x20 value=0
    python f3009_write_reg.py --seq        # scripted effect-switch test

Only lighting-related registers are touched. Recovery: re-run the official
driver or hold Fn+Esc (~5 s) on the keyboard for a factory reset.
"""
import sys
import time

import hid

VID, PID = 0x1A2C, 0x7F05
THROTTLE = 0.12  # the official driver enforces >=100 ms between writes


def open_dev():
    devs = [d for d in hid.enumerate(VID, PID)
            if d["usage_page"] == 0xFF01 and d["usage"] == 0x0001]
    if not devs:
        raise SystemExit("F3009 wired vendor collection (Col07) not found")
    dev = hid.device()
    dev.open_path(devs[0]["path"])
    return dev


def write_reg(dev, reg: int, v0=0, v1=0, v2=0, v3=0):
    frame = bytes([0x07, 0xFF, 0xFF, reg & 0xFF, v0 & 0xFF, v1 & 0xFF, v2 & 0xFF, v3 & 0xFF])
    n = dev.send_feature_report(frame)
    print(f"  -> wrote {frame.hex(' ')}  (returned {n})")
    time.sleep(THROTTLE)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    dev = open_dev()
    try:
        if len(sys.argv) >= 2 and not sys.argv[1].startswith("--"):
            nums = [int(a, 16) for a in sys.argv[1:]]
            print("frame = 07 ff ff " + " ".join(f"{n:02x}" for n in nums))
            write_reg(dev, *nums)
            print("done")
            return

        if len(sys.argv) >= 2 and sys.argv[1] == "--spdtest":
            print("=== speed byte test with BREATHING effect ===")
            write_reg(dev, 0x20, 0x02, 0x00, 0x00, 0x00)   # switch to breathing
            time.sleep(1)
            seq = [
                ((0x02, 0x02, 0x05, 0x00, 0x00), "d0=2  expect FAST breathing"),
                ((0x02, 0x00, 0x05, 0x00, 0x00), "d0=0  expect SLOW breathing"),
            ]
            for r in range(3):
                for vals, desc in seq:
                    f = " ".join(f"{b:02x}" for b in (0x07, 0xFF, 0xFF, *vals))
                    print(f"round {r + 1}: {desc}   frame = {f}")
                    write_reg(dev, *vals)
                    time.sleep(4)
            print("done (left at d0=0 slow)")
            return

        if len(sys.argv) >= 2 and sys.argv[1] == "--brtest":
            print("=== brightness byte test: watch for BRIGHT/DIM alternating ===")
            print("(reg 0x00 = parameters of effect 0 = the STEADY effect now active)")
            write_reg(dev, 0x20, 0x00, 0x00, 0x00, 0x00)   # make sure effect 0 is active
            time.sleep(1)
            seq = [
                ((0x00, 0x00, 0x05, 0x00, 0x00), "d1=5  expect BRIGHT"),
                ((0x00, 0x00, 0x00, 0x00, 0x00), "d1=0  expect OFF/DIM"),
            ]
            for r in range(3):
                for vals, desc in seq:
                    f = " ".join(f"{b:02x}" for b in (0x07, 0xFF, 0xFF, *vals))
                    print(f"round {r + 1}: {desc}   frame = {f}")
                    write_reg(dev, *vals)
                    time.sleep(3)
            print("done (left at d1=0)")
            return

        if len(sys.argv) >= 2 and sys.argv[1] == "--scan":
            steps = [
                ("effect=0, byte5=5  (brightness?)", (0x20, 0x00, 0x05, 0x00, 0x00)),
                ("effect=0, byte5=0", (0x20, 0x00, 0x00, 0x00, 0x00)),
                ("effect=0, byte6=5", (0x20, 0x00, 0x00, 0x05, 0x00)),
                ("effect=0, byte6=0", (0x20, 0x00, 0x00, 0x00, 0x00)),
                ("effect=0, byte7=5", (0x20, 0x00, 0x00, 0x00, 0x05)),
                ("effect=0, byte7=0", (0x20, 0x00, 0x00, 0x00, 0x00)),
                ("reg=0x00, d0=5  (per-effect table?)", (0x00, 0x05, 0x00, 0x00, 0x00)),
                ("reg=0x00, d0=0", (0x00, 0x00, 0x00, 0x00, 0x00)),
                ("effect=0 (final)", (0x20, 0x00, 0x00, 0x00, 0x00)),
            ]
            print("=== byte scan: watch for ANY brightness change ===")
            for i, (desc, args) in enumerate(steps, 1):
                f = " ".join(f"{b:02x}" for b in (0x07, 0xFF, 0xFF, *args))
                print(f"step {i}: {desc}")
                print(f"        frame = {f}")
                write_reg(dev, *args)
                time.sleep(3.5)
            print("scan done")
            return

        if len(sys.argv) >= 2 and sys.argv[1] == "--tour":
            steps = [
                ("effect 0 (常亮), brightness 5, speed 2", (0x20, 0x00, 0x05, 0x02, 0x00)),
                ("effect 2 (呼吸), brightness 5, speed 2", (0x20, 0x02, 0x05, 0x02, 0x00)),
                ("effect 4 (随波逐流), brightness 5, speed 2", (0x20, 0x04, 0x05, 0x02, 0x00)),
                ("effect 4, brightness 1 -> expect much DARKER", (0x20, 0x04, 0x01, 0x02, 0x00)),
                ("effect 4, brightness 5, speed 0 -> expect SLOWER", (0x20, 0x04, 0x05, 0x00, 0x00)),
                ("restore effect 4, brightness 5, speed 2", (0x20, 0x04, 0x05, 0x02, 0x00)),
            ]
            print("=== guided tour: watch the keyboard at each step ===")
            for i, (desc, args) in enumerate(steps, 1):
                f = " ".join(f"{b:02x}" for b in (0x07, 0xFF, 0xFF, *args))
                print(f"step {i}: {desc}")
                print(f"        frame = {f}")
                write_reg(dev, *args)
                time.sleep(4)
            print("tour done")
            return

        print("=== scripted effect-select test (watch the keyboard!) ===")
        print("step 1: expect STEADY (常亮)")
        write_reg(dev, 0x20, 0x00)
        time.sleep(3)
        print("step 2: expect BREATHING (呼吸)")
        write_reg(dev, 0x20, 0x02)
        time.sleep(3)
        print("step 3: expect NEON/flow (随波逐流, index 4)")
        write_reg(dev, 0x20, 0x04)
        time.sleep(3)
        print("step 4: back to STEADY (常亮)")
        write_reg(dev, 0x20, 0x00)
        print("done")
    finally:
        dev.close()


if __name__ == "__main__":
    main()
