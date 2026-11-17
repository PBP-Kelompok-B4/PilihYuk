// Run with node product_catalog/test_suites/test_catalog_client.cjs (no npm dependency).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const elements = new Map();
for (const id of ['catalog-filter', 'catalog-results', 'catalog-status']) {
    elements.set(id, {listeners: {}, attributes: {}, innerHTML: '', textContent: '',
        addEventListener(name, fn) { this.listeners[name] = fn; },
        setAttribute(name, value) { this.attributes[name] = value; },
        removeAttribute(name) { delete this.attributes[name]; }});
}
const requests = [];
const history = {replaceState(...args) { this.url = String(args[2]); }};
const context = {document: {getElementById: id => elements.get(id)},
    window: {location: {href: 'http://localhost/katalog/', pathname: '/katalog/'}},
    URL, URLSearchParams, AbortController, history,
    FormData: class { constructor() { return [['q', '<script>'], ['brand', 'Test']]; } },
    fetch(url, options) { return new Promise((resolve, reject) => requests.push({url, options, resolve, reject})); }};
vm.runInNewContext(fs.readFileSync('static/js/product_catalog.js', 'utf8'), context);
const flush = () => new Promise(resolve => setImmediate(resolve));
(async () => {
    const form = elements.get('catalog-filter');
    const results = elements.get('catalog-results');
    const status = elements.get('catalog-status');
    let prevented = false;
    form.listeners.submit({preventDefault() { prevented = true; }});
    assert(prevented);
    assert.equal(requests[0].url.searchParams.get('brand'), 'Test');
    assert.equal(requests[0].url.searchParams.get('partial'), '1');
    requests[0].resolve({ok: true, text: async () => '<p>Escaped server HTML</p>'});
    await flush();
    assert.equal(results.innerHTML, '<p>Escaped server HTML</p>');
    assert(!history.url.includes('partial='));
    results.listeners.click({target: {closest: () => ({href: 'http://localhost/katalog/?brand=Test&page=2'})}, preventDefault() {}});
    assert.equal(requests[1].url.searchParams.get('page'), '2');
    requests[1].resolve({ok: false});
    await flush();
    assert(status.textContent.startsWith('Gagal'));
    assert.equal(results.innerHTML, '<p>Escaped server HTML</p>');
    form.listeners.submit({preventDefault() {}});
    form.listeners.submit({preventDefault() {}});
    assert(requests[2].options.signal.aborted);
    requests[3].resolve({ok: true, text: async () => '<p>Latest</p>'});
    requests[2].resolve({ok: true, text: async () => '<p>Stale</p>'});
    await flush();
    assert.equal(results.innerHTML, '<p>Latest</p>');
    // B succeeds, then A fails. Test both HTTP and rejected-network failures.
    for (const failure of ['http', 'network']) {
        form.listeners.submit({preventDefault() {}});
        const a = requests[requests.length - 1];
        form.listeners.submit({preventDefault() {}});
        const b = requests[requests.length - 1];
        b.resolve({ok: true, text: async () => `<p>Newest ${failure}</p>`});
        await flush();
        const latest = {html: results.innerHTML, status: status.textContent, url: history.url};
        if (failure === 'http') a.resolve({ok: false});
        else a.reject(new Error('old network failure'));
        await flush();
        assert.equal(results.innerHTML, latest.html);
        assert.equal(status.textContent, latest.status);
        assert.equal(history.url, latest.url);
        }
    // B fails, then A succeeds: keep B's error and the previously displayed data.
    form.listeners.submit({preventDefault() {}});
    const oldSuccess = requests[requests.length - 1];
    form.listeners.submit({preventDefault() {}});
    const newFailure = requests[requests.length - 1];
    const previousHTML = results.innerHTML;
    const previousURL = history.url;
    newFailure.resolve({ok: false});
    await flush();
    const newestError = status.textContent;
    assert(newestError.startsWith('Gagal'));
    oldSuccess.resolve({ok: true, text: async () => '<p>Outdated success</p>'});
    await flush();
    assert.equal(status.textContent, newestError);
    assert.equal(results.innerHTML, previousHTML);
    assert.equal(history.url, previousURL);
    // A's failure while B is pending must not clear B's loading/error state.
    form.listeners.submit({preventDefault() {}});
    const oldPending = requests[requests.length - 1];
    form.listeners.submit({preventDefault() {}});
    const latestPending = requests[requests.length - 1];
    const loadingStatus = status.textContent;
    oldPending.reject(new Error('stale failure while loading'));
    await flush();
    assert.equal(status.textContent, loadingStatus);
    latestPending.resolve({ok: true, text: async () => '<p>Final</p>'});
    await flush();
    assert.equal(results.innerHTML, '<p>Final</p>');
    console.log('PASS: AJAX filtering, pagination, error, loading, and stale response handling');
})().catch(error => { console.error(error); process.exitCode = 1; });
