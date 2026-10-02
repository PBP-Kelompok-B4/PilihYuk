let toastTimer;

function showToast(title, message, type = 'normal', duration = 3000) {
    const toast = document.getElementById('toast-component');
    if (!toast) return;
    toast.dataset.type = type;
    document.getElementById('toast-title').textContent = title;
    document.getElementById('toast-message').textContent = message;

    clearTimeout(toastTimer);
    if (!toast.matches(':popover-open')) {
        toast.showPopover();
        void toast.offsetHeight;
    }
    toast.classList.add('toast-show');

    toastTimer = setTimeout(() => {
        toast.classList.remove('toast-show');
        toastTimer = setTimeout(() => toast.hidePopover(), 300);
    }, duration);
}
