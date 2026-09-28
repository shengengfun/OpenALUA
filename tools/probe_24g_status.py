"""Hunt for a status/battery query on the 2.4 GHz dongle.

The official tool never asks for the battery (confirmed by disassembling its
envelope builders), and the vendor input pipe is silent until spoken to. So we
keep the *proven* envelope shape and only vary the command discriminator byte
(offset 5, which is 0xAA for the lighting command we captured), then listen for
a reply on the 65-byte input pipe.

Bounded and recorded: every frame we send is printed, and we stop at the first
shape that answers. If the keyboard ever stops responding, unplug/replug it.

Usage:
    python tools/probe_24g_status.py            # send the frames
    python tools/probe_24g_status.py --dry-run
"""
import sys
import time

import hid

VID = 0x1A2C
PID = 0x7FFF
VENDOR_PAGE = 0xFF01
MAGIC = bytes.fromhex("bbaa9988aa")

# Envelope layout, from the official builder at 0x00421599:
#   [0]=00 (report id)  [1..4]=BB AA 99 88  [5]=command  [6..10]=payload  [11..64]=0
# The lighting command uses [5]=0xAA and payload = <effect> <brightness> <speed> 0 0.
# (cmd, payload4, label)
CANDIDATES = [
    (0x00, (0, 0, 0, 0), "命令 00"),
    (0x01, (0, 0, 0, 0), "命令 01"),
    (0x02, (0, 0, 0, 0), "命令 02"),
    (0x10, (0, 0, 0, 0), "命令 10"),
    (0x20, (0, 0, 0, 0), "命令 20"),
    (0xF0, (0, 0, 0, 0), "命令 F0"),
    (0xF1, (0, 0, 0, 0), "命令 F1"),
    (0xAA, (0xF1, 0, 0, 0), "灯光族 + F1（有线读命令的形状）"),
    (0xAA, (0xF0, 0xAA, 0, 0), "官方 07 F0 AA 的 2.4G 版本"),
    (0xAA, (0x01, 0, 0, 0), "灯光族 + 01"),
    (0xAA, (0x10, 0, 0, 0), "灯光族 + 10"),
]

# These two shapes are what the official tool sends right before / after the
# lighting command. They may switch modes, so they are opt-in.
RISKY = [
    (0x00, (0, 0, 0, 0), "官方第二形态（全零载荷，cmd=00）"),
    (0xAA, (0xAA, 0xAA, 0xAA, 0xAA), "官方第一形态（全 AA 载荷）"),
]


def open_vendor():
    for d in hid.enumerate(VID, PID):
        if d.get("usage_page") == VENDOR_PAGE and d.get("usage") == 0x0001:
            dev = hid.device()
            dev.open_path(d["path"])
            return dev
    raise SystemExit("没找到厂商集合 —— 确认键盘在 2.4G 模式")


def frame(cmd, payload4):
    return bytes([0x00]) + bytes.fromhex("bbaa9988") + bytes([cmd]) + bytes(payload4) + bytes(65 - 10)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    dry = "--dry-run" in sys.argv
    log = open(r"research/probe_24g_status.txt", "w", encoding="utf-8")

    def emit(s):
        print(s)
        log.write(s + "\n")
        log.flush()

    dev = None if dry else open_vendor()
    todo = list(CANDIDATES)
    if "--risky" in sys.argv:
        todo += RISKY
        emit("（已包含高风险候选）\n")
    hits = []
    try:
        for cmd, payload4, label in todo:
            f = frame(cmd, payload4)
            emit(f"--- {label}")
            emit(f"    发: {' '.join(f'{b:02x}' for b in f[:12])} …")
            if dry:
                continue
            try:
                n = dev.write(f)
            except Exception as e:
                emit(f"    写失败: {e}")
                continue
            # listen for a reply on the input pipe
            got = []
            end = time.time() + 0.45
            while time.time() < end:
                data = dev.read(65, timeout_ms=120)
                if data:
                    got.append(bytes(data))
            if got:
                for r in got[:6]:
                    emit(f"    收 ({len(r)}B): {' '.join(f'{b:02x}' for b in r[:20])}")
                hits.append((label, got[0]))
            else:
                emit("    无应答")
    finally:
        if dev is not None:
            dev.close()

    emit("")
    if hits:
        emit(f"★ {len(hits)} 个命令得到了应答：")
        for label, r in hits:
            emit(f"  {label} -> {' '.join(f'{b:02x}' for b in r[:20])}")
    else:
        emit("所有候选命令都没有应答。")
    log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
