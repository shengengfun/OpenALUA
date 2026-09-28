"""Watch F3009 wired state while the user presses on-keyboard Fn combos.

- polls feature report id 7 every 100 ms, prints only CHANGES
- simultaneously reads the 0xFF00 input collection (2-byte frames)
READ-ONLY: no set_feature calls are made.
"""
import sys
import threading
import time

import hid

VID, PID = 0x1A2C, 0x7F05


def watch_feature(duration: float):
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
        except Exception as e:  # noqa: BLE001
            print(f"[feat] err {e}")
            time.sleep(0.3)
            continue
        if data != last:
            print(f"[feat] +{time.time() - t0:5.1f}s  {data.hex(' ')}")
            last = data
        time.sleep(0.1)
    dev.close()


def watch_input(duration: float):
    devs = [d for d in hid.enumerate(VID, PID)
            if d["usage_page"] == 0xFF00 and d["usage"] == 0x0001]
    if not devs:
        print("[in] FF00 collection missing")
        return
    dev = hid.device()
    dev.open_path(devs[0]["path"])
    dev.set_nonblocking(True)
    t0 = time.time()
    while time.time() - t0 < duration:
        try:
            data = dev.read(8, timeout_ms=200)
        except Exception as e:  # noqa: BLE001
            print(f"[in] err {e}")
            break
        if data:
            print(f"[in] +{time.time() - t0:5.1f}s  {bytes(data).hex(' ')}")
        time.sleep(0.05)
    dev.close()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    print(f"watching for {duration:.0f}s — press Fn light keys now")
    tf = threading.Thread(target=watch_feature, args=(duration,), daemon=True)
    ti = threading.Thread(target=watch_input, args=(duration,), daemon=True)
    tf.start()
    ti.start()
    tf.join()
    ti.join()
    print("watch done")


if __name__ == "__main__":
    main()
