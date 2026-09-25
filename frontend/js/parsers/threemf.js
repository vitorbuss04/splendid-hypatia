/**
 * 3MF and .gcode.3mf Metadata Extractor for Bambu Studio, OrcaSlicer, PrusaSlicer & SuperSlicer
 * Reads ZIP contents or embedded G-code in the browser using JSZip and G-code parser.
 */
if (typeof cleanFilamentProfileName === 'undefined') {
    function cleanFilamentProfileName(profile, fileName = '') {
        if (!profile || typeof profile !== 'string') return '';
        let cleaned = profile.trim().replace(/^["']|["']$/g, '');
        cleaned = cleaned.replace(/\s*[\(\[][^()\[\]]*\.[a-z0-9_-]{2,6}\s*[\)\]]/gi, '');
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
}

function parseTimeStringToSeconds(timeVal) {
    if (!timeVal) return 0;
    if (typeof timeVal === 'number') return timeVal;
    const str = String(timeVal).trim();
    if (!str) return 0;
    if (/^\d+(?:\.\d+)?$/.test(str)) {
        return parseFloat(str);
    }
    const hhmmss = str.match(/(\d{1,3}):(\d{2}):(\d{2})/);
    if (hhmmss) {
        return (parseInt(hhmmss[1], 10) * 3600) + (parseInt(hhmmss[2], 10) * 60) + parseInt(hhmmss[3], 10);
    }
    const hhmm = str.match(/(\d{1,3}):(\d{2})/);
    if (hhmm) {
        return (parseInt(hhmm[1], 10) * 3600) + (parseInt(hhmm[2], 10) * 60);
    }
    const dMatch = str.match(/(\d+)\s*d/i);
    const hMatch = str.match(/(\d+(?:\.\d+)?)\s*h/i);
    const mMatch = str.match(/(\d+(?:\.\d+)?)\s*m/i);
    const sMatch = str.match(/(\d+(?:\.\d+)?)\s*s/i);
    if (dMatch || hMatch || mMatch || sMatch) {
        const d = dMatch ? parseFloat(dMatch[1]) : 0;
        const h = hMatch ? parseFloat(hMatch[1]) : 0;
        const m = mMatch ? parseFloat(mMatch[1]) : 0;
        const s = sMatch ? parseFloat(sMatch[1]) : 0;
        return (d * 86400) + (h * 3600) + (m * 60) + s;
    }
    return parseFloat(str) || 0;
}

async function parse3mfMetadata(file) {
    if (typeof JSZip === 'undefined') {
        throw new Error("Biblioteca JSZip não carregada. Verifique sua conexão com a internet.");
    }

    let cleanFileName = '';
    if (file && typeof file.name === 'string') {
        cleanFileName = file.name.replace(/^.*[\\\/]/, '').replace(/\.(?:gcode\.3mf|3mf|gcode)$/i, '').trim();
    }

    let zip;
    try {
        zip = await JSZip.loadAsync(file);
    } catch (zipErr) {
        // Fallback: If not a valid ZIP/3MF, attempt parsing as raw G-Code text
        // (common when files are named .gcode.3mf but contain raw G-code)
        try {
            if (typeof file.text === 'function') {
                const rawText = await file.text();
                if (typeof parseGcodeMetadata === 'function') {
                    const meta = parseGcodeMetadata(rawText);
                    if (meta && (meta.print_time_hours > 0 || meta.part_weight_g > 0)) {
                        const cleanName = cleanFileName || 'Placa 1';
                        return [{
                            name: cleanName || "Placa 1",
                            print_time_hours: meta.print_time_hours || 0,
                            part_weight_g: meta.part_weight_g || 0,
                            purge_weight_g: 0.0,
                            filament_type: meta.filament_type || "PLA",
                            slicer_filament_profile: cleanFilamentProfileName(meta.slicer_filament_profile || meta.filament_type || null, file ? file.name : '') || null,
                            failure_margin_percent: 10.0,
                            quantity: 1,
                        }];
                    }
                }
            }
        } catch (_) {}
        throw zipErr;
    }

    const plates = [];

    // 1. Search for slice_info.xml or slice_info.config (standard in Bambu Studio / OrcaSlicer .3mf and .gcode.3mf)
    const sliceFiles = zip.file(/(?:^|\/)slice_info\.(?:xml|config)$/i);
    let sliceInfoFile = (sliceFiles && sliceFiles.length > 0) ? sliceFiles[0] : null;

    if (!sliceInfoFile) {
        const potentialXmls = zip.file(/.*slice.*(?:\.xml|\.config)$/i);
        if (potentialXmls && potentialXmls.length > 0) {
            sliceInfoFile = potentialXmls[0];
        }
    }

    if (sliceInfoFile) {
        const xmlText = await sliceInfoFile.async("text");
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(xmlText, "text/xml");

        const plateNodes = xmlDoc.querySelectorAll("plate");
        if (plateNodes && plateNodes.length > 0) {
            plateNodes.forEach((node, idx) => {
                let index = idx + 1;
                let predictionSeconds = 0;
                let weightGrams = 0;
                let purgeGrams = 0;
                let filamentType = "PLA";
                let plateCustomName = null;
                let plateFilamentProfile = null;
                let plateFilamentSlot = null;
                let plateFilamentColorHex = null;

                // Metadata items inside plate
                const metaTags = node.querySelectorAll("metadata");
                metaTags.forEach(meta => {
                    const key = (meta.getAttribute("key") || "").toLowerCase();
                    const val = meta.getAttribute("value");
                    if (key === "index") index = parseInt(val, 10) || index;
                    if (key === "name" || key === "plate_name" || key === "title" || key === "label") {
                        if (val && val.trim()) plateCustomName = val.trim();
                    }
                    if (key === "prediction" || key === "print_time" || key === "prediction_time" || key === "time" || key === "estimated_time" || key === "printing_time" || key === "total_time" || key === "total_estimated_time") {
                        predictionSeconds = parseTimeStringToSeconds(val);
                    }
                    if (key === "weight" || key === "plate_weight" || key === "filament_weight" || key === "filament_used" || key === "total_weight") {
                        weightGrams = parseFloat(val) || 0;
                    }
                    if (key === "flush_weight" || key === "purge_weight" || key === "waste_weight") {
                        purgeGrams = parseFloat(val) || 0;
                    }
                    if (key === "filament_profile" || key === "filament_name" || key === "profile" || key === "tray_info_idx") {
                        if (val && val.trim() && !plateFilamentProfile) plateFilamentProfile = cleanFilamentProfileName(val.trim(), file ? file.name : '');
                    }
                });

                // Fallback to node attributes if metadata tags omitted
                if (!predictionSeconds) {
                    predictionSeconds = parseTimeStringToSeconds(
                        node.getAttribute("prediction") ||
                        node.getAttribute("print_time") ||
                        node.getAttribute("prediction_time") ||
                        node.getAttribute("time") ||
                        node.getAttribute("estimated_time")
                    );
                }
                if (!weightGrams) {
                    weightGrams = parseFloat(
                        node.getAttribute("weight") ||
                        node.getAttribute("plate_weight") ||
                        node.getAttribute("filament_weight") ||
                        "0"
                    ) || 0;
                }
                if (!plateCustomName) {
                    const attrName = node.getAttribute("name") || node.getAttribute("plate_name") || node.getAttribute("title");
                    if (attrName && attrName.trim()) plateCustomName = attrName.trim();
                }

                // Filament elements inside plate
                const filamentNodes = node.querySelectorAll("filament");
                let totalFilamentGrams = 0;
                const filamentTypes = [];
                filamentNodes.forEach((f) => {
                    let usedG = parseFloat(f.getAttribute("used_g") || f.getAttribute("weight") || f.getAttribute("used_weight") || "0") || 0;
                    // If weight is 0 but length is present, approximate grams: ~3.0g per meter of 1.75mm filament
                    if (usedG === 0) {
                        const usedM = parseFloat(f.getAttribute("used_m") || "0") || 0;
                        const usedMm = parseFloat(f.getAttribute("used_mm") || "0") || 0;
                        if (usedM > 0) usedG = usedM * 2.98;
                        else if (usedMm > 0) usedG = (usedMm / 1000) * 2.98;
                    }
                    const flushG = parseFloat(f.getAttribute("flush_g") || f.getAttribute("purge_g") || "0") || 0;
                    const type = f.getAttribute("type");
                    if (type && !filamentTypes.includes(type)) filamentTypes.push(type);
                    const prof = f.getAttribute("profile") || f.getAttribute("profile_name") || f.getAttribute("name") || f.getAttribute("tray_info_idx");
                    if (prof && !plateFilamentProfile && !prof.startsWith('#')) {
                        const isOpaque = /^[A-Za-z0-9_-]{3,15}$/.test(prof.trim()) && !/pla|petg|abs|tpu|pc|nylon|basic|matte|silk|wood|flex|carbon/i.test(prof);
                        if (!isOpaque) {
                            plateFilamentProfile = cleanFilamentProfileName(prof.trim(), file ? file.name : '');
                        }
                    }
                    const fId = parseInt(f.getAttribute("id"), 10);
                    if (fId && !plateFilamentSlot) plateFilamentSlot = fId;
                    const fColor = f.getAttribute("color");
                    if (fColor && !plateFilamentColorHex) plateFilamentColorHex = fColor;

                    totalFilamentGrams += usedG;
                    if (flushG > 0 && purgeGrams === 0) {
                        purgeGrams += flushG;
                    }
                });

                if (filamentTypes.length > 0) {
                    filamentType = filamentTypes.join(", ");
                }

                // Combine total filament (part + purge/flush) into part_weight_g
                let totalWeight = weightGrams;
                if (totalFilamentGrams > 0) {
                    totalWeight = totalFilamentGrams;
                } else if (purgeGrams > 0) {
                    totalWeight = weightGrams + purgeGrams;
                }

                const printTimeHours = predictionSeconds > 0 ? (predictionSeconds / 3600) : 0;

                // Naming strategy:
                // If cleanFileName exists, use it (exact filename without extension)
                // If multi plate file, use `${cleanFileName} - Placa ${index}`
                // Otherwise fallback to slicer custom name or generic Placa ${index}
                let finalName;
                if (cleanFileName) {
                    finalName = plateNodes.length === 1 ? cleanFileName : `${cleanFileName} - Placa ${index}`;
                } else if (plateCustomName && !/^placa\s*\d+$/i.test(plateCustomName) && !/^plate\s*\d+$/i.test(plateCustomName)) {
                    finalName = plateCustomName;
                } else {
                    finalName = `Placa ${index}`;
                }

                plates.push({
                    name: finalName,
                    plate_index: index,
                    print_time_hours: parseFloat(printTimeHours.toFixed(2)),
                    part_weight_g: parseFloat(totalWeight.toFixed(2)),
                    purge_weight_g: 0.0,
                    filament_type: filamentType,
                    slicer_filament_profile: cleanFilamentProfileName(plateFilamentProfile, file ? file.name : '') || null,
                    filament_slot: plateFilamentSlot || null,
                    filament_color_hex: plateFilamentColorHex || null,
                    failure_margin_percent: 10.0,
                    quantity: 1,
                });
            });

            // Complement plates with embedded G-code inside the ZIP archive (time, weight, filament type & profile)
            const gcodeFiles = zip.file(/(?:Metadata\/)?.*\.gcode$/i).filter(f => !f.dir);
            if (gcodeFiles && gcodeFiles.length > 0) {
                gcodeFiles.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }));
                for (let idx = 0; idx < plates.length; idx++) {
                    const p = plates[idx];
                    const plateIdx = p.plate_index || (idx + 1);
                    const matchedGcode = gcodeFiles.find(gf => {
                        const num = gf.name.match(/(?:plate|placa)[-_ ]*(\d+)/i);
                        return num && parseInt(num[1], 10) === plateIdx;
                    }) || (idx < gcodeFiles.length ? gcodeFiles[idx] : null);

                    if (matchedGcode) {
                        try {
                            const gText = await matchedGcode.async("text");
                            const meta = (typeof parseGcodeMetadata === 'function') ? parseGcodeMetadata(gText, file ? file.name : '') : null;
                            if (meta) {
                                if (p.print_time_hours === 0 && meta.print_time_hours > 0) {
                                    p.print_time_hours = meta.print_time_hours;
                                }
                                if (p.part_weight_g === 0 && meta.part_weight_g > 0) {
                                    p.part_weight_g = meta.part_weight_g;
                                }
                                if ((!p.filament_type || p.filament_type === 'PLA') && meta.filament_type) {
                                    p.filament_type = meta.filament_type;
                                }
                                if ((!p.slicer_filament_profile || p.slicer_filament_profile === p.filament_type) && meta.slicer_filament_profile) {
                                    p.slicer_filament_profile = cleanFilamentProfileName(meta.slicer_filament_profile, file ? file.name : '');
                                }
                                if (!p.filament_color_hex && meta.filament_color_hex) {
                                    p.filament_color_hex = meta.filament_color_hex;
                                }
                                if (!p.filament_slot && meta.filament_slot) {
                                    p.filament_slot = meta.filament_slot;
                                }
                            }
                        } catch (_) {}
                    }
                }
            }

            // Check config files (Metadata/project_settings.config, model_settings.config, etc.)
            const configFiles = zip.file(/(?:Metadata\/)?(?:project_settings|model_settings|Slic3r_PE|PrusaSlicer)\.(?:config|json|ini)$/i).filter(f => !f.dir);
            for (const cf of configFiles) {
                try {
                    const cfgText = await cf.async("text");
                    let cfgProfiles = [];
                    let cfgTypes = [];
                    if (cfgText.trim().startsWith('{')) {
                        const parsed = JSON.parse(cfgText);
                        if (Array.isArray(parsed.filament_settings_id)) {
                            cfgProfiles = parsed.filament_settings_id.map(s => cleanFilamentProfileName(String(s).trim().replace(/^["']|["']$/g, ''), file ? file.name : ''));
                        } else if (typeof parsed.filament_settings_id === 'string') {
                            cfgProfiles = [cleanFilamentProfileName(parsed.filament_settings_id.trim().replace(/^["']|["']$/g, ''), file ? file.name : '')];
                        }
                        if (Array.isArray(parsed.filament_type)) {
                            cfgTypes = parsed.filament_type.map(s => String(s).trim());
                        }
                    } else {
                        const match = cfgText.match(/filament_settings_id\s*=\s*(.+)/i);
                        if (match) {
                            cfgProfiles = match[1].split(';').map(s => cleanFilamentProfileName(s.trim().replace(/^["']|["']$/g, ''), file ? file.name : '')).filter(Boolean);
                        }
                        const tMatch = cfgText.match(/filament_type\s*=\s*(.+)/i);
                        if (tMatch) {
                            cfgTypes = tMatch[1].split(';').map(s => s.trim().replace(/^["']|["']$/g, '')).filter(Boolean);
                        }
                    }
                    if (cfgProfiles.length > 0 || cfgTypes.length > 0) {
                        for (let idx = 0; idx < plates.length; idx++) {
                            const slot = plates[idx].filament_slot;
                            const slotIdx = (slot && slot > 0 && slot <= cfgProfiles.length) ? (slot - 1) : (idx < cfgProfiles.length ? idx : 0);
                            if ((!plates[idx].slicer_filament_profile || plates[idx].slicer_filament_profile === plates[idx].filament_type) && cfgProfiles.length > 0) {
                                plates[idx].slicer_filament_profile = cfgProfiles[slotIdx] || cfgProfiles[0];
                            }
                            if ((!plates[idx].filament_type || plates[idx].filament_type === 'PLA') && cfgTypes.length > 0 && cfgTypes[slotIdx]) {
                                plates[idx].filament_type = cfgTypes[slotIdx];
                            }
                        }
                        break;
                    }
                } catch (_) {}
            }

            // Fallback: if slicer_filament_profile still not populated, use filament_type
            for (let idx = 0; idx < plates.length; idx++) {
                if (!plates[idx].slicer_filament_profile && plates[idx].filament_type) {
                    plates[idx].slicer_filament_profile = cleanFilamentProfileName(plates[idx].filament_type, file ? file.name : '');
                }
            }
        }
    }

    // 2. Search for embedded G-code inside the .3mf/.gcode.3mf ZIP archive (e.g. Metadata/plate_1.gcode or plate_*.gcode)
    if (plates.length === 0 || plates.every(p => p.print_time_hours === 0 && p.part_weight_g === 0)) {
        const gcodeFiles = zip.file(/(?:Metadata\/)?.*\.gcode$/i).filter(f => !f.dir);
        if (gcodeFiles && gcodeFiles.length > 0) {
            gcodeFiles.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }));
            const gcodePlates = [];
            for (let idx = 0; idx < gcodeFiles.length; idx++) {
                const gFile = gcodeFiles[idx];
                const gText = await gFile.async("text");
                const meta = (typeof parseGcodeMetadata === 'function') ? parseGcodeMetadata(gText, file ? file.name : '') : { print_time_hours: 0, part_weight_g: 0 };

                let pName;
                if (cleanFileName) {
                    pName = gcodeFiles.length === 1 ? cleanFileName : `${cleanFileName} - Placa ${idx + 1}`;
                } else {
                    const rawName = gFile.name.replace(/^.*[\\\/]/, '').replace(/\.gcode$/i, '');
                    const plateNumMatch = rawName.match(/(?:plate|placa)[-_ ]*(\d+)/i);
                    if (plateNumMatch) {
                        pName = `Placa ${plateNumMatch[1]}`;
                    } else {
                        pName = rawName || `Placa ${idx + 1}`;
                    }
                }

                gcodePlates.push({
                    name: pName,
                    print_time_hours: meta.print_time_hours || 0,
                    part_weight_g: meta.part_weight_g || 0,
                    purge_weight_g: 0.0,
                    filament_type: meta.filament_type || "PLA",
                    slicer_filament_profile: cleanFilamentProfileName(meta.slicer_filament_profile || meta.filament_type || null, file ? file.name : '') || null,
                    filament_color_hex: meta.filament_color_hex || null,
                    filament_slot: meta.filament_slot || null,
                    failure_margin_percent: 10.0,
                    quantity: 1,
                });
            }
            if (gcodePlates.length > 0 && gcodePlates.some(p => p.print_time_hours > 0 || p.part_weight_g > 0)) {
                return gcodePlates;
            }
        }
    }


    // 3. Fallback to slicer config files (Bambu/Orca model_settings or Prusa print_config.ini)
    if (plates.length === 0) {
        const configFile = zip.file(/Metadata\/.*(?:model_settings|project_settings)\.config/i)[0] ||
                           zip.file(/print_config\.ini/i)[0];
        if (configFile) {
            const configText = await configFile.async("text");
            const timeMatch = configText.match(/"prediction":\s*"?([0-9.]+)"?/i) || 
                              configText.match(/prediction\s*=\s*([0-9.]+)/i) ||
                              configText.match(/estimated[ _]printing[ _]time\s*=\s*([0-9.]+)/i);
            const weightMatch = configText.match(/"weight":\s*"?([0-9.]+)"?/i) || 
                                configText.match(/weight\s*=\s*([0-9.]+)/i) ||
                                configText.match(/filament[ _]used[ _]\[g\]\s*=\s*([0-9.]+)/i);

            const secs = timeMatch ? parseFloat(timeMatch[1]) : 0;
            const weight = weightMatch ? parseFloat(weightMatch[1]) : 0;

            const fallbackName = cleanFileName || "Placa 1";
            plates.push({
                name: fallbackName,
                print_time_hours: parseFloat((secs / 3600).toFixed(2)),
                part_weight_g: parseFloat(weight.toFixed(2)),
                purge_weight_g: 0.0,
                filament_type: "PLA",
                slicer_filament_profile: "PLA",
                failure_margin_percent: 10.0,
                quantity: 1,
            });
        }
    }

    // 4. Default fallback if it's an un-sliced 3MF
    if (plates.length === 0) {
        const fallbackName = cleanFileName ? `${cleanFileName} (Não fatiado)` : "Placa 1 (Não fatiado)";
        plates.push({
            name: fallbackName,
            print_time_hours: 0.0,
            part_weight_g: 0.0,
            purge_weight_g: 0.0,
            filament_type: "PLA",
            failure_margin_percent: 10.0,
            quantity: 1,
            notes: "Arquivo 3MF sem metadados de fatiamento. Preencha o tempo e peso manualmente.",
        });
    }

    return plates;
}
