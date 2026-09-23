import re
import math
import pytest

def python_parse_gcode(gcode_text: str):
    """
    Python mirror of frontend/js/parsers/gcode.js to ensure regression prevention
    and strict parity for slicer metadata extraction.
    """
    print_time_seconds = 0
    print_time_priority = 0
    filament_grams = 0
    filament_millimeters = 0
    filament_type = None

    lines = gcode_text.splitlines()
    header_lines = lines[:3000]
    footer_lines = lines[-3000:]
    candidate_lines = header_lines + footer_lines

    def extract_from_line(raw_line: str):
        nonlocal print_time_seconds, print_time_priority, filament_grams, filament_millimeters, filament_type
        line = raw_line.strip()
        if not line.startswith(";"):
            return
        lower = line.lower()

        # Skip silent/stealth mode to ensure normal mode is never clobbered
        if "(silent mode)" in lower or "(stealth mode)" in lower:
            return

        # 1. Cura / Creality time
        cura_time = re.search(r"^;\s*time(?:_elapsed)?:\s*(\d+)(?:\s*(?:s|sec|seconds)?\s*$|\s*$)", lower)
        if cura_time and print_time_priority < 2:
            print_time_seconds = int(cura_time.group(1))
            print_time_priority = 2

        sec_tag = re.search(r"^;\s*(?:total_time|print_time|estimated_time|job_time|total_print_time)\s*[:=]\s*(\d+)(?:\s*(?:s|sec|seconds)?\s*$|\s*$)", lower)
        if sec_tag and print_time_priority < 2:
            print_time_seconds = int(sec_tag.group(1))
            print_time_priority = 1

        time_keywords = [
            "estimated printing time (normal mode)", "total estimated time", "estimated printing time",
            "model printing time", "estimated print time", "printing time", "print time", "build time",
            "total time", "total print time", "estimated time", "job time", "print duration", "time:"
        ]
        matched_kw = next((k for k in time_keywords if k in lower), None)
        if matched_kw:
            is_high_pri = "normal mode" in matched_kw or "total estimated time" in matched_kw
            if is_high_pri or print_time_priority < 2:
                target_segment = line
                kw_idx = lower.find(matched_kw)
                if kw_idx != -1:
                    target_segment = line[kw_idx + len(matched_kw):]

                hhmmss = re.search(r"(?:=|\:|\s)\s*(\d{1,3}):(\d{2}):(\d{2})(?!\d)", target_segment)
                if hhmmss:
                    h, m, s = int(hhmmss.group(1)), int(hhmmss.group(2)), int(hhmmss.group(3))
                    calculated = (h * 3600) + (m * 60) + s
                    if calculated > 0:
                        print_time_seconds = calculated
                        print_time_priority = 2 if is_high_pri else 1
                else:
                    hhmm = re.search(r"(?:=|\:|\s)\s*(\d{1,3}):(\d{2})(?!\d)", target_segment)
                    if hhmm:
                        h, m = int(hhmm.group(1)), int(hhmm.group(2))
                        calculated = (h * 3600) + (m * 60)
                        if calculated > 0:
                            print_time_seconds = calculated
                            print_time_priority = 2 if is_high_pri else 1
                    else:
                        d_match = re.search(r"(\d+)\s*d(?:ays?)?\b", target_segment, re.I)
                        h_match = re.search(r"(\d+(?:\.\d+)?)\s*h(?:ours?|r|oras?)?\b", target_segment, re.I)
                        m_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:m(?!m)(?:in(?:ute)?s?)?)\b", target_segment, re.I)
                        s_match = re.search(r"(\d+(?:\.\d+)?)\s*s(?:ec(?:ond)?s?)?\b", target_segment, re.I)
                        if d_match or h_match or m_match or s_match:
                            days = float(d_match.group(1)) if d_match else 0
                            hours = float(h_match.group(1)) if h_match else 0
                            mins = float(m_match.group(1)) if m_match else 0
                            secs = float(s_match.group(1)) if s_match else 0
                            calculated = round((days * 86400) + (hours * 3600) + (mins * 60) + secs)
                            if calculated > 0:
                                print_time_seconds = calculated
                                print_time_priority = 2 if is_high_pri else 1

        # 2. Filament Weight
        if "filament used [g]" in lower or "filament used [grams]" in lower:
            numbers = re.findall(r"[0-9]+(?:\.[0-9]+)?", line)
            if numbers:
                total_g = sum(float(n) for n in numbers)
                if total_g > 0:
                    filament_grams = total_g

        cura_weight = re.search(r"filament\s+(?:weight|used)\s*[:=]\s*([0-9.]+)\s*g?", line, re.I)
        if cura_weight and not filament_grams and "[mm]" not in lower and "[m]" not in lower:
            filament_grams = float(cura_weight.group(1))

        # 3. Filament Length
        if re.search(r"filament used\s*\[?(?:mm|m)\]?", lower) and not filament_grams:
            m_match = re.search(r"[:=]\s*([0-9.]+)\s*m(?:$|\s)", line, re.I)
            mm_match = re.search(r"[:=]\s*([0-9.]+)\s*(?:mm)?(?:$|\s)", line, re.I)
            if m_match:
                filament_millimeters = float(m_match.group(1)) * 1000
            elif mm_match:
                filament_millimeters = float(mm_match.group(1))

        # 4. Filament Material
        mat_match = re.search(r"filament_type(?:\s*\[\d+\])?\s*=\s*([A-Za-z0-9_-]+)", line, re.I)
        if mat_match and not filament_type:
            filament_type = mat_match.group(1).strip()

        cura_mat = re.search(r"^;\s*material(?:_\d+)?:\s*([A-Za-z0-9_-]+)", line, re.I)
        if cura_mat and not filament_type:
            filament_type = cura_mat.group(1).strip()

    for raw_line in candidate_lines:
        extract_from_line(raw_line)

    if (not print_time_seconds or not filament_grams) and len(lines) > 6000:
        for i in range(3000, len(lines) - 3000):
            if lines[i].startswith(";"):
                extract_from_line(lines[i])
                if print_time_seconds and filament_grams:
                    break

    if not filament_grams and filament_millimeters > 0:
        radius_mm = 1.75 / 2.0
        volume_mm3 = math.pi * (radius_mm ** 2) * filament_millimeters
        volume_cm3 = volume_mm3 / 1000.0
        filament_grams = volume_cm3 * 1.24

    hours = round(print_time_seconds / 3600.0, 2) if print_time_seconds > 0 else 0.0
    return {
        "print_time_hours": hours,
        "part_weight_g": round(filament_grams, 2),
        "filament_type": filament_type,
    }


