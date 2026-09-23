/**
 * 3MF Metadata Extractor for Bambu Studio & OrcaSlicer
 * Reads ZIP contents in the browser using JSZip.
 */
async function parse3mfMetadata(file) {
    if (typeof JSZip === 'undefined') {
        throw new Error("Biblioteca JSZip não carregada. Verifique sua conexão com a internet.");
    }

    const zip = await JSZip.loadAsync(file);
    const plates = [];

    // 1. Look for Metadata/slice_info.xml (standard in Bambu Studio / OrcaSlicer)
    const sliceInfoFile = zip.file("Metadata/slice_info.xml") || 
                          zip.file(/Metadata\/.*slice_info\.xml/i)[0] ||
                          zip.file(/Metadata\/.*\.xml/i)[0];

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
                    const key = meta.getAttribute("key");
                    const val = meta.getAttribute("value");
                    if (key === "index") index = parseInt(val, 10) || index;
                    if (key === "prediction") predictionSeconds = parseFloat(val) || 0;
                    if (key === "weight") weightGrams = parseFloat(val) || 0;
                });

                // Filament elements inside plate
                const filamentNodes = node.querySelectorAll("filament");
                let totalFilamentGrams = 0;
                filamentNodes.forEach((f, fIdx) => {
                    const usedG = parseFloat(f.getAttribute("used_g")) || 0;
                    const type = f.getAttribute("type");
                    if (type && fIdx === 0) filamentType = type;
                    totalFilamentGrams += usedG;
                });

                if (totalFilamentGrams > 0 && (!weightGrams || totalFilamentGrams > weightGrams)) {
                    // Difference may be purge or prime tower
                    if (weightGrams > 0 && totalFilamentGrams > weightGrams) {
                        purgeGrams = totalFilamentGrams - weightGrams;
                    } else {
                        weightGrams = totalFilamentGrams;
                    }
                }

                const printTimeHours = predictionSeconds > 0 ? (predictionSeconds / 3600) : 0;

                plates.push({
                    name: `Placa ${index}`,
                    print_time_hours: parseFloat(printTimeHours.toFixed(2)),
                    part_weight_g: parseFloat(weightGrams.toFixed(2)),
                    purge_weight_g: parseFloat(purgeGrams.toFixed(2)),
                    filament_type: filamentType,
                    failure_margin_percent: 10.0,
                    quantity: 1,
                });
            });
        }
    }

    // 2. If no plates extracted from slice_info.xml, fallback to search config files
    if (plates.length === 0) {
        const configFile = zip.file("Metadata/model_settings.config") || 
                           zip.file("Metadata/project_settings.config");
        if (configFile) {
            const configText = await configFile.async("text");
            const timeMatch = configText.match(/"prediction":\s*"?([0-9.]+)"?/i) || configText.match(/prediction\s*=\s*([0-9.]+)/i);
            const weightMatch = configText.match(/"weight":\s*"?([0-9.]+)"?/i) || configText.match(/weight\s*=\s*([0-9.]+)/i);

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

    // Default fallback if it's an un-sliced 3MF
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
