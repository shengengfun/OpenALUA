"""Read HID capabilities (report lengths, feature value caps) for the AULA
keyboard vendor collections using the Windows HID API directly. READ-ONLY."""
import ctypes
import sys
from ctypes import wintypes

hidapi_hid = ctypes.WinDLL("hid.dll")
setupapi = ctypes.WinDLL("setupapi.dll", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32.dll", use_last_error=True)

HIDP_STATUS_SUCCESS = 0x00110000
HidP_Input = 0
HidP_Output = 1
HidP_Feature = 2


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


# HIDP_VALUE_CAPS (only the fields we need are at fixed offsets; define fully)
class HIDP_CAPS_RESERVED(ctypes.Structure):
    pass


class _RANGE(ctypes.Structure):
    _fields_ = [("DataIndexMin", wintypes.USHORT), ("DataIndexMax", wintypes.USHORT),
                ("StringMin", wintypes.USHORT), ("StringMax", wintypes.USHORT),
                ("DesignatorMin", wintypes.USHORT), ("DesignatorMax", wintypes.USHORT),
                ("DataIndexMin_" if False else "Reserved1", wintypes.USHORT),
                ("Reserved2", wintypes.USHORT)]


class HIDP_VALUE_CAPS(ctypes.Structure):
    class _U(ctypes.Union):
        class _R(ctypes.Structure):
            _fields_ = [("Reserved", wintypes.USHORT * 6)]  # not used; see parse below
        _fields_ = [("NotRange", ctypes.c_ubyte * 12), ("Range", ctypes.c_ubyte * 12)]
    _fields_ = [
        ("UsagePage", wintypes.USHORT),
        ("ReportID", ctypes.c_ubyte),
        ("BitField", ctypes.c_ubyte),
        ("LinkCollection", wintypes.USHORT),
        ("LinkUsage", wintypes.USHORT),
        ("LinkUsagePage", wintypes.USHORT),
        ("IsRange", wintypes.USHORT),
        ("IsStringArray", wintypes.USHORT),
        ("IsAlias", wintypes.USHORT),
        ("BitSize", wintypes.USHORT),
        ("ReportCount", wintypes.USHORT),
        ("Reserved2", wintypes.USHORT * 5),
        ("UnitsExp", wintypes.ULONG),
        ("Units", wintypes.ULONG),
        ("LogicalMin", wintypes.LONG),
        ("LogicalMax", wintypes.LONG),
        ("PhysicalMin", wintypes.LONG),
        ("PhysicalMax", wintypes.LONG),
    ]


# Correct layout: HIDP_VALUE_CAPS is 64 bytes on x64? Rather than fight the
# struct, decode via raw bytes using the documented layout.
HIDP_VALUE_CAPS_SIZE = 64  # sizeof(HIDP_VALUE_CAPS) on Windows (packed 32-bit fields)


def parse_value_caps(raw: bytes):
    """Decode HIDP_VALUE_CAPS from bytes (documented MS layout, 32/64-bit same)."""
    import struct
    usage_page, report_id, bit_field, link_col, link_usage, link_usage_page = struct.unpack_from("<HBBHHH", raw, 0)
    is_range, is_string_array, is_alias, bit_size, report_count = struct.unpack_from("<HHHHH", raw, 12)
    # range fields at offset 24: 8 x USHORT (UsageMin/Max, StringMin/Max, DesignatorMin/Max, DataIndexMin/Max)
    if is_range:
        usage_min, usage_max, str_min, str_max, des_min, des_max, dix_min, dix_max = struct.unpack_from("<HHHHHHHH", raw, 24)
        return dict(usage_page=usage_page, report_id=report_id, is_range=True,
                    usage_min=usage_min, usage_max=usage_max, data_index_min=dix_min, data_index_max=dix_max,
                    bit_size=bit_size, report_count=report_count, link_collection=link_col)
    else:
        usage, = struct.unpack_from("<H", raw, 24)
        return dict(usage_page=usage_page, report_id=report_id, is_range=False,
                    usage=usage, bit_size=bit_size, report_count=report_count, link_collection=link_col)


def get_caps(path: bytes):
    # hid.dll needs UTF-16 path
    p = ctypes.c_wchar_p(path.decode("utf-8"))
    access = 0  # no access needed for preparsed data? need a handle
    handle = kernel32.CreateFileW(p, 0, 3, None, 3, 0, None)  # GENERIC_NONE, share RW
    if handle == -1 or handle is None:
        return None, f"CreateFile failed err={ctypes.get_last_error()}"
    try:
        attrs = HIDD_ATTRIBUTES()
        attrs.Size = ctypes.sizeof(HIDD_ATTRIBUTES)
        if not hidapi_hid.HidD_GetAttributes(handle, ctypes.byref(attrs)):
            return None, "HidD_GetAttributes failed"
        preparsed = ctypes.c_void_p()
        if not hidapi_hid.HidD_GetPreparsedData(handle, ctypes.byref(preparsed)):
            return None, "GetPreparsedData failed"
        caps = HIDP_CAPS()
        st = hidapi_hid.HidP_GetCaps(preparsed, ctypes.byref(caps))
        if st != HIDP_STATUS_SUCCESS:
            hidapi_hid.HidD_FreePreparsedData(preparsed)
            return None, f"HidP_GetCaps status=0x{st:08x}"
        out = dict(attrs=(attrs.VendorID, attrs.ProductID, attrs.VersionNumber),
                   caps=dict(usage=caps.Usage, usage_page=caps.UsagePage,
                             input_len=caps.InputReportByteLength,
                             output_len=caps.OutputReportByteLength,
                             feature_len=caps.FeatureReportByteLength,
                             n_feature_values=caps.NumberFeatureValueCaps,
                             n_feature_buttons=caps.NumberFeatureButtonCaps,
                             n_input_values=caps.NumberInputValueCaps))
        # feature value caps
        n = caps.NumberFeatureValueCaps
        if n:
            buf = (ctypes.c_ubyte * (n * HIDP_VALUE_CAPS_SIZE))()
            length = ctypes.c_ulong(n * HIDP_VALUE_CAPS_SIZE)
            st = hidapi_hid.HidP_GetValueCaps(HidP_Feature, ctypes.cast(buf, ctypes.POINTER(HIDP_VALUE_CAPS)), ctypes.byref(length), preparsed)
            if st == HIDP_STATUS_SUCCESS:
                raw = bytes(buf)
                out["feature_values"] = [parse_value_caps(raw[i * HIDP_VALUE_CAPS_SIZE:(i + 1) * HIDP_VALUE_CAPS_SIZE]) for i in range(n)]
            else:
                out["feature_values"] = f"err 0x{st:08x}"
        hidapi_hid.HidD_FreePreparsedData(preparsed)
        return out, None
    finally:
        kernel32.CloseHandle(handle)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import hid
    devs = [d for d in hid.enumerate() if d["vendor_id"] == 0x1A2C]
    for d in devs:
        print("=" * 100)
        print(f"iface={d.get('interface_number')} usage_page=0x{d['usage_page']:04x} usage=0x{d['usage']:04x}")
        print(f"path={d['path'].decode(errors='replace')}")
        info, err = get_caps(d["path"])
        if err:
            print(f"  ERROR: {err}")
            continue
        c = info["caps"]
        print(f"  attrs vid:pid=0x{info['attrs'][0]:04x}:0x{info['attrs'][1]:04x} ver=0x{info['attrs'][2]:04x}")
        print(f"  usage=0x{c['usage']:04x} usage_page=0x{c['usage_page']:04x}")
        print(f"  report len: input={c['input_len']} output={c['output_len']} feature={c['feature_len']}")
        print(f"  feature value caps: n={c['n_feature_values']} buttons={c['n_feature_buttons']}")
        fv = info.get("feature_values")
        if isinstance(fv, list):
            for v in fv:
                if v["is_range"]:
                    print(f"    report_id={v['report_id']:3d} usage_page=0x{v['usage_page']:04x} range usage=0x{v['usage_min']:04x}-0x{v['usage_max']:04x} bitsize={v['bit_size']} count={v['report_count']}")
                else:
                    print(f"    report_id={v['report_id']:3d} usage_page=0x{v['usage_page']:04x} usage=0x{v['usage']:04x} bitsize={v['bit_size']} count={v['report_count']}")


if __name__ == "__main__":
    main()