def test_prusa_slicer_gcode_parsing():
    sample = """
; generated by PrusaSlicer 2.7.1 on 2026-03-10
; filament_type = PETG
; filament used [mm] = 4520.3
; filament used [cm3] = 10.87
; filament used [g] = 32.50
; estimated printing time (normal mode) = 2h 15m 30s
G21
G90
M107
    """
    res = python_parse_gcode(sample)
    assert res["print_time_hours"] == 2.26
    assert res["part_weight_g"] == 32.50
    assert res["filament_type"] == "PETG"


def test_prusa_multi_material_gcode_parsing():
    sample = """
; generated by PrusaSlicer MMU
; filament_type = PLA
; filament used [g] = 14.20, 8.50, 3.10
; estimated printing time (normal mode) = 1h 45m
    """
    res = python_parse_gcode(sample)
    assert res["part_weight_g"] == 25.80
    assert res["print_time_hours"] == 1.75
    assert res["filament_type"] == "PLA"


def test_cura_gcode_parsing():
    sample = """
;FLAVOR:Marlin
;TIME:5400
;Filament used: 42.1g
;Generated with Cura_SteamEngine 5.4.0
M140 S60
    """
    res = python_parse_gcode(sample)
    assert res["print_time_hours"] == 1.50
    assert res["part_weight_g"] == 42.10


def test_cura_with_spaces_and_elapsed():
    sample = """
;FLAVOR:Marlin
; TIME: 7200
; TIME_ELAPSED: 7200
; Filament used: 55.4g
    """
    res = python_parse_gcode(sample)
    assert res["print_time_hours"] == 2.0
    assert res["part_weight_g"] == 55.4


def test_hh_mm_ss_format_gcode_parsing():
    sample = """
; total time: 03:30:00
; filament used [g] = 50.0
    """
    res = python_parse_gcode(sample)
    assert res["print_time_hours"] == 3.50
    assert res["part_weight_g"] == 50.0


def test_hh_mm_format_gcode_parsing():
    sample = """
; Estimated print time: 1:30
; filament used [g] = 20.0
    """
    res = python_parse_gcode(sample)
    assert res["print_time_hours"] == 1.50
    assert res["part_weight_g"] == 20.0


