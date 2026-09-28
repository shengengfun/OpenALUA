"""F3009 wired register read probe.

Sends the driver's own read frame (07 F1 idx ...) via feature report, then
reads back report 7. Dumps how the response varies with idx.

Safety: this exercises the *read* command path used by the official driver;
it does not modify settings.
"""
import sys
import time

import hid

VID, PID = 0x1A2C, 0x7F05
THROTTLE = 0.12  # official driver throttles writes to >=100 ms


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    devs = [d for d in hid.enumerate(VID, PID) if d["usage_page"] == 0xFF01 and d["usage"] == 0x0001]
    if not devs:
        print("Col07 not found")
        return
    dev = hid.device()
    dev.open_path(devs[0]["path"])
    try:
        # baseline
        print("baseline:", bytes(dev.get_feature_report(7, 8)).hex(" "))
        for idx in range(0, 16):
            frame = bytes([7, 0xF1, idx, 0, 0, 0, 0, 0])
            sent = dev.send_feature_report(frame)
            time.sleep(THROTTLE)
            resp = bytes(dev.get_feature_report(7, 8))
            print(f"F1 idx={idx:2d} sent={sent} -> {resp.hex(' ')}")
            time.sleep(THROTTLE)
    finally:
        dev.close()


if __name__ == "__main__":
    main()
