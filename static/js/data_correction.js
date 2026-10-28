/* Modul 4 (Antrean Data): peningkatan halaman dengan JavaScript.
 *
 * Notes:
 * - Semua halaman tetap berfungsi tanpa JavaScript (form POST biasa). File ini hanya
 *   menambah kirim lewat fetch tanpa memuat ulang halaman.
 * - Server tidak berubah: permintaan memakai header Accept: application/json, jadi view
 *   membalas JSON (responses.wants_json). Bentuk error dari server:
 *       {"error": {"id": "...", "message": "..."}, "fields": {"<field>": [{"message": "..."}]}}
 * - Kunci JSON yang dibaca file ini (dijaga tes Django JsJsonContractTests; atribut data-*
 *   dan <template> di HTML dijaga JsTemplateHookTests):
 *       ajukan  201: detail_url, product.product_name      gagal: error.message, fields
 *       tinjau  200: item.id, item.status, item.status_label, item.label, stale
 *               gagal: error.message, fields.review_note
 *       tarik   200: deleted, id                           gagal: error.message
 *       401 di mana pun: diarahkan ke halaman masuk (?next= halaman ini).
 * - Umpan balik selalu lewat showToast(title, message, type, duration) dari toast.js.
 *   Type yang punya gaya di tailwind.html: "success" dan "error"; selain itu tampil biasa.
 * - Satu nama global saja: window.DataCorrection.
 *
 * Daftar isi:
 * 1. Helper      : getCsrfToken, postJSON, reportFailure, swapRegion, setError
 * 2. Form ajukan : baris "Field | Nilai saat ini | Usulan nilai" + "+ Tambah field lain"
 * 3. Moderasi    : Setujui/Tolak, cek catatan, chip, statistik, item berikutnya
 * 4. Tarik       : hapus kartu sesudah ditarik
 * 5. Antrean     : urutan, filter, dan halaman /antrean/ tanpa memuat ulang
 * 6. Pemasangan  : event delegation dan tombol kembali browser
 */
