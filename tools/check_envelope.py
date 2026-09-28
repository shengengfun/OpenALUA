"""Byte-level sanity check: our envelope builders vs the captured official frames.

Runs without any hardware. Catches exactly the class of bug that shipped in
MiaKeyDrv v0.1.0 (an extra 0xAA shifting the whole payload one byte right,
which the firmware silently ignores).
"""
import io
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
sys.path.insert(0, __file__.rsplit("/", 1)[0])

from f3009_24g import frame as tour_frame  # noqa: E402
from probe_speed_range import dongle_frame, wired_frame  # noqa: E402

# verbatim from research/capture_24g.log (official ShinetekTools.exe, 2.4G)
CAPTURED = [
    ("00 bb aa 99 88 aa 0a 05 02 00", (10, 5, 2)),
    ("00 bb aa 99 88 aa 00 05 00 00", (0, 5, 0)),
    ("00 bb aa 99 88 aa 13 05 02 00", (19, 5, 2)),
    ("00 bb aa 99 88 aa 00 04 00 00", (0, 4, 0)),
]

fail = 0
for hexline, args in CAPTURED:
    want = bytes.fromhex(hexline)
    for name, fn in (("f3009_24g", tour_frame), ("probe_speed_range", dongle_frame)):
        got = fn(*args)
        ok_len = len(got) == 65
        ok_head = got[: len(want)] == want
        ok_pad = all(b == 0 for b in got[len(want):])
        status = "ok " if (ok_len and ok_head and ok_pad) else "FAIL"
        if status == "FAIL":
            fail += 1
            print(f"{status} {name}{args}")
            print(f"     want   65 len, head {' '.join(f'{b:02x}' for b in want)}")
            print(f"     got    {len(got)} len, head "
                  f"{' '.join(f'{b:02x}' for b in got[:len(want)])}")
        else:
            print(f"{status} {name}{args}  len={len(got)}")

# the wired path, cross-checked against the feature frames in the same log
WIRED = [
    ("07 ff ff 00 05 00 00 00", (0, 5, 0)),
    ("07 ff ff 02 05 02 00 00", (2, 5, 2)),
    ("07 ff ff 13 05 02 00 00", (19, 5, 2)),
]
for hexline, args in WIRED:
    got = wired_frame(*args)
    want = bytes.fromhex(hexline)
    status = "ok " if got == want else "FAIL"
    if status == "FAIL":
        fail += 1
    print(f"{status} wired{args}  {' '.join(f'{b:02x}' for b in got)}")

print()
print("ALL OK" if fail == 0 else f"{fail} MISMATCH(ES)")
sys.exit(1 if fail else 0)
