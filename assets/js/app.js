const navToggle = document.querySelector('.nav-toggle');
const mainNav = document.querySelector('.main-nav');

if (navToggle && mainNav) {
  navToggle.addEventListener('click', () => {
    const isOpen = mainNav.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', String(isOpen));
  });
}

document.querySelectorAll('input[type="file"]').forEach((input) => {
  input.addEventListener('change', () => {
    const label = input.closest('.file-input')?.querySelector('[data-file-label]');
    if (!label) return;
    label.textContent = input.files.length ? `${input.files.length} файл(ов) выбрано` : label.textContent;
  });
});

document.querySelectorAll('[data-accordion] .accordion-item').forEach((item) => {
  item.addEventListener('click', () => {
    item.parentElement.querySelectorAll('.accordion-item').forEach((button) => button.classList.remove('active'));
    item.classList.add('active');
  });
});

document.querySelectorAll('[data-auth-tab]').forEach((tab) => {
  tab.addEventListener('click', () => {
    const target = tab.dataset.authTab;
    document.querySelectorAll('[data-auth-tab]').forEach((button) => button.classList.toggle('active', button === tab));
    document.querySelectorAll('[data-auth-form]').forEach((form) => form.classList.toggle('active', form.dataset.authForm === target));
  });
});

document.querySelectorAll('[data-tab-link]').forEach((link) => {
  link.addEventListener('click', (event) => {
    const id = link.getAttribute('href');
    if (!id || !id.startsWith('#')) return;
    const panel = document.querySelector(id);
    if (!panel?.matches('[data-tab-panel]')) return;
    event.preventDefault();
    document.querySelectorAll('[data-tab-link]').forEach((item) => item.classList.toggle('active', item === link));
    document.querySelectorAll('[data-tab-panel]').forEach((item) => item.classList.toggle('active', item === panel));
    history.replaceState(null, '', id);
  });
});

const initialHash = window.location.hash;
if (initialHash) {
  const initialLink = document.querySelector(`[data-tab-link][href="${initialHash}"]`);
  if (initialLink) initialLink.click();
}

document.querySelectorAll('[data-status-filters] button').forEach((button) => {
  button.addEventListener('click', () => {
    const filter = button.dataset.filter;
    const group = button.closest('[data-status-filters]');
    group.querySelectorAll('button').forEach((item) => item.classList.toggle('active', item === button));
    group.parentElement.querySelectorAll('tbody tr[data-status]').forEach((row) => {
      row.hidden = filter !== 'all' && row.dataset.status !== filter;
    });
  });
});

document.querySelectorAll('[data-save-draft]').forEach((button) => {
  button.addEventListener('click', () => {
    const form = button.closest('form');
    const result = form.querySelector('[data-form-result]');
    const data = Object.fromEntries(new FormData(form).entries());
    localStorage.setItem('tendercheck.applicationDraft', JSON.stringify(data));
    if (result) {
      result.className = 'form-result';
      result.textContent = 'Черновик сохранён в браузере.';
    }
  });
});

document.querySelectorAll('[data-modal-open]').forEach((button) => {
  button.addEventListener('click', () => {
    const modal = document.querySelector(`[data-modal="${button.dataset.modalOpen}"]`);
    if (modal) modal.hidden = false;
  });
});

document.querySelectorAll('[data-modal-close]').forEach((button) => {
  button.addEventListener('click', () => {
    button.closest('[data-modal]').hidden = true;
  });
});

document.querySelectorAll('[data-api-form]').forEach((form) => {
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const result = form.querySelector('[data-form-result]');
    const submit = form.querySelector('[type="submit"]');
    const endpoint = form.dataset.endpoint;
    const success = form.dataset.success || 'Готово.';

    if (!form.reportValidity()) return;

    const password = form.querySelector('[name="password"]');
    const repeat = form.querySelector('[name="password_repeat"]');
    if (password && repeat && password.value !== repeat.value) {
      if (result) {
        result.className = 'form-result error';
        result.textContent = 'Пароли не совпадают.';
      }
      return;
    }

    if (!endpoint) {
      if (result) {
        result.className = 'form-result error';
        result.textContent = 'Для формы не задан API endpoint.';
      }
      return;
    }

    try {
      form.classList.add('is-loading');
      if (submit) submit.disabled = true;
      const response = await fetch(endpoint, { method: 'POST', body: new FormData(form) });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      if (result) {
        result.className = 'form-result';
        result.textContent = success;
      }
      form.reset();
    } catch (error) {
      if (result) {
        result.className = 'form-result error';
        result.textContent = 'Backend недоступен или вернул ошибку. Запустите backend/server.py и повторите отправку.';
      }
    } finally {
      form.classList.remove('is-loading');
      if (submit) submit.disabled = false;
    }
  });
});
