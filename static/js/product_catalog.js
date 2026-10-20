(() => {
    const form = document.getElementById('catalog-filter');
    const results = document.getElementById('catalog-results');
    const status = document.getElementById('catalog-status');
    if (!form || !results || !status) return;
    let controller;
    async function load(url) {
        if (controller) controller.abort();
        const current = new AbortController();
        controller = current;
        status.textContent = 'Memuat produk…';
        results.setAttribute('aria-busy', 'true');
        try {
            const endpoint = new URL(url, window.location.href);
            endpoint.searchParams.set('partial', '1');
            const response = await fetch(endpoint, {signal: current.signal});
            if (!response.ok) throw new Error('request failed');
            const html = await response.text();
            if (controller !== current) return;
            results.innerHTML = html;
            endpoint.searchParams.delete('partial');
            history.replaceState(null, '', endpoint);
            status.textContent = 'Produk diperbarui.';
        } catch (error) {
            if (controller === current && error.name !== 'AbortError') status.textContent = 'Gagal memuat produk. Coba terapkan filter lagi.';
        } finally {
            if (controller === current) results.removeAttribute('aria-busy');
        }
    }
    form.addEventListener('submit', event => {
        event.preventDefault();
        const url = new URL(form.action || window.location.pathname, window.location.href);
        url.search = new URLSearchParams(new FormData(form)).toString();
        load(url);
    });
    results.addEventListener('click', event => {
        const link = event.target.closest('a[data-page]');
        if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        load(link.href);
    });
})();
