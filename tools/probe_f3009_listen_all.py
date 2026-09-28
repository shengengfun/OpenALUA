"""Listen on ALL HID collections of the F3009 (wired) and print any inbound
traffic, so we can identify which collection carries control/status events.

READ-ONLY: no writes to the device.
"""
import sys
import threading
import time

import hid

VID, PID = 0x1A2C, 0x7F05


def reader(path: bytes, label: str, duration: float):
    dev = hid.device()
    try:
        dev.open_path(path)
    except Exception as e:  # noqa: BLE001
        print(f"[{label}] open failed: {e}")
        return
    dev.set_nonblocking(True)
    t0 = time.time()
    try:
        while time.time() - t0 < duration:
            try:
                data = dev.read(64, timeout_ms=150)
            except Exception as e:  # noqa: BLE001
                print(f"[{label}] read err: {e}")
                break
            if data:
                print(f"[{label}] +{time.time() - t0:5.1f}s  {bytes(data).hex(' ')}")
    finally:
        dev.close()


def poll_feature(duration: float):
    """Poll feature report id 7 and print only changes (read-only)."""
    devs = [d for d in hid.enumerate(VID, PID)
            if d["usage_page"] == 0xFF01 and d["usage"] == 0x0001]
    if not devs:
        print("[feat] Col07 missing")
        return
    dev = hid.device()
    dev.open_path(devs[0]["path"])
    last = None
    t0 = time.time()
    while time.time() - t0 < duration:
        try:
            data = bytes(dev.get_feature_report(7, 8))
        except Exception:  # noqa: BLE001
            time.sleep(0.25)
            continue
        if data != last:
            print(f"[FEAT] +{time.time() - t0:5.1f}s  {data.hex(' ')}")
            last = data
        time.sleep(0.08)
    dev.close()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    devs = [d for d in hid.enumerate(VID, PID)]
    print(f"F3009 wired collections: {len(devs)}")
    threads = []
    for d in devs:
        label = (f"if{d.get('interface_number', -1)} "
                 f"up=0x{d['usage_page']:04x}/u=0x{d['usage']:04x}")
        t = threading.Thread(target=reader, args=(d["path"], label, duration), daemon=True)
        t.start()
        threads.append(t)
    tf = threading.Thread(target=poll_feature, args=(duration,), daemon=True)
    tf.start()
    print(f"\n--- listening {duration:.0f}s : press M1 / M2 / wheel now ---")
    for t in threads:
        t.join()
    tf.join()
    print("listen done")


if __name__ == "__main__":
    main()