def test_bambu_orca_combined_line_parsing():
    sample = """
; HEADER_BLOCK_START
; total filament used [g] = 38.60
; model printing time: 1h 10m 00s; total estimated time: 1h 30m 00s
; filament_type = ABS
    """
    res = python_parse_gcode(sample)
    assert res["print_time_hours"] == 1.50
    assert res["part_weight_g"] == 38.60
    assert res["filament_type"] == "ABS"


def test_creality_and_generic_seconds():
    sample = """
; total_time: 3600
; filament used [g] = 15.0
    """
    res = python_parse_gcode(sample)
    assert res["print_time_hours"] == 1.00
    assert res["part_weight_g"] == 15.00


def test_footer_deep_in_gcode():
    # Slicer with 800 lines of config after estimated time
    lines = ["; start"] + ["G1 X10 Y10"] * 2000
    lines.append("; estimated printing time (normal mode) = 2h 00m 00s")
    lines.append("; filament used [g] = 60.0")
    lines.extend([f"; config_param_{i} = val" for i in range(800)])
    sample = "\n".join(lines)
    res = python_parse_gcode(sample)
    assert res["print_time_hours"] == 2.0
    assert res["part_weight_g"] == 60.0


def test_prusa_normal_mode_not_clobbered_by_silent_mode():
    sample = """
; generated by PrusaSlicer 2.7.4 on 2026-04-12
; estimated printing time (normal mode) = 1h 20m 00s
; estimated printing time (silent mode) = 2h 00m 00s
; filament used [g] = 30.0
; filament_type = PLA
    """
    res = python_parse_gcode(sample)
    assert res["print_time_hours"] == 1.33
    assert res["part_weight_g"] == 30.0
    assert res["filament_type"] == "PLA"


def test_time_colon_format_gcode_parsing():
    sample = """
; generated by Custom Slicer
; TIME: 01:30:00
; filament used [g] = 45.0
    """
    res = python_parse_gcode(sample)
    assert res["print_time_hours"] == 1.50
    assert res["part_weight_g"] == 45.0


def test_nozzle_mm_does_not_interfere_with_minutes():
    sample = """
; layer: 0.2mm, nozzle: 0.4mm, print time: 1h 30m
; filament used [g] = 22.0
    """
    res = python_parse_gcode(sample)
    assert res["print_time_hours"] == 1.50
    assert res["part_weight_g"] == 22.0


def test_cura_material_extraction():
    sample = """
;FLAVOR:Marlin
;TIME:3600
;Filament used: 25.0g
;MATERIAL:PETG
;Generated with Cura_SteamEngine 5.4.0
    """
    res = python_parse_gcode(sample)
    assert res["print_time_hours"] == 1.00
    assert res["part_weight_g"] == 25.0
    assert res["filament_type"] == "PETG"


def python_parse_3mf(data: bytes):
    """
    Python mirror of frontend/js/parsers/threemf.js
    """
    import io
    import zipfile
    import xml.etree.ElementTree as ET

    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except Exception:
        # Fallback to plain text G-code
        text = data.decode("utf-8", errors="ignore")
        meta = python_parse_gcode(text)
        return [{
            "name": "Placa 1",
            "print_time_hours": meta["print_time_hours"],
            "part_weight_g": meta["part_weight_g"],
            "purge_weight_g": 0.0,
            "filament_type": meta["filament_type"] or "PLA",
        }]

    plates = []
    # 1. Look for slice_info.xml
    slice_names = [n for n in zf.namelist() if n.endswith("slice_info.xml")]
    if slice_names:
        xml_data = zf.read(slice_names[0])
        root = ET.fromstring(xml_data)
        for idx, plate in enumerate(root.findall(".//plate")):
            prediction_secs = 0.0
            weight_g = 0.0
            purge_g = 0.0
            fil_types = []
            for meta in plate.findall("metadata"):
                k = (meta.get("key") or "").lower()
                v = meta.get("value")
                if k in ["prediction", "print_time"]:
                    prediction_secs = float(v)
                elif k in ["weight", "plate_weight"]:
                    weight_g = float(v)
                elif k in ["flush_weight", "purge_weight", "waste_weight"]:
                    purge_g = float(v)
            for f in plate.findall("filament"):
                t = f.get("type")
                if t and t not in fil_types:
                    fil_types.append(t)
            plates.append({
                "name": f"Placa {idx + 1}",
                "print_time_hours": round(prediction_secs / 3600.0, 2),
                "part_weight_g": round(weight_g, 2),
                "purge_weight_g": round(purge_g, 2),
                "filament_type": ", ".join(fil_types) if fil_types else "PLA"
            })

    # 2. Look for embedded G-code inside .gcode.3mf
    if not plates or all(p["print_time_hours"] == 0 and p["part_weight_g"] == 0 for p in plates):
        import re

        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

        gcode_names = [n for n in zf.namelist() if n.lower().endswith(".gcode") and not n.endswith("/") and not n.endswith("\\")]
        if gcode_names:
            gcode_names.sort(key=natural_sort_key)
            gcode_plates = []
            for idx, gname in enumerate(gcode_names):
                gtext = zf.read(gname).decode("utf-8", errors="ignore")
                meta = python_parse_gcode(gtext)

                base = gname.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                base_clean = re.sub(r'\.gcode$', '', base, flags=re.IGNORECASE)
                plate_match = re.search(r'(?:plate|placa)[-_ ]*(\d+)', base_clean, re.IGNORECASE)
                if plate_match:
                    p_name = f"Placa {plate_match.group(1)}"
                else:
                    p_name = base_clean or f"Placa {idx + 1}"

                gcode_plates.append({
                    "name": p_name,
                    "print_time_hours": meta["print_time_hours"],
                    "part_weight_g": meta["part_weight_g"],
                    "purge_weight_g": 0.0,
                    "filament_type": meta["filament_type"] or "PLA"
                })
            if gcode_plates and any(p["print_time_hours"] > 0 or p["part_weight_g"] > 0 for p in gcode_plates):
                return gcode_plates

    return plates


