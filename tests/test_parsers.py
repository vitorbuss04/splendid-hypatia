import re
import math
import pytest

def clean_filament_profile_name(profile: str, filename: str = "") -> str:
    if not profile:
        return ""
    cleaned = profile.strip().strip("\"'")
    cleaned = re.sub(r'\s*[\(\[][^()\[\]]*\.[a-z0-9_-]{2,6}\s*[\)\]]', '', cleaned, flags=re.I)
    if filename:
        base = re.sub(r'\.(?:gcode\.3mf|3mf|gcode|stl|step|stp|obj)$', '', re.split(r'[\\/]', filename)[-1], flags=re.I).strip()
        if base and len(base) >= 2:
            cleaned = re.sub(r'\s*[\(\[]\s*' + re.escape(base) + r'(?:\.[^()\[\]]+)?\s*[\)\]]', '', cleaned, flags=re.I)
    return re.sub(r'\s{2,}', ' ', cleaned).strip()

def python_parse_gcode(gcode_text: str, filename: str = ""):
    """
    Python mirror of frontend/js/parsers/gcode.js to ensure regression prevention
    and strict parity for slicer metadata extraction.
    """
    print_time_seconds = 0
    print_time_priority = 0
    filament_grams = 0
    filament_millimeters = 0
    filament_type = None
    filament_profile = None
    filament_vendor = None

    lines = gcode_text.splitlines()
    header_lines = lines[:3000]
    footer_lines = lines[-3000:]
    candidate_lines = header_lines + footer_lines

    active_slot = None
    filament_settings_parts = []
    filament_vendor_parts = []
    filament_type_parts = []
    filament_colour_parts = []

    def extract_from_line(raw_line: str):
        nonlocal print_time_seconds, print_time_priority, filament_grams, filament_millimeters, filament_type, filament_profile, filament_vendor, active_slot, filament_settings_parts, filament_vendor_parts, filament_type_parts, filament_colour_parts
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
                filament_millimeters = float(m_match.group(1)) * 1000.0
            elif mm_match:
                filament_millimeters = float(mm_match.group(1))

        # 4. Filament Material
        mat_match = re.search(r"^;\s*filament_type(?:\s*\[\d+\])?\s*=\s*(.+)", line, re.I)
        if mat_match and not filament_type_parts:
            filament_type_parts = [p.strip().strip('"\'') for p in mat_match.group(1).split(";") if p.strip().strip('"\'')]

        cura_mat = re.search(r"^;\s*material(?:_\d+)?:\s*([A-Za-z0-9_-]+)", line, re.I)
        if cura_mat and not filament_type:
            filament_type = cura_mat.group(1).strip()

        # 5. Active Filament Slot (Bambu Studio / OrcaSlicer e.g. ; filament: 2)
        if not active_slot:
            slot_match = re.search(r"^;\s*(?:filament|filament_slot|tray_id)\s*[:=]\s*(\d+)", line, re.I)
            if slot_match:
                active_slot = int(slot_match.group(1))

        # 6. Filament Settings / Profile / Vendor / Colour
        settings_match = re.search(r"filament_settings_id(?:\s*\[\d+\])?\s*=\s*(.+)", line, re.I)
        if settings_match and not filament_settings_parts:
            raw_val = settings_match.group(1).strip()
            filament_settings_parts = [p.strip().strip('"\'') for p in raw_val.split(";") if p.strip().strip('"\'')]

        vendor_match = re.search(r"filament_vendor(?:\s*\[\d+\])?\s*=\s*(.+)", line, re.I)
        if vendor_match and not filament_vendor_parts:
            raw_val = vendor_match.group(1).strip()
            filament_vendor_parts = [p.strip().strip('"\'') for p in raw_val.split(";") if p.strip().strip('"\'')]

        col_match = re.search(r"filament_colou?r(?:\s*\[\d+\])?\s*=\s*(.+)", line, re.I)
        if col_match and not filament_colour_parts:
            raw_val = col_match.group(1).strip()
            filament_colour_parts = [p.strip().strip('"\'') for p in raw_val.split(";") if p.strip().strip('"\'')]

        cura_name = re.search(r"^;\s*filament_name(?:_\d+)?:\s*(.+)", line, re.I)
        if cura_name and not filament_profile:
            filament_profile = cura_name.group(1).strip().strip('"\'')

    for raw_line in candidate_lines:
        extract_from_line(raw_line)

    target_idx = (active_slot - 1) if (active_slot and active_slot > 0) else 0
    if filament_settings_parts and not filament_profile:
        filament_profile = filament_settings_parts[target_idx] if target_idx < len(filament_settings_parts) else filament_settings_parts[0]
    if filament_vendor_parts and not filament_vendor:
        filament_vendor = filament_vendor_parts[target_idx] if target_idx < len(filament_vendor_parts) else filament_vendor_parts[0]
    if filament_type_parts and not filament_type:
        filament_type = filament_type_parts[target_idx] if target_idx < len(filament_type_parts) else filament_type_parts[0]
    filament_colour_hex = None
    if filament_colour_parts:
        filament_colour_hex = filament_colour_parts[target_idx] if target_idx < len(filament_colour_parts) else filament_colour_parts[0]

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

    slicer_profile = None
    if filament_profile:
        slicer_profile = filament_profile
        if filament_vendor:
            v_words = [w for w in re.split(r'[\s_-]+', filament_vendor.lower()) if len(w) > 2 and w not in ['lab', 'labs', 'ltd', 'inc', 'corp', 'the', '3d']]
            p_lower = slicer_profile.lower()
            if not any(w in p_lower for w in v_words):
                slicer_profile = f"{filament_vendor} {slicer_profile}"
    elif filament_vendor and filament_type:
        slicer_profile = f"{filament_vendor} {filament_type}"
    elif filament_type:
        slicer_profile = filament_type

    hours = round(print_time_seconds / 3600.0, 2) if print_time_seconds > 0 else 0.0
    return {
        "print_time_hours": hours,
        "part_weight_g": round(filament_grams, 2),
        "filament_type": filament_type,
        "slicer_filament_profile": clean_filament_profile_name(slicer_profile, filename) or None,
        "filament_color_hex": filament_colour_hex,
        "filament_slot": active_slot,
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


def python_parse_time_string_to_seconds(time_val):
    if not time_val:
        return 0.0
    if isinstance(time_val, (int, float)):
        return float(time_val)
    s = str(time_val).strip()
    if not s:
        return 0.0
    if re.match(r"^\d+(?:\.\d+)?$", s):
        return float(s)
    hhmmss = re.search(r"(\d{1,3}):(\d{2}):(\d{2})", s)
    if hhmmss:
        h, m, sec = int(hhmmss.group(1)), int(hhmmss.group(2)), int(hhmmss.group(3))
        return float((h * 3600) + (m * 60) + sec)
    hhmm = re.search(r"(\d{1,3}):(\d{2})", s)
    if hhmm:
        h, m = int(hhmm.group(1)), int(hhmm.group(2))
        return float((h * 3600) + (m * 60))
    d_match = re.search(r"(\d+)\s*d", s, re.I)
    h_match = re.search(r"(\d+(?:\.\d+)?)\s*h", s, re.I)
    m_match = re.search(r"(\d+(?:\.\d+)?)\s*m", s, re.I)
    s_match = re.search(r"(\d+(?:\.\d+)?)\s*s", s, re.I)
    if d_match or h_match or m_match or s_match:
        d = float(d_match.group(1)) if d_match else 0.0
        h = float(h_match.group(1)) if h_match else 0.0
        m = float(m_match.group(1)) if m_match else 0.0
        sec = float(s_match.group(1)) if s_match else 0.0
        return (d * 86400.0) + (h * 3600.0) + (m * 60.0) + sec
    try:
        return float(s)
    except ValueError:
        return 0.0


def python_parse_3mf(data: bytes, filename: str = None):
    """
    Python mirror of frontend/js/parsers/threemf.js
    """
    import io
    import re
    import zipfile
    import xml.etree.ElementTree as ET

    clean_filename = ""
    if filename:
        clean_filename = re.sub(r"^.*[\\\/]", "", filename)
        clean_filename = re.sub(r"\.(?:gcode\.3mf|3mf|gcode)$", "", clean_filename, flags=re.I).strip()

    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except Exception:
        # Fallback to plain text G-code
        text = data.decode("utf-8", errors="ignore")
        meta = python_parse_gcode(text)
        return [{
            "name": clean_filename or "Placa 1",
            "print_time_hours": meta["print_time_hours"],
            "part_weight_g": meta["part_weight_g"],
            "purge_weight_g": 0.0,
            "filament_type": meta["filament_type"] or "PLA",
        }]

    plates = []
    # 1. Look for slice_info.xml or slice_info.config
    slice_names = [n for n in zf.namelist() if re.search(r"(?:^|/)slice_info\.(?:xml|config)$", n, re.I) or re.search(r".*slice.*(?:\.xml|\.config)$", n, re.I)]
    if slice_names:
        xml_data = zf.read(slice_names[0])
        root = ET.fromstring(xml_data)
        plate_nodes = root.findall(".//plate")
        for idx, plate in enumerate(plate_nodes):
            prediction_secs = 0.0
            weight_g = 0.0
            purge_g = 0.0
            fil_types = []
            plate_custom_name = None
            plate_filament_profile = None
            plate_filament_slot = None
            plate_filament_color_hex = None

            for meta in plate.findall("metadata"):
                k = (meta.get("key") or "").lower()
                v = meta.get("value") or ""
                if k in ["prediction", "print_time", "prediction_time", "time", "estimated_time", "printing_time", "total_time", "total_estimated_time"]:
                    prediction_secs = python_parse_time_string_to_seconds(v)
                elif k in ["weight", "plate_weight", "filament_weight", "filament_used", "total_weight"]:
                    try:
                        weight_g = float(v)
                    except ValueError:
                        pass
                elif k in ["flush_weight", "purge_weight", "waste_weight"]:
                    try:
                        purge_g = float(v)
                    except ValueError:
                        pass
                elif k in ["name", "plate_name", "title", "label"]:
                    if v.strip():
                        plate_custom_name = v.strip()
                elif k in ["filament_profile", "filament_name", "profile", "tray_info_idx"]:
                    if v.strip() and not plate_filament_profile:
                        plate_filament_profile = v.strip()

            if not prediction_secs:
                for attr_k in ["prediction", "print_time", "prediction_time", "time", "estimated_time"]:
                    if plate.get(attr_k):
                        prediction_secs = python_parse_time_string_to_seconds(plate.get(attr_k))
                        if prediction_secs:
                            break

            if not weight_g:
                for attr_k in ["weight", "plate_weight", "filament_weight", "filament_used"]:
                    if plate.get(attr_k):
                        try:
                            weight_g = float(plate.get(attr_k))
                            if weight_g:
                                break
                        except ValueError:
                            pass

            if not plate_custom_name:
                for attr_k in ["name", "plate_name", "title"]:
                    if plate.get(attr_k) and plate.get(attr_k).strip():
                        plate_custom_name = plate.get(attr_k).strip()
                        break

            total_fil_g = 0.0
            for f in plate.findall("filament"):
                t = f.get("type")
                if t and t not in fil_types:
                    fil_types.append(t)
                prof = f.get("profile") or f.get("profile_name") or f.get("name") or f.get("tray_info_idx")
                if prof and not plate_filament_profile and not prof.startswith("#"):
                    is_opaque = bool(re.match(r"^[A-Za-z0-9_-]{3,15}$", prof.strip()) and not re.search(r"pla|petg|abs|tpu|pc|nylon|basic|matte|silk", prof, re.I))
                    if not is_opaque:
                        plate_filament_profile = prof.strip()
                if f.get("id") and f.get("id").isdigit() and not plate_filament_slot:
                    plate_filament_slot = int(f.get("id"))
                if f.get("color") and not plate_filament_color_hex:
                    plate_filament_color_hex = f.get("color")
                used_g = 0.0
                for attr in ["used_g", "weight", "used_weight", "amount"]:
                    if f.get(attr):
                        try:
                            used_g = float(f.get(attr))
                            break
                        except ValueError:
                            pass
                if used_g == 0.0 and f.get("used_m"):
                    try:
                        used_g = float(f.get("used_m")) * 2.98
                    except ValueError:
                        pass
                flush_g = 0.0
                for attr in ["flush_g", "purge_g"]:
                    if f.get(attr):
                        try:
                            flush_g = float(f.get(attr))
                            break
                        except ValueError:
                            pass
                total_fil_g += used_g
                if flush_g > 0 and purge_g == 0:
                    purge_g += flush_g

            part_weight = weight_g
            if total_fil_g > 0:
                if purge_g > 0:
                    if part_weight > purge_g and part_weight == total_fil_g:
                        part_weight = total_fil_g - purge_g
                elif total_fil_g > part_weight and part_weight > 0:
                    purge_g = total_fil_g - part_weight
                elif part_weight == 0:
                    part_weight = total_fil_g

            if plate_custom_name and not re.match(r"^placa\s*\d+$", plate_custom_name, re.I) and not re.match(r"^plate\s*\d+$", plate_custom_name, re.I):
                final_name = plate_custom_name
            elif clean_filename:
                plate_match = re.search(r"(?:plate|placa)[-_ ]*(\d+)", clean_filename, re.I)
                if plate_match:
                    final_name = f"Placa {plate_match.group(1)}"
                elif len(plate_nodes) == 1:
                    final_name = clean_filename
                else:
                    final_name = f"{clean_filename} - Placa {idx + 1}"
            else:
                final_name = f"Placa {idx + 1}"

            plates.append({
                "name": final_name,
                "print_time_hours": round(prediction_secs / 3600.0, 2),
                "part_weight_g": round(part_weight, 2),
                "purge_weight_g": round(purge_g, 2),
                "filament_type": ", ".join(fil_types) if fil_types else "PLA",
                "slicer_filament_profile": plate_filament_profile or None,
                "filament_slot": plate_filament_slot,
                "filament_color_hex": plate_filament_color_hex,
            })

        # Complement plates with embedded G-code inside the ZIP archive
        gcode_names = [n for n in zf.namelist() if n.lower().endswith(".gcode") and not n.endswith("/") and not n.endswith("\\")]
        if gcode_names:
            for idx, p in enumerate(plates):
                matched_gname = next((g for g in gcode_names if f"plate_{idx+1}" in g.lower() or f"placa_{idx+1}" in g.lower()), None)
                if not matched_gname and idx < len(gcode_names):
                    matched_gname = gcode_names[idx]
                if matched_gname:
                    gtext = zf.read(matched_gname).decode("utf-8", errors="ignore")
                    meta = python_parse_gcode(gtext)
                    if p["print_time_hours"] == 0 and meta["print_time_hours"] > 0:
                        p["print_time_hours"] = meta["print_time_hours"]
                    if p["part_weight_g"] == 0 and meta["part_weight_g"] > 0:
                        p["part_weight_g"] = meta["part_weight_g"]
                    if p.get("filament_type") in [None, "", "PLA"] and meta.get("filament_type"):
                        p["filament_type"] = meta["filament_type"]
                    if not p.get("slicer_filament_profile") and meta.get("slicer_filament_profile"):
                        p["slicer_filament_profile"] = meta["slicer_filament_profile"]
                    if not p.get("filament_color_hex") and meta.get("filament_color_hex"):
                        p["filament_color_hex"] = meta["filament_color_hex"]
                    if not p.get("filament_slot") and meta.get("filament_slot"):
                        p["filament_slot"] = meta["filament_slot"]

        # Check config files in zip (project_settings.config, model_settings.config, etc.)
        cfg_names = [n for n in zf.namelist() if any(k in n.lower() for k in ["project_settings.config", "model_settings.config", "slic3r_pe.config", "prusaslicer.ini"]) and not n.lower().endswith("slice_info.config")]
        for cfg_name in cfg_names:
            try:
                import json
                cfg_raw = zf.read(cfg_name).decode("utf-8", errors="ignore")
                profiles = []
                types = []
                if cfg_raw.strip().startswith("{"):
                    cfg_json = json.loads(cfg_raw)
                    raw_prof = cfg_json.get("filament_settings_id", [])
                    if isinstance(raw_prof, list):
                        profiles = [str(x).strip().strip('"\'') for x in raw_prof]
                    elif isinstance(raw_prof, str):
                        profiles = [raw_prof.strip().strip('"\'')]
                    raw_types = cfg_json.get("filament_type", [])
                    if isinstance(raw_types, list):
                        types = [str(x).strip().strip('"\'') for x in raw_types]
                else:
                    m = re.search(r"filament_settings_id\s*=\s*(.+)", cfg_raw)
                    if m:
                        profiles = [s.strip().strip('"\'') for s in m.group(1).split(";") if s.strip()]
                    tm = re.search(r"filament_type\s*=\s*(.+)", cfg_raw)
                    if tm:
                        types = [s.strip().strip('"\'') for s in tm.group(1).split(";") if s.strip()]

                if profiles or types:
                    for idx, p in enumerate(plates):
                        slot = p.get("filament_slot")
                        slot_idx = (slot - 1) if (slot and 0 < slot <= len(profiles)) else (idx if idx < len(profiles) else 0)
                        if (not p.get("slicer_filament_profile") or p.get("slicer_filament_profile") == p.get("filament_type")) and slot_idx < len(profiles):
                            p["slicer_filament_profile"] = profiles[slot_idx]
                        if p.get("filament_type") in [None, "", "PLA"] and slot_idx < len(types):
                            p["filament_type"] = types[slot_idx]
                    break
            except Exception:
                pass

        for p in plates:
            if not p.get("slicer_filament_profile") and p.get("filament_type"):
                p["slicer_filament_profile"] = p["filament_type"]
            if p.get("slicer_filament_profile"):
                p["slicer_filament_profile"] = clean_filament_profile_name(p["slicer_filament_profile"], filename) or None

    # 2. Look for embedded G-code inside .gcode.3mf
    if not plates or all(p["print_time_hours"] == 0 and p["part_weight_g"] == 0 for p in plates):
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

        gcode_names = [n for n in zf.namelist() if n.lower().endswith(".gcode") and not n.endswith("/") and not n.endswith("\\")]
        if gcode_names:
            gcode_names.sort(key=natural_sort_key)
            gcode_plates = []
            for idx, gname in enumerate(gcode_names):
                gtext = zf.read(gname).decode("utf-8", errors="ignore")
                meta = python_parse_gcode(gtext, filename)

                base = gname.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                base_clean = re.sub(r'\.gcode$', '', base, flags=re.IGNORECASE)
                plate_match = re.search(r'(?:plate|placa)[-_ ]*(\d+)', base_clean, re.IGNORECASE)
                if len(gcode_names) == 1 and clean_filename:
                    clean_num = re.search(r'(?:plate|placa)[-_ ]*(\d+)', clean_filename, re.IGNORECASE)
                    p_name = f"Placa {clean_num.group(1)}" if clean_num else clean_filename
                elif plate_match:
                    p_name = f"Placa {plate_match.group(1)}"
                else:
                    p_name = base_clean or f"Placa {idx + 1}"

                prof = clean_filament_profile_name(meta.get("slicer_filament_profile") or meta["filament_type"] or "PLA", filename)
                gcode_plates.append({
                    "name": p_name,
                    "print_time_hours": meta["print_time_hours"],
                    "part_weight_g": meta["part_weight_g"],
                    "purge_weight_g": 0.0,
                    "filament_type": meta["filament_type"] or "PLA",
                    "slicer_filament_profile": prof or None,
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


def test_batch_seven_gcode_3mf_files():
    """
    Verifies the user requirement:
    Simulates dropping 7 .gcode.3mf files in batch.
    Asserts that:
    1. 7 distinct plates are created (one per file).
    2. Each plate has its correct respective time, part weight, and filament type.
    """
    import io
    import zipfile

    # Define 7 distinct plates with unique parameters
    file_specs = [
        {"name": "peca_01.gcode.3mf", "time_sec": 3600, "weight": 25.4, "mat": "PLA"},
        {"name": "peca_02.gcode.3mf", "time_sec": 7200, "weight": 52.8, "mat": "PETG"},
        {"name": "peca_03.gcode.3mf", "time_sec": 5400, "weight": 41.2, "mat": "ABS"},
        {"name": "peca_04.gcode.3mf", "time_sec": 1800, "weight": 14.5, "mat": "TPU"},
        {"name": "peca_05.gcode.3mf", "time_sec": 9000, "weight": 68.0, "mat": "PLA-CF"},
        {"name": "peca_06.gcode.3mf", "time_sec": 10800, "weight": 85.3, "mat": "PETG"},
        {"name": "peca_07.gcode.3mf", "time_sec": 2700, "weight": 19.7, "mat": "PLA"},
    ]

    batch_plates = []
    for spec in file_specs:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<config>
  <plate>
    <metadata key="index" value="1"/>
    <metadata key="prediction" value="{spec['time_sec']}"/>
    <metadata key="weight" value="{spec['weight']}"/>
    <filament id="1" type="{spec['mat']}" used_g="{spec['weight']}"/>
  </plate>
</config>"""
            zf.writestr("Metadata/slice_info.xml", xml)

        # Parse each file with its filename
        res = python_parse_3mf(buf.getvalue(), filename=spec["name"])
        assert len(res) == 1, f"Expected 1 plate from {spec['name']}, got {len(res)}"
        batch_plates.extend(res)

    assert len(batch_plates) == 7, f"Expected 7 plates created in total, got {len(batch_plates)}"

    for idx, (spec, plate) in enumerate(zip(file_specs, batch_plates), 1):
        expected_hours = round(spec["time_sec"] / 3600.0, 2)
        assert plate["name"] == spec["name"].replace(".gcode.3mf", ""), f"Plate name mismatch on plate {idx}"
        assert plate["print_time_hours"] == expected_hours, f"Time mismatch on plate {idx}: expected {expected_hours}, got {plate['print_time_hours']}"
        assert plate["part_weight_g"] == spec["weight"], f"Weight mismatch on plate {idx}: expected {spec['weight']}, got {plate['part_weight_g']}"
        assert plate["filament_type"] == spec["mat"], f"Filament mismatch on plate {idx}: expected {spec['mat']}, got {plate['filament_type']}"


def test_gcode_3mf_slice_info_with_hhmmss_and_attributes():
    """
    Verifies that slice_info.xml with formatted HH:MM:SS times and XML attributes
    (used in various Bambu Studio / OrcaSlicer releases) parses correctly.
    """
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<config>
  <plate index="1" prediction="02:30:00" weight="64.2">
    <filament id="1" type="PETG" used_g="64.2"/>
  </plate>
</config>"""
        zf.writestr("Metadata/slice_info.xml", xml)

    res = python_parse_3mf(buf.getvalue(), filename="Suporte_Frontal.gcode.3mf")
    assert len(res) == 1
    assert res[0]["name"] == "Suporte_Frontal"
    assert res[0]["print_time_hours"] == 2.50
    assert res[0]["part_weight_g"] == 64.2
    assert res[0]["filament_type"] == "PETG"


def test_gcode_3mf_complements_missing_time_from_embedded_gcode():
    """
    Verifies that if slice_info.xml has 0 time (prediction missing),
    the parser inspects embedded Metadata/plate_1.gcode to complement time and weight.
    """
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<config>
  <plate>
    <metadata key="index" value="1"/>
    <metadata key="weight" value="38.5"/>
    <filament id="1" type="ABS" used_g="38.5"/>
  </plate>
</config>"""
        zf.writestr("Metadata/slice_info.xml", xml)
        gcode = """; generated by OrcaSlicer
; TIME: 7200
; Filament used: 38.5g
; filament_type = ABS
G28
"""
        zf.writestr("Metadata/plate_1.gcode", gcode)

    res = python_parse_3mf(buf.getvalue(), filename="Tampa.gcode.3mf")
    assert len(res) == 1
    assert res[0]["name"] == "Tampa"
    assert res[0]["print_time_hours"] == 2.00
    assert res[0]["part_weight_g"] == 38.5
    assert res[0]["filament_type"] == "ABS"


def test_gcode_filament_settings_id_and_vendor_extraction():
    """
    Verifies that Bambu Studio and OrcaSlicer G-code headers with filament_settings_id
    and filament_vendor correctly extract the filament profile string.
    """
    sample = """
; generated by Bambu Studio
; total filament used [g] = 52.3
; total estimated time: 01:45:00
; filament_type = PLA
; filament_vendor = "Bambu Lab"
; filament_settings_id = "Bambu PLA Basic @BBL X1C"
G28
"""
    res = python_parse_gcode(sample)
    assert res["print_time_hours"] == 1.75
    assert res["part_weight_g"] == 52.3
    assert res["filament_type"] == "PLA"
    assert res["slicer_filament_profile"] == "Bambu PLA Basic @BBL X1C"


def test_gcode_3mf_filament_profile_from_embedded_gcode():
    """
    Verifies that a .gcode.3mf with embedded plate_1.gcode containing filament_settings_id
    correctly populates slicer_filament_profile.
    """
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<config>
  <plate index="1" prediction="3600" weight="25.0">
    <filament id="1" type="PLA" used_g="25.0"/>
  </plate>
</config>"""
        zf.writestr("Metadata/slice_info.xml", xml)
        gcode = """; Bambu Studio plate 1
; filament_settings_id = "PolyLite PLA @Custom"
; filament_vendor = "Polymaker"
; filament_type = PLA
; total estimated time: 1h 00m
; filament used [g] = 25.0
"""
        zf.writestr("Metadata/plate_1.gcode", gcode)

    res = python_parse_3mf(buf.getvalue(), filename="peca.gcode.3mf")
    assert len(res) == 1
    assert res[0]["name"] == "peca"
    assert res[0]["slicer_filament_profile"] == "Polymaker PolyLite PLA @Custom"


def test_gcode_3mf_filament_profile_from_project_settings_config():
    """
    Verifies that 3MF archives with Metadata/project_settings.config extract
    filament profile names from the JSON filament_settings_id list.
    """
    import io
    import zipfile
    import json

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<config>
  <plate index="1" prediction="5400" weight="40.0">
    <filament id="1" type="PETG" used_g="40.0"/>
  </plate>
</config>"""
        zf.writestr("Metadata/slice_info.xml", xml)
        cfg = {
            "filament_settings_id": ["Prusament PETG @MK4", "Generic PLA"],
            "filament_type": ["PETG", "PLA"]
        }
        zf.writestr("Metadata/project_settings.config", json.dumps(cfg))

    res = python_parse_3mf(buf.getvalue(), filename="engrenagem.gcode.3mf")
    assert len(res) == 1
    assert res[0]["name"] == "engrenagem"
    assert res[0]["slicer_filament_profile"] == "Prusament PETG @MK4"


def test_gcode_3mf_filament_profile_from_slice_info_tray_info_idx():
    """
    Verifies that slice_info.xml with tray_info_idx attribute in <filament>
    is recognized as the slicer filament profile.
    """
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<config>
  <plate index="1" prediction="7200" weight="80.0">
    <filament id="1" type="PLA" tray_info_idx="Bambu PLA Matte" used_g="80.0"/>
  </plate>
</config>"""
        zf.writestr("Metadata/slice_info.xml", xml)

    res = python_parse_3mf(buf.getvalue(), filename="gabinete.3mf")
    assert len(res) == 1
    assert res[0]["name"] == "gabinete"
    assert res[0]["slicer_filament_profile"] == "Bambu PLA Matte"


def test_clean_filament_profile_removes_file_references():
    """
    Verifies that file references such as '(patolino-kratos.3mf)' or '[model.gcode]'
    embedded by Bambu Studio/OrcaSlicer inside filament presets are cleanly stripped.
    """
    sample_gcode = """; generated by BambuStudio
; filament_settings_id = "3D Prime PLA Basic(patolino-kratos.3mf)"
; estimated printing time (normal mode) = 2h 15m
; filament used [g] = 60.5
; filament_type = PLA
"""
    res_gcode = python_parse_gcode(sample_gcode, filename="patolino-kratos.gcode")
    assert res_gcode["slicer_filament_profile"] == "3D Prime PLA Basic"

    # Also test with 3MF slice_info.xml
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<config>
  <plate index="1" prediction="5400" weight="45.0">
    <filament id="1" type="PLA" tray_info_idx="3D Prime PLA Basic(patolino-kratos.3mf)" used_g="45.0"/>
  </plate>
</config>"""
        zf.writestr("Metadata/slice_info.xml", xml)

    res_3mf = python_parse_3mf(buf.getvalue(), filename="patolino-kratos.gcode.3mf")
    assert len(res_3mf) == 1
    assert res_3mf[0]["slicer_filament_profile"] == "3D Prime PLA Basic"


def test_orcaslicer_multi_slot_gcode_resolution():
    sample_gcode = """; generated by OrcaSlicer
; filament: 2
; filament_settings_id = "3D Prime PLA Basic";"Voolt3D PLA Premium 0.4";"3D Prime PLA Basic"
; filament_vendor = "3D Prime";Voolt3D;"3D Prime"
; filament_type = PLA;PLA;PLA
; filament_colour = #9D432C;#F72323;#A6A9AA
; estimated printing time (normal mode) = 2h 46m 49s
; filament used [g] = 29.11
"""
    res = python_parse_gcode(sample_gcode, filename="patolino-kratos-4-vermelho.gcode")
    assert res["filament_slot"] == 2
    assert res["slicer_filament_profile"] == "Voolt3D PLA Premium 0.4"
    assert res["filament_type"] == "PLA"
    assert res["filament_color_hex"] == "#F72323"


def test_orcaslicer_slot4_petg_gcode_resolution():
    sample_gcode = """; generated by OrcaSlicer
; filament: 4
; filament_settings_id = "3D Prime PLA Basic";"Voolt3D PLA Premium 0.4";"3D Prime PLA Basic";"Soleyin PETG Basic @BBL A1"
; filament_vendor = "3D Prime";Voolt3D;"3D Prime";Soleyin
; filament_type = PLA;PLA;PLA;PETG
; filament_colour = #9D432C;#F72323;#A6A9AA;#FFFFFF
; estimated printing time (normal mode) = 15m 12s
; filament used [g] = 2.40
"""
    res = python_parse_gcode(sample_gcode, filename="patolino-kratos-5-branco.gcode")
    assert res["filament_slot"] == 4
    assert res["slicer_filament_profile"] == "Soleyin PETG Basic @BBL A1"
    assert res["filament_type"] == "PETG"
    assert res["filament_color_hex"] == "#FFFFFF"


def python_analyze_gcode_layers(gcode_text: str, total_plate_weight: float = 0.0, total_plate_time_hours: float = 0.0, filament_density: float = 1.24):
    """
    Python mirror of analyzeGcodeLayers from frontend/js/parsers/gcode.js.
    """
    lines = gcode_text.splitlines()
    relative_e = False
    cum_extrusion_mm = 0.0
    last_e = 0.0
    max_e_in_segment = 0.0
    rel_e_pos = 0.0
    current_z = 0.20
    current_layer_index = 1
    current_time_elapsed_sec = 0.0
    initial_m73_remaining_min = None
    layer_has_extrusion = False
    comment_layer_pending = False
    layers = []

    def finalize_layer(layer_idx, z_val, time_sec):
        nonlocal layers, cum_extrusion_mm
        layers.append({
            "layer": layer_idx,
            "z": round(z_val, 3),
            "cum_extrusion_mm": cum_extrusion_mm,
            "time_elapsed_sec": time_sec
        })

    for line in lines:
        raw = line.strip()
        if not raw:
            continue

        if raw.startswith("M83"):
            relative_e = True
            continue
        elif raw.startswith("M82"):
            relative_e = False
            continue

        if raw.startswith("M73"):
            m = re.search(r"R\s*(\d+)", raw, re.I)
            if m:
                rem_min = int(m.group(1))
                if initial_m73_remaining_min is None or rem_min > initial_m73_remaining_min:
                    initial_m73_remaining_min = rem_min
                current_time_elapsed_sec = max(0, initial_m73_remaining_min - rem_min) * 60

        if raw.startswith(";TIME_ELAPSED:"):
            m = re.search(r";TIME_ELAPSED:\s*([\d\.]+)", raw)
            if m:
                current_time_elapsed_sec = float(m.group(1))

        is_layer_transition = False
        if re.search(r"^;\s*(?:LAYER_CHANGE|BEFORE_LAYER_CHANGE)", raw, re.I):
            is_layer_transition = True
            comment_layer_pending = True

        l_match = re.search(r"^;\s*(?:LAYER\s*[:=]\s*(\d+)|layer\s+(\d+))", raw, re.I)
        if l_match:
            is_layer_transition = True
            comment_layer_pending = True

        z_match = re.search(r"^;\s*Z\s*[:=]\s*([\d\.]+)", raw, re.I)
        if z_match:
            current_z = float(z_match.group(1))

        if raw.startswith(("G0", "G1", "G2", "G3", "G92")):
            z_cmd = re.search(r"\bZ\s*([\d\.-]+)", raw, re.I)
            if z_cmd:
                try:
                    new_z = float(z_cmd.group(1))
                    if new_z > current_z:
                        if not comment_layer_pending and layer_has_extrusion and (new_z - current_z >= 0.05):
                            is_layer_transition = True
                        current_z = new_z
                except ValueError:
                    pass
                comment_layer_pending = False

            e_cmd = re.search(r"\bE\s*([\d\.-]+)", raw, re.I)
            if e_cmd:
                try:
                    e_val = float(e_cmd.group(1))
                    if raw.startswith("G92"):
                        last_e = e_val
                        max_e_in_segment = e_val
                        rel_e_pos = 0.0
                    else:
                        if relative_e:
                            if e_val < 0:
                                rel_e_pos += e_val
                            else:
                                unretract = min(e_val, -rel_e_pos) if rel_e_pos < 0 else 0.0
                                true_ext = e_val - unretract
                                rel_e_pos += e_val
                                if rel_e_pos > 0:
                                    rel_e_pos = 0.0
                                cum_extrusion_mm += true_ext
                                if true_ext > 0:
                                    layer_has_extrusion = True
                        else:
                            if e_val > max_e_in_segment:
                                delta = e_val - max_e_in_segment
                                cum_extrusion_mm += delta
                                max_e_in_segment = e_val
                                if delta > 0:
                                    layer_has_extrusion = True
                            last_e = e_val
                except ValueError:
                    pass

        if is_layer_transition and layer_has_extrusion:
            finalize_layer(current_layer_index, current_z, current_time_elapsed_sec)
            current_layer_index += 1
            layer_has_extrusion = False

    if layer_has_extrusion and (not layers or layers[-1]["layer"] != current_layer_index):
        finalize_layer(current_layer_index, current_z, current_time_elapsed_sec)

    if not layers:
        layers.append({"layer": 1, "z": current_z, "cum_extrusion_mm": cum_extrusion_mm, "time_elapsed_sec": current_time_elapsed_sec})

    total_extrusion = cum_extrusion_mm
    volumetric_total_g = (total_extrusion * math.pi * ((1.75 / 2.0) ** 2) / 1000.0) * filament_density
    final_total_weight_g = total_plate_weight if total_plate_weight > 0 else volumetric_total_g
    final_total_time_sec = (total_plate_time_hours * 3600.0) if total_plate_time_hours > 0 else (current_time_elapsed_sec or 3600.0)

    for i, l in enumerate(layers):
        l["layer"] = i + 1
        ratio = (l["cum_extrusion_mm"] / total_extrusion) if total_extrusion > 0 else 1.0
        l["percent"] = round(ratio * 100.0, 1)
        l["cum_weight_g"] = round(ratio * final_total_weight_g, 2)
        if l["time_elapsed_sec"] == 0.0 and ratio > 0:
            l["time_elapsed_sec"] = round(ratio * final_total_time_sec)
        l["time_elapsed_min"] = round(l["time_elapsed_sec"] / 60.0)

    def get_loss_at_layer(target_layer: int):
        idx = max(1, min(len(layers), int(target_layer))) - 1
        item = layers[idx]
        sec = int(item["time_elapsed_sec"])
        return {
            "layer": item["layer"],
            "z": item["z"],
            "weight_g": item["cum_weight_g"],
            "hours": sec // 3600,
            "minutes": (sec % 3600) // 60,
            "total_seconds": sec,
            "percent": item["percent"],
        }

    def get_loss_at_z(target_z: float):
        best_idx = 0
        for i, l in enumerate(layers):
            if l["z"] <= target_z:
                best_idx = i
            else:
                break
        return get_loss_at_layer(best_idx + 1)

    return {
        "total_layers": len(layers),
        "max_z": layers[-1]["z"],
        "total_extrusion_mm": round(total_extrusion, 2),
        "total_weight_g": round(final_total_weight_g, 2),
        "total_time_seconds": int(final_total_time_sec),
        "layers": layers,
        "get_loss_at_layer": get_loss_at_layer,
        "get_loss_at_z": get_loss_at_z,
    }


def test_analyze_gcode_layers_relative_mode_bambu():
    gcode = """
M83
G1 Z0.2 F18000
;LAYER_CHANGE
;Z:0.200
;AFTER_LAYER_CHANGE
;LAYER:1
M73 P0 R100
G1 X10 Y10 E10.0
G1 E-0.8 F3600 ; retract
G1 X15 Y15
G1 E0.8 F3600 ; unretract
G1 X20 Y10 E5.0
;LAYER_CHANGE
;Z:0.400
;AFTER_LAYER_CHANGE
;LAYER:2
M73 P50 R50
G1 X20 Y20 E15.0
;LAYER_CHANGE
;Z:0.600
;AFTER_LAYER_CHANGE
;LAYER:3
M73 P100 R0
G1 X30 Y30 E30.0
"""
    res = python_analyze_gcode_layers(gcode, total_plate_weight=60.0, total_plate_time_hours=1.6667)
    assert res["total_layers"] == 3
    assert res["max_z"] == 0.6
    assert res["total_extrusion_mm"] == 60.0 # 15 + 15 + 30

    l1 = res["get_loss_at_layer"](1)
    assert l1["layer"] == 1
    assert l1["weight_g"] == 15.0 # 15mm / 60mm * 60g = 15g (25%)
    assert l1["percent"] == 25.0

    l2 = res["get_loss_at_layer"](2)
    assert l2["layer"] == 2
    assert l2["weight_g"] == 30.0 # 30mm / 60mm * 60g = 30g (50%)
    assert l2["percent"] == 50.0
    assert l2["minutes"] == 50 # 100min total - 50min remaining = 50min elapsed

    l3 = res["get_loss_at_layer"](3)
    assert l3["layer"] == 3
    assert l3["weight_g"] == 60.0
    assert l3["percent"] == 100.0


def test_analyze_gcode_layers_absolute_mode_cura():
    gcode = """
;FLAVOR:Marlin
;TIME:3600
M82
G92 E0
;LAYER:0
;TIME_ELAPSED:60
G1 Z0.200 F1200
G1 X10 Y10 E10.0
G1 E8.0 F2400 ; retract 2mm
;LAYER:1
;TIME_ELAPSED:180
G1 Z0.400 F1200
G1 E10.0 F2400 ; unretract
G1 X20 Y20 E20.0
;LAYER:2
;TIME_ELAPSED:360
G92 E0
G1 Z0.600 F1200
G1 X30 Y30 E20.0
"""
    res = python_analyze_gcode_layers(gcode, total_plate_weight=40.0, total_plate_time_hours=0.1)
    assert res["total_layers"] == 3
    assert res["max_z"] == 0.6
    assert res["total_extrusion_mm"] == 40.0 # Layer 1: 10, Layer 2: 20-10=10, Layer 3: 20 -> total 40mm

    l1 = res["get_loss_at_layer"](1)
    assert l1["weight_g"] == 10.0 # 25% of 40g
    assert l1["total_seconds"] == 60

    l2 = res["get_loss_at_layer"](2)
    assert l2["weight_g"] == 20.0 # 50% of 40g
    assert l2["total_seconds"] == 180

    l3 = res["get_loss_at_layer"](3)
    assert l3["weight_g"] == 40.0 # 100% of 40g
    assert l3["total_seconds"] == 360


def test_analyze_gcode_layers_z_height_lookup():
    gcode = """
M83
G1 Z0.2 F18000
;LAYER:1
;Z:0.200
G1 X10 Y10 E10.0
;LAYER:2
;Z:0.400
G1 X20 Y20 E10.0
;LAYER:3
;Z:0.600
G1 X30 Y30 E20.0
"""
    res = python_analyze_gcode_layers(gcode, total_plate_weight=80.0)
    # Looking up Z = 0.3 should give Layer 1 (Z 0.2)
    at_z_03 = res["get_loss_at_z"](0.3)
    assert at_z_03["layer"] == 1
    assert at_z_03["weight_g"] == 20.0 # 10 / 40 * 80g = 20g

    # Looking up Z = 0.55 should give Layer 2 (Z 0.4)
    at_z_055 = res["get_loss_at_z"](0.55)
    assert at_z_055["layer"] == 2
    assert at_z_055["weight_g"] == 40.0 # 20 / 40 * 80g = 40g








