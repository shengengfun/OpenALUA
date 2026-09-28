"""Enumerate HID devices, with focus on the AULA (VID 0x1A2C) keyboard."""
import hid
import sys

sys.stdout.reconfigure(encoding="utf-8")

rows = hid.enumerate()
print(f"total HID collections: {len(rows)}")
print(f"{'VID:PID':>12} {'if':>3} {'usage_page':>10} {'usage':>6}  {'serial':<20} path")
for d in sorted(rows, key=lambda x: (x["vendor_id"], x["product_id"], x.get("interface_number", -1))):
    vidpid = f"{d['vendor_id']:04X}:{d['product_id']:04X}"
    iface = d.get("interface_number", -1)
    mark = " <== AULA" if d["vendor_id"] == 0x1A2C else ""
    print(f"{vidpid:>12} {iface:>3} 0x{d['usage_page']:04x}   0x{d['usage']:04x}  "
          f"{(d.get('serial_number') or ''):<20} {d['path'].decode(errors='replace')}{mark}")
    if d["vendor_id"] == 0x1A2C:
        print(f"             product={d.get('product')!r} mfr={d.get('manufacturer')!r} release=0x{d.get('release_number', 0):04x}")
