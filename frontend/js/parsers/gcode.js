/**
 * G-Code Metadata Extractor
 * Parses Cura, PrusaSlicer, SuperSlicer, Bambu Studio, OrcaSlicer, IdeaMaker, Creality Print, Klipper G-code headers and comments.
 */
function parseGcodeMetadata(gcodeText) {
    let printTimeSeconds = 0;
    let printTimePriority = 0; // 0 = none, 1 = generic, 2 = authoritative (normal mode, total estimated time, cura TIME)
    let filamentGrams = 0;
    let filamentMillimeters = 0;
    let filamentType = null;

    const lines = gcodeText.split('\n');
    // Top 3000 and bottom 3000 lines
    const headerLines = lines.slice(0, 3000);
    const footerLines = lines.slice(-3000);
    let candidateLines = [...headerLines, ...footerLines];

    function extractFromLine(rawLine) {
        const line = rawLine.trim();
        if (!line.startsWith(';')) return;
        const lower = line.toLowerCase();

        // Skip silent/stealth mode to ensure normal mode is never clobbered
        if (lower.includes('(silent mode)') || lower.includes('(stealth mode)')) {
            return;
        }

        // 1. Match Print Time
        // Cura / Creality: ;TIME:8130 or ; TIME: 8130 or ;TIME_ELAPSED:8130 (seconds only)
        const curaTimeMatch = lower.match(/^;\s*time(?:_elapsed)?:\s*(\d+)(?:\s*(?:s|sec|seconds)?\s*$|\s*$)/);
        if (curaTimeMatch && printTimePriority < 2) {
            printTimeSeconds = parseInt(curaTimeMatch[1], 10);
            printTimePriority = 2;
        }

        // Generic seconds tag: ;total_time: 5400, ;print_time = 5400, ;estimated_time: 5400
        const secTagMatch = lower.match(/^;\s*(?:total_time|print_time|estimated_time|job_time|total_print_time)\s*[:=]\s*(\d+)(?:\s*(?:s|sec|seconds)?\s*$|\s*$)/);
        if (secTagMatch && printTimePriority < 2) {
            printTimeSeconds = parseInt(secTagMatch[1], 10);
            printTimePriority = 1;
        }

        // Descriptive time strings:
        // Prusa / SuperSlicer / Orca / Bambu: ; estimated printing time (normal mode) = 1h 25m 30s
        // Bambu / Orca: ; model printing time: 1h 23m 45s; total estimated time: 1h 25m 10s
        const timeKeywords = [
            'estimated printing time (normal mode)', 'total estimated time', 'estimated printing time',
            'model printing time', 'estimated print time', 'printing time', 'print time', 'build time',
            'total time', 'total print time', 'estimated time', 'job time', 'print duration', 'time:'
        ];
        
        const matchedKw = timeKeywords.find(k => lower.includes(k));
        if (matchedKw) {
            const isHighPriority = matchedKw.includes('normal mode') || matchedKw.includes('total estimated time');
            if (isHighPriority || printTimePriority < 2) {
                // Extract segment specifically after keyword
                let targetSegment = line;
                const kwIdx = lower.indexOf(matchedKw);
                if (kwIdx !== -1) {
                    targetSegment = line.slice(kwIdx + matchedKw.length);
                }

                // Check HH:MM:SS format
                const hhmmss = targetSegment.match(/(?:=|\:|\s)\s*(\d{1,3}):(\d{2}):(\d{2})(?!\d)/);
                if (hhmmss) {
                    const h = parseInt(hhmmss[1], 10) || 0;
                    const m = parseInt(hhmmss[2], 10) || 0;
                    const s = parseInt(hhmmss[3], 10) || 0;
                    const calculated = (h * 3600) + (m * 60) + s;
                    if (calculated > 0) {
                        printTimeSeconds = calculated;
                        printTimePriority = isHighPriority ? 2 : 1;
                    }
                } else {
                    // Check HH:MM format (e.g. 1:30, 01:45)
                    const hhmm = targetSegment.match(/(?:=|\:|\s)\s*(\d{1,3}):(\d{2})(?!\d)/);
                    if (hhmm) {
                        const h = parseInt(hhmm[1], 10) || 0;
                        const m = parseInt(hhmm[2], 10) || 0;
                        const calculated = (h * 3600) + (m * 60);
                        if (calculated > 0) {
                            printTimeSeconds = calculated;
                            printTimePriority = isHighPriority ? 2 : 1;
                        }
                    } else {
                        // Check descriptive: 1d 2h 30m 15s or 1h 30m or 45m
                        const dMatch = targetSegment.match(/(\d+)\s*d(?:ays?)?\b/i);
                        const hMatch = targetSegment.match(/(\d+(?:\.\d+)?)\s*h(?:ours?|r|oras?)?\b/i);
                        const mMatch = targetSegment.match(/(\d+(?:\.\d+)?)\s*(?:m(?!m)(?:in(?:ute)?s?)?)\b/i);
                        const sMatch = targetSegment.match(/(\d+(?:\.\d+)?)\s*s(?:ec(?:ond)?s?)?\b/i);
                        if (dMatch || hMatch || mMatch || sMatch) {
                            const days = dMatch ? parseFloat(dMatch[1]) : 0;
                            const hours = hMatch ? parseFloat(hMatch[1]) : 0;
                            const mins = mMatch ? parseFloat(mMatch[1]) : 0;
                            const secs = sMatch ? parseFloat(sMatch[1]) : 0;
                            const calculated = Math.round((days * 86400) + (hours * 3600) + (mins * 60) + secs);
                            if (calculated > 0) {
                                printTimeSeconds = calculated;
                                printTimePriority = isHighPriority ? 2 : 1;
                            }
                        }
                    }
                }
            }
        }

        // 2. Match Filament Weight
        // Prusa / SuperSlicer / Bambu: ; filament used [g] = 45.2 or ; total filament used [g] = 45.2
        if (lower.includes('filament used [g]') || lower.includes('filament used [grams]')) {
            const numbers = line.match(/[0-9]+(?:\.[0-9]+)?/g);
            if (numbers && numbers.length > 0) {
                const totalG = numbers.reduce((acc, n) => acc + (parseFloat(n) || 0), 0);
                if (totalG > 0) filamentGrams = totalG;
            }
        }

        // Cura / Orca: ;Filament weight = 45.2g or ; filament used [g] : 45.2 or ;Filament used: 42.1g
        const curaWeightMatch = line.match(/filament\s+(?:weight|used)\s*[:=]\s*([0-9.]+)\s*g?/i);
        if (curaWeightMatch && !filamentGrams && !lower.includes('[mm]') && !lower.includes('[m]')) {
            filamentGrams = parseFloat(curaWeightMatch[1]) || 0;
        }

        // 3. Match Filament Length if weight not directly found
        if (lower.match(/filament used\s*\[?(?:mm|m)\]?/) && !filamentGrams) {
            const mMatch = line.match(/[:=]\s*([0-9.]+)\s*m(?:$|\s)/i);
            const mmMatch = line.match(/[:=]\s*([0-9.]+)\s*(?:mm)?(?:$|\s)/i);
            if (mMatch) {
                filamentMillimeters = (parseFloat(mMatch[1]) || 0) * 1000;
            } else if (mmMatch) {
                filamentMillimeters = parseFloat(mmMatch[1]) || 0;
            }
        }

        // 4. Filament Material (PLA, PETG, ABS, etc.)
        // Prusa / Bambu / Orca: ; filament_type = PLA
        const matMatch = line.match(/filament_type(?:\s*\[\d+\])?\s*=\s*([A-Za-z0-9_-]+)/i);
        if (matMatch && !filamentType) {
            filamentType = matMatch[1].trim();
        }

        // Cura: ;MATERIAL:PLA or ;MATERIAL_1:PLA
        const curaMatMatch = line.match(/^;\s*material(?:_\d+)?:\s*([A-Za-z0-9_-]+)/i);
        if (curaMatMatch && !filamentType) {
            filamentType = curaMatMatch[1].trim();
        }
    }

    for (const rawLine of candidateLines) {
        extractFromLine(rawLine);
    }

    // Fallback: if either print time or filament weight not found, scan any comment line in full file
    if ((!printTimeSeconds || !filamentGrams) && lines.length > 6000) {
        for (let i = 3000; i < lines.length - 3000; i++) {
            if (lines[i].charCodeAt(0) === 59) { // starts with ';'
                extractFromLine(lines[i]);
                if (printTimeSeconds && filamentGrams) break;
            }
        }
    }

    // Approximate weight from length if needed (1.75mm PLA ~ 1.24 g/cm3)
    if (!filamentGrams && filamentMillimeters > 0) {
        const radiusMm = 1.75 / 2;
        const volumeMm3 = Math.PI * (radiusMm * radiusMm) * filamentMillimeters;
        const volumeCm3 = volumeMm3 / 1000;
        filamentGrams = volumeCm3 * 1.24;
    }

    const printTimeHours = printTimeSeconds > 0 ? (printTimeSeconds / 3600) : 0;

    return {
        print_time_hours: parseFloat(printTimeHours.toFixed(2)),
        part_weight_g: parseFloat(filamentGrams.toFixed(2)),
        filament_type: filamentType,
    };
}
