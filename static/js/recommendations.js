(() => {
    const form = document.querySelector('[data-vote-form]');
    if (!form) return;

    const buttons = [...form.querySelectorAll('[data-vote-button]')];
    const status = form.querySelector('[data-vote-status]');
    const agreeCount = document.querySelector('[data-agree-count]');
    const disagreeCount = document.querySelector('[data-disagree-count]');
    const score = document.querySelector('[data-score]');

    function showCurrentVote(value) {
        form.dataset.currentVote = value ?? '';
    }

    form.addEventListener('submit', async event => {
        event.preventDefault();
        const button = event.submitter;
        if (!button) return;

        buttons.forEach(item => { item.disabled = true; });
        status.textContent = 'Menyimpan suara...';

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                body: new URLSearchParams({value: button.value}),
                headers: {
                    'Accept': 'application/json',
                    'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value,
                },
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Permintaan gagal.');

            showCurrentVote(data.value);
            agreeCount.textContent = data.agree_count;
            disagreeCount.textContent = data.disagree_count;
            score.textContent = data.score;
            status.textContent = data.value === null ? 'Suara ditarik.' : 'Suara disimpan.';
        } catch (error) {
            status.textContent = error.message || 'Gagal menyimpan suara. Coba lagi.';
        } finally {
            buttons.forEach(item => { item.disabled = false; });
        }
    });
})();
