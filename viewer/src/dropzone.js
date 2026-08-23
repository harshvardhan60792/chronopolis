async function readAllChunks(readable) {
    const reader = readable.getReader();
    let out = new Uint8Array();
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const next = new Uint8Array(out.length + value.length);
        next.set(out);
        next.set(value, out.length);
        out = next;
    }
    return out;
}

async function decompress(bytes, format) {
    const ds = new DecompressionStream(format);
    const writer = ds.writable.getWriter();
    writer.write(bytes);
    writer.close();
    return readAllChunks(ds.readable);
}

// Extracts city.json from a .zip - not a full unzip (the browser can't run
// citygen's Python analysis on raw source, that needs a real backend), just
// enough of the ZIP container format to find and decompress one entry named
// city.json, so a zip *bundle* someone shares (e.g. a `citygen export`-style
// package, or GitHub's own repo zip if it happens to contain one) can be
// dropped directly. Uses the browser's native DecompressionStream - no zip
// library dependency.
async function extractCityJsonFromZip(buffer) {
    const view = new DataView(buffer);
    const bytes = new Uint8Array(buffer);

    const EOCD_SIG = 0x06054b50;
    const maxCommentLen = 65535;
    const searchStart = Math.max(0, bytes.length - 22 - maxCommentLen);
    let eocdOffset = -1;
    for (let i = bytes.length - 22; i >= searchStart; i--) {
        if (view.getUint32(i, true) === EOCD_SIG) { eocdOffset = i; break; }
    }
    if (eocdOffset === -1) {
        throw new Error("That doesn't look like a valid .zip file.");
    }

    const totalEntries = view.getUint16(eocdOffset + 10, true);
    const centralDirOffset = view.getUint32(eocdOffset + 16, true);
    const CDH_SIG = 0x02014b50;

    let cursor = centralDirOffset;
    let match = null;
    for (let i = 0; i < totalEntries; i++) {
        if (view.getUint32(cursor, true) !== CDH_SIG) break;
        const compMethod = view.getUint16(cursor + 10, true);
        const compSize = view.getUint32(cursor + 20, true);
        const nameLen = view.getUint16(cursor + 28, true);
        const extraLen = view.getUint16(cursor + 30, true);
        const commentLen = view.getUint16(cursor + 32, true);
        const localOffset = view.getUint32(cursor + 42, true);
        const name = new TextDecoder().decode(bytes.subarray(cursor + 46, cursor + 46 + nameLen));

        const isCityJson = name === 'city.json' || name.endsWith('/city.json');
        if (isCityJson || (!match && name.endsWith('.city.json'))) {
            match = { compMethod, compSize, localOffset, name };
            if (isCityJson) break;
        }
        cursor += 46 + nameLen + extraLen + commentLen;
    }

    if (!match) {
        throw new Error("No city.json found inside that zip.");
    }

    const lhNameLen = view.getUint16(match.localOffset + 26, true);
    const lhExtraLen = view.getUint16(match.localOffset + 28, true);
    const dataStart = match.localOffset + 30 + lhNameLen + lhExtraLen;
    const compData = bytes.subarray(dataStart, dataStart + match.compSize);

    let outBytes;
    if (match.compMethod === 0) {
        outBytes = compData;
    } else if (match.compMethod === 8) {
        outBytes = await decompress(compData, 'deflate-raw');
    } else {
        throw new Error(`Unsupported zip compression (method ${match.compMethod}) - only stored or deflate entries are supported.`);
    }

    return new TextDecoder().decode(outBytes);
}

export function setupDropzone(onCityLoaded, onError) {
    const dz = document.getElementById('dropzone');
    if (!dz) return;

    // Highlight on drag over
    window.addEventListener('dragover', (e) => {
        e.preventDefault();
        dz.classList.add('drag-active');
    });

    window.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dz.classList.remove('drag-active');
    });

    window.addEventListener('drop', async (e) => {
        e.preventDefault();
        dz.classList.remove('drag-active');
        
        if (e.dataTransfer.files.length === 0) return;
        const file = e.dataTransfer.files[0];

        const isZip = file.name.endsWith('.zip');
        if (!file.name.endsWith('.json') && !file.name.endsWith('.json.gz') && !isZip) {
            onError(new Error("Please drop a .json, .json.gz, or .zip (containing a city.json) file"));
            return;
        }

        try {
            const buffer = await file.arrayBuffer();
            let text;

            if (isZip) {
                text = await extractCityJsonFromZip(buffer);
            } else if (file.name.endsWith('.json.gz')) {
                text = new TextDecoder().decode(await decompress(buffer, 'gzip'));
            } else {
                text = new TextDecoder().decode(buffer);
            }

            const data = JSON.parse(text);
            onCityLoaded(data);
        } catch (err) {
            onError(err instanceof Error && isZip ? err : new Error("That file isn't valid JSON. Re-run citygen and try again."));
        }
    });
    
    // Also handle file input browse
    const input = document.getElementById('file-input');
    if (input) {
        input.addEventListener('change', async (e) => {
            if (e.target.files.length === 0) return;
            const file = e.target.files[0];
            // reuse drop logic
            const dt = new DataTransfer();
            dt.items.add(file);
            window.dispatchEvent(new DragEvent('drop', { dataTransfer: dt }));
        });
    }
}
