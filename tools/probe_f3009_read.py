"""Read-only probe: HidD_GetFeature on F3009 wired vendor collection Col07.

Reads feature report id 7 (and a few neighbors). NO writes.
"""
import sys

import hid

VID, PID = 0x1A2C, 0x7F05


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    devs = [d for d in hid.enumerate(VID, PID) if d["usage_page"] == 0xFF01 and d["usage"] == 0x0001]
    if not devs:
        print("Col07 vendor collection not found (is F3009 wired & awake?)")
        return
    path = devs[0]["path"]
    print(f"path={path.decode(errors='replace')}")
    dev = hid.device()
    dev.open_path(path)
    try:
        for rid in [7, 6, 8, 1, 0]:
            size = 8
            try:
                data = bytes(dev.get_feature_report(rid, size))
                print(f"get_feature id={rid:3d} -> {len(data)}B  {data.hex(' ')}")
            except (OSError, ValueError) as e:
                print(f"get_feature id={rid:3d} -> ERROR {e}")
    finally:
        dev.close()


if __name__ == "__main__":
    main()
