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

        // 1. Match Print Time
        // Prusa / SuperSlicer / Orca: ; estimated printing time (normal mode) = 1h 25m 30s
        if (line.includes('estimated printing time') || line.includes('print time')) {
            const timeMatch = line.match(/(?:(?:(\d+)d\s*)?(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?)|(?:(\d+):(\d+):(\d+))/i);
            if (timeMatch) {
                if (timeMatch[5] !== undefined) {
                    // HH:MM:SS format
                    const h = parseInt(timeMatch[5], 10) || 0;
                    const m = parseInt(timeMatch[6], 10) || 0;
                    const s = parseInt(timeMatch[7], 10) || 0;
                    printTimeSeconds = (h * 3600) + (m * 60) + s;
                } else {
                    const days = parseInt(timeMatch[1], 10) || 0;
                    const hours = parseInt(timeMatch[2], 10) || 0;
                    const mins = parseInt(timeMatch[3], 10) || 0;
                    const secs = parseInt(timeMatch[4], 10) || 0;
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
        // Prusa / SuperSlicer: ; filament used [g] = 45.2
        const prusaWeightMatch = line.match(/^;(?:\s*filament used \[g\]\s*=\s*)([0-9.]+)/i);
        if (prusaWeightMatch) {
            filamentGrams = parseFloat(prusaWeightMatch[1]);
        }

        // Cura / Orca: ;Filament weight = 45.2g or ; filament used [g] : 45.2
        const curaWeightMatch = line.match(/filament (?:weight|used)\s*[:=]\s*([0-9.]+)\s*g/i);
        if (curaWeightMatch && !filamentGrams) {
            filamentGrams = parseFloat(curaWeightMatch[1]);
        }

        // 3. Match Filament Length if weight not directly found
        // ; filament used [mm] = 15200.5
        const lengthMatch = line.match(/filament used\s*\[?(?:mm|m)\]?\s*[:=]\s*([0-9.]+)/i);
        if (lengthMatch && !filamentMillimeters) {
            filamentMillimeters = parseFloat(lengthMatch[1]);
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
