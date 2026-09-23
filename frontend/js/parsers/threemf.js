/**
 * 3MF Metadata Extractor for Bambu Studio, OrcaSlicer, PrusaSlicer & SuperSlicer
 * Reads ZIP contents in the browser using JSZip.
 */
async function parse3mfMetadata(file) {
    if (typeof JSZip === 'undefined') {
        throw new Error("Biblioteca JSZip não carregada. Verifique sua conexão com a internet.");
    }

    const zip = await JSZip.loadAsync(file);
    const plates = [];

    // 1. Search for slice_info.xml (standard in Bambu Studio / OrcaSlicer)
    const sliceFiles = zip.file(/(?:^|\/)slice_info\.xml$/i);
    let sliceInfoFile = (sliceFiles && sliceFiles.length > 0) ? sliceFiles[0] : null;

    if (!sliceInfoFile) {
        const potentialXmls = zip.file(/.*slice.*\.xml$/i);
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

                // Metadata items inside plate
                const metaTags = node.querySelectorAll("metadata");
                metaTags.forEach(meta => {
                    const key = (meta.getAttribute("key") || "").toLowerCase();
                    const val = meta.getAttribute("value");
                    if (key === "index") index = parseInt(val, 10) || index;
                    if (key === "prediction" || key === "print_time") predictionSeconds = parseFloat(val) || 0;
                    if (key === "weight" || key === "plate_weight") weightGrams = parseFloat(val) || 0;
                    if (key === "flush_weight" || key === "purge_weight" || key === "waste_weight") {
                        purgeGrams = parseFloat(val) || 0;
                    }
                });

                // Filament elements inside plate
                const filamentNodes = node.querySelectorAll("filament");
                let totalFilamentGrams = 0;
                const filamentTypes = [];
                filamentNodes.forEach((f) => {
                    const usedG = parseFloat(f.getAttribute("used_g")) || 0;
                    const flushG = parseFloat(f.getAttribute("flush_g")) || parseFloat(f.getAttribute("purge_g")) || 0;
                    const type = f.getAttribute("type");
                    if (type && !filamentTypes.includes(type)) filamentTypes.push(type);
                    totalFilamentGrams += usedG;
                    if (flushG > 0 && purgeGrams === 0) {
                        purgeGrams += flushG;
                    }
                });

                if (filamentTypes.length > 0) {
                    filamentType = filamentTypes.join(", ");
                }

                // Balance part vs purge weights
                let partWeight = weightGrams;
                if (totalFilamentGrams > 0) {
                    if (purgeGrams > 0) {
                        if (partWeight > purgeGrams && partWeight === totalFilamentGrams) {
                            partWeight = totalFilamentGrams - purgeGrams;
                        }
                    } else if (totalFilamentGrams > partWeight && partWeight > 0) {
                        purgeGrams = totalFilamentGrams - partWeight;
                    } else if (partWeight === 0) {
                        partWeight = totalFilamentGrams;
                    }
                }

                const printTimeHours = predictionSeconds > 0 ? (predictionSeconds / 3600) : 0;

                plates.push({
                    name: `Placa ${index}`,
                    print_time_hours: parseFloat(printTimeHours.toFixed(2)),
                    part_weight_g: parseFloat(partWeight.toFixed(2)),
                    purge_weight_g: parseFloat(purgeGrams.toFixed(2)),
                    filament_type: filamentType,
                    failure_margin_percent: 10.0,
                    quantity: 1,
                });
            });
        }
    }

    // 2. Fallback to slicer config files (Bambu/Orca model_settings or Prusa print_config.ini)
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

            plates.push({
                name: "Placa 1",
                print_time_hours: parseFloat((secs / 3600).toFixed(2)),
                part_weight_g: parseFloat(weight.toFixed(2)),
                purge_weight_g: 0.0,
                filament_type: "PLA",
                failure_margin_percent: 10.0,
                quantity: 1,
            });
        }
    }

    // 3. Default fallback if it's an un-sliced 3MF
    if (plates.length === 0) {
        plates.push({
            name: "Placa 1 (Não fatiado)",
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