(() => {
    'use strict';

    const LOGIN_URL = (document.currentScript && document.currentScript.dataset.loginUrl) || '/masuk/';
    const NUMBER = new Intl.NumberFormat('id-ID');
    const FAILURE_TITLES = {
        400: 'Periksa kembali isian',
        403: 'Akses ditolak',
        404: 'Data tidak ditemukan',
        409: 'Tidak bisa diproses',
    };
    const correctionForms = new WeakMap();  // form ajukan -> keadaan baris dinamis
    let rowCounter = 0;
    let shownUrl = window.location.pathname + window.location.search;  // isi yang sedang tampil

    // 1. Helper

    function getCsrfToken(form) {
        const input = (form && form.querySelector('[name=csrfmiddlewaretoken]'))
            || document.querySelector('[name=csrfmiddlewaretoken]');
        if (input && input.value) return input.value;
        // Cadangan: cookie csrftoken. Kalau CSRF_COOKIE_HTTPONLY aktif, cookie ini tidak
        // terbaca JavaScript dan hasilnya kosong (server lalu menolak dengan 403).
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    // Hasil: {ok, status, data}. status 0 berarti gagal jaringan (tidak ada respons).
    async function postJSON(url, formData, form) {
        let response;
        try {
            response = await fetch(url, {
                method: 'POST',
                body: formData,
                credentials: 'same-origin',
                headers: {'Accept': 'application/json', 'X-CSRFToken': getCsrfToken(form)},
            });
        } catch (error) {
            return {ok: false, status: 0, data: null};
        }
        const isJson = (response.headers.get('Content-Type') || '').includes('application/json');
        const data = isJson ? await response.json().catch(() => null) : null;
        // Balasan sukses yang bukan JSON (mis. halaman HTML) dianggap gagal.
        return {ok: response.ok && data !== null, status: response.status, data};
    }

    function toast(title, message, type, duration) {
        if (typeof window.showToast === 'function') window.showToast(title, message, type, duration);
    }

    function goToLogin() {
        const next = window.location.pathname + window.location.search;
        window.location.assign(`${LOGIN_URL}?next=${encodeURIComponent(next)}`);
    }

    // 400, 403, 404, 409 memakai pesan server; 401 ke halaman masuk; 500 dan gagal jaringan
    // memakai pesan umum.
    function reportFailure(result) {
        const message = result.data && result.data.error && result.data.error.message;
        if (result.status === 401) return goToLogin();
        if (result.status === 0) {
            return toast('Tidak ada koneksi', 'Periksa koneksi internet lalu coba lagi.', 'error');
        }
        if (result.status === 403 && !message) {  // token CSRF kedaluwarsa (balasan HTML Django)
            return toast('Sesi formulir kedaluwarsa', 'Muat ulang halaman lalu coba lagi.', 'error');
        }
        if (result.status >= 500 || !message) {
            return toast('Terjadi kesalahan di server', 'Coba lagi beberapa saat lagi.', 'error');
        }
        return toast(FAILURE_TITLES[result.status] || 'Gagal', message, 'error');
    }

    // getAttribute, bukan properti action: di form tinjau ada tombol bernama "action", jadi
    // properti itu berisi tombol-tombol tersebut, bukan alamat tujuan.
    function formAction(form) {
        return form.getAttribute('action') || window.location.href;
    }

    function cloneTemplate(root, selector) {
        return root.querySelector(selector).content.firstElementChild.cloneNode(true);
    }

    function hidePopover(element) {
        if (element && typeof element.hidePopover === 'function' && element.matches(':popover-open')) {
            element.hidePopover();
        }
    }

    function setBusy(buttons, busy) {
        buttons.forEach(button => {
            button.disabled = busy;
            button.setAttribute('aria-busy', String(busy));
        });
    }

    // Muat halaman lain (HTML), lalu ganti satu bagian halaman ini dengan bagian yang sama
    // dari halaman itu. Kalau gagal, pindah halaman seperti biasa.
    async function swapRegion(url, selector, {push = true, focus = true} = {}) {
        try {
            const response = await fetch(url, {credentials: 'same-origin', headers: {'Accept': 'text/html'}});
            const target = new URL(url, window.location.href);
            if (response.redirected && new URL(response.url).pathname !== target.pathname) {
                window.location.assign(response.url);  // mis. sesi habis -> halaman masuk
                return null;
            }
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const page = new DOMParser().parseFromString(await response.text(), 'text/html');
            const current = document.querySelector(selector);
            const next = page.querySelector(selector);
            if (!current || !next) throw new Error('bagian halaman tidak ditemukan');
            current.replaceWith(next);
            document.title = page.title;
            const state = {dataCorrection: true};
            const sameUrl = target.href === window.location.href;
            if (push && !sameUrl) window.history.pushState(state, '', target.href);
            else window.history.replaceState(state, '', target.href);
            shownUrl = target.pathname + target.search;
            enhance(next);
            if (focus) focusRegion(next);
            return next;
        } catch (error) {
            window.location.assign(url);
            return null;
        }
    }

    function swapMain(url, options) {
        return swapRegion(url, 'main', options);
    }

    // Fokus ke bagian baru (panel review, judul halaman, atau daftar antrean), lalu gulir ke
    // sana hanya kalau tidak terlihat. 96 px = tinggi header lengket + sedikit jarak.
    function focusRegion(region) {
        const target = region.matches('[data-queue-results]') ? region
            : region.querySelector('[data-review-panel]') || region.querySelector('h1');
        if (!target) return;
        if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
        target.focus({preventScroll: true});
        const top = target.getBoundingClientRect().top;
        if (top < 0 || top > window.innerHeight) window.scrollTo({top: window.scrollY + top - 96});
    }

    // Error per field, tepat di bawah kotaknya (sama seperti versi server).
    function setError(input, messages) {
        clearError(input);
        const box = document.createElement('div');
        box.id = `${input.id}_error`;
        messages.forEach(message => {
            const line = cloneTemplate(input.form, '[data-error-template]');
            line.textContent = message;
            box.append(line);
        });
        input.after(box);
        input.setAttribute('aria-invalid', 'true');
        const ids = (input.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
        input.setAttribute('aria-describedby', [...new Set([...ids, box.id])].join(' '));
    }

    function clearError(input) {
        const box = document.getElementById(`${input.id}_error`);
        if (box) box.remove();
        input.removeAttribute('aria-invalid');
        const ids = (input.getAttribute('aria-describedby') || '').split(/\s+/)
            .filter(id => id && id !== `${input.id}_error`);
        if (ids.length) input.setAttribute('aria-describedby', ids.join(' '));
        else input.removeAttribute('aria-describedby');
    }

    // 2. Form ajukan
    // Kotak asli (input + error + teks bantuan) dipindah dari daftar 14 kotak ke baris yang
    // memilih field itu, jadi nama, atribut, dan isi POST-nya sama persis dengan versi tanpa JS.

    function enhanceCorrectionForm(form) {
        if (correctionForms.has(form)) return;
        const fields = [...form.querySelectorAll('[data-static-fields] [data-field-row]')].map(row => ({
            name: row.dataset.field,
            label: row.dataset.label,
            group: row.closest('[data-group-title]').dataset.groupTitle,
            current: row.dataset.current,
            display: row.dataset.currentDisplay,
            focus: row.hasAttribute('data-focus'),
            home: row,
            control: row.querySelector('[data-field-control]'),
            input: row.querySelector('[data-field-control] input'),
        }));
        const state = {
            fields,
            byName: new Map(fields.map(field => [field.name, field])),
            list: form.querySelector('[data-rows]'),
            addButton: form.querySelector('[data-add-field]'),
        };
        correctionForms.set(form, state);

        form.querySelector('[data-static-fields]').hidden = true;
        form.querySelector('[data-dynamic-fields]').hidden = false;
        form.querySelectorAll('[data-static-only]').forEach(element => { element.hidden = true; });
        form.querySelectorAll('[data-dynamic-only]').forEach(element => { element.hidden = false; });

        // Baris awal: field dari ?field=, field yang sudah berisi, atau field yang punya error.
        const initial = fields.filter(field => field.focus || field.input.value.trim()
            || field.control.querySelector(`[id="${field.input.id}_error"]`));
        (initial.length ? initial : [null]).forEach(field => addRow(form, field));
        const first = initial.find(field => field.focus);
        if (first) first.input.focus();
    }

    function addRow(form, field) {
        const state = correctionForms.get(form);
        const row = cloneTemplate(form, '[data-row-template]');
        const select = row.querySelector('[data-field-select]');
        select.id = `pilih-field-${++rowCounter}`;
        row.querySelector('[data-select-label]').htmlFor = select.id;
        const groups = new Map();
        state.fields.forEach(item => {
            if (!groups.has(item.group)) {
                const optgroup = document.createElement('optgroup');
                optgroup.label = item.group;
                groups.set(item.group, optgroup);
                select.append(optgroup);
            }
            groups.get(item.group).append(new Option(item.label, item.name));
        });
        state.list.append(row);
        setField(form, row, field);
        return row;
    }

    function setField(form, row, field) {
        const state = correctionForms.get(form);
        const previous = state.byName.get(row.dataset.field);
        let carried = '';
        if (previous && previous !== field) {
            carried = previous.input.value;  // isian dibawa ke field baru, field lama dikosongkan
            previous.input.value = '';
            clearError(previous.input);
            previous.input.removeAttribute('aria-label');
            previous.home.append(previous.control);
        }
        const slot = row.querySelector('[data-input-slot]');
        const current = row.querySelector('[data-current-value]');
        slot.querySelector('[data-placeholder-input]').hidden = Boolean(field);
        if (field) {
            row.dataset.field = field.name;
            if (carried && !field.input.value) field.input.value = carried;
            field.input.setAttribute('aria-label', `Usulan nilai untuk ${field.label}`);
            slot.append(field.control);
            if (field.current.trim()) current.textContent = field.display;
            else current.replaceChildren(cloneTemplate(form, '[data-unknown-template]'));
        } else {
            delete row.dataset.field;
            current.textContent = '—';
        }
        row.querySelector('[data-field-select]').value = field ? field.name : '';
        refreshRows(form);
    }

    // Field yang sudah dipakai di baris lain dinonaktifkan; tombol hapus hanya ada kalau
    // barisnya lebih dari satu; "+ Tambah field lain" mati kalau semua field sudah dipakai.
    function refreshRows(form) {
        const state = correctionForms.get(form);
        const rows = [...state.list.querySelectorAll('[data-row]')];
        const used = new Set(rows.map(row => row.dataset.field).filter(Boolean));
        rows.forEach(row => {
            row.querySelectorAll('option').forEach(option => {
                const usedElsewhere = used.has(option.value) && option.value !== row.dataset.field;
                option.disabled = Boolean(option.value) && usedElsewhere;
            });
            row.querySelector('[data-remove-field]').hidden = rows.length === 1;
        });
        state.addButton.disabled = used.size >= state.fields.length;
    }

    function onAddField(button) {
        const form = button.closest('[data-correction-form]');
        const state = correctionForms.get(form);
        const empty = [...state.list.querySelectorAll('[data-row]')].find(row => !row.dataset.field);
        (empty || addRow(form, null)).querySelector('[data-field-select]').focus();
    }

    function onRemoveField(button) {
        const form = button.closest('[data-correction-form]');
        const row = button.closest('[data-row]');
        const neighbour = row.previousElementSibling || row.nextElementSibling;
        setField(form, row, null);
        row.remove();
        refreshRows(form);
        if (neighbour) neighbour.querySelector('[data-field-select]').focus();
        else correctionForms.get(form).addButton.focus();
    }

    function onFieldSelect(select) {
        const form = select.closest('[data-correction-form]');
        const field = correctionForms.get(form).byName.get(select.value) || null;
        setField(form, select.closest('[data-row]'), field);
    }

    function showFormAlert(form, messages) {
        const alert = form.querySelector('[data-form-alert]');
        alert.replaceChildren(...messages.map(message => {
            const line = document.createElement('p');
            line.textContent = message;
            return line;
        }));
        alert.hidden = messages.length === 0;
    }

    async function submitCorrection(form, event) {
        event.preventDefault();
        const button = form.querySelector('[data-submit-button]');
        if (button.disabled) return;  // cegah klik ganda
        const label = button.textContent;
        button.textContent = 'Mengirim…';
        setBusy([button], true);
        showFormAlert(form, []);
        form.querySelectorAll('[data-row] [aria-invalid="true"]').forEach(clearError);

        const result = await postJSON(formAction(form), new FormData(form), form);
        if (result.ok) {
            const product = result.data.product.product_name || 'produk ini';
            const message = `Usulan untuk ${product} menunggu tinjauan kurator.`;
            toast('Pengajuan berhasil dikirim', message, 'success');
            const url = new URL(result.data.detail_url, window.location.href);
            url.searchParams.set('terkirim', '1');
            await swapMain(url.href);  // kartu sukses dari server, tanpa memuat ulang halaman
            return;
        }
        button.textContent = label;
        setBusy([button], false);
        if (result.status === 400 && result.data) {
            const loose = [];
            let firstInvalid = null;
            Object.entries(result.data.fields || {}).forEach(([name, errors]) => {
                const messages = errors.map(error => error.message);
                const input = form.elements.namedItem(name);
                if (input instanceof HTMLInputElement && input.closest('[data-row]')) {
                    setError(input, messages);
                    firstInvalid = firstInvalid || input;
                } else {
                    loose.push(...messages.map(message => `${name}: ${message}`));
                }
            });
            showFormAlert(form, [result.data.error.message, ...loose]);
            if (firstInvalid) firstInvalid.focus();
        }
        reportFailure(result);
    }

    // 3. Moderasi

    function onRejectTrigger(trigger, event) {
        const form = trigger.closest('[data-review-form]');
        const note = form.elements.namedItem('review_note');
        if (note.value.trim()) {
            clearError(note);
            return;  // popover konfirmasi dibuka oleh browser
        }
        event.preventDefault();  // catatan kosong: jangan buka konfirmasi
        setError(note, [form.dataset.noteRequired]);
        note.focus();
    }

    async function submitReview(form, event) {
        const action = event.submitter && event.submitter.value;
        if (action !== 'approve' && action !== 'reject') return;  // terkirim biasa (tanpa fetch)
        event.preventDefault();
        const note = form.elements.namedItem('review_note');
        const dialog = form.querySelector('[data-reject-dialog]');
        if (action === 'reject' && !note.value.trim()) {
            hidePopover(dialog);
            setError(note, [form.dataset.noteRequired]);
            note.focus();
            return;
        }
        const buttons = [...form.querySelectorAll('button')];
        if (buttons.some(button => button.disabled)) return;
        setBusy(buttons, true);
        const body = new FormData(form);
        body.set('action', action);
        const result = await postJSON(formAction(form), body, form);
        hidePopover(dialog);
        if (result.ok) {
            await afterReview(form, result.data);
            return;
        }
        setBusy(buttons, false);
        const noteErrors = result.data && result.data.fields && result.data.fields.review_note;
        if (noteErrors) {
            setError(note, noteErrors.map(error => error.message));
            note.focus();
        }
        reportFailure(result);
        if (result.status === 404 || result.status === 409) {
            await swapMain(window.location.href, {push: false});  // tampilkan keadaan terbaru
        }
    }

    async function afterReview(form, data) {
        const panel = form.closest('[data-review-panel]');
        const subject = `${data.item.label} untuk ${panel ? panel.dataset.productName : 'produk ini'}`;
        const approved = data.item.status === 'approved';
        if (approved && data.stale) {
            toast('Usulan disetujui, nilai lama ditimpa',
                `${subject}: nilai produk sempat berubah sejak diajukan dan kini sudah ditimpa.`,
                'normal', 6000);  // lebih lama dari bawaan 3 detik supaya sempat terbaca
        } else if (approved) {
            toast('Usulan disetujui', `${subject}; data produk sudah diperbarui.`, 'success');
        } else {
            toast('Usulan ditolak', `${subject}; catatan tersimpan untuk pengaju.`, 'success');
        }

        const row = document.querySelector(`[data-queue-row][data-item-id="${data.item.id}"]`);
        if (row) {
            row.dataset.status = data.item.status;
            const holder = row.querySelector('[data-row-status]');
            const chipTemplate = document.querySelector(`template[data-chip-template="${data.item.status}"]`);
            if (holder && chipTemplate) {
                const chip = chipTemplate.content.firstElementChild.cloneNode(true);
                chip.textContent = data.item.status_label;
                holder.replaceChildren(chip);
            }
        }
        bumpStat('pending', -1);
        bumpStat(approved ? 'approved' : 'rejected', 1);

        // Item pending berikutnya di daftar; kalau tidak ada, kembali ke antrean (empty state
        // tampil dari server bila memang sudah habis).
        const rows = [...document.querySelectorAll('[data-queue-row]')];
        const pending = rows.filter(item => item.dataset.status === 'pending');
        const after = pending.find(item => rows.indexOf(item) > rows.indexOf(row));
        const next = after || pending[0];
        const back = form.elements.namedItem('next').value || window.location.pathname;
        await swapMain(next ? next.dataset.reviewUrl : back);
    }

    function bumpStat(name, delta) {
        const element = document.querySelector(`[data-stat="${name}"]`);
        if (!element) return;
        const value = Number(element.textContent.replace(/\D/g, '')) + delta;
        element.textContent = NUMBER.format(Math.max(0, value));
    }

    // 4. Tarik pengajuan

    async function submitWithdraw(form, event) {
        event.preventDefault();
        const buttons = [...form.querySelectorAll('button')];
        if (buttons.some(button => button.disabled)) return;
        setBusy(buttons, true);
        const dialog = form.closest('[popover]');
        const result = await postJSON(formAction(form), new FormData(form), form);
        hidePopover(dialog);
        if (result.ok && result.data.deleted) {
            const message = `Pengajuan untuk ${form.dataset.productName} sudah dihapus.`;
            toast('Pengajuan ditarik', message, 'success');
            const card = document.querySelector(`[data-correction-card="${result.data.id}"]`);
            if (!card) {
                // Dari halaman detail -> Pengajuan Saya. replaceState: detail itu sudah tidak ada.
                await swapMain(form.dataset.afterUrl, {push: false});
                return;
            }
            const neighbour = card.nextElementSibling || card.previousElementSibling;
            card.remove();
            if (document.querySelector('[data-correction-card]')) {
                neighbour.querySelector('a').focus();
            } else {
                await swapMain(window.location.href, {push: false});  // empty state atau halaman lain
            }
            return;
        }
        setBusy(buttons, false);
        reportFailure(result);
        if (result.status === 409) await swapMain(window.location.href, {push: false});
        else if (result.status === 404) await swapMain(form.dataset.afterUrl, {push: false});
    }

    // 5. Antrean kontribusi: hanya tautan ke /antrean/ sendiri (chip urutan, chip filter,
    // nomor halaman, "Bersihkan filter"). "Lengkapi Data" dan "Detail" tetap pindah halaman.

    function isPlainClick(event) {
        return event.button === 0 && !event.defaultPrevented
            && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
    }

    function onQueueLink(link, event) {
        if ((link.target && link.target !== '_self') || link.hasAttribute('download')) return;
        const url = new URL(link.href, window.location.href);
        if (url.origin !== window.location.origin || url.pathname !== window.location.pathname) return;
        event.preventDefault();
        loadQueue(url.href, true);
    }

    async function loadQueue(url, push) {
        const region = document.querySelector('[data-queue-results]');
        region.setAttribute('aria-busy', 'true');
        const next = await swapRegion(url, '[data-queue-results]', {push});
        if (!next) return;
        const status = document.querySelector('[data-queue-status]');
        const summary = next.querySelector('[data-queue-summary]') || next.querySelector('section p');
        if (status) status.textContent = summary ? summary.textContent.trim() : '';
    }

    // 6. Pemasangan

    function enhance(root) {
        root.querySelectorAll('[data-correction-form]').forEach(enhanceCorrectionForm);
    }

    document.addEventListener('submit', event => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement)) return;
        if (form.matches('[data-correction-form]')) submitCorrection(form, event);
        else if (form.matches('[data-review-form]')) submitReview(form, event);
        else if (form.matches('[data-withdraw-form]')) submitWithdraw(form, event);
    });

    document.addEventListener('click', event => {
        const target = event.target instanceof Element ? event.target : null;
        if (!target) return;
        const reject = target.closest('[data-reject-trigger]');
        const add = target.closest('[data-add-field]');
        const remove = target.closest('[data-remove-field]');
        const link = target.closest('[data-queue-results] a[href]');
        if (reject) onRejectTrigger(reject, event);
        else if (add) onAddField(add);
        else if (remove) onRemoveField(remove);
        else if (link && isPlainClick(event)) onQueueLink(link, event);
    });

    document.addEventListener('change', event => {
        if (event.target instanceof HTMLSelectElement && event.target.matches('[data-field-select]')) {
            onFieldSelect(event.target);
        }
    });

    // Error hilang begitu isiannya diubah.
    document.addEventListener('input', event => {
        const input = event.target;
        if (input instanceof HTMLElement && input.getAttribute('aria-invalid') === 'true'
            && input.closest('[data-correction-form], [data-review-form]')) {
            clearError(input);
        }
    });

    // Tombol kembali/maju browser sesudah history.pushState di atas.
    window.addEventListener('popstate', () => {
        if (window.location.pathname + window.location.search === shownUrl) return;  // hanya #anchor
        if (document.querySelector('[data-queue-results]')) loadQueue(window.location.href, false);
        else swapMain(window.location.href, {push: false});
    });

    enhance(document);
    window.DataCorrection = Object.freeze({getCsrfToken, postJSON, swapMain});
})();