def test_gcode_3mf_with_slice_info():
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<config>
  <plate>
    <metadata key="index" value="1"/>
    <metadata key="prediction" value="7200"/>
    <metadata key="weight" value="45.5"/>
    <filament id="1" type="PETG" used_g="45.5"/>
  </plate>
</config>"""
        zf.writestr("Metadata/slice_info.xml", xml_content)

    res = python_parse_3mf(buf.getvalue())
    assert len(res) == 1
    assert res[0]["print_time_hours"] == 2.0
    assert res[0]["part_weight_g"] == 45.5
    assert res[0]["filament_type"] == "PETG"


def test_gcode_3mf_with_embedded_gcode():
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        gcode_content = """; generated by OrcaSlicer
; TIME: 5400
; Filament used: 32.5g
; filament_type = ABS
G28
"""
        zf.writestr("Metadata/plate_1.gcode", gcode_content)

    res = python_parse_3mf(buf.getvalue())
    assert len(res) == 1
    assert res[0]["print_time_hours"] == 1.50
    assert res[0]["part_weight_g"] == 32.5
    assert res[0]["filament_type"] == "ABS"


def test_gcode_3mf_plain_text_fallback():
    raw_content = """; generated by Bambu Studio
; total estimated time = 00:30:00
; filament used [g] = 15.0
; filament_type = PLA
G1 X10 Y10
""".encode("utf-8")

    res = python_parse_3mf(raw_content)
    assert len(res) == 1
    assert res[0]["print_time_hours"] == 0.50
    assert res[0]["part_weight_g"] == 15.0
    assert res[0]["filament_type"] == "PLA"


def test_multi_plate_gcode_3mf_natural_sort_and_naming():
    """
    Verifies that multi-plate .gcode.3mf archives with 10+ plates:
    1. Sort naturally (Placa 1, Placa 2, ..., Placa 9, Placa 10) instead of lexicographically.
    2. Extract plate index from filename into 'Placa X'.
    """
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # Intentionally write in mixed order
        plate_numbers = [1, 10, 2, 5, 3, 4, 6, 7, 8, 9]
        for pnum in plate_numbers:
            content = f"""; generated by OrcaSlicer
; TIME: {pnum * 3600}
; Filament used: {pnum * 10}.0g
; filament_type = PETG
G28
"""
            zf.writestr(f"Metadata/plate_{pnum}.gcode", content)

    res = python_parse_3mf(buf.getvalue())
    assert len(res) == 10
    expected_names = [f"Placa {i}" for i in range(1, 11)]
    actual_names = [p["name"] for p in res]
    assert actual_names == expected_names, f"Expected {expected_names}, got {actual_names}"
    for i, p in enumerate(res, 1):
        assert p["print_time_hours"] == float(i)
        assert p["part_weight_g"] == float(i * 10)
        assert p["filament_type"] == "PETG"



