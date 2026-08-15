

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
        
        if (!file.name.endsWith('.json') && !file.name.endsWith('.json.gz')) {
            onError(new Error("Please drop a .json or .json.gz file"));
            return;
        }
        
        try {
            const buffer = await file.arrayBuffer();
            let text;
            
            if (file.name.endsWith('.json.gz')) {
                const ds = new DecompressionStream('gzip');
                const writer = ds.writable.getWriter();
                writer.write(buffer);
                writer.close();
                const reader = ds.readable.getReader();
                let decompressed = new Uint8Array();
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    const temp = new Uint8Array(decompressed.length + value.length);
                    temp.set(decompressed);
                    temp.set(value, decompressed.length);
                    decompressed = temp;
                }
                text = new TextDecoder().decode(decompressed);
            } else {
                text = new TextDecoder().decode(buffer);
            }
            
            const data = JSON.parse(text);
            onCityLoaded(data);
        } catch (err) {
            onError(new Error("That file isn't valid JSON. Re-run citygen and try again."));
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
