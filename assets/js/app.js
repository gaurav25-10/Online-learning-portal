document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-confirm]').forEach((element) => {
    element.addEventListener('click', (event) => {
      if (!confirm(element.dataset.confirm)) {
        event.preventDefault();
      }
    });
  });

  document.querySelectorAll('.auto-dismiss').forEach((alert) => {
    setTimeout(() => alert.remove(), 3500);
  });
});

