"""Probe the vhidflt virtual device (DEED:FEED) exposed by the AULA driver.

If ShinetekTools talks through this device instead of the raw keyboard, the
same 8-byte command frames should work here.

READ-ONLY: GetFeature only (no SetFeature in this script).
"""
import sys

import hid

VID, PID = 0xDEED, 0xFEED


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    devs = [d for d in hid.enumerate(VID, PID)]
    if not devs:
        print("vhidev (DEED:FEED) not present — is the AULA driver installed?")
        return
    print(f"vhidev collections: {len(devs)}")
    for d in devs:
        print("=" * 90)
        print(f"iface={d.get('interface_number')} usage_page=0x{d['usage_page']:04x} usage=0x{d['usage']:04x}")
        print(f"  product={d.get('product')!r} serial={(d.get('serial_number') or '')[:60]!r}")
        print(f"  path={d['path'].decode(errors='replace')}")
        dev = hid.device()
        try:
            dev.open_path(d["path"])
        except Exception as e:  # noqa: BLE001
            print(f"  open failed: {e}")
            continue
        try:
            for rid in range(1, 9):
                for size in (8, 9, 16, 64, 65):
                    try:
                        data = bytes(dev.get_feature_report(rid, size))
                    except Exception:  # noqa: BLE001
                        continue
                    if data:
                        print(f"  get_feature id={rid} size={size} -> {len(data)}B {data[:32].hex(' ')}")
                        break
        finally:
            dev.close()


if __name__ == "__main__":
    main()
