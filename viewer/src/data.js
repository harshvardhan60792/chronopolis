export async function loadCity() {
    if (window.__CHRONOPOLIS_CITY__) {
        const decoded = atob(window.__CHRONOPOLIS_CITY__);
        const bytes = new Uint8Array(decoded.length);
        for (let i = 0; i < decoded.length; i++) {
            bytes[i] = decoded.charCodeAt(i);
        }
        const ds = new DecompressionStream('gzip');
        const writer = ds.writable.getWriter();
        writer.write(bytes);
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
        const text = new TextDecoder().decode(decompressed);
        return JSON.parse(text);
    }
    
    const urlParams = new URLSearchParams(window.location.search);
    const cityUrl = urlParams.get('city') || './city.json';
    
    try {
        const res = await fetch(cityUrl);
        if (res.ok) {
            return await res.json();
        }
    } catch (e) {
        if (urlParams.get('city')) {
            throw e;
        }
    }
    return null;
}
