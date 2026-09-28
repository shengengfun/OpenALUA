"""Passive read-only listener on the AULA F3009 vendor collections.

Opens the vendor HID collections and prints every input report received
for a few seconds. NO output/feature reports are sent.
"""
import sys
import threading
import time

import hid

VID, PID = 0x1A2C, 0x7FFF


def dump(path: bytes, label: str, duration: float, stop_evt: threading.Event):
    dev = hid.device()
    try:
        dev.open_path(path)
    except Exception as e:  # noqa: BLE001
        print(f"[{label}] open failed: {e}")
        return
    dev.set_nonblocking(False)
    end = time.time() + duration
    print(f"[{label}] reading until +{duration}s ...")
    while time.time() < end and not stop_evt.is_set():
        try:
            data = dev.read(65, timeout_ms=400)
        except Exception as e:  # noqa: BLE001
            print(f"[{label}] read error: {e}")
            break
        if data:
            b = bytes(data)
            print(f"[{label}] {len(b):3d}B  {b.hex(' ')}")
    dev.close()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
    targets = [d for d in hid.enumerate(VID, PID)
               if d["usage_page"] >= 0xFF00]
    if not targets:
        print("no vendor collections found")
        return
    stop = threading.Event()
    threads = []
    for d in targets:
        label = f"if{d.get('interface_number')} up=0x{d['usage_page']:04x}/u=0x{d['usage']:04x}"
        t = threading.Thread(target=dump, args=(d["path"], label, duration, stop), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    print("done")


if __name__ == "__main__":
    main()
