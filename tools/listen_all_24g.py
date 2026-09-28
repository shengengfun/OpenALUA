"""Listen to every AULA 1A2C:7FFF collection at once and report which one
actually delivers input reports.

MI_00 claims to be a boot keyboard yet declares a 65-byte input report, which is
way more than a keyboard needs - so the extra bytes may carry link status /
battery. This test tells us which pipe is live and what it contains.

Usage: python tools/listen_all_24g.py [seconds]
"""
import sys
import time

import hid

VID = 0x1A2C
PID = 0x7FFF


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0

    cols = [d for d in hid.enumerate(VID, PID)]
    handles = []
    for d in cols:
        try:
            h = hid.device()
            h.open_path(d["path"])
            h.set_nonblocking(False)
            handles.append((d, h))
            iface = d.get("interface_number")
            print(f"打开 iface={iface} usage_page=0x{d['usage_page']:04x} "
                  f"usage=0x{d['usage']:04x}")
        except Exception as e:
            print(f"跳过 {d['path'][:60]}…: {e}")

    if not handles:
        print("一个都打不开")
        return 1

    print(f"\n监听 {seconds:.0f} 秒 —— 请大力敲键盘、按旋钮\n")
    counts = {}
    dead = []
    end = time.time() + seconds
    try:
        while time.time() < end:
            for d, h in handles:
                if (d, h) in dead:
                    continue
                try:
                    data = h.read(65, timeout_ms=40)
                except OSError as e:
                    iface = d.get("interface_number")
                    print(f"  [iface={iface} usage_page=0x{d['usage_page']:04x}] "
                          f"读不了（{e}），放弃这条")
                    dead.append((d, h))
                    continue
                if not data:
                    continue
                key = (d.get("interface_number"), d.get("usage_page"), d.get("usage"))
                counts[key] = counts.get(key, 0) + 1
                if counts[key] <= 6:
                    print(f"[iface={key[0]} up=0x{key[1]:04x} u=0x{key[2]:04x}] "
                          f"len={len(data):3d}  "
                          f"{' '.join(f'{b:02x}' for b in bytes(data)[:24])}")
    except KeyboardInterrupt:
        pass
    finally:
        for _d, h in handles:
            h.close()

    print("\n各集合收到的报告数：")
    for k, c in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  iface={k[0]} usage_page=0x{k[1]:04x} usage=0x{k[2]:04x}: {c}")
    if not counts:
        print("  （全都没数据）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
