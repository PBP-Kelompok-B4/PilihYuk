(() => {
    'use strict';

    function notify(message, type = 'success') {
        if (typeof showToast === 'function') showToast('PilihYuk', message, type);
        const status = document.querySelector('[data-module-status]');
        if (status) status.textContent = message;
    }

    async function request(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest', ...options.headers},
        });
        if (response.redirected) throw new Error('Sesi berakhir. Muat ulang halaman untuk masuk kembali.');
        let data;
        try { data = await response.json(); }
        catch { throw new Error('Respons tidak dapat dibaca. Coba lagi.'); }
        if (!response.ok || !data.ok) {
            const errors = Object.values(data.errors || {}).flat().join(' ');
            throw new Error(errors || data.message || 'Perubahan gagal disimpan.');
        }
        return data;
    }

    function post(form) {
        const body = new FormData(form);
        return request(form.action, {
            method: 'POST', body,
            headers: {'X-CSRFToken': body.get('csrfmiddlewaretoken')},
        });
    }

    function fragment(html) {
        const template = document.createElement('template');
        template.innerHTML = html.trim();
        return template.content.firstElementChild;
    }

    const preferences = document.querySelector('[data-preferences]');
    if (preferences) {
        async function preview(row) {
            if (!row.dataset.id) return;
            const params = new URLSearchParams({nutrient: row.dataset.nutrient, direction: row.querySelector('select').value});
            const output = row.querySelector('[data-preview]');
            try {
                const data = await request(`${preferences.dataset.previewUrl}?${params}`);
                const samples = data.samples.map(item => `${item.name}: ${item.value} ${item.unit}`).join('; ');
                output.textContent = `${data.ranked_count} dari ${data.total_active} produk memiliki data. ${samples}`;
            } catch (error) { output.textContent = error.message; }
        }

        preferences.addEventListener('submit', async event => {
            const form = event.target;
            if (!form.matches('[data-preference-save], [data-preference-toggle]')) return;
            event.preventDefault();
            const row = form.closest('[data-nutrient]');
            if (row.dataset.busy) return;
            const saved = row.cloneNode(true);
            const shouldPreview = form.matches('[data-preference-toggle]') || row.dataset.direction !== row.querySelector('select').value;
            row.dataset.busy = 'true';
            row.setAttribute('aria-busy', 'true');
            try {
                const pending = post(form);
                row.querySelectorAll('button, input, select').forEach(control => { control.disabled = true; });
                const data = await pending;
                const updated = fragment(data.html);
                updated.dataset.direction = updated.querySelector('select').value;
                row.replaceWith(updated);
                if (shouldPreview && updated.dataset.id) preview(updated);
                notify(data.message);
            } catch (error) {
                row.replaceWith(saved);
                // Nilai kontrol dikembalikan ke data terakhir dari server.
                saved.querySelector('select').value = saved.dataset.direction;
                saved.querySelectorAll('[name="weight"]').forEach(control => {
                    if (control.type === 'radio') control.checked = control.value === saved.dataset.weight;
                });
                notify(error.message, 'error');
            }
        });
        preferences.addEventListener('change', event => {
            const form = event.target.closest('[data-preference-save]');
            if (form) form.requestSubmit();
        });
        preferences.querySelectorAll('[data-nutrient]').forEach(row => {
            row.dataset.direction = row.querySelector('select').value;
            row.dataset.weight = row.querySelector('[type="radio"]:checked').value;
        });
    }
})();
