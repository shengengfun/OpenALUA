"""F3009 read-frame position sweep.

The write frame layout is 07 FF FF idx d0 d1 d2 00 (idx at byte 3).
The read frame seen in the driver is 07 F1 00 00 00 00 00 00.
Here we sweep the selector byte through positions 2/3/4 of the read frame
and report any response that differs from the idle baseline.
"""
import sys
import time

import hid

VID, PID = 0x1A2C, 0x7F05
THROTTLE = 0.11


def send_get(dev, frame: bytes) -> bytes:
    dev.send_feature_report(frame)
    time.sleep(THROTTLE)
    return bytes(dev.get_feature_report(7, 8))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    devs = [d for d in hid.enumerate(VID, PID) if d["usage_page"] == 0xFF01 and d["usage"] == 0x0001]
    if not devs:
        print("Col07 not found")
        return
    dev = hid.device()
    dev.open_path(devs[0]["path"])
    try:
        baseline = bytes(dev.get_feature_report(7, 8))
        print(f"baseline          {baseline.hex(' ')}")
        for pos in (2, 3, 4):
            for val in list(range(0, 12)) + [0x10, 0x20, 0xFF]:
                frame = bytearray([7, 0xF1, 0, 0, 0, 0, 0, 0])
                frame[pos] = val
                resp = send_get(dev, bytes(frame))
                tag = "" if resp == baseline else "   <== DIFF"
                print(f"read pos={pos} val=0x{val:02x}  {resp.hex(' ')}{tag}")
            time.sleep(0.2)
    finally:
        dev.close()


if __name__ == "__main__":
    main()
