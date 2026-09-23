import re
import math
import pytest

def python_parse_gcode(gcode_text: str):
    """
    Python mirror of frontend/js/parsers/gcode.js to ensure regression prevention
    and strict parity for slicer metadata extraction.
    """
    print_time_seconds = 0
    filament_grams = 0
    filament_millimeters = 0
    filament_type = None

    lines = gcode_text.splitlines()
    header_lines = lines[:3000]
    footer_lines = lines[-3000:]
    candidate_lines = header_lines + footer_lines

    def extract_from_line(raw_line: str):
        nonlocal print_time_seconds, filament_grams, filament_millimeters, filament_type
        line = raw_line.strip()
        if not line.startswith(";"):
            return
        lower = line.lower()

        # 1. Cura / Creality time
        cura_time = re.search(r"^;\s*time(?:_elapsed)?:\s*(\d+)", lower)
        if cura_time and not print_time_seconds:
            print_time_seconds = int(cura_time.group(1))

        sec_tag = re.search(r"^;\s*(?:total_time|print_time|estimated_time|job_time|total_print_time)\s*[:=]\s*(\d+)(?:\s|$)", lower)
        if sec_tag and not print_time_seconds:
            print_time_seconds = int(sec_tag.group(1))

        time_keywords = [
            "estimated printing time", "total estimated time", "model printing time",
            "estimated print time", "printing time", "print time", "build time",
            "total time", "total print time", "estimated time", "job time", "print duration"
        ]
        if any(k in lower for k in time_keywords):
            target_segment = line
            if "total estimated time:" in lower:
                parts = re.split(r"total estimated time:", line, flags=re.I)
                if len(parts) > 1:
                    target_segment = parts[1]
            elif "estimated printing time (normal mode) =" in lower:
                parts = re.split(r"estimated printing time \(normal mode\) =", line, flags=re.I)
                if len(parts) > 1:
                    target_segment = parts[1]

            hhmmss = re.search(r"(?:=|\:|\s)\s*(\d{1,3}):(\d{2}):(\d{2})(?!\d)", target_segment)
            if hhmmss:
                h, m, s = int(hhmmss.group(1)), int(hhmmss.group(2)), int(hhmmss.group(3))
                calculated = (h * 3600) + (m * 60) + s
                if calculated > 0:
                    print_time_seconds = calculated
            else:
                hhmm = re.search(r"(?:=|\:)\s*(\d{1,3}):(\d{2})(?!\d)", target_segment)
                if hhmm:
                    h, m = int(hhmm.group(1)), int(hhmm.group(2))
                    calculated = (h * 3600) + (m * 60)
                    if calculated > 0:
                        print_time_seconds = calculated
                else:
                    d_match = re.search(r"(\d+)\s*d(?:ays?)?", target_segment, re.I)
                    h_match = re.search(r"(\d+(?:\.\d+)?)\s*h(?:ours?|r|oras?)?", target_segment, re.I)
                    m_match = re.search(r"(\d+(?:\.\d+)?)\s*m(?:in(?:ute)?s?)?", target_segment, re.I)
                    s_match = re.search(r"(\d+(?:\.\d+)?)\s*s(?:ec(?:ond)?s?)?", target_segment, re.I)
                    if d_match or h_match or m_match or s_match:
                        days = float(d_match.group(1)) if d_match else 0
                        hours = float(h_match.group(1)) if h_match else 0
                        mins = float(m_match.group(1)) if m_match else 0
                        secs = float(s_match.group(1)) if s_match else 0
                        calculated = round((days * 86400) + (hours * 3600) + (mins * 60) + secs)
                        if calculated > 0:
                            print_time_seconds = calculated

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
        mat_match = re.search(r"filament_type\s*=\s*([A-Za-z0-9_-]+)", line, re.I)
        if mat_match:
            filament_type = mat_match.group(1).strip()

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
