"""Passively listen to the 2.4 GHz dongle's 65-byte vendor input pipe.

No writes at all — this only reads, so it is safe to run while you use the
keyboard normally. If the dongle reports battery / link status, it should show
up here as an input report whose payload starts with the vendor magic.

Usage: python tools/listen_24g.py [seconds]
"""
import sys
import time

import hid

VID = 0x1A2C
PID = 0x7FFF
VENDOR_PAGE = 0xFF01
MAGIC = bytes.fromhex("bbaa9988aa")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 90.0
    log_path = sys.argv[2] if len(sys.argv) > 2 else r"research/listen_24g.txt"
    log = open(log_path, "w", encoding="utf-8")

    def emit(line):
        print(line)
        log.write(line + "\n")
        log.flush()

    target = None
    for d in hid.enumerate(VID, PID):
        if d.get("usage_page") == VENDOR_PAGE and d.get("usage") == 0x0001:
            target = d
            break
    if target is None:
        print("没找到厂商集合 —— 确认键盘在 2.4G 模式")
        return 1

    dev = hid.device()
    dev.open_path(target["path"])
    emit(f"监听 {target['path'].decode()}")
    emit(f"时长 {seconds:.0f} 秒 —— 期间请照常使用键盘（按键、按旋钮、切办公/游戏模式）\n")

    seen = {}
    end = time.time() + seconds
    try:
        while time.time() < end:
            data = dev.read(65, timeout_ms=200)
            if not data:
                continue
            raw = bytes(data)
            stamp = time.strftime("%H:%M:%S")
            tag = ""
            if raw[1:6] == MAGIC:
                tag = "  <== 厂商魔数"
            emit(f"[{stamp}] len={len(raw):3d}  {' '.join(f'{b:02x}' for b in raw[:20])}{tag}")
            seen[raw[:20]] = seen.get(raw[:20], 0) + 1
    except KeyboardInterrupt:
        pass
    finally:
        dev.close()

    emit(f"\n共 {sum(seen.values())} 份报告，{len(seen)} 种不同的前 20 字节：")
    for k, c in sorted(seen.items(), key=lambda kv: -kv[1])[:30]:
        emit(f"  {c:4d}x  {' '.join(f'{b:02x}' for b in k)}")
    log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
