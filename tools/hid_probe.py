"""Read-only HID probe for the AULA keyboard vendor collections.

1) Print HIDP_CAPS (report lengths, feature value caps count) via Windows HID API.
2) Scan feature report IDs 0..64 with HidD_GetFeature (read-only).
3) Dump raw report descriptor if the installed hidapi exposes it.

NO writes (SetFeature / SetOutputReport) are performed.
"""
import ctypes
import sys
from ctypes import wintypes

hid_dll = ctypes.WinDLL("hid.dll")
kernel32 = ctypes.WinDLL("kernel32.dll", use_last_error=True)

HIDP_STATUS_SUCCESS = 0x00110000


class HIDD_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Size", wintypes.ULONG), ("VendorID", wintypes.USHORT),
                ("ProductID", wintypes.USHORT), ("VersionNumber", wintypes.USHORT)]


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [("Usage", wintypes.USHORT), ("UsagePage", wintypes.USHORT),
                ("InputReportByteLength", wintypes.USHORT),
                ("OutputReportByteLength", wintypes.USHORT),
                ("FeatureReportByteLength", wintypes.USHORT),
                ("Reserved", wintypes.USHORT * 17),
                ("NumberLinkCollectionNodes", wintypes.USHORT),
                ("NumberInputButtonCaps", wintypes.USHORT),
                ("NumberInputValueCaps", wintypes.USHORT),
                ("NumberInputDataIndices", wintypes.USHORT),
                ("NumberOutputButtonCaps", wintypes.USHORT),
                ("NumberOutputValueCaps", wintypes.USHORT),
                ("NumberOutputDataIndices", wintypes.USHORT),
                ("NumberFeatureButtonCaps", wintypes.USHORT),
                ("NumberFeatureValueCaps", wintypes.USHORT),
                ("NumberFeatureDataIndices", wintypes.USHORT)]


def open_handle(path: bytes):
    p = ctypes.c_wchar_p(path.decode("utf-8"))
    h = kernel32.CreateFileW(p, 0, 3, None, 3, 0, None)  # no access, share RW
    if h in (-1, None):
        return None
    return h


def caps_of(handle):
    attrs = HIDD_ATTRIBUTES()
    attrs.Size = ctypes.sizeof(HIDD_ATTRIBUTES)
    if not hid_dll.HidD_GetAttributes(handle, ctypes.byref(attrs)):
        return None, "HidD_GetAttributes failed"
    preparsed = ctypes.c_void_p()
    if not hid_dll.HidD_GetPreparsedData(handle, ctypes.byref(preparsed)):
        return None, "GetPreparsedData failed"
    try:
        caps = HIDP_CAPS()
        st = hid_dll.HidP_GetCaps(preparsed, ctypes.byref(caps))
        if st != HIDP_STATUS_SUCCESS:
            return None, f"HidP_GetCaps 0x{st:08x}"
        return dict(attrs=(attrs.VendorID, attrs.ProductID, attrs.VersionNumber), caps=caps), None
    finally:
        hid_dll.HidD_FreePreparsedData(preparsed)


def hexdump(b: bytes, limit=96):
    s = b[:limit].hex(" ")
    return s + (" ..." if len(b) > limit else "")


def scan_feature_reports(path: bytes, feature_len: int, ids=range(0, 65)):
    import hid
    results = []
    dev = hid.device()
    try:
        dev.open_path(path)
    except Exception as e:  # noqa: BLE001
        return None, f"open_path failed: {e}"
    try:
        for rid in ids:
            try:
                data = bytes(dev.get_feature_report(rid, feature_len))
            except (OSError, ValueError):
                continue
            if len(data) > 1:
                results.append((rid, data))
    finally:
        dev.close()
    return results, None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import hid
    devs = [d for d in hid.enumerate() if d["vendor_id"] == 0x1A2C]
    print(f"AULA collections: {len(devs)}")
    for d in devs:
        print("=" * 100)
        print(f"iface={d.get('interface_number')} usage_page=0x{d['usage_page']:04x} usage=0x{d['usage']:04x}")
        print(f"path={d['path'].decode(errors='replace')}")
        h = open_handle(d["path"])
        if h is None:
            print(f"  CreateFile failed err={ctypes.get_last_error()}")
            continue
        info, err = caps_of(h)
        kernel32.CloseHandle(h)
        if err:
            print(f"  caps error: {err}")
            continue
        c = info["caps"]
        print(f"  vid:pid=0x{info['attrs'][0]:04x}:0x{info['attrs'][1]:04x} fw_ver=0x{info['attrs'][2]:04x}")
        print(f"  report lens: in={c.InputReportByteLength} out={c.OutputReportByteLength} feature={c.FeatureReportByteLength}")
        print(f"  feature value/button caps: {c.NumberFeatureValueCaps}/{c.NumberFeatureButtonCaps}"
              f"  input value caps: {c.NumberInputValueCaps}")
        if c.FeatureReportByteLength:
            hits, serr = scan_feature_reports(d["path"], c.FeatureReportByteLength)
            if serr:
                print(f"  feature scan: {serr}")
            else:
                ids = [hex(r[0]) for r in hits]
                print(f"  feature scan hits: {ids if ids else 'NONE'}")
                for rid, data in hits:
                    nonzero = sum(1 for b in data if b)
                    print(f"    id=0x{rid:02x} len={len(data)} nonzero_bytes={nonzero}: {hexdump(data)}")


if __name__ == "__main__":
    main()
