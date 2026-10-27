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
        const rows = [...preferences.querySelectorAll('[data-nutrient]')];
        const status = preferences.querySelector('[data-draft-status]');
        const summary = preferences.querySelector('[data-draft-summary]');
        const output = preferences.querySelector('[data-combined-preview]');
        const loading = preferences.querySelector('[data-preview-loading]');
        const retry = preferences.querySelector('[data-preview-retry]');
        let saving = false;
        let previewVersion = 0;
        let previewTimer;
        function readDraft() {
            return rows.map(row => ({nutrient: row.dataset.nutrient,
                active: row.querySelector('[role="switch"]').getAttribute('aria-checked') === 'true',
                direction: row.querySelector('[data-direction-input]:checked').value,
                weight: Number(row.querySelector('[data-weight-input]:checked').value)}));
        }
        let baseline = JSON.stringify(readDraft());
        function element(tag, classes, text) {
            const node = document.createElement(tag);
            node.className = classes;
            node.textContent = text;
            return node;
        }
        function renderDraft() {
            summary.replaceChildren();
            readDraft().forEach((item, index) => {
                const row = rows[index];
                row.querySelectorAll('fieldset').forEach(field => { field.disabled = saving || !item.active; });
                row.querySelector('[data-toggle-track]').classList.toggle('bg-brand', item.active);
                row.querySelector('[data-toggle-track]').classList.toggle('bg-track', !item.active);
                row.querySelector('[data-toggle-thumb]').classList.toggle('translate-x-4', item.active);
                if (item.active) summary.append(element('span', 'chip bg-mint text-brand',
                    `${row.querySelector('h3').textContent.trim()} ${item.direction === 'max' ? '↑' : '↓'} · ${['Rendah', 'Sedang', 'Tinggi'][item.weight - 1]}`));
            });
            if (!summary.childElementCount) summary.append(element('p', 'text-sm text-muted', 'Belum ada preferensi aktif.'));
            status.textContent = saving ? 'Menyimpan…' : JSON.stringify(readDraft()) === baseline ? 'Semua perubahan tersimpan.' : 'Ada perubahan belum disimpan.';
            preferences.querySelectorAll('button').forEach(button => { button.disabled = saving; });
        }
        function jsonPost(url, draft) {
            return request(url, {method: 'POST', body: JSON.stringify({preferences: draft}),
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': preferences.querySelector('[name=csrfmiddlewaretoken]').value}});
        }
        async function preview() {
            const version = ++previewVersion;
            const draft = readDraft();
            retry.hidden = true;
            if (!draft.some(item => item.active)) {
                loading.hidden = true;
                output.removeAttribute('aria-busy');
                output.replaceChildren(element('p', 'rounded-xl bg-surface p-4 text-sm text-muted', 'Aktifkan nutrien untuk melihat pratinjau.'));
                return;
            }
            loading.hidden = false;
            output.setAttribute('aria-busy', 'true');
            try {
                const data = await jsonPost(preferences.dataset.previewUrl, draft);
                if (version !== previewVersion) return;
                output.replaceChildren(element('p', 'rounded-xl bg-mint p-5 text-sm font-semibold text-brand', `${data.ranked_count} produk dapat diperingkat`));
                if (!data.samples.length) output.append(element('p', 'text-sm text-muted', 'Belum ada produk dengan data pada nutrien aktif.'));
                data.samples.forEach((sample, index) => {
                    const card = element('div', 'rounded-xl border border-line p-3', '');
                    card.append(element('p', 'break-words text-sm font-semibold', `${index + 1}. ${sample.name || 'Tidak diketahui'}`));
                    card.append(element('p', 'mt-1 break-words text-xs text-muted', sample.values.map(value =>
                        `${value.label}: ${value.value === null ? 'Tidak diketahui' : value.value + ' ' + value.unit}`).join(' · ')));
                    output.append(card);
                });
            } catch (error) {
                if (version === previewVersion) {
                    output.replaceChildren(element('p', 'rounded-xl bg-warm p-4 text-sm', `Pratinjau gagal dimuat. ${error.message}`));
                    retry.hidden = false;
                }
            } finally {
                if (version === previewVersion) { loading.hidden = true; output.removeAttribute('aria-busy'); }
            }
        }
        function changed() {
            ++previewVersion;
            clearTimeout(previewTimer);
            renderDraft();
            previewTimer = setTimeout(preview, 200);
        }
        preferences.addEventListener('change', event => {
            if (event.target.matches('[data-direction-input], [data-weight-input]')) changed();
        });
        preferences.addEventListener('click', async event => {
            const toggle = event.target.closest('[data-draft-toggle]');
            if (toggle && !saving) {
                toggle.setAttribute('aria-checked', String(toggle.getAttribute('aria-checked') !== 'true'));
                changed();
            }
            if (event.target.closest('[data-draft-reset]') && !saving) {
                rows.forEach(row => {
                    row.querySelector('[role="switch"]').setAttribute('aria-checked', 'false');
                    row.querySelectorAll('[data-direction-input]').forEach(input => { input.checked = input.value === row.dataset.defaultDirection; });
                    row.querySelectorAll('[data-weight-input]').forEach(input => { input.checked = input.value === '2'; });
                });
                changed();
                notify('Preferensi direset. Klik Simpan Preferensi untuk menerapkan perubahan.', 'normal');
            }
            if (event.target.closest('[data-preview-retry]')) preview();
            if (event.target.closest('[data-draft-save]') && !saving) {
                saving = true;
                preferences.setAttribute('aria-busy', 'true');
                const draft = readDraft();
                renderDraft();
                try {
                    const data = await jsonPost(preferences.dataset.saveUrl, draft);
                    baseline = JSON.stringify(draft);
                    notify(data.message);
                } catch (error) { notify(error.message, 'error'); }
                finally { saving = false; preferences.removeAttribute('aria-busy'); renderDraft(); }
            }
        });
        renderDraft();
        preview();
    }
    const decisions = document.querySelector('[data-decisions]');
    if (decisions) {
        const results = decisions.querySelector('[data-decision-results]');
        const filterForm = decisions.querySelector('[data-decision-filter]');
        const loading = decisions.querySelector('[data-history-loading]');
        const errorPanel = decisions.querySelector('[data-history-error]');
        const createDialog = decisions.querySelector('[data-create-dialog]');
        const editDialog = decisions.querySelector('[data-edit-dialog]');
        const confirmDialog = decisions.querySelector('[data-confirm-dialog]');
        const openers = new WeakMap();
        let pendingDelete;
        let latestLoad = 0;
        let filterTimer;
        let writing = false;
        let lastHistoryUrl = window.location.href;
        function openDialog(dialog, opener) {
            openers.set(dialog, opener);
            dialog.showModal();
        }
        decisions.querySelectorAll('dialog').forEach(dialog => {
            dialog.addEventListener('close', () => {
                const opener = openers.get(dialog);
                if (opener?.isConnected) opener.focus({preventScroll: true});
            });
            if (dialog.hasAttribute('data-open-on-load')) dialog.showModal();
        });
        async function loadHistory(url, reportError = true) {
            const loadId = ++latestLoad;
            lastHistoryUrl = url;
            const focused = results.contains(document.activeElement) ? document.activeElement.id : '';
            loading.hidden = false;
            errorPanel.hidden = true;
            results.setAttribute('aria-busy', 'true');
            try {
                const data = await request(url);
                if (loadId !== latestLoad) return false;
                results.innerHTML = data.html;
                decisions.querySelector('[data-history-tools]').innerHTML = data.tools_html;
                decisions.querySelector('[data-export]').href = data.export_url;
                for (const key of ['total', 'shelves', 'products']) decisions.querySelector(`[data-summary-${key}]`).textContent = data.summary[key];
                history.replaceState(null, '', data.url);
                lastHistoryUrl = window.location.href;
                const params = new URL(data.url, window.location.origin).searchParams;
                for (const control of filterForm.elements) {
                    if (control.name && document.activeElement !== control) control.value = params.get(control.name) || '';
                }
                if (focused) (document.getElementById(focused) || results).focus({preventScroll: true});
                return true;
            } catch (error) {
                if (loadId === latestLoad) {
                    errorPanel.hidden = false;
                    if (reportError) notify(error.message, 'error');
                }
                return false;
            } finally {
                if (loadId === latestLoad) { loading.hidden = true; results.removeAttribute('aria-busy'); }
            }
        }
        function applyFilters() {
            clearTimeout(filterTimer);
            if (writing) return;
            loadHistory(`${filterForm.action}?${new URLSearchParams(new FormData(filterForm))}`);
        }
        decisions.addEventListener('submit', async event => {
            const form = event.target;
            if (form === filterForm) { event.preventDefault(); applyFilters(); return; }
            if (!form.matches('[data-decision-create], [data-decision-update], [data-decision-delete], [data-decision-bulk]')) return;
            event.preventDefault();
            if (writing) return;
            let removed = [];
            if (form.matches('[data-decision-bulk]')) {
                const selected = new Set(new FormData(form).getAll('ids'));
                if (!selected.size) { notify('Pilih setidaknya satu keputusan.', 'error'); return; }
                removed = [...results.querySelectorAll('[data-decision]')].filter(row => selected.has(row.dataset.decision));
            } else if (form.matches('[data-decision-delete]')) removed = [form.closest('[data-decision]')];
            if (removed.length && form.dataset.confirmed !== 'true') {
                pendingDelete = form;
                decisions.querySelector('[data-confirm-message]').textContent = `${removed.length} keputusan akan dihapus permanen. Catatan yang dihapus tidak dapat dikembalikan.`;
                openDialog(confirmDialog, document.activeElement);
                return;
            }
            delete form.dataset.confirmed;
            clearTimeout(filterTimer);
            writing = true;
            ++latestLoad;
            form.setAttribute('aria-busy', 'true');
            results.setAttribute('aria-busy', 'true');
            const focused = document.activeElement;
            const controls = [...decisions.querySelectorAll('input, select, textarea, button')].filter(control => !control.disabled);
            try {
                const pending = post(form);
                controls.forEach(control => { control.disabled = true; });
                removed.forEach(row => { row.hidden = true; });
                let data;
                try { data = await pending; }
                catch (error) {
                    removed.forEach(row => { row.hidden = false; });
                    notify(error.message, 'error');
                    return;
                }
                if (form.matches('[data-decision-create]')) form.reset();
                form.closest('dialog')?.close();
                const refreshed = await loadHistory(lastHistoryUrl, false);
                if (!refreshed) removed.forEach(row => { row.remove(); });
                notify(refreshed ? data.message : `${data.message} Muat ulang daftar untuk melihat perubahan.`, refreshed ? 'success' : 'normal');
            } finally {
                writing = false;
                form.removeAttribute('aria-busy');
                loading.hidden = true;
                results.removeAttribute('aria-busy');
                controls.forEach(control => { control.disabled = false; });
                if (!decisions.querySelector('dialog[open]')) {
                    if (focused?.isConnected && !focused.closest('dialog')) focused.focus({preventScroll: true});
                    else results.focus({preventScroll: true});
                }
            }
        });
        decisions.addEventListener('click', event => {
            const close = event.target.closest('[data-close-dialog]');
            if (close) close.closest('dialog').close();
            const create = event.target.closest('[data-open-create]');
            if (create && !writing) openDialog(createDialog, create);
            const edit = event.target.closest('[data-decision-edit]');
            if (edit && !writing) {
                const form = editDialog.querySelector('form');
                form.action = edit.dataset.updateUrl;
                form.querySelector('textarea').value = edit.closest('[data-decision]').querySelector('[data-note-text]').textContent;
                openDialog(editDialog, edit);
            }
            if (event.target.closest('[data-confirm-delete]') && pendingDelete?.isConnected) {
                confirmDialog.close();
                pendingDelete.dataset.confirmed = 'true';
                pendingDelete.requestSubmit();
                pendingDelete = null;
            }
            if (event.target.closest('[data-history-retry]') && !writing) loadHistory(lastHistoryUrl);
            const link = event.target.closest('[data-page], [data-filter-reset], [data-history-chip]');
            if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
            event.preventDefault();
            if (writing) return;
            clearTimeout(filterTimer);
            loadHistory(link.href);
        });
        filterForm.addEventListener('input', event => {
            if (event.target.name !== 'q') return;
            ++latestLoad;
            clearTimeout(filterTimer);
            filterTimer = setTimeout(applyFilters, 300);
        });
        filterForm.addEventListener('change', event => { if (event.target.name !== 'q') applyFilters(); });
        decisions.addEventListener('error', event => {
            if (event.target.matches('[data-product-image]')) {
                event.target.hidden = true;
                event.target.parentElement.classList.add('bg-placeholder');
            }
        }, true);
    }
})();
