"""Trim the raw PnP dump down to the battery-relevant evidence."""
import io
import re

SRC = "research/bt_battery.txt"
OUT = "research/bt_battery_evidence.txt"

lines = io.open(SRC, encoding="utf-8", errors="replace").read().splitlines()

keep = []
for l in lines:
    s = l.strip()
    if not s:
        continue
    if (
        "104EA319" in s
        or re.match(r"^---", s)
        or "BTHLE" in s.upper()
        or "DEVPKEY_Bluetooth_DeviceAddress" in s
        or "DEVPKEY_Device_IsPresent" in s
        or "DEVPKEY_Device_DevNodeStatus" in s
    ):
        keep.append(s)

io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(keep) + "\n")
print("kept %d of %d lines -> %s" % (len(keep), len(lines), OUT))
