/**
 * Cleans slicer profile names by removing embedded project/file references,
 * e.g. "3D Prime PLA Basic(patolino-kratos.3mf)" -> "3D Prime PLA Basic"
 */
function cleanFilamentProfileName(profile, fileName = '') {
    if (!profile || typeof profile !== 'string') return '';
    let cleaned = profile.trim().replace(/^["']|["']$/g, '');

    // Remove file references in parentheses or brackets, e.g. (patolino-kratos.3mf), [part.gcode]
    cleaned = cleaned.replace(/\s*[\(\[][^()\[\]]*\.[a-z0-9_-]{2,6}\s*[\)\]]/gi, '');

    // If fileName is provided, remove parenthesized match of base filename if present
    if (fileName && typeof fileName === 'string') {
        const base = fileName.replace(/^.*[\\\/]/, '').replace(/\.(?:gcode\.3mf|3mf|gcode|stl|step|stp|obj)$/i, '').trim();
        if (base && base.length >= 2) {
            const escaped = base.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            cleaned = cleaned.replace(new RegExp(`\\s*[\\(\\[]\\s*${escaped}(?:\\.[^()\\[\\]]+)?\\s*[\\)\\]]`, 'gi'), '');
        }
    }

    cleaned = cleaned.replace(/\s{2,}/g, ' ').trim();
    return cleaned;
}

if (typeof window !== 'undefined') {
    window.cleanFilamentProfileName = cleanFilamentProfileName;
}

function parseGcodeMetadata(gcodeText, fileName = '') {
    let printTimeSeconds = 0;
    let printTimePriority = 0; // 0 = none, 1 = generic, 2 = authoritative (normal mode, total estimated time, cura TIME)
    let filamentGrams = 0;
    let filamentMillimeters = 0;
    let filamentType = null;
    let filamentProfile = null;
    let filamentVendor = null;

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
        // Prusa / Bambu / Orca: ; filament_type = PLA or ; filament_type = PLA;PLA;PLA;PETG
        const matMatch = line.match(/^;\s*filament_type(?:\s*\[\d+\])?\s*=\s*(.+)/i);
        if (matMatch && filamentTypeParts.length === 0) {
            filamentTypeParts = matMatch[1].trim().split(';').map(s => s.trim().replace(/^["']|["']$/g, '')).filter(Boolean);
        }

        // Cura: ;MATERIAL:PLA or ;MATERIAL_1:PLA
        const curaMatMatch = line.match(/^;\s*material(?:_\d+)?:\s*([A-Za-z0-9_-]+)/i);
        if (curaMatMatch && !filamentType) {
            filamentType = curaMatMatch[1].trim();
        }

        // 5. Active Filament Slot (Bambu Studio / OrcaSlicer e.g. ; filament: 2)
        if (!activeSlot) {
            const slotMatch = line.match(/^;\s*(?:filament|filament_slot|tray_id)\s*[:=]\s*(\d+)/i);
            if (slotMatch) {
                activeSlot = parseInt(slotMatch[1], 10);
            }
        }

        // 6. Filament Settings / Profile / Vendor / Colour (Bambu Studio, OrcaSlicer, PrusaSlicer, Cura, etc.)
        // e.g. ; filament_settings_id = "Bambu PLA Basic @BBL X1C"
        const settingsMatch = line.match(/filament_settings_id(?:\s*\[\d+\])?\s*=\s*(.+)/i);
        if (settingsMatch && filamentSettingsParts.length === 0) {
            filamentSettingsParts = settingsMatch[1].trim().split(';').map(s => s.trim().replace(/^["']|["']$/g, '')).filter(Boolean);
        }

        // e.g. ; filament_vendor = "Bambu Lab"
        const vendorMatch = line.match(/filament_vendor(?:\s*\[\d+\])?\s*=\s*(.+)/i);
        if (vendorMatch && filamentVendorParts.length === 0) {
            filamentVendorParts = vendorMatch[1].trim().split(';').map(s => s.trim().replace(/^["']|["']$/g, '')).filter(Boolean);
        }

        // e.g. ; filament_colour = #9D432C;#F72323
        const colMatch = line.match(/filament_colou?r(?:\s*\[\d+\])?\s*=\s*(.+)/i);
        if (colMatch && filamentColourParts.length === 0) {
            filamentColourParts = colMatch[1].trim().split(';').map(s => s.trim().replace(/^["']|["']$/g, '')).filter(Boolean);
        }

        // Cura filament name: ;FILAMENT_NAME:Generic PLA
        const curaNameMatch = line.match(/^;\s*filament_name(?:_\d+)?:\s*(.+)/i);
        if (curaNameMatch && !filamentProfile) {
            filamentProfile = curaNameMatch[1].trim().replace(/^["']|["']$/g, '');
        }
    }

    let activeSlot = null;
    let filamentSettingsParts = [];
    let filamentVendorParts = [];
    let filamentTypeParts = [];
    let filamentColourParts = [];

    for (const rawLine of candidateLines) {
        extractFromLine(rawLine);
    }

    // Resolve target slot index (0-based, while activeSlot is 1-based)
    const targetIdx = (activeSlot && activeSlot > 0) ? (activeSlot - 1) : 0;
    if (filamentSettingsParts.length > 0 && !filamentProfile) {
        filamentProfile = filamentSettingsParts[targetIdx] || filamentSettingsParts[0];
    }
    if (filamentVendorParts.length > 0 && !filamentVendor) {
        filamentVendor = filamentVendorParts[targetIdx] || filamentVendorParts[0];
    }
    if (filamentTypeParts.length > 0 && !filamentType) {
        filamentType = filamentTypeParts[targetIdx] || filamentTypeParts[0];
    }
    let filamentColourHex = null;
    if (filamentColourParts.length > 0) {
        filamentColourHex = filamentColourParts[targetIdx] || filamentColourParts[0];
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

    let slicerFilamentProfile = null;
    if (filamentProfile) {
        slicerFilamentProfile = filamentProfile;
        if (filamentVendor) {
            const vWords = filamentVendor.toLowerCase().split(/\s+/).filter(w => w.length > 2 && !['lab', 'labs', 'ltd', 'inc', 'corp', 'the', '3d'].includes(w));
            const hasVendor = vWords.some(w => slicerFilamentProfile.toLowerCase().includes(w));
            if (!hasVendor) {
                slicerFilamentProfile = `${filamentVendor} ${slicerFilamentProfile}`;
            }
        }
    } else if (filamentVendor && filamentType) {
        slicerFilamentProfile = `${filamentVendor} ${filamentType}`;
    } else if (filamentType) {
        slicerFilamentProfile = filamentType;
    }

    const printTimeHours = printTimeSeconds > 0 ? (printTimeSeconds / 3600) : 0;

    return {
        print_time_hours: parseFloat(printTimeHours.toFixed(2)),
        part_weight_g: parseFloat(filamentGrams.toFixed(2)),
        filament_type: filamentType,
        slicer_filament_profile: cleanFilamentProfileName(slicerFilamentProfile, fileName) || null,
        filament_color_hex: filamentColourHex || null,
        filament_slot: activeSlot || null,
    };
}

/**
 * Analyzes a G-code toolpath layer-by-layer to calculate cumulative material (mm and grams)
 * and elapsed time (seconds and minutes) up to each layer.
 *
 * @param {string} gcodeText - Raw G-code text content.
 * @param {number} totalPlateWeight - Baseline plate weight (g) for calibrated proportionality.
 * @param {number} totalPlateTimeHours - Baseline plate time (hours) for calibrated time calculation.
 * @param {number} filamentDensity - Material density in g/cm³ (default 1.24 for PLA, 1.27 for PETG, etc.)
 */
function analyzeGcodeLayers(gcodeText, totalPlateWeight = 0, totalPlateTimeHours = 0, filamentDensity = 1.24) {
    if (!gcodeText || typeof gcodeText !== 'string') {
        throw new Error('Conteúdo G-code vazio ou inválido.');
    }

    const lines = gcodeText.split('\n');
    let relativeE = false;
    let cumExtrusionMm = 0;
    let lastE = 0;
    let maxEInSegment = 0;
    let relEPos = 0;
    let currentZ = 0.20;
    let currentLayerIndex = 1;
    let currentTimeElapsedSec = 0;
    let initialM73RemainingMin = null;
    let layerHasExtrusion = false;
    let commentLayerPending = false;
    const layers = [];

    function finalizeLayer(layerIdx, zVal, timeSec) {
        layers.push({
            layer: layerIdx,
            z: Math.round(zVal * 1000) / 1000,
            cumExtrusionMm: cumExtrusionMm,
            timeElapsedSec: timeSec
        });
    }

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;

        if (line.startsWith('M83')) { relativeE = true; continue; }
        if (line.startsWith('M82')) { relativeE = false; continue; }

        if (line.startsWith('M73')) {
            const m = line.match(/R\s*(\d+)/i);
            if (m) {
                const remMin = parseInt(m[1], 10);
                if (initialM73RemainingMin === null || remMin > initialM73RemainingMin) {
                    initialM73RemainingMin = remMin;
                }
                currentTimeElapsedSec = Math.max(0, initialM73RemainingMin - remMin) * 60;
            }
        }

        if (line.startsWith(';TIME_ELAPSED:')) {
            const m = line.match(/;TIME_ELAPSED:\s*([\d\.]+)/i);
            if (m) currentTimeElapsedSec = parseFloat(m[1]);
        }

        let isLayerTransition = false;
        if (/^;\s*(?:LAYER_CHANGE|BEFORE_LAYER_CHANGE)/i.test(line)) {
            isLayerTransition = true;
            commentLayerPending = true;
        }
        const lMatch = line.match(/^;\s*(?:LAYER\s*[:=]\s*(\d+)|layer\s+(\d+))/i);
        if (lMatch) {
            isLayerTransition = true;
            commentLayerPending = true;
        }

        const zMatch = line.match(/^;\s*Z\s*[:=]\s*([\d\.]+)/i);
        if (zMatch) currentZ = parseFloat(zMatch[1]);

        if (line.startsWith('G0') || line.startsWith('G1') || line.startsWith('G2') || line.startsWith('G3') || line.startsWith('G92')) {
            const zCmd = line.match(/\bZ\s*([\d\.-]+)/i);
            if (zCmd) {
                const newZ = parseFloat(zCmd[1]);
                if (newZ > currentZ) {
                    if (!commentLayerPending && layerHasExtrusion && (newZ - currentZ >= 0.05)) {
                        isLayerTransition = true;
                    }
                    currentZ = newZ;
                }
                commentLayerPending = false;
            }

            const eCmd = line.match(/\bE\s*([\d\.-]+)/i);
            if (eCmd) {
                const eVal = parseFloat(eCmd[1]);
                if (line.startsWith('G92')) {
                    lastE = eVal;
                    maxEInSegment = eVal;
                    relEPos = 0;
                } else {
                    if (relativeE) {
                        if (eVal < 0) {
                            relEPos += eVal;
                        } else {
                            const unretract = (relEPos < 0) ? Math.min(eVal, -relEPos) : 0;
                            const trueExt = eVal - unretract;
                            relEPos += eVal;
                            if (relEPos > 0) relEPos = 0;
                            cumExtrusionMm += trueExt;
                            if (trueExt > 0) layerHasExtrusion = true;
                        }
                    } else {
                        if (eVal > maxEInSegment) {
                            const delta = eVal - maxEInSegment;
                            cumExtrusionMm += delta;
                            maxEInSegment = eVal;
                            if (delta > 0) layerHasExtrusion = true;
                        }
                        lastE = eVal;
                    }
                }
            }
        }

        if (isLayerTransition && layerHasExtrusion) {
            finalizeLayer(currentLayerIndex, currentZ, currentTimeElapsedSec);
            currentLayerIndex++;
            layerHasExtrusion = false;
        }
    }

    if (layerHasExtrusion && (layers.length === 0 || layers[layers.length - 1].layer !== currentLayerIndex)) {
        finalizeLayer(currentLayerIndex, currentZ, currentTimeElapsedSec);
    }

    if (layers.length === 0) {
        layers.push({ layer: 1, z: currentZ || 0.2, cumExtrusionMm, timeElapsedSec: currentTimeElapsedSec });
    }

    const totalExtrusion = cumExtrusionMm;
    const volumetricTotalG = (totalExtrusion * Math.PI * Math.pow(1.75 / 2, 2) / 1000) * (filamentDensity || 1.24);
    const finalTotalWeightG = totalPlateWeight > 0 ? totalPlateWeight : volumetricTotalG;
    const finalTotalTimeSec = (totalPlateTimeHours > 0) ? (totalPlateTimeHours * 3600) : (currentTimeElapsedSec || 3600);

    for (let i = 0; i < layers.length; i++) {
        const l = layers[i];
        l.layer = i + 1;
        const ratio = totalExtrusion > 0 ? (l.cumExtrusionMm / totalExtrusion) : 1;
        l.percent = parseFloat((ratio * 100).toFixed(1));
        l.cumWeightG = parseFloat((ratio * finalTotalWeightG).toFixed(2));
        if (l.timeElapsedSec === 0 && ratio > 0) {
            l.timeElapsedSec = Math.round(ratio * finalTotalTimeSec);
        }
        l.timeElapsedMin = Math.round(l.timeElapsedSec / 60);
    }

    return {
        totalLayers: layers.length,
        maxZ: layers[layers.length - 1].z,
        totalExtrusionMm: parseFloat(totalExtrusion.toFixed(2)),
        totalWeightG: parseFloat(finalTotalWeightG.toFixed(2)),
        totalTimeSeconds: Math.round(finalTotalTimeSec),
        layers,
        getLossAtLayer(targetLayer) {
            const idx = Math.max(1, Math.min(layers.length, parseInt(targetLayer, 10) || 1)) - 1;
            const item = layers[idx];
            const sec = item.timeElapsedSec;
            return {
                layer: item.layer,
                z: item.z,
                weightG: item.cumWeightG,
                hours: Math.floor(sec / 3600),
                minutes: Math.floor((sec % 3600) / 60),
                totalSeconds: sec,
                percent: item.percent
            };
        },
        getLossAtZ(targetZ) {
            const zNum = parseFloat(targetZ) || 0;
            let bestIdx = 0;
            for (let i = 0; i < layers.length; i++) {
                if (layers[i].z <= zNum) bestIdx = i;
                else break;
            }
            return this.getLossAtLayer(bestIdx + 1);
        }
    };
}

if (typeof window !== 'undefined') {
    window.cleanFilamentProfileName = cleanFilamentProfileName;
    window.parseGcodeMetadata = parseGcodeMetadata;
    window.analyzeGcodeLayers = analyzeGcodeLayers;
}
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { cleanFilamentProfileName, parseGcodeMetadata, analyzeGcodeLayers };
}
