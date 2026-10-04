// Tombol "Tampilkan/Sembunyikan" di field password.
document.querySelectorAll('[data-toggle-password]').forEach((btn) => {
    btn.addEventListener('click', () => {
        const input = document.getElementById(btn.dataset.togglePassword);
        const show = input.type === 'password';
        input.type = show ? 'text' : 'password';
        btn.textContent = show ? 'Sembunyikan' : 'Tampilkan';
        btn.setAttribute('aria-pressed', String(show));
    });
});
