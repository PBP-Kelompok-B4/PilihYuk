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
            const focusedId = row.contains(document.activeElement) ? document.activeElement.id : '';
            const saved = row.cloneNode(true);
            const shouldPreview = form.matches('[data-preference-toggle]') || row.dataset.direction !== row.querySelector('select').value;
            row.dataset.busy = 'true';
            row.setAttribute('aria-busy', 'true');
            try {
                const pending = post(form);
                if (form.matches('[data-preference-toggle]')) {
                    const active = !row.dataset.id;
                    row.querySelector('[role="switch"]').setAttribute('aria-checked', String(active));
                    row.querySelector('[data-active-label]').textContent = active ? 'Aktif' : 'Nonaktif';
                    row.querySelector('[data-toggle-track]').classList.toggle('bg-brand', active);
                    row.querySelector('[data-toggle-track]').classList.toggle('bg-track', !active);
                    row.querySelector('[data-toggle-thumb]').classList.toggle('translate-x-4', active);
                }
                row.querySelectorAll('button, input, select').forEach(control => { control.disabled = true; });
                const data = await pending;
                const updated = fragment(data.html);
                updated.dataset.direction = updated.querySelector('select').value;
                row.replaceWith(updated);
                if (focusedId) document.getElementById(focusedId)?.focus({preventScroll: true});
                if (shouldPreview && updated.dataset.id) preview(updated);
                notify(data.message);
            } catch (error) {
                row.replaceWith(saved);
                // Nilai kontrol dikembalikan ke data terakhir dari server.
                saved.querySelector('select').value = saved.dataset.direction;
                saved.querySelectorAll('[name="weight"]').forEach(control => {
                    if (control.type === 'radio') control.checked = control.value === saved.dataset.weight;
                });
                if (focusedId) document.getElementById(focusedId)?.focus({preventScroll: true});
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
    const decisions = document.querySelector('[data-decisions]');
    if (decisions) {
        const results = decisions.querySelector('[data-decision-results]');
        const filterForm = decisions.querySelector('[data-decision-filter]');
        let latestLoad = 0;
        let filterTimer;
        let writing = false;

        async function loadHistory(url) {
            const loadId = ++latestLoad;
            const hadFocus = results.contains(document.activeElement);
            const focusedId = hadFocus ? document.activeElement.id : '';
            results.setAttribute('aria-busy', 'true');
            try {
                const data = await request(url);
                if (loadId !== latestLoad) return false;
                results.innerHTML = data.html;
                history.replaceState(null, '', data.url);
                if (hadFocus) (document.getElementById(focusedId) || results).focus({preventScroll: true});
                return true;
            } catch (error) {
                if (loadId === latestLoad) notify(`Riwayat belum diperbarui. ${error.message}`, 'error');
                return false;
            } finally {
                if (loadId === latestLoad) results.removeAttribute('aria-busy');
            }
        }

        function applyFilters() {
            clearTimeout(filterTimer);
            if (writing) return;
            const params = new URLSearchParams(new FormData(filterForm));
            loadHistory(`${filterForm.action}?${params}`);
        }

        decisions.addEventListener('submit', async event => {
            const form = event.target;
            if (form === filterForm) {
                event.preventDefault();
                applyFilters();
                return;
            }
            if (!form.matches('[data-decision-create], [data-decision-update], [data-decision-delete], [data-decision-bulk]')) return;
            event.preventDefault();
            if (writing) return;
            let removed = [];
            if (form.matches('[data-decision-bulk]')) {
                const selected = new Set(new FormData(form).getAll('ids'));
                if (!selected.size) {
                    notify('Pilih setidaknya satu keputusan.', 'error');
                    return;
                }
                removed = [...results.querySelectorAll('[data-decision]')].filter(row => selected.has(row.dataset.decision));
            } else if (form.matches('[data-decision-delete]')) {
                removed = [form.closest('[data-decision]')];
            }
            clearTimeout(filterTimer);
            writing = true;
            ++latestLoad;
            results.setAttribute('aria-busy', 'true');
            const focused = document.activeElement;
            const controls = [...decisions.querySelectorAll('input, select, textarea, button')].filter(control => !control.disabled);
            try {
                const pending = post(form);
                controls.forEach(control => { control.disabled = true; });
                removed.forEach(row => { row.hidden = true; });
                let data;
                try {
                    data = await pending;
                } catch (error) {
                    removed.forEach(row => { row.hidden = false; });
                    const note = form.matches('[data-decision-update]') ? form.querySelector('textarea') : null;
                    if (note) note.value = note.defaultValue;
                    notify(error.message, 'error');
                    return;
                }
                if (form.matches('[data-decision-create]')) form.reset();
                const refreshed = await loadHistory(window.location.href);
                if (!refreshed) removed.forEach(row => { row.remove(); });
                notify(refreshed ? data.message : `${data.message} Muat ulang daftar untuk melihat perubahan.`, refreshed ? 'success' : 'normal');
            } finally {
                writing = false;
                results.removeAttribute('aria-busy');
                controls.forEach(control => { control.disabled = false; });
                if (focused && decisions.contains(focused)) focused.focus({preventScroll: true});
                else (document.getElementById(focused?.id) || results).focus({preventScroll: true});
            }
        });

        decisions.addEventListener('click', event => {
            const link = event.target.closest('[data-page], [data-filter-reset]');
            if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
            event.preventDefault();
            if (writing) return;
            clearTimeout(filterTimer);
            if (link.matches('[data-filter-reset]')) {
                for (const control of filterForm.elements) {
                    if (control.name) control.value = '';
                }
            }
            loadHistory(link.href);
        });
        filterForm.addEventListener('input', event => {
            if (event.target.name !== 'q') return;
            clearTimeout(filterTimer);
            filterTimer = setTimeout(applyFilters, 300);
        });
        filterForm.addEventListener('change', event => {
            if (event.target.name !== 'q') applyFilters();
        });
    }
})();
