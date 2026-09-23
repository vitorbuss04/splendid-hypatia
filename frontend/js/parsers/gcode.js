/**
 * G-Code Metadata Extractor
 * Parses Cura, PrusaSlicer, SuperSlicer, Bambu Studio and OrcaSlicer G-code headers and comments.
 */
function parseGcodeMetadata(gcodeText) {
    let printTimeSeconds = 0;
    let filamentGrams = 0;
    let filamentMillimeters = 0;
    let filamentType = null;

    // Read top 500 and bottom 500 lines as slicers write metadata either at start or at end
    const lines = gcodeText.split('\n');
    const headerLines = lines.slice(0, 500);
    const footerLines = lines.slice(-500);
    const candidateLines = [...headerLines, ...footerLines];

    for (const rawLine of candidateLines) {
        const line = rawLine.trim();
        if (!line.startsWith(';')) continue;

        // 1. Match Print Time
        // Prusa / SuperSlicer / Orca: ; estimated printing time (normal mode) = 1h 25m 30s
        if (line.includes('estimated printing time') || line.includes('print time') || line.includes('build time') || line.includes('total time')) {
            // Check HH:MM:SS format first
            const hhmmss = line.match(/(?:=|\:)\s*(\d+):(\d+):(\d+)/);
            if (hhmmss) {
                const h = parseInt(hhmmss[1], 10) || 0;
                const m = parseInt(hhmmss[2], 10) || 0;
                const s = parseInt(hhmmss[3], 10) || 0;
                const calculated = (h * 3600) + (m * 60) + s;
                if (calculated > 0) printTimeSeconds = calculated;
            } else {
                const dMatch = line.match(/(\d+)\s*d(?:ays?)?/i);
                const hMatch = line.match(/(\d+)\s*h(?:ours?|r)?/i);
                const mMatch = line.match(/(\d+)\s*m(?:in(?:ute)?s?)?/i);
                const sMatch = line.match(/(\d+)\s*s(?:ec(?:ond)?s?)?/i);
                if (dMatch || hMatch || mMatch || sMatch) {
                    const days = dMatch ? parseInt(dMatch[1], 10) : 0;
                    const hours = hMatch ? parseInt(hMatch[1], 10) : 0;
                    const mins = mMatch ? parseInt(mMatch[1], 10) : 0;
                    const secs = sMatch ? parseInt(sMatch[1], 10) : 0;
                    const calculated = (days * 86400) + (hours * 3600) + (mins * 60) + secs;
                    if (calculated > 0) printTimeSeconds = calculated;
                }
            }
        }

        // Cura: ;TIME:8130
        const curaTimeMatch = line.match(/^;TIME:\s*(\d+)/i);
        if (curaTimeMatch && !printTimeSeconds) {
            printTimeSeconds = parseInt(curaTimeMatch[1], 10);
        }

        // 2. Match Filament Weight
        // Prusa / SuperSlicer: ; filament used [g] = 45.2 or multi-material = 12.5, 4.3
        if (line.match(/filament used\s*\[g\]/i)) {
            const numbers = line.match(/[0-9]+(?:\.[0-9]+)?/g);
            if (numbers && numbers.length > 0) {
                const totalG = numbers.reduce((acc, n) => acc + (parseFloat(n) || 0), 0);
                if (totalG > 0) filamentGrams = totalG;
            }
        }

        // Cura / Orca: ;Filament weight = 45.2g or ; filament used [g] : 45.2
        const curaWeightMatch = line.match(/filament (?:weight|used)\s*[:=]\s*([0-9.]+)\s*g?/i);
        if (curaWeightMatch && !filamentGrams && !line.includes('[mm]') && !line.includes('[m]')) {
            filamentGrams = parseFloat(curaWeightMatch[1]) || 0;
        }

        // 3. Match Filament Length if weight not directly found
        // ; filament used [mm] = 15200.5 or ;Filament used: 3.45m
        if (line.match(/filament used\s*\[?(?:mm|m)\]?/i) && !filamentGrams) {
            const mMatch = line.match(/[:=]\s*([0-9.]+)\s*m(?:$|\s)/i);
            const mmMatch = line.match(/[:=]\s*([0-9.]+)\s*(?:mm)?(?:$|\s)/i);
            if (mMatch) {
                filamentMillimeters = (parseFloat(mMatch[1]) || 0) * 1000;
            } else if (mmMatch) {
                filamentMillimeters = parseFloat(mmMatch[1]) || 0;
            }
        }

        // 4. Filament Material (PLA, PETG, ABS)
        const matMatch = line.match(/filament_type\s*=\s*([A-Za-z0-9_-]+)/i);
        if (matMatch) {
            filamentType = matMatch[1].trim();
        }
    }

    // If weight wasn't found but length was, approximate with standard 1.75mm PLA (1.24 g/cm3)
    if (!filamentGrams && filamentMillimeters > 0) {
        // Volume = pi * r^2 * h -> pi * (0.875 mm)^2 * h mm
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
