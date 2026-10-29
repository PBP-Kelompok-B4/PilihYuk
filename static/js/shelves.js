(() => {
    const root = document.querySelector('[data-shelf-products]');
    if (!root) return;
    const max = Number(root.dataset.max);
    const search = root.querySelector('[data-candidate-search]');
    const query = search.querySelector('[name=q]');
    const candidates = root.querySelector('[data-candidates]');
    const items = root.querySelector('[data-items]');
    const count = root.querySelector('[data-count]');
    const empty = root.querySelector('[data-empty]');
    const status = root.querySelector('[data-status]');
    const csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;
    let total = items.children.length;
    let controller;
    let timer;

    function clone(selector) {
        return root.querySelector(selector).content.firstElementChild.cloneNode(true);
    }

    function fill(row, product) {
        row.dataset.productId = product.id;
        row.querySelector('[data-name]').textContent = product.name || 'Tanpa nama';
        row.querySelector('[data-brand]').textContent = [product.brand, product.quantity].filter(Boolean).join(' · ');
        if (product.image_url) {
            const image = document.createElement('img');
            image.src = product.image_url;
            image.alt = '';
            image.loading = 'lazy';
            image.className = 'h-full w-full object-contain';
            row.querySelector('[data-thumb]').append(image);
        }
        return row;
    }

    function markAdded(row, added) {
        row.querySelector('[data-add]').hidden = added;
        row.querySelector('[data-added]').hidden = !added;
    }

    function setTotal(value) {
        total = value;
        count.textContent = `${total} / ${max} produk`;
        empty.hidden = total > 0;
        candidates.querySelectorAll('[data-add]').forEach(button => { button.disabled = total >= max; });
    }

    async function post(url, body) {
        const response = await fetch(url, {
            method: 'POST', body, headers: {'Accept': 'application/json', 'X-CSRFToken': csrf},
        });
        const isJson = (response.headers.get('Content-Type') || '').includes('application/json');
        const data = isJson ? await response.json() : {};
        if (!response.ok) throw new Error(data.error || 'Permintaan gagal. Muat ulang halaman lalu coba lagi.');
        return data;
    }

    async function load() {
        if (controller) controller.abort();
        const current = new AbortController();
        controller = current;
        const url = new URL(root.dataset.candidatesUrl, window.location.href);
        url.searchParams.set('q', query.value.trim());
        try {
            const response = await fetch(url, {signal: current.signal, headers: {'Accept': 'application/json'}});
            if (!response.ok) throw new Error('request failed');
            const data = await response.json();
            candidates.replaceChildren(...data.results.map(product => {
                const row = fill(clone('[data-candidate-template]'), product);
                markAdded(row, product.in_shelf);
                row.querySelector('[data-add]').disabled = total >= max;
                return row;
            }));
            status.textContent = data.count ? `${data.count} produk ditemukan.` : 'Produk tidak ditemukan.';
        } catch (error) {
            if (error.name !== 'AbortError') status.textContent = 'Gagal memuat produk. Coba lagi.';
        } finally {
        }
    }

    candidates.addEventListener('click', async event => {
        const button = event.target.closest('[data-add]');
        if (!button) return;
        const row = button.closest('li');
        button.disabled = true;
        try {
            const data = await post(root.dataset.addUrl, new URLSearchParams({product: row.dataset.productId}));
            const item = fill(clone('[data-item-template]'), data.product);
            item.querySelector('[data-remove]').action = `${root.dataset.addUrl}${data.product.id}/hapus/`;
            items.append(item);
            markAdded(row, true);
            setTotal(data.item_count);
            showToast('Produk ditambahkan', data.product.name, 'success');
        } catch (error) {
            showToast('Gagal menambah produk', error.message, 'error');
        } finally {
            button.disabled = total >= max;
        }
    });

    items.addEventListener('submit', async event => {
        event.preventDefault();
        const form = event.target;
        const row = form.closest('li');
        const button = form.querySelector('button');
        button.disabled = true;
        try {
            const data = await post(form.action, new FormData(form));
            row.remove();
            const candidate = candidates.querySelector(`[data-product-id="${row.dataset.productId}"]`);
            if (candidate) markAdded(candidate, false);
            setTotal(data.item_count);
            showToast('Produk dikeluarkan', row.querySelector('[data-name]').textContent, 'success');
        } catch (error) {
            button.disabled = false;
            showToast('Gagal mengeluarkan produk', error.message, 'error');
        }
    });

    search.addEventListener('submit', event => {
        event.preventDefault();
        load();
    });
    query.addEventListener('input', () => {
        clearTimeout(timer);
        timer = setTimeout(load, 250);
    });
    load();
})();

(() => {
    const form = document.querySelector('[data-compare-form]');
    if (!form) return;
    const max = Number(form.dataset.max);
    const boxes = [...form.querySelectorAll('[name=banding]')];
    const table = document.querySelector('[data-comparison]');
    const status = document.querySelector('[data-compare-status]');
    let controller;

    function limit() {
        const full = boxes.filter(box => box.checked).length >= max;
        boxes.forEach(box => { box.disabled = full && !box.checked; });
    }

    async function load() {
        if (controller) controller.abort();
        const current = new AbortController();
        controller = current;
        const url = new URL(window.location.pathname, window.location.href);
        boxes.filter(box => box.checked).forEach(box => url.searchParams.append('banding', box.value));
        const partial = new URL(url);
        partial.searchParams.set('partial', '1');
        try {
            const response = await fetch(partial, {signal: current.signal});
            if (!response.ok) throw new Error('request failed');
            table.innerHTML = await response.text();
            history.replaceState(null, '', url);
            status.textContent = 'Tabel perbandingan diperbarui.';
        } catch (error) {
            if (error.name !== 'AbortError') status.textContent = 'Gagal memperbarui tabel. Coba lagi.';
        } finally {
        }
    }

    form.querySelector('[data-compare-submit]').hidden = true;
    form.addEventListener('change', event => {
        if (!boxes.some(box => box.checked)) event.target.checked = true;
        limit();
        load();
    });
    form.addEventListener('submit', event => {
        event.preventDefault();
        load();
    });
    limit();
})();

(() => {
    const form = document.querySelector('[data-save-form]');
    if (!form) return;
    const input = form.querySelector('[name=saved]');
    const button = form.querySelector('button');
    const label = form.querySelector('[data-save-label]');
    const count = document.querySelector('[data-save-count]');

    form.addEventListener('submit', async event => {
        event.preventDefault();
        button.disabled = true;
        try {
            const response = await fetch(form.action, {
                method: 'POST', body: new FormData(form), headers: {'Accept': 'application/json'},
            });
            const isJson = (response.headers.get('Content-Type') || '').includes('application/json');
            if (!response.ok || !isJson) throw new Error('request failed');
            const data = await response.json();
            input.value = data.saved ? '0' : '1';
            label.textContent = data.saved ? 'Tersimpan di Shelf Saya' : 'Simpan ke Shelf Saya';
            if (count) count.textContent = `Disimpan ${data.save_count} pengguna`;
            showToast(data.saved ? 'Shelf disimpan' : 'Simpanan dibatalkan',
                data.saved ? 'Shelf ini ada di halaman Shelf Saya.' : 'Shelf ini dihapus dari Shelf Saya.', 'success');
        } catch (error) {
            showToast('Gagal menyimpan shelf', 'Muat ulang halaman lalu coba lagi.', 'error');
        } finally {
            button.disabled = false;
        }
    });
})();
