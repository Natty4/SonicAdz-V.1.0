/**
 * Telegram WebApp Integration Module
 */
const TelegramWebApp = (function() {
  // Private variables
  let tg;
  let user;

  
    // Initialize Telegram WebApp
    function init() {
      if (!window?.Telegram && !window?.Telegram?.WebApp) {
        showAlert("403 <br/>SonicAdz. available on telegram miniapps, please use our bot.", "error",0);
        switchView("none");
        window.history.pushState({}, "", "/");
        return false;
      }


      tg = window?.Telegram?.WebApp;
      user = tg.initDataUnsafe?.user;

      document.documentElement.classList.add("in-telegram");
      tg.ready();
      tg.expand();
      tg.enableClosingConfirmation();
      tg.disableVerticalSwipes();

      applyTelegramTheme();
      tg.onEvent("themeChanged", () => applyTelegramTheme(tg.colorScheme));

      return true;
    }

  // Apply Telegram theme
  function applyTelegramTheme(scheme) {
      const theme = scheme || tg?.colorScheme || "dark";
      document.body.classList.remove("theme-light", "theme-dark");
      document.body.classList.add(`theme-${theme}`);
      document.documentElement.setAttribute("data-theme", theme);

      // Determine the header color based on the current theme
      let headerColor;
      if (theme === 'dark') {
        headerColor = '#15202b';
      } else {
        headerColor = '#ffffff';
      }

      // Set Telegram Mini App header color
      try {
        if (tg?.setHeaderColor) {
          tg.setHeaderColor(headerColor);
        }
      } catch (e) {
        console.warn("Failed to set Telegram header color:", e);
      }
  }

  // Setup Telegram UI elements
  function setupUI() {
    if (!user) {
      switchView("none");
      showAlert(
        `403 <br/>SonicAdz. for creators available on telegram miniapps, please visit our bot<br/>`,
        "info",
        0
      );
      window.history.pushState({}, "", "/");
      return false;
    }

    // Set user name
    const userNameEl = document.getElementById("userNameEl");
    if (userNameEl) {
      userNameEl.textContent = `${user.first_name || ""} ${user.last_name || ""}`.trim();
    }

    switchView("dashboardView");


  //   // Show version warning if needed
    if (tg.platform !== "unknown" && !tg.isVersionAtLeast("6.4")) {
      showWarning(`Telegram ${tg.platform} v.${tg.version}. Please update for the best experience.`);
    }

    // // Setup header and back button
    tg.showHeader?.();
    tg.setHeaderTitle?.("SonicAdz Creator");

    if (tg.BackButton) {
      tg.BackButton.show?.();
      tg.BackButton.onClick(() => {
        // window.history.length > 1 ? window.history.back() : tg.close();
         tg.close();
      });
    }

    return true;
  }

  // Setup navigation scroll behavior
  function setupScrollBehavior() {
    const nav = document.querySelector(".card-grid");
    if (!nav) return;

    let lastScrollTop = 0;

    window.addEventListener("scroll", () => {
      const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
      if (currentScroll > lastScrollTop) {
        nav.classList.add("hidden");
      } else {
        nav.classList.remove("hidden");
      }
      lastScrollTop = currentScroll <= 0 ? 0 : currentScroll;
    });

    // Tap/double-tap toggle
    let lastTapTime = 0;
    document.addEventListener("touchend", function() {
      const currentTime = new Date().getTime();
      const tapLength = currentTime - lastTapTime;
      if (tapLength < 300 && tapLength > 0) {
        nav.classList.toggle("hidden");
      }
      lastTapTime = currentTime;
    });

    document.addEventListener("dblclick", () => {
      nav.classList.toggle("hidden");
    });
  }

  // Setup bot link handler
  function setupBotLink() {
    const botBtn = document.getElementById("openBot");
    if (!botBtn) return;

    const bot = botBtn.dataset.botLink;
    botBtn.addEventListener("click", function(e) {
      e.preventDefault();
      if (tg.openTelegramLink) {
        tg.openTelegramLink(bot);
      } else {
        window.open(bot, "_blank");
      }
    });
  }

  // Public API
  return {
    init: function() {
      if (!init()) return false;
      if (!setupUI()) return false;
      setupScrollBehavior();
      setupBotLink();
      return true;
    },
    getUser: function() {
      return user;
    },
    getInstance: function() {
      return tg;
    }
  };
})();

/**
 * View Management Module
 */
const ViewManager = (function() {
  const views = document.querySelectorAll('.view');
  const navButtons = document.querySelectorAll('nav .tab');
  const viewOrder = Array.from(views).map(v => v.id);
  let startX = 0;
  let endX = 0;

  // Now switchView ONLY handles UI updates (views + buttons)
  function switchView(viewId) {
    views.forEach(v => v.classList.add('hidden'));
    try {
      document.getElementById(viewId).classList.remove('hidden');
    } catch {
      document.querySelectorAll('nav').forEach(v => v.classList.add('hidden'));
      document.getElementById('app').remove();
      console.warn('Unauthorized!');
    }

    navButtons.forEach(btn => {
      if (btn.dataset.view === viewId) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }

  function addSwipeSupport(container) {
    container?.addEventListener('touchstart', (e) => {
      startX = e.touches[0].clientX;
    });

    container?.addEventListener('touchend', (e) => {
      endX = e.changedTouches[0].clientX;
      handleSwipe();
    });
  }

  function handleSwipe() {
    const deltaX = endX - startX;
    const threshold = 100;

    if (Math.abs(deltaX) > threshold) {
      const currentView = document.querySelector('.view:not(.hidden)');
      const currentIndex = viewOrder.indexOf(currentView.id);

      if (deltaX < 0 && currentIndex < viewOrder.length - 1) {
        const nextView = viewOrder[currentIndex + 1];
        TabController.switchTab(nextView);  // notify TabController!
      } else if (deltaX > 0 && currentIndex > 0) {
        const prevView = viewOrder[currentIndex - 1];
        TabController.switchTab(prevView);  // notify TabController!
      }
    }
  }

  function init() {
    navButtons.forEach(button => {
      button.addEventListener('click', () => {
        const targetView = button.dataset.view;
        TabController.switchTab(targetView); // Use TabController for consistency
      });
    });

    const swipeContainer = document.getElementById('views') || document.body;
    addSwipeSupport(swipeContainer);

    // Make switchView globally available for TabController to call
    window.switchView = switchView;
  }

  return {
    init,
    switchView
  };
})();

/**
 * Alert System Module
 */
const AlertSystem = (function() {
  // Show alert message
  function showAlert(message, type = 'info', timeout = 5000) {
    const container = document.getElementById('alert-messages');
    if (!container) return;

    const tg = TelegramWebApp.getInstance();
    tg?.HapticFeedback.notificationOccurred(type);

    const messages = Array.isArray(message)
      ? message
      : typeof message === 'object'
      ? Object.entries(message).map(([key, val]) => `${key}: ${val}`)
      : [message];

    messages.forEach(msg => {
      const alertEl = document.createElement('div');
      alertEl.className = `alert alert-${type} alert-dismissible fade show`;
      alertEl.setAttribute('role', 'alert');

      alertEl.innerHTML = `
        ${msg}
        <button type="button" class="close" aria-label="Close">&times;</button>
      `;

      container.appendChild(alertEl);

      // Manual close support
      const closeBtn = alertEl.querySelector('.close');
      if (closeBtn) {
          closeBtn.addEventListener('click', () => {
              alertEl.classList.remove('show');
              alertEl.classList.add('fade-out');
              setTimeout(() => alertEl.remove(), 500);
          });
      }

      // Auto-dismiss
      if (timeout !== 0) {
        setTimeout(() => {
          alertEl.classList.remove('show');
          alertEl.classList.add('fade-out');
          setTimeout(() => alertEl.remove(), 500);
        }, timeout);
      }
    });
  }

  // Public API
  return {
    show: showAlert
  };
})();

// Make showAlert available globally
window.showAlert = AlertSystem.show;

/**
 * Payment Method Module
 */

const PaymentMethod = (function () {
  const API_URL = '/api/payment-method-choice/';
  let methods = [];

  const form = document.getElementById('paymentMethodForm');
  const methodToggleGroup = document.getElementById('methodTypeToggle');
  const methodTypeInput = document.getElementById('methodType');
  const commonField = document.getElementById('commonField');
  const bankFields = document.getElementById('bankFields');
  const walletFields = document.getElementById('walletFields');
  const methodActions = document.getElementById('methodActions');

  function resetFields(fields) {
    if (!fields) return;
    fields.querySelectorAll('input, select').forEach(input => {
      input.value = '';
      input.classList.remove('error');
      removeErrorMessage(input);
      input.required = false;
    });
  }

  function markError(input) {
    input.classList.add('error');
    input.setAttribute('aria-invalid', 'true');
  }

  function showError(input, message) {
    if (!input) return;
    input.classList.add('error');
    input.setAttribute('aria-invalid', 'true');
    const existingError = input.nextElementSibling;
    if (existingError?.classList.contains('error-message')) {
      existingError.remove();
    }
    const error = document.createElement('div');
    error.className = 'error-message';
    error.textContent = message;
    input.insertAdjacentElement('afterend', error);
  }

  function removeErrorMessage(input) {
    const existing = input.parentNode.querySelector('.error-message');
    if (existing) existing.remove();
    input.classList.remove('error');
    input.removeAttribute('aria-invalid');
  }

  function validateInput(input) {
    removeErrorMessage(input);
    if (!input.value.trim()) {
      showError(input, 'This field is required');
      return false;
    }

    if (input.name === 'account_number' && !/^\d{6,20}$/.test(input.value)) {
      showError(input, 'Enter a valid account number');
      return false;
    }

    if (input.name === 'phone_number' && !/^(\+251|0)?(9|7)\d{8}$/.test(input.value)) {
      showError(input, 'Enter a valid phone number');
      return false;
    }

    return true;
  }

  function toggleSubmitButton() {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (!submitBtn) return;
    const visibleInputs = Array.from(form.querySelectorAll('input:not([type="hidden"]):not([type="checkbox"])'))
      .filter(input => input.offsetParent !== null);

    const allValid = visibleInputs.every(validateInput);
    submitBtn.disabled = !allValid;
  }

  async function loadMethods() {
    try {
      const res = await fetch(API_URL);
      methods = await res.json();
      renderMethodOptions();
    } catch (err) {
      console.warn('Failed to load method types:', err);
      showAlert('Unable to load payment method. Try again later.', 'error');
    }
    finally{
      // Ensure submit button is updated after methods are loaded
      toggleSubmitButton();
    }
  }

  // Autofill Telegram name
  function autofillAccountName(fullName) {
    const accountInput = document.getElementById('accountName');
    if (accountInput && !accountInput.value.trim()) {
      accountInput.value = fullName;
      accountInput.classList.add('autofilled');
      setTimeout(() => accountInput.classList.remove('autofilled'), 2000);
      accountInput.dispatchEvent(new Event('input'));
    }
  }

  function renderMethodOptions() {
    methodToggleGroup.innerHTML = '';
    const categories = ['bank', 'wallet'];

    categories.forEach(category => {
      const row = document.createElement('div');
      row.className = `method-row scrollable-row row-${category} flex gap-2 mb-2 overflow-x-auto`;
      const filtered = methods.filter(m => m.category === category);

      filtered.forEach(method => {
        const div = document.createElement('div');
        div.className = 'method-option';
        div.dataset.id = method.id;
        div.dataset.category = category;
        div.innerHTML = `
          ${method.logo ? `<img src="${method.logo}" alt="${method.name}" width="50" height="50" style="border-radius: 5px;" />` 
          : `<i class="fas fa-bank fa-2x"></i>`}
          <span>${method.short_name}</span>
        `;
        row.appendChild(div);
      });

      if (filtered.length > 0) {
        methodToggleGroup.appendChild(row);
      }
    });

    setupMethodSelection();
  }

  function setupMethodSelection() {
    const methodOptions = document.querySelectorAll('.method-option');

    methodOptions.forEach(methodOption => {
      methodOption.addEventListener('click', () => {
        methodOptions.forEach(o => {
          o.classList.remove('active');
          o.classList.add('hidden');
        });

        methodOption.classList.remove('hidden');
        methodOption.classList.add('active');

        const methodId = methodOption.dataset.id;
        const methodCategory = methodOption.dataset.category;

        methodTypeInput.value = methodId;
        methodTypeInput.dispatchEvent(new Event('change'));

        resetFields(bankFields);
        resetFields(walletFields);

        if (methodCategory === 'bank') {
          bankFields.classList.remove('hidden');
          walletFields.classList.add('hidden');
          document.getElementById('accountNumber').required = true;
        } else {
          walletFields.classList.remove('hidden');
          bankFields.classList.add('hidden');
          document.getElementById('phoneNumber').required = true;
        }

        methodActions.classList.remove('hidden');
        commonField.classList.remove('hidden');

        autofillAccountName();
        toggleSubmitButton();
      });
    });
  }

  function setupFormInputs() {
    const inputs = form.querySelectorAll('input:not([type="hidden"])');
    inputs.forEach(input => {
      input.addEventListener('input', () => {
        validateInput(input);
        toggleSubmitButton();
      });
    });
  }

  async function handleFormSubmit(e) {
    e.preventDefault();
    const tg = TelegramWebApp.getInstance();
    const submitBtn = form.querySelector('button[type="submit"]');
    const msgBox = document.getElementById('formErrorMessage');
    msgBox.textContent = '';

    const visibleInputs = Array.from(form.querySelectorAll('input:not([type="hidden"]):not([type="checkbox"])'))
      .filter(input => input.offsetParent !== null);

    let isValid = true;
    visibleInputs.forEach(input => {
      if (!validateInput(input)) isValid = false;
    });

    if (!isValid) {
      toggleSubmitButton();
      return;
    }

    const formData = new FormData(form);
    const payload = {};

    for (const [key, value] of formData.entries()) {
      if (key === 'csrfmiddlewaretoken') continue;
      if (key === 'is_default') {
        payload[key] = form.querySelector('#isDefault').checked;
        continue;
      }
      if (value.trim() !== '') payload[key] = value.trim();
    }

    try {
      submitBtn.disabled = true;
      const res = await fetch('/api/payments/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (res.ok) {
        showAlert(data.message || 'Payment method added successfully!', 'success');
        form.reset();
        resetFields(bankFields);
        resetFields(walletFields);
        document.querySelectorAll('.method-option').forEach(o => o.classList.remove('active'));
        methodActions.classList.add('hidden');
        commonField.classList.add('hidden');
        toggleBottomSheet(false);
        await TabController.refreshCurrentTab();
      } else {
        tg?.HapticFeedback?.notificationOccurred("error");
        if (typeof data === 'object') {
          for (const field in data) {
            const input = form.querySelector(`[name="${field}"]`);
            if (input && Array.isArray(data[field])) {
              showError(input, data[field][0]);
              showAlert(data[field][0], 'error');
            }
          }
        } else {
          showAlert('An error occurred. Try again.', 'error');
        }
      }
    } catch (err) {
      console.error('Submission error:', err);
      showAlert('Network error. Try again.', 'error');
    } finally {
      submitBtn.disabled = false;
      toggleSubmitButton();
    }
  }

  async function init(userData = null) {
    if (!form) return;

    loadMethods();
    setupFormInputs();

    if (userData) {
      const fullName = [userData.first_name, userData.last_name].filter(Boolean).join(' ').trim();
      autofillAccountName(fullName);
    } else {
      try {
        const res = await fetch('/api/settings/user/');
        if (res.ok) {
          const user = await res.json();
          const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ').trim();
          autofillAccountName(fullName);
        }
      } catch (err) {
        console.warn('Could not fetch user data for name autofill', err);
      }
    }

    form.addEventListener('submit', handleFormSubmit);
  }

  return {
    init,
    toggleSubmitButton,
    resetFields
  };
})();


/**
 * Bottom Sheet Module
 */
const BottomSheet = (function() {
  // Toggle bottom sheet visibility
  function toggleBottomSheet(show = null) {
  const wrapper = document.getElementById('bottomSheetWrapper');
  const sheet = document.getElementById('bottomSheet');
  const isVisible = wrapper && !wrapper.classList.contains('hidden');

  if (show === true || (!isVisible && show !== false)) {
    wrapper.classList.remove('hidden');
    document.body.classList.add('no-scroll');
    document.querySelectorAll('.view').forEach(v => v.classList.add('no-scroll'));
    setTimeout(async () => {
      sheet.classList.add('show');
      PaymentMethod.toggleSubmitButton();  

      // Reuse cached settings data if available
      let userData = window.cachedUserData;
      if (!userData) {
        try {
          userData = await ApiService.getSettingsData();
          window.cachedUserData = userData;
        } catch (err) {
          console.warn('Could not load user settings:', err);
        }
      }

      PaymentMethod.init(userData);

    }, 20);
  } else {
    sheet.classList.remove('show');
    setTimeout(() => {
      wrapper.classList.add('hidden');
      document.body.classList.remove('no-scroll');
      document.querySelectorAll('.view').forEach(v => v.classList.remove('no-scroll'));

      const form = document.getElementById('paymentMethodForm');
      if (form) form.reset();
      
      const bank = document.getElementById('bankFields');
      const wallet = document.getElementById('walletFields');
      if (bank) {
        PaymentMethod.resetFields(bank);
        bank.classList.add('hidden');
      }
      if (wallet) {
        PaymentMethod.resetFields(wallet);
        wallet.classList.add('hidden');
      }

      const methodTypeInput = document.getElementById('methodType');
      if (methodTypeInput) methodTypeInput.value = '';

      const methodActions = document.getElementById('methodActions');
      const commonField = document.getElementById('commonField');
      if (methodActions) methodActions.classList.add('hidden');
      if (commonField) commonField.classList.add('hidden');

      const methodOptions = document.querySelectorAll('.method-option');
      methodOptions.forEach(opt => opt.classList.remove('active'));

      PaymentMethod.toggleSubmitButton();
    }, 20);
  }
}



  // Initialize bottom sheet
  function init() {
    const closeModalBtn = document.getElementById('closeModal');
    if (closeModalBtn) {
      closeModalBtn.addEventListener('click', () => {
        const modal = document.getElementById('paymentModal');
        if (modal) modal.classList.remove('open');
      });
    }

    window.showPaymentModal = function() {
      const modal = document.getElementById('paymentModal');
      if (modal) modal.classList.add('open');
    };
    
    window.toggleBottomSheet = toggleBottomSheet;
  }

  // Public API
  return {
    init: init
  };
})();

/**
 * Chart Module
 */
const ChartModule = (function() {
  // Initialize charts
  function init() {
    const dark = document.documentElement.getAttribute('data-theme') === 'dark';
    const bg = dark
      ? ['rgba(18, 208, 104, 0.7)', 'rgba(46, 149, 196, 0.7)', 'rgba(46, 149, 196, 0.7)', 'rgba(76, 31, 255, 0.7)']
      : ['rgba(18, 208, 104, 1)', 'rgba(46, 149, 196, 1)', 'rgba(46, 149, 196, 1)', 'rgba(76, 31, 255, 1)'];
    const bd = dark
      ? ['rgba(18, 208, 104, 0.6)', 'rgba(46, 149, 196, 0.6)', 'rgba(46, 149, 196, 0.6)', 'rgba(76, 31, 255, 0.6)']
      : ['rgba(18, 208, 104, 1)', 'rgba(46, 149, 196, 1)', 'rgba(46, 149, 196, 1)', 'rgba(76, 31, 255, 1)'];

    // Line Chart: Creator Earnings
    const lineChartEl = document.getElementById('creatorEarningsLineChart');
    if (lineChartEl) {
      new Chart(lineChartEl.getContext('2d'), {
        type: 'line',
        data: {
          labels: ['W1', 'W2', 'W3', 'W4'],
          datasets: [{
            label: 'Earnings (ETB)',
            data: [],
            borderColor: bd[0], 
            borderWidth: 2, 
            tension: 0.3, 
            fill: true,
            backgroundColor: ctx => {
              const g = ctx.chart.ctx.createLinearGradient(0,0,0,ctx.chart.height);
              g.addColorStop(0, dark ? 'rgba(18, 208, 104, 0.3)' : 'rgba(18, 208, 104, 0.4)');
              g.addColorStop(1, 'rgba(18, 208, 104, 0)');
              return g;
            },
            pointRadius: 2,
            pointBackgroundColor: bg,
            pointBorderColor: bd,
          }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
      });
    }
  }

  // Public API
  return {
    init: init
  };
})();

/**
 * Channel Registration Module
 */
const ChannelRegistration = (function() {
  // Load checkbox options
  async function loadCheckboxOptions() {
    try {
      const [langRes, catRes] = await Promise.all([
        fetch('/api/languages/'),
        fetch('/api/categories/')
      ]);

      const languages = await langRes.json();
      const categories = await catRes.json();

      renderCheckboxGroup('languageCheckboxes', 'language', languages);
      renderCheckboxGroup('categoryCheckboxes', 'category', categories);

      limitCheckboxGroup('language', 3);
      limitCheckboxGroup('category', 3);

      document.querySelectorAll('input[name="language"], input[name="category"]').forEach(cb => {
        cb.addEventListener('change', toggleChannelSubmitButton);
      });
    } catch (err) {
      console.warn("Failed to load options:", err);
      showAlert("Failed to load categories/languages", "error");
    }
  }

  // Render checkbox group
  function renderCheckboxGroup(containerId, name, items, selected = []) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = '';

  items.forEach(item => {
    const checkboxId = `${name}_${item.id}`;

    const input = document.createElement('input');
    input.type = 'checkbox';
    input.id = checkboxId;
    input.name = name;
    input.value = item.id;
    if (selected.includes(item.id)) input.checked = true;

    const label = document.createElement('label');
    label.setAttribute('for', checkboxId);
    label.className = 'pill';
    label.textContent = item.name;

    container.appendChild(input);
    container.appendChild(label);
  });
}
  window.renderCheckboxGroup = renderCheckboxGroup

  // Limit checkbox selections
  function limitCheckboxGroup(name, max = 3) {
    const checkboxes = document.querySelectorAll(`input[name="${name}"]`);
    const container = checkboxes[0]?.closest('.checkbox-pill-group');
    const errorId = `${name}-error`;

    checkboxes.forEach(cb => {
      cb.addEventListener('change', () => {
        const selected = [...checkboxes].filter(c => c.checked);
        const existingError = document.getElementById(errorId);

        if (selected.length > 0 && existingError) {
          existingError.remove();
        }

        if (selected.length > max) {
          cb.checked = false;
          showAlert(`You can only select up to ${max} ${name}s`, 'warning');
        }
      
      });
    });
  }
  window.limitCheckboxGroup = limitCheckboxGroup

  // Toggle channel bottom sheet
  function toggleChannelBottomSheet(show = null) {
    const wrapper = document.getElementById('channelBottomSheetWrapper');
    const sheet = document.getElementById('channelBottomSheet');
    const form = document.getElementById('channelRegistrationForm');
    const verifySection = document.getElementById('channelVerificationMessage');
    const channelHeader = document.getElementById('channel_sheet_header');

    const isVisible = wrapper && !wrapper.classList.contains('hidden');
    toggleChannelSubmitButton();
    
    if (show === true || (!isVisible && show !== false)) {
      wrapper.classList.remove('hidden');
      document.body.classList.add('no-scroll');
      channelHeader.classList.remove('hidden');
      setTimeout(() => {
        sheet.classList.add('show');
      }, 20);
    } else {
      sheet.classList.remove('show');
      setTimeout(() => {
        wrapper.classList.add('hidden');
        document.body.classList.remove('no-scroll');

        if (form) form.reset();
        resetChannelErrors();
        if (verifySection) verifySection.classList.add('hidden');
        if (form) form.classList.remove('hidden');
      }, 100);
    }
  }

  // Show inline error
  function showInlineError(input, message) {
    removeInlineError(input);
    input.classList.add('error');
    input.setAttribute('aria-invalid', 'true');

    const error = document.createElement('span');
    error.className = 'error-message';
    error.textContent = message;

    input.insertAdjacentElement('afterend', error);
  }

  // Remove inline error
  function removeInlineError(input) {
    input.classList.remove('error');
    input.removeAttribute('aria-invalid');
    const next = input.nextElementSibling;
    if (next && next.classList.contains('error-message')) {
      next.remove();
    }
  }

  // Reset channel errors
  function resetChannelErrors() {
    const form = document.getElementById('channelRegistrationForm');
    if (!form) return;

    form.querySelectorAll('.error-message').forEach(el => el.remove());
    form.querySelectorAll('.error').forEach(el => {
      el.classList.remove('error');
      el.removeAttribute('aria-invalid');
    });
  }

  // Toggle channel submit button
  function toggleChannelSubmitButton() {
    const form = document.getElementById('channelRegistrationForm');
    if (!form) return;

    const submitBtn = form.querySelector('button[type="submit"]');
    if (!submitBtn) return;

    const isChannelLinkValid = /^https:\/\/t\.me\/[a-zA-Z0-9_]{5,}$/.test(form.channel_link.value.trim());
    const isMinCpmValid = parseFloat(form.min_cpm.value) > 0;

    const langChecked = form.querySelectorAll('input[name="language"]:checked').length;
    const catChecked = form.querySelectorAll('input[name="category"]:checked').length;

    const isValid = isChannelLinkValid && isMinCpmValid && langChecked > 0 && catChecked > 0;

    submitBtn.disabled = !isValid;
  }

  // Handle channel form errors
  // function handleChannelFormErrors(errors) {
  //   Object.entries(errors).forEach(([field, messages]) => {
  //     const input = document.querySelector(`#channelRegistrationForm [name="${field}"]`);
  //     if (input) showInlineError(input, messages[0] || 'Invalid input');
  //   });
  // }

  function handleChannelFormErrors(errors) {
    // Handle field-level errors
    Object.entries(errors).forEach(([field, messages]) => {
      if (field === 'non_field_errors') {
        // Show non-field errors in a general alert or above the form
        showAlert(messages[0] || 'Something went wrong.', 'error');
        return;
      }

      const input = document.querySelector(`#channelRegistrationForm [name="${field}"]`);
      if (input) {
        showInlineError(input, messages[0] || 'Invalid input');
      }
    });
  }

  // Handle channel form submission
  async function handleChannelFormSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const errorBox = document.getElementById('channelFormError');
    const submitBtn = form.querySelector('button[type="submit"]');
    const verifySection = document.getElementById('channelVerificationMessage');
    const botLink = document.getElementById('openBot').dataset.botLink;

    errorBox.textContent = '';
    resetChannelErrors();

    const getCheckedValues = name =>
      Array.from(form.querySelectorAll(`input[name="${name}"]:checked`)).map(cb => cb.value);

    const payload = {
      channel_link: form.channel_link.value,
      language: getCheckedValues("language"),
      category: getCheckedValues("category"),
      min_cpm: form.min_cpm.value
    };

    let hasError = false;

    // Language checkboxes
    const langSelected = payload.language.length;
    const langContainer = document.getElementById('languageCheckboxes');
    const langErrorId = 'language-error';
    const langExistingError = document.getElementById(langErrorId);

    if (langSelected === 0) {
      hasError = true;
      if (!langExistingError) {
        const err = document.createElement('div');
        err.className = 'error-message';
        err.id = langErrorId;
        err.textContent = 'Please select at least one language.';
        langContainer?.after(err);
      }
    } else {
      langExistingError?.remove();
    }

    // Category checkboxes
    const catSelected = payload.category.length;
    const catContainer = document.getElementById('categoryCheckboxes');
    const catErrorId = 'category-error';
    const catExistingError = document.getElementById(catErrorId);
    const onboardingBlock = document.getElementById('onboarding-block');

    if (catSelected === 0) {
      hasError = true;
      if (!catExistingError) {
        const err = document.createElement('div');
        err.className = 'error-message text-xs mt-1';
        err.id = catErrorId;
        err.textContent = 'Please select at least one category.';
        catContainer?.after(err);
      }
    } else {
      catExistingError?.remove();
    }

    if (hasError) return;

    try {
      submitBtn.disabled = true;
      const closeBtn = document.querySelector('.sheet-header #closeChannelBtn');
      const res = await fetch('/api/channels/connect/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      const tg = TelegramWebApp.getInstance();

      if (res.ok && data.verification_link) {
        tg?.HapticFeedback?.notificationOccurred("success");

        activationCode = data.verification_link;
        channelLink = payload.channel_link;

        form.classList.add('hidden');
        verifySection.classList.remove('hidden');

        setupVerificationButtons();

        if (closeBtn) {
          closeBtn.classList.add('hidden');
        }

        showAlert('Channel submitted! Please continue to verification.', 'success');
      } else if (data.errors) {
        tg?.HapticFeedback?.notificationOccurred("error");
        handleChannelFormErrors(data.errors);
      } else {
        showAlert(data.detail || 'Something went wrong.', 'error');
      }
    } catch (err) {
      showAlert('Network error. Please try again.', 'error');
    } finally {
      submitBtn.disabled = false;
      onboardingBlock.remove();

    }
  }

  // Setup channel link validation
  function setupChannelLinkValidation() {
    const channelLinkInput = document.getElementById('channelLink');
    if (!channelLinkInput) return;

    channelLinkInput.addEventListener('input', () => {
      const value = channelLinkInput.value.trim();
      const isValid = /^https:\/\/t\.me\/[a-zA-Z0-9_]{5,}$/.test(value);
      if (!isValid) {
        showInlineError(channelLinkInput, 'Enter a valid Telegram channel link (e.g., https://t.me/yourchannel)');
      } else {
        removeInlineError(channelLinkInput);
      }
      toggleChannelSubmitButton();
    });
  }

  // Setup CPM validation
  function setupCpmValidation() {
    const minCpmInput = document.getElementById('minCpm');
    if (!minCpmInput) return;

    minCpmInput.addEventListener('input', () => {
      const value = parseFloat(minCpmInput.value);
      if (isNaN(value) || value <= 0) {
        showInlineError(minCpmInput, 'Minimum CPM must be a positive number');
      } else {
        removeInlineError(minCpmInput);
      }
      toggleChannelSubmitButton(); 
    });
  }

// Setup button logic in verification section
function setupVerificationButtons() {
    const tg = TelegramWebApp.getInstance();
    const proceedBtn = document.getElementById('proceedBtn');
    const verifyBtn = document.getElementById('verifyBtn');
    const instruction = document.getElementById('instructionText');
    const botLink = document.getElementById('openBot').dataset.botLink;
    const closeBtn = document.querySelector('.sheet-header #closeChannelBtn');
    const channelHeader = document.getElementById('channel_sheet_header');

    // Disable verify at first
    verifyBtn.disabled = true;
    verifyBtn.classList.add('disabled');
    channelHeader.classList.add('hidden');

    // Proceed button now opens the Telegram deep link to add bot to channel
    proceedBtn.addEventListener('click', function (e) {
        e.preventDefault();
        const botUsername = botLink.split('/').pop(); // Extract bot username from botLink
        const deepLink = `https://t.me/${botUsername}?startchannel=1`;

        // Open the link in Telegram app
        if (window.Telegram?.WebApp) {
            Telegram.WebApp.openTelegramLink(deepLink); // For Telegram Web App
        } else {
            window.open(deepLink, '_blank'); // For non-Telegram Web App environments
        }

        // Enable verify button after the user proceeds
        setTimeout(() => {
            proceedBtn.remove();
            verifyBtn.disabled = false;
            verifyBtn.classList.remove('disabled');
        }, 1000); 
    });

    // Complete verification
    verifyBtn.addEventListener('click', async function (e) {
        e.preventDefault();
        verifyBtn.disabled = true;
        verifyBtn.innerHTML = '<span class="text-brand"><i class="fas fa-spinner fa-spin"> </i> Verifying...</span>';

        try {
            const res = await fetch('/api/channels/verify/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ activation_code: activationCode })
            });

            const data = await res.json();

            if (res.ok) {
                tg?.HapticFeedback?.notificationOccurred("success");
                showAlert(data.message || '🎉 Channel verified successfully! <br/> now you start serve & earn', 'success');
                toggleChannelBottomSheet(false);
                await TabController.refreshCurrentTab();
            } else {
                tg?.HapticFeedback?.notificationOccurred("error");
                instruction?.classList?.remove('hidden');
                closeBtn.classList.remove('hidden');
                showAlert(data.error || 'Verification failed, please try again.', 'error');
            }
        } catch (err) {
            instruction?.classList?.remove('hidden');
            closeBtn.classList.remove('hidden');
            showAlert('Network error during verification, please try again.', 'error');
        } finally {
            verifyBtn.disabled = false;
            verifyBtn.innerHTML = 'Complete Verification';
        }
    });
}

  // Initialize channel registration
  function init() {
    const form = document.getElementById('channelRegistrationForm');
    if (!form) return;

    document.getElementById("channelBottomSheetWrapper")?.addEventListener("click", loadCheckboxOptions, { once: true });
    form.addEventListener('submit', handleChannelFormSubmit);
    setupChannelLinkValidation();
    setupCpmValidation();
    window.toggleChannelBottomSheet = toggleChannelBottomSheet;
    window.showTransaction = function() {
      const transactions = document.getElementById('transactions');
      if (transactions) transactions.classList.toggle('hidden');
    };
  }

  // Public API
  return {
    init: init
  };
})();

/**
 * Utility Functions
 */
function getCSRFToken() {
  return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

function setupSwipeRefresh({ container, onRefresh }) {
  let startY = 0;
  let isPulling = false;
  let isRefreshing = false;
  const threshold = 200;

  const indicator = document.getElementById('pull-down-indicator');

  container.addEventListener('touchstart', (e) => {
    if (container.scrollTop === 0) {
      startY = e.touches[0].clientY;
      isPulling = true;
    }
  });

  container.addEventListener('touchmove', (e) => {
    if (!isPulling || isRefreshing) return;

    const currentY = e.touches[0].clientY;
    const deltaY = currentY - startY;

    if (deltaY > 15) {
      indicator.style.display = 'block';
      indicator.textContent = deltaY > threshold ? '↻ Release to refresh' : '↓ Pull to refresh';
    }
  });

  container.addEventListener('touchend', async (e) => {
    if (!isPulling || isRefreshing) return;

    const endY = e.changedTouches[0].clientY;
    const deltaY = endY - startY;

    if (deltaY > threshold) {
      isRefreshing = true;
      indicator.textContent = 'Refreshing...';

      try {
        await onRefresh();
      } finally {
        setTimeout(() => {
          indicator.style.display = 'none';
          indicator.textContent = '↓ Pull to refresh';
          isRefreshing = false;
        }, 600);
      }
    } else {
      indicator.style.display = 'none';
    }

    isPulling = false;
  });
}

function copyToClipboard(button, text) {
    navigator.clipboard.writeText(text).then(() => {
      // Save current icon element
      const originalIcon = button.innerHTML;

      // Replace with "Copied" text
      button.innerHTML = '<span class="text-xs text-secondary">Copied</span>';

      // Restore icon after 1s
      setTimeout(() => {
        button.innerHTML = originalIcon;
      }, 2000);
    });
  }

         
function togglePreloader(show, removeAfter = false) {
    const preloader = document.getElementById('preloader');
    if (!preloader) return;

    if (show) {
        // Show and reset preloader state
        preloader.style.display = 'flex'; // Make visible
        preloader.classList.remove('zoom-out'); // Reset animation state
        document.body.style.overflow = 'hidden';
    } else {
        // Zoom out and then hide or remove
        preloader.classList.add('zoom-out');

        setTimeout(() => {
        if (removeAfter) {
            preloader.remove(); // Fully remove from DOM
        } else {
            preloader.style.display = 'none'; // Just hide
        }
        document.body.style.overflow = '';
        }, 1500); // Match zoom animation duration
    }
}

function initTooltips(container = document) {
  const tooltipIcons = container.querySelectorAll('.tooltip-icon');

  tooltipIcons.forEach(icon => {
    // Avoid duplicate listeners
    icon.removeEventListener('mouseenter', handleMouseEnter);
    icon.removeEventListener('mouseleave', handleMouseLeave);

    icon.addEventListener('mouseenter', handleMouseEnter);
    icon.addEventListener('mouseleave', handleMouseLeave);
  });

  function handleMouseEnter(e) {
    const icon = e.currentTarget;
    const tooltipText = icon.getAttribute('data-tooltip');

    if (!tooltipText) return;

    // Create temp tooltip for measurement
    const tempTooltip = document.createElement('div');
    tempTooltip.textContent = tooltipText;
    tempTooltip.style.position = 'absolute';
    tempTooltip.style.visibility = 'hidden';
    tempTooltip.style.padding = '5px 10px';
    tempTooltip.style.fontSize = '12px';
    tempTooltip.style.width = '200px';
    document.body.appendChild(tempTooltip);

    const iconRect = icon.getBoundingClientRect();
    const tooltipRect = tempTooltip.getBoundingClientRect();
    document.body.removeChild(tempTooltip);

    const spaceLeft = iconRect.left;
    const spaceRight = window.innerWidth - iconRect.right;
    const spaceTop = iconRect.top;

    // Horizontal positioning
    if (spaceRight < tooltipRect.width / 2) {
      icon.style.setProperty('--tooltip-left', '100%');
      icon.style.setProperty('--tooltip-transform', 'translateX(-100%)');
    } else if (spaceLeft < tooltipRect.width / 2) {
      icon.style.setProperty('--tooltip-left', '0');
      icon.style.setProperty('--tooltip-transform', 'translateX(0)');
    } else {
      icon.style.setProperty('--tooltip-left', '50%');
      icon.style.setProperty('--tooltip-transform', 'translateX(-50%)');
    }

    // Vertical positioning
    if (spaceTop < tooltipRect.height + 10) {
      icon.style.setProperty('--tooltip-top', '100%');
      icon.style.setProperty('--tooltip-bottom', 'auto');
    } else {
      icon.style.setProperty('--tooltip-top', 'auto');
      icon.style.setProperty('--tooltip-bottom', '100%');
    }
  }

  function handleMouseLeave(e) {
    const icon = e.currentTarget;
    icon.style.removeProperty('--tooltip-left');
    icon.style.removeProperty('--tooltip-transform');
    icon.style.removeProperty('--tooltip-top');
    icon.style.removeProperty('--tooltip-bottom');
  }
}


/**
 * API Service Module
 */
const ApiService = (function() {
  // Base API URL
  const BASE_URL = '/api/';

  // Common headers
  const headers = {
    'Content-Type': 'application/json',
    'X-CSRFToken': getCSRFToken()
  };

    // Helper function for API requests
  async function fetchData(endpoint, options = {}, retryCount = 1) {
    const url = `${BASE_URL}${endpoint}`;
    const config = {
      ...options,
      headers: {
        ...headers,
        ...(options.headers || {})
      }
    };

    let attempt = 0;
    let lastError;

    while (attempt <= retryCount) {
      try {
        const response = await fetch(url, config);

        if (!response.ok) {
          throw new Error(`API request failed: ${response.status}`);
        }

        const contentType = response.headers.get('Content-Type');
        if (contentType && contentType.includes('application/json')) {
          return await response.json();
        } else {
          return response;
        }

      } catch (err) {
        lastError = err;
        console.warn(`API retry ${attempt + 1} failed:`, err.message);
        attempt++;
        if (attempt > retryCount) {
          console.error('API failed after retries:', lastError);
          throw lastError;
        }
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }
  }

  // API endpoints
  const endpoints = {
    dashboard: 'dashboard/',
    channels: 'channels/',
    payments: 'payments/',
    ads: 'ad-placements/',
    transactions: 'transactions/',
    settings: 'settings/user/',
    notifications: 'notifications/',
    unreadCount: 'notifications/unread-count/'
  };

  // Public API
  return {
    getDashboardData: async function() {
      return fetchData(endpoints.dashboard);
    },

    getChannels: async function() {
      return fetchData(endpoints.channels);
    },

    getPaymentData: async function() {
      return fetchData(endpoints.payments);
    },

    getAdsData: async function() {
      return fetchData(endpoints.ads);
    },

    getTransactions: async function() {
      return fetchData(endpoints.transactions);
    },

    getSettingsData: async function() {
      return fetchData(endpoints.settings);
    },

    updateUserProfile: async function(payload) {
      return fetchData(endpoints.settings, {
        method: 'PATCH',
        body: JSON.stringify(payload)
      });
    },

    getNotifications: async function() {
      return fetchData(endpoints.notifications);
    },

    getUnreadNotificationCount: async function() {
      return fetchData(endpoints.unreadCount);
    },

    markNotificationRead: async function(notificationId) {
      return fetchData(`notifications/${notificationId}/mark-read/`, {
        method: 'PATCH'
      });
    },

    markAllNotificationsRead: async function() {
      return fetchData(`notifications/mark-all-read/`, {
        method: 'PATCH'
      });
    },

    clearNotification: async function(notificationId) {
      return fetchData(`notifications/${notificationId}/`, {
        method: 'DELETE'
      });
    }
  };
})();

/**
 * Data Renderer Module
 */
const DataRenderer = (function() {
  // Render dashboard view
  function renderDashboard(data) {
    const user = TelegramWebApp.getUser();
    // Update charts if needed
    const chartEl = document.getElementById('creatorEarningsLineChart');
    if (chartEl && data.chart_data) {
      const chart = Chart.getChart(chartEl);
      if (chart) {
        chart.data.datasets[0].data = data.chart_data;
        chart.data.labels = data.week_labels;
        chart.options.plugins.tooltip.callbacks = {
          title: function(tooltipItems) {
            const index = tooltipItems[0].dataIndex;
            const label = data.week_labels[index];
            const range = data.week_ranges[index];
            return `${label} (${range})`;
          }
        };
        chart.update();
      }
    }

    // Render top channels
    const channelsGrid = document.querySelector('.channels-grid');
    if (channelsGrid && data.top_channels) {
      channelsGrid.innerHTML = data.top_channels.map(channel => `
        <div class="channel-card relative container">
          <div class="channel-header">
            <img src="${channel.pp_url || user?.photo_url || '/static/default-avatar.png'}" alt="${channel.title.slice(0, 6) + '...'}" class="channel-icon">
            <div class="channel-info">
              <h3 class="channel-name">${channel.title.length > 21 ? channel.title.slice(0, 21) + '...' : channel.title}</h3>
              <p class="channel-subscribers">${channel.subscribers} subscribers</p>
            </div>
            <div class="status-position channel-status badge ${channel.status}">
              ${channel.status_display}
            </div>
          </div>
          <div class="channel-stats">
            <div class="channel-stat">
              <p class="stat-label">Ads Running</p>
              <p class="stat-value">${channel.stats?.active_ads || '-'}</p>
            </div>
            <div class="channel-stat">
              <p class="stat-label">Score</p>
              <p class="stat-value">${channel.stats?.engagement_rate || '-'}</p>
            </div>
            <div class="channel-stat">
              <p class="stat-label">Earnings</p>
              <p class="stat-value">ETB ${channel.stats?.total_earnings.toFixed(2) || '0.00'}</p>
            </div>
          </div>
          <div class="channel-actions">
            <span class="text-xs text-brand cursor-pointer" id="viewDetails" onclick="switchView('channelsView')">View Details</span>
            <span class="text-xs text-brand cursor-pointer" id="manageAds" onclick="switchView('adsView')">Manage Ads</span>
          </div>
        </div>
      `).join('');
    }

    // Render activity logs
    const activityList = document.querySelector('.activity-list');
    if (activityList && data.activity_logs) {
      activityList.innerHTML = data.activity_logs.map(log => `
        <li class="activity-item">
          <div class="activity-icon">
            ${getIconForAction(log.action_flag_display)}
          </div>
          <div class="activity-content">
            <p><strong>${log.change_message}</strong> ${log.action_flag_display}</p>
            <span class="activity-time">${getRelativeTime(log.timestamp)}</span>
          </div>
        </li>
      `).join('');
    }

    // Render notifications
    renderNotifications(data.notifications, data.unread_count);
  }

  function getIconForAction(action) {
    switch (action.toLowerCase()) {
      case 'addition':
        return `
          <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
          </svg>`;
      case 'deletion':
        return `
          <svg viewBox="0 0 24 24" width="24" height="24" stroke="#d01277" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>`;
      case 'change':
        return `
          <svg viewBox="0 0 24 24" width="24" height="24" stroke="#23c16b" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>`;
      default:
        return `
          <svg viewBox="0 0 24 24" width="24" height="24" stroke="gray" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10" />
          </svg>`;
    }
  }

  function getRelativeTime(timestamp) {
    const isoTimestamp = timestamp.replace(' ', 'T');
    const logTime = new Date(isoTimestamp);
    const now = new Date();

    if (isNaN(logTime)) return 'invalid date';

    const diffMs = now - logTime;
    if (diffMs < 0) return 'just now';

    const diffMinutes = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMinutes < 1) return 'just now';
    if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
  }

  // Notification rendering
  function renderNotifications(notifications, unreadCount) {
    const notificationContainer = document.getElementById('notification-modal');
    if (!notificationContainer) {
      console.error('Notification modal container not found');
      return;
    }

    // Filter notifications to show only unread (is_read=false) and active (is_active=true)
    const unreadNotifications = notifications.filter(n => !n.is_read && n.is_active !== false);

    // Update badge
    const badge = document.getElementById('notification-badge');
    const notificationIcon = document.querySelector('.action-btn.notifications i');

    if (badge) {
      badge.textContent = unreadCount || 0;
      badge.style.display = unreadCount > 0 ? 'inline-block' : 'none';
    }else if (unreadCount > 0) {
        // Badge didn't exist, but we now have notifications — create badge
        const newBadge = document.createElement('span');
        newBadge.id = 'notification-badge';
        newBadge.className = 'badge';
        newBadge.textContent = unreadCount;
        notificationIcon.parentNode.appendChild(newBadge);
      }

      // Update icon
      if (unreadCount > 0) {
        notificationIcon.classList.remove('fa-home');
        notificationIcon.classList.add('fa-bell');
      } else {
        notificationIcon.classList.remove('fa-bell');
        notificationIcon.classList.add('fa-home');
      }

    // Render modal content
    notificationContainer.innerHTML = `
      <div class="notification-modal-content">
        <div class="notification-header">
          <h2>Notifications</h2>
          <div>
            <button id="mark-all-read" aria-label="Mark all notifications as read">Mark All Read</button>
            <button id="minimize-modal" aria-label="Minimize notifications">
              <i class="fas fa-minus"></i>
            </button>
          </div>
        </div>
        <div class="notification-list">
          ${unreadNotifications.length > 0 ? unreadNotifications.map(notification => `
            <div class="notification-card" data-id="${notification.id}" role="alert" aria-live="polite">
              <div class="notification-content">
                <div>
                  <h3 class="unread">${notification.title}</h3>
                  <p>${notification.message}</p>
                  <span>${getRelativeTime(notification.created_at)}</span>
                </div>
                <span class="notification-type">${notification.type}</span>
              </div>
            </div>
          `).join('') : `
            <p class="no-notifications">No new notifications</p>
          `}
        </div>
      </div>
    `;

    // Auto-open modal if unread notifications exist
    if (unreadCount > 0) {
      notificationContainer.classList.remove('notification-hidden');
      notificationContainer.classList.add('notification-visible');
      document.body.style.overflow = 'hidden';
      document.body.style.touchAction = 'none';
      document.body.classList.add('no-scroll');
    } else {
      notificationContainer.classList.add('notification-hidden');
      notificationContainer.classList.remove('notification-visible');
      document.body.style.overflow = '';
      document.body.style.touchAction = '';
      document.body.classList.remove('no-scroll');
    }

    // Initialize swipe gestures
    initializeSwipeGestures();

    // Event listeners
    const markAllReadBtn = document.getElementById('mark-all-read');
    if (markAllReadBtn) {
      markAllReadBtn.addEventListener('click', () => {
       
        ApiService.markAllNotificationsRead()
          .then(response => {

            return fetchNotifications();
          })
          .catch(err => console.error('Failed to mark all read:', err));
      });
    }

    document.getElementById('minimize-modal')?.addEventListener('click', () => {
      notificationContainer.classList.add('notification-hidden');
      notificationContainer.classList.remove('notification-visible');
      document.body.style.overflow = '';
      document.body.style.touchAction = '';
      document.body.classList.remove('no-scroll');
    });
  }

  function initializeSwipeGestures() {
    const cards = document.querySelectorAll('.notification-card');
    const threshold = 50; // px

    cards.forEach(card => {
      let startX = 0;
      let currentX = 0;
      let isDragging = false;

      // Touch Events
      card.addEventListener('touchstart', e => {
        startX = e.touches[0].clientX;
        isDragging = true;
        card.classList.add('swiping');
      });

      card.addEventListener('touchmove', e => {
        if (!isDragging) return;
        currentX = e.touches[0].clientX;
        const deltaX = currentX - startX;
        card.style.transform = `translateX(${deltaX}px)`;
      });

      card.addEventListener('touchend', e => {
        isDragging = false;
        const deltaX = e.changedTouches[0].clientX - startX;
        handleSwipeAction(card, deltaX);
      });

      // Mouse Events (Desktop)
      card.addEventListener('mousedown', e => {
        startX = e.clientX;
        isDragging = true;
        card.classList.add('swiping');
        e.preventDefault();
      });

      card.addEventListener('mousemove', e => {
        if (!isDragging) return;
        currentX = e.clientX;
        const deltaX = currentX - startX;
        card.style.transform = `translateX(${deltaX}px)`;
      });

      card.addEventListener('mouseup', e => {
        if (!isDragging) return;
        isDragging = false;
        const deltaX = e.clientX - startX;
        handleSwipeAction(card, deltaX);
      });

      // Cancel swipe on leave (e.g., mouse leaves card)
      card.addEventListener('mouseleave', e => {
        if (isDragging && e.buttons === 0) {
          isDragging = false;
          card.style.transform = '';
          card.classList.remove('swiping');
        }
      });

      // Reset on cancel (mouse up outside or touchcancel)
      card.addEventListener('touchcancel', () => resetCard(card));
      document.addEventListener('mouseup', () => {
        if (isDragging) {
          isDragging = false;
          resetCard(card);
        }
      });
    });

  function handleSwipeAction(card, deltaX) {
    card.classList.remove('swiping');

    if (deltaX > threshold) {
        // Swipe right → mark as read & clear
        card.style.transition = 'transform 0.3s ease';
        card.style.transform = 'translateX(100%)';

        setTimeout(() => {
          const notificationId = card.dataset.id;

          // First mark as read, then clear
          ApiService.markNotificationRead(notificationId)
            .then(() => ApiService.clearNotification(notificationId))
            .then(() => {
              card.remove();
              fetchNotifications();
            })
            .catch(err => {
              console.error('Failed to clear notification:', err);
              resetCard(card);
            });
        }, 300);
    } else if (deltaX < -threshold) {
      // Swipe left → mark as read
      card.style.transition = 'transform 0.3s ease';
      card.style.transform = 'translateX(-100%)';

      setTimeout(() => {
        const notificationId = card.dataset.id;
        ApiService.markNotificationRead(notificationId)
          .then(() => {
            const title = card.querySelector('h3');
            title.classList.add('read');
            title.classList.remove('unread');
            fetchNotifications();
          })
          .catch(err => {
            console.error('Failed to mark read:', err);
            resetCard(card);
          });
      }, 300);
    } else {
      // Not a valid swipe → reset
      resetCard(card);
    }
  }

  function resetCard(card) {
    card.style.transition = 'transform 0.3s ease';
      card.style.transform = 'translateX(0)';
      setTimeout(() => {
          card.style.transition = '';
        }, 300);
      }
    }

  function fetchNotifications() {
    Promise.all([
      ApiService.getNotifications(),
      ApiService.getUnreadNotificationCount()
    ])
      .then(([notifications, unreadCount]) => {

        const count = typeof unreadCount === 'object' && unreadCount !== null
          ? unreadCount.unread_count
          : unreadCount;

        renderNotifications(Array.isArray(notifications) ? notifications : [], count || 0);
      })
  }


  // render channels
  function renderChannels(data) {
    const user = TelegramWebApp.getUser();
    const channelsView = document.getElementById('channelsView');
    
    // Clear existing content
    channelsView.innerHTML = '';

    if (data && data.length > 0) {
        // Using map to create an array of HTML strings for all channels
        const channelsHTML = data.map(channel => {
            const containerId = `channel-${channel.id}`;

            return `
                <div class="channel-detail-container mt-4" id="${containerId}">
                    <div class="channel-card relative container">
                        <div class="channel-header">
                            <img src="${channel.pp_url ? channel.pp_url : user?.photo_url}" alt="${channel.title}" class="channel-icon">
                            <div class="channel-info">
                                <h3 class="channel-name">
                                    ${channel.title ? (channel.title.length > 21 ? channel.title.slice(0, 21) + '…' : channel.title) : 'N/A'}
                                </h3>
                                <p class="channel-subscribers">${channel.subscribers} subscribers</p>
                            </div>
                            <div class="status-position channel-status badge ${channel.status}">
                                ${channel.status_display}
                            </div>
                        </div>
                        <div class="channel-stats">
                            <div class="channel-stat">
                                <p class="stat-label">Ads Running</p>
                                <p class="stat-value">${channel?.stats?.active_ads || "-"}</p>
                            </div>
                            <div class="channel-stat">
                                <p class="stat-label">Score</p>
                                <p class="stat-value">${channel?.stats?.engagement_rate || "-"}</p>
                            </div>
                            <div class="channel-stat">
                                <p class="stat-label">Earnings</p>
                                <p class="stat-value">ETB ${channel?.stats?.total_earnings.toFixed(2) || "0.00"}</p>
                            </div>
                        </div>
                        
                        ${channel.status === 'pending' ? `
                            <div class="channel-actions">
                                <button id="proceedBtn2" class="btn btn-sm btn-outline mt-2">Add Bot</button>
                                <button class="verifyBtn2 btn btn-primary mt-2" disabled data-channel-id="${channel.id}">
                                  Complete Verification
                                </button>
                            </div>
                        ` : ''}

                    </div>

                    <div class="channel-meta animate-slide-in-right mt-2">
                        <div class="grid-2 gap-1">
                            <div class="card flex flex-row gap-1 items-baseline flex-wrap">
                                <i class="fas fa-link text-info"></i>
                                <a href="${channel.channel_link}" target="_blank">${channel.channel_link.length > 30 ? channel.channel_link.slice(0, 23) + '...' : channel.channel_link}</a>
                            </div>
                            <div class="card flex flex-row gap-1 items-baseline flex-wrap">
                                <i class="${channel.auto_publish ? 'fas fa-bolt text-success' : 'fas fa-user-check text-warning'}"></i>
                                <span data-field="auto_publish">
                                    ${channel.auto_publish ? ' Auto-Publish Enabled' : ' Manual Approval Required'}
                                </span>
                            </div>
                            <div class="card">
                                <div class="flex flex-row gap-1 items-baseline">
                                    <i class="fas fa-clock text-info"></i>
                                    ${channel.timezone || '<em>Not specified</em>'}
                                </div>
                                <span class="timestamps text-xs text-muted gap-1 ml-4">
                                    <small>Current Time:</small> ${new Date().toLocaleString('en-US', {
                                        month: 'long', day: 'numeric', year: 'numeric',
                                        hour: 'numeric', minute: 'numeric', second: 'numeric', hour12: true
                                    })}
                                </span>
                            </div>
                            <div class="card flex flex-row gap-1 items-baseline flex-wrap">
                                <i class="fas fa-globe text-info"></i>
                                ${channel.region_display || '<em>Not specified</em>'}
                            </div>
                            <div class="card flex flex-row gap-1 items-baseline flex-wrap">
                                <i class="fas fa-language text-info"></i>
                                <span data-field="language">${channel.language.length > 0 ? channel.language.join(', ') : '<em>Not specified</em>'}</span>
                            </div>
                            <div class="card flex flex-row gap-1 items-baseline flex-wrap">
                                <i class="fas fa-tags text-info"></i>
                                ${channel.category.length > 0 ? channel.category.join(', ') : '<em>Not specified</em>'}
                            </div>
                            <div class="card flex flex-row gap-1 items-baseline flex-wrap">
                                <i class="fas fa-hand-holding-dollar text-info"></i>
                                <span data-field="min_cpm">ETB ${channel.min_cpm}</span>
                                <span class="text-muted tooltip-icon" data-tooltip="The Minimum Cost Per 1000 Impressions you want to charge for this channel, Birr.">
                                    <i class="fas fa-info-circle"></i>
                                </span>
                            </div>
                            <div class="card flex flex-row gap-1 items-baseline flex-wrap">
                                <i class="fas fa-repeat text-info"></i>
                                Max - <span data-field="repost_preference_frequency">${channel.repost_preference_frequency}</span>x/
                                <span data-field="repost_preference">${channel.repost_preference}</span>
                            </div>
                        </div>

                        <div class="card timestamps flex-row justify-between">
                            <div class="text-xs text-muted text-left gap-1 mt-2 border-0 items-start"> 
                              <div><i class="fas fa-calendar-plus text-info"></i>
                                  <strong>Created:</strong> ${new Date(channel.created_at).toLocaleString()}
                              </div>
                              <div><i class="fas fa-calendar-check text-info"></i>
                                  <strong>Last Updated:</strong> ${new Date(channel.updated_at).toLocaleString()}
                              </div>
                            </div>

                            <div class="channel-actions flex items-center gap-0">
                              <button class="p-1 edit-channel-btn bg-transparent text-brand border-0" data-id="${channel.id}" title="Edit channel preference">
                                <i class="fas fa-pen-to-square"></i>
                              </button>
                              <button class="p-1 delete-channel-btn bg-transparent text-danger border-0" data-id="${channel.id}" title="Remove This channel">
                                <i class="fas fa-trash"></i>
                              </button>
                            </div>
                        </div>
                    </div>

                    ${channel.admin_notes ? `
                        <blockquote class="admin-notes">
                            <i class="fas fa-comments"></i>
                            <strong>Admin Notes:</strong> <p>${channel.admin_notes}</p>
                        </blockquote>
                    ` : ''}
                </div>

                <div class="mt-4">
                    <div class="section-header">
                        <h3 class="text-brand text-sm">Ads in this Channel ( ${channel.ad_placements?.length || 0} )</h3>
                        <div class="text-xs text-brand cursor-pointer" onclick="switchView('adsView')">View All</div>
                    </div>
                </div>
            </div>
        `;
        });
        channelsView.innerHTML = channelsHTML.join('');
        bindVerifyButtons();
        channelsView.innerHTML += `
        <div class="flex justify-center items-center mt-8">
            <button class="card border-primary bg-transparent text-muted p-2 cursor-pointer" id="createChannel" onclick="toggleChannelBottomSheet()">
                <i class="fas fa-plus-circle"></i>
                <span>Add more channels</span>
            </button>
        </div>
        `;
    } else {
        channelsView.innerHTML = `
            <div class="flex justify-center h-screen items-center">
                <button class="card" id="createChannel" onclick="toggleChannelBottomSheet()">
                    <i class="fas fa-plus-circle"></i>
                    <span>Add channel</span>
                </button>
            </div>
        `;
    }

    bindChannelActionButtons(data);
    initTooltips(channelsView);
   
}

async function loadEditCheckboxOptions(channel) {
  try {
    const [langRes, catRes] = await Promise.all([
      fetch('/api/languages/'),
      // fetch('/api/categories/')
    ]);

    const languages = await langRes.json();
    // const categories = await catRes.json();

    const langGroup = document.getElementById('edit-language-group');
    // const catGroup = document.getElementById('edit-category-group');

    if (!langGroup) return;
    langGroup.innerHTML = languages.map(lang => {
      const id = `edit_language_${lang.id}`;
      const isChecked = channel.language.includes(lang.name);
      return `
        <input type="checkbox" id="${id}" name="language" value="${lang.id}" ${isChecked ? 'checked' : ''}>
        <label for="${id}" class="pill">${lang.name}</label>
      `;
    }).join('');

    // if (catGroup) {
    //   catGroup.innerHTML = '';
    //   categories.forEach(cat => {
    //     const id = `edit_category_${cat.id}`;
    //     catGroup.innerHTML += `
    //       <input type="checkbox" id="${id}" name="category" value="${cat.id}">
    //       <label for="${id}" class="pill">${cat.name}</label>
    //     `;
    //   });
    // }

    limitCheckboxGroup('language', 3);
    // limitCheckboxGroup('category', 3);

  } catch (err) {
    console.warn("Failed to load options:", err);
    showAlert("Failed to load languages/categories", "error");
  }
}

function toggleEditChannelBottomSheet(show = null, channel = null) {
  const wrapper = document.getElementById('editChannelBottomSheetWrapper');
  const sheet = document.getElementById('editChannelBottomSheet');
  const form = document.getElementById('editChannelForm');
  
  const isVisible = wrapper && !wrapper.classList.contains('hidden');
  
  if (show === true || (!isVisible && show !== false)) {
    if (channel) {
      // Set the channel ID on the form
      if (form) form.dataset.channelId = channel.id;
      populateEditForm(channel);
    }
    wrapper.classList.remove('hidden');
    document.body.classList.add('no-scroll');
    setTimeout(() => {
      sheet.classList.add('show');
    }, 20);
  } else {
    sheet.classList.remove('show');
    setTimeout(() => {
      wrapper.classList.add('hidden');
      document.body.classList.remove('no-scroll');
      // Clear the channel ID when closing
      if (form) form.removeAttribute('data-channel-id');
    }, 100);
  }
}

function populateEditForm(channel) {
  document.getElementById('editMinCpm').value = channel.min_cpm;
  document.getElementById('editRepostFrequency').value = channel.repost_preference_frequency;
  document.getElementById('editRepostPreference').value = channel.repost_preference;
  document.getElementById('editAutoPublish').checked = channel.auto_publish;
  
  // Load languages
  loadEditCheckboxOptions(channel);
}


let currentFormSubmitHandler = null;

function bindChannelActionButtons(data) {
  // Remove previous submit handler if it exists
  const form = document.getElementById('editChannelForm');
  if (form && currentFormSubmitHandler) {
    form.removeEventListener('submit', currentFormSubmitHandler);
  }

  data.forEach(channel => {
    const editBtn = document.querySelector(`.edit-channel-btn[data-id="${channel.id}"]`);
    const deleteBtn = document.querySelector(`.delete-channel-btn[data-id="${channel.id}"]`);

    // Clean up old listeners first
    if (editBtn) {
      editBtn.replaceWith(editBtn.cloneNode(true));
    }
    if (deleteBtn) {
      deleteBtn.replaceWith(deleteBtn.cloneNode(true));
    }

    // Add fresh listeners
    document.querySelector(`.edit-channel-btn[data-id="${channel.id}"]`)
      ?.addEventListener('click', () => {
        currentEditingChannelId = channel.id;
        toggleEditChannelBottomSheet(true, channel);
      });
      
    document.querySelector(`.delete-channel-btn[data-id="${channel.id}"]`)
      ?.addEventListener('click', () => deleteChannel(channel, `channel-${channel.id}`));
  });

  // Create new submit handler
  currentFormSubmitHandler = function(e) {
    e.preventDefault();
    if (currentEditingChannelId) {
      saveChannelEdit(currentEditingChannelId);
    } else {
      console.error('No channel ID found for editing');
      showAlert('Error: No channel selected for editing', 'error');
    }
  };

  // Add the new handler
  form?.addEventListener('submit', currentFormSubmitHandler);
  
  // Clean up close/cancel handlers
  const closeBtn = document.getElementById('closeEditChannelBtn');
  const cancelBtn = document.getElementById('cancelEditChannelBtn');
  
  if (closeBtn) {
    closeBtn.replaceWith(closeBtn.cloneNode(true));
    document.getElementById('closeEditChannelBtn').addEventListener('click', () => {
      currentEditingChannelId = null;
      toggleEditChannelBottomSheet(false);
    });
  }
  
  if (cancelBtn) {
    cancelBtn.replaceWith(cancelBtn.cloneNode(true));
    document.getElementById('cancelEditChannelBtn').addEventListener('click', () => {
      currentEditingChannelId = null;
      toggleEditChannelBottomSheet(false);
    });
  }
}


async function saveChannelEdit(channelId) {
  const form = document.getElementById('editChannelForm');
  if (!form || !channelId) return;

  const submitBtn = form.querySelector('button[type="submit"]');
  if (submitBtn.disabled) return;
  
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

  try {
    const updated = {
      min_cpm: form.min_cpm.value,
      repost_preference_frequency: form.repost_preference_frequency.value,
      repost_preference: form.repost_preference.value,
      auto_publish: form.auto_publish.checked,
      language: Array.from(document.querySelectorAll('#edit-language-group input[name="language"]:checked')).map(cb => cb.value)
    };

    // Validation (single alert for all errors)
    const errors = [];
    if (updated.language.length === 0) errors.push('• Select at least one language');
    if (updated.repost_preference_frequency <= 0) errors.push('• Repost frequency must be > 0');
    if (updated.min_cpm <= 0) errors.push('• Minimum CPM must be > 0');
    if (!updated.repost_preference) errors.push('• Select a repost preference type');

    if (errors.length > 0) {
      showAlert(`Please fix these issues:\n\n${errors.join('\n')}`, 'warning');
      return;
    }

    const res = await fetch(`/api/channels/${channelId}/`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken()
      },
      body: JSON.stringify(updated)
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.message || 'Update failed');
    }

    showAlert('✓ Channel updated successfully!', 'success');
    toggleEditChannelBottomSheet(false);
    TabController.refreshCurrentTab();

  } catch (err) {
    console.error('Update error:', err);
    showAlert(`Error: ${err.message || 'Failed to update channel'}`, 'error');
  } finally {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = 'Save Changes';
    }
  }
}



async function deleteChannel(channel, containerId) {
  const popupParams = {
    title: "Remove Channel",
    message: `Are you sure you want to Remove channel "${channel.title}"?\nThis action cannot be undone.`,
    buttons: [
      { id: "confirm", type: "destructive", text: "Yes Remove" },
      { id: "cancel", type: "default", text: "Cancel" }
    ]
  };

  Telegram.WebApp.showPopup(popupParams, async function (buttonId) {
    if (buttonId !== 'confirm') return;

    try {
      const res = await fetch(`/api/channels/${channel.id}/`, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': getCSRFToken()
        }
      });

      if (res.ok) {
        showAlert('Channel removed successfully.', 'success');
        await TabController.refreshCurrentTab();
      } else {
        const data = await res.json();
        showAlert(data.error || 'Failed to remove channel.', 'error');
      }
    } catch (err) {
      showAlert('Network error while removing channel.', 'error');
    }
  });
}

function bindVerifyButtons() {
  const channelsView = document.getElementById('channelsView');

  channelsView.addEventListener('click', function (e) {
    if (e.target && e.target.id === 'proceedBtn2') {
      proceedBtn2 = e.target;
      const verifyBtn = proceedBtn2.nextElementSibling;
      const botLink = document.getElementById('openBot').dataset.botLink;
      
      e.preventDefault();
      const botUsername = botLink.split('/').pop(); // Extract bot username from botLink
      const deepLink = `https://t.me/${botUsername}?startchannel=1`;

      // Open the link in Telegram app
      if (window.Telegram?.WebApp) {
          Telegram.WebApp.openTelegramLink(deepLink); // For Telegram Web App
      } else {
          window.open(deepLink, '_blank'); // For non-Telegram Web App environments
      }

      // Enable verify button after the user proceeds
      setTimeout(() => {
          proceedBtn2.remove();
          verifyBtn.disabled = false;
          verifyBtn.classList.remove('disabled');
      }, 1000); 
    }
    // Check if the clicked element is a 'verifyBtn2'
    if (e.target && e.target.classList.contains('verifyBtn2')) {
      const channelId = e.target.dataset.channelId;
      handleVerification(e.target, channelId);
    }
  });
}

async function handleVerification(button, channelId) {
  if (!channelId) {
    showAlert('Channel ID not found, please try again.', 'error');
    return;
  }

  const tg = TelegramWebApp.getInstance();
  button.disabled = true;
  button.innerHTML = '<span class="text-brand"><i class="fas fa-spinner fa-spin"> </i> Verifying...</span>';

  try {
    const res = await fetch(`/api/channels/verify/${channelId}/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken()
      }
    });

    const data = await res.json();

    if (res.ok) {
      tg?.HapticFeedback?.notificationOccurred("success");
      showAlert(data.message || '🎉 Channel verified successfully! <br/> now you start serve & earn', 'success');
      button.remove();
      await TabController.refreshCurrentTab();
    } else {
      tg?.HapticFeedback?.notificationOccurred("error");
      button.innerHTML = 'Complete Verification';
      button.disabled = false;
      showAlert(data.error || 'Verification failed, please try again.', 'error');
    }
  } catch (err) {
    showAlert('Network error during verification, please try again.', 'error');
  } finally {
    button.disabled = false;
    button.innerHTML = 'Complete Verification';
  }
}

  // Render payment view
function renderPayments(data) {
  const paymentView = document.getElementById('paymentView');

  paymentView.innerHTML = `
    <div class="card mt-4">
      <div class="section-header">
        <h3>Earning Account</h3>
      </div>
      <div class="earning mt-2">
        <div class="dashboard-cards grid-1-2">
          <div>
            <div class="card metric-card">
              <div class="card-content gap-2 text-left">
                <div class="metric-label">Available Balance</div>
                <div class="metric-value text-success">ETB ${data.balance.available || '0.00'}</div>
                <div class="metric-label text-muted text-xs">
                  +${data.balance.escrow || '0.00'} pending
                </div>
              </div>
              <div class="btn btn-sm btn-outline--green mt-2 text-success" id="withdraw-btn">
                Get Paid
              </div>
            </div>
          </div>

          ${data.last_withdrawal || data.latest_withdrawal_request ? `
            <div class="card metric-card gap-2">
              <div class="card-content text-left">
                ${data.latest_withdrawal_request ? `
                  <div class="metric-value">Latest Withdrawal Request</div>
                  <div class="metric-label text-sm text-muted">
                    ${new Date(data.latest_withdrawal_request.created_at).toLocaleDateString('en-US', {
                      year: 'numeric', month: 'short', day: 'numeric'
                    })}
                  </div>
                  <div class="metric-label">
                    <em>
                      ETB ${data.latest_withdrawal_request.amount} — 
                      ${data.latest_withdrawal_request.method_display || 'Unknown Method'} — 
                      ${data.latest_withdrawal_request.method_type === 'bank' ? `Account ending ${data.latest_withdrawal_request.account_ending}` 
                        : data.latest_withdrawal_request.method_type === 'wallet' ? `Wallet ending ${data.latest_withdrawal_request.account_ending}` 
                        : 'Unknown'} — 
                      Ref: ${data.latest_withdrawal_request.reference}
                    </em>
                  </div>
                  <div class="metric-label mt-1">
                    <span class="badge ${
                      data.latest_withdrawal_request.status === 'approved' ? 'info' : 'warning'
                    }">
                      ${data.latest_withdrawal_request.status.charAt(0).toUpperCase() + data.latest_withdrawal_request.status.slice(1)}
                    </span>
                  </div>
                ` : ''}
                ${data.last_withdrawal ? `
                  <div class="metric-value mt-2">Last Withdrawal</div>
                  <div class="metric-label text-sm text-muted">
                    ${new Date(data.last_withdrawal.completed_at).toLocaleDateString('en-US', {
                      year: 'numeric', month: 'short', day: 'numeric'
                    })}
                  </div>
                  <div class="metric-label">
                    <em>
                      ETB ${data.last_withdrawal.amount} — 
                      ${data.last_withdrawal.method_display || 'Unknown Method'} — 
                      ${data.last_withdrawal.method_type === 'bank' ? `Account ending ${data.last_withdrawal.account_ending}` 
                        : data.last_withdrawal.method_type === 'wallet' ? `Wallet ending ${data.last_withdrawal.account_ending}` 
                        : 'Unknown'} — 
                      Ref: ${data.last_withdrawal.reference}
                    </em>
                  </div>
                  <div class="metric-label mt-1">
                    <span class="badge success">
                      Completed
                    </span>
                  </div>
                ` : ''}
                <div class="text-xs text-brand mt-3 cursor-pointer" id="openTransactions" onclick="showTransaction(true)">
                  View Transactions
                </div>
              </div>
            </div>
          ` : ''}
        </div>

        <div class="mt-4">
          <div class="card-content">
            <div class="metric-value p-2 border-b text-md">Payment Methods</div>
            <ul class="grid-2 gap-1 mt-4">
              ${data.payment_methods.sort((a, b) => b.is_default - a.is_default).map(method => {
                const typeDetail = method.payment_method_type_details || {};
                const category = typeDetail.category || '';
                let detail = '';
                switch (category) {
                  case 'wallet':
                    detail = method.phone_number ? `****${method.phone_number.slice(-4)}` : '****';
                    break;
                  case 'bank':
                  case 'credit_card':
                    detail = method.account_number ? `****${method.account_number.slice(-4)}` : '****';
                    break;
                  case 'crypto':
                    detail = typeDetail.short_name || 'Crypto Wallet';
                    break;
                  default:
                    detail = 'Unknown';
                }
                return `
                  <li class="card flex flex-row items-center gap-2 ${method.is_default ? 'bg-background-alt' : ''}">
                    <img 
                      src="${typeDetail.logo || '/static/images/default-payment.png'}" 
                      alt="${typeDetail.name || 'Payment'}" 
                      class="rounded-full object-cover" 
                      style="width: 32px; height: 32px;"
                      onerror="this.src='/static/images/default-payment.png'">
                    <div class="text-sm">
                      <div>${typeDetail.short_name || 'Unknown Method'}</div>
                      <span class="text-xs">${detail}</span>
                    </div>
                    <div class="text-xs ml-auto">
                      ${method.status === 'verified' && method.is_default 
                        ? '<i class="fas fa-check-circle text-success" title="Verified Default"></i>' 
                        : method.status === 'verified' 
                        ? `<i class="fas fa-check text-primary" data-payment-method-id="${method.id}" title="Verified"></i>`
                        : method.status === 'rejected'
                        ? `<i class="fas fa-times-circle text-danger" title="Rejected"></i>`
                        : `<i class="fas fa-spinner text-warning" title="${method.status.charAt(0).toUpperCase() + method.status.slice(1)}"></i>`}
                      ${method.is_default ? '' 
                        : `<i class="fas fa-ellipsis-v payment-method-action cursor-pointer top-0 right-0 absolute p-1" 
                              data-payment-method-id="${method.id}" 
                              title="More Actions"></i>`}
                    </div>
                  </li>
                `;
              }).join('')}
              <div class="wh-auto border-0 justify-center items-center flex bg-transparent bottom-0 right-0 absolute p-1" onclick="toggleBottomSheet(true)">
                <i class="fas fa-plus-circle fa-2x text-success shadow-lg"></i>
              </div>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <div id="transactions" class="mt-4 hidden">
      <div class="section-header">
        <h3>Transaction History</h3>
        <div class="cursor-pointer" onclick="showTransaction(false)"><i class="fas fa-chevron-up"></i></div>
      </div>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Type</th>
              <th>Amount</th>
              <th>Balance</th>
              <th>Reference</th>
            </tr>
          </thead>
          <tbody>
            ${data.transactions.length === 0 ? `
              <tr><td colspan="5" class="text-center">No transactions yet.</td></tr>
            ` : data.transactions.map(tx => `
              <tr>
                <td>${new Date(tx.date).toLocaleString('en-US', {
                  year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                })}</td>
                <td><i class="${tx.icon_class}"></i> ${tx.display_type}</td>
                <td>ETB ${tx.amount}</td>
                <td>${tx.balance_detail || 'N/A'}</td>
                <td>${tx.reference}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
        ${data.pagination ? `
          <div class="pagination mt-2">
            ${data.pagination.previous ? `<button onclick="fetchTransactions('${data.pagination.previous}')">Previous</button>` : ''}
            ${data.pagination.next ? `<button onclick="fetchTransactions('${data.pagination.next}')">Next</button>` : ''}
          </div>
        ` : ''}
      </div>
    </div>
  `;

  // Handle pagination
  document.querySelectorAll('.pagination button').forEach(button => {
    button.addEventListener('click', async () => {
      const url = button.getAttribute('onclick').match(/'([^']+)'/)[1];
      try {
        const response = await fetch(url, {
          headers: {
            'X-CSRFToken': getCSRFToken()
          }
        });
        const newData = await response.json();
        renderPayments({
          balance: data.balance,
          payment_methods: data.payment_methods,
          last_withdrawal: data.last_withdrawal,
          latest_withdrawal_request: data.latest_withdrawal_request,
          transactions: newData.results,
          pagination: {
            next: newData.next,
            previous: newData.previous,
            count: newData.count
          }
        });
      } catch (err) {
        showAlert('Failed to load transactions.', 'error');
      }
    });
  });

  // Handle Get Paid button click
  document.getElementById('withdraw-btn').addEventListener('click', function() {
    if (this.classList.contains('disabled')) return;
    if (!data || !data.balance) {
      showAlert("No balance data available", "error");
      return;
    }

    const availableBalance = parseFloat(data.balance.available);
    const withdrawButton = this;

    if (availableBalance > 0) {
      const maxAmountElem = document.getElementById('max-amount');
      const withdrawAmountInput = document.getElementById('withdraw-amount');
      withdrawAmountInput.setAttribute('max', availableBalance);
      withdrawAmountInput.value = availableBalance.toFixed(2);
      maxAmountElem.textContent = `ETB ${availableBalance.toFixed(2)}`;
      toggleWithdrawalBottomSheet(true);

      const confirmBtn = document.getElementById('confirm-withdrawal');
      const cancelBtn = document.getElementById('cancel-withdrawal');

      confirmBtn.onclick = async function() {
        const amount = parseFloat(withdrawAmountInput.value);
        if (isNaN(amount) || amount <= 0 || amount > availableBalance) {
          showAlert("Please enter a valid amount", "warning");
          return;
        }
        if (amount < (data.balance.min_withdrawal_amount || 100)) {
          showAlert("Minimum withdrawal amount is ETB 100", "warning");
          return;
        }

        const paymentMethodId = data.payment_methods.find(method => method.is_default && method.status === 'verified')?.id;
        if (!paymentMethodId) {
          showAlert("No verified payment method found. Please add a payment method first.", "warning");
          toggleWithdrawalBottomSheet(false);
          return;
        }

        toggleWithdrawalBottomSheet(false);
        withdrawButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        withdrawButton.classList.add('disabled');

        try {
          const response = await fetch('/api/withdrawal/request/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
              amount: amount,
              user_payment_method_id: paymentMethodId
            })
          });
          const result = await response.json();
          if (result.message) {
            showAlert(result.message || 'Withdrawal request submitted successfully!', 'success');
            await TabController.refreshCurrentTab();
          } else {
            showAlert(result.error || 'Failed to process withdrawal request.', 'error');
          }
        } catch (err) {
          showAlert('An error occurred while processing the withdrawal request.', 'error');
          console.error(err);
        } finally {
          withdrawButton.innerHTML = 'Get Paid';
          withdrawButton.classList.remove('disabled');
        }
      };

      cancelBtn.onclick = function() {
        toggleWithdrawalBottomSheet(false);
      };
    } else {
      showAlert("Insufficient balance to withdraw", "warning");
    }
  });

  // Event listener for payment method actions
  document.querySelectorAll('.payment-method-action').forEach(item => {
    item.addEventListener('click', (e) => {
      const paymentMethodId = e.target.dataset.paymentMethodId;
      openPaymentMethodOptions(paymentMethodId, `payment-method-${paymentMethodId}`);
    });
  });
}

// Existing functions (unchanged)
function toggleWithdrawalBottomSheet(show) {
  const wrapper = document.getElementById('withdrawBottomSheetWrapper');
  const sheet = document.getElementById('withdrawalBottomSheet');
  const isVisible = wrapper && !wrapper.classList.contains('hidden');

  if (show === true || (!isVisible && show !== false)) {
    wrapper.classList.remove('hidden');
    document.body.classList.add('no-scroll');
    setTimeout(() => {
      sheet.classList.add('show');
    }, 20);
  } else {
    sheet.classList.remove('show');
    setTimeout(() => {
      wrapper.classList.add('hidden');
      document.body.classList.remove('no-scroll');
    }, 20);
  }
}

function showConfirmationPopup(title, message, buttons, callback) {
  Telegram.WebApp.showPopup({
    title: title,
    message: message,
    buttons: buttons
  }, callback);
}

function removePaymentMethod(paymentMethodId, containerId) {
  const popupParams = {
    title: "Remove Payment Method",
    message: "Are you sure you want to remove this payment method?\nThis action cannot be undone.",
    buttons: [
      { id: "confirm", type: "destructive", text: "Yes, Remove" },
      { id: "cancel", type: "default", text: "Cancel" }
    ]
  };

  showConfirmationPopup(popupParams.title, popupParams.message, popupParams.buttons, async function(buttonId) {
    if (buttonId !== 'confirm') return;

    try {
      const res = await fetch(`/api/payment-methods/${paymentMethodId}/`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken()
        }
      });

      if (res.ok) {
        showAlert('Payment method removed successfully.', 'success');
        await TabController.refreshCurrentTab();
      } else {
        const data = await res.json();
        showAlert(data.error || 'Failed to remove payment method.', 'error');
      }
    } catch (err) {
      showAlert('Network error while removing payment method.', 'error');
    }
  });
}

function makeDefaultPaymentMethod(paymentMethodId, containerId) {
  const popupParams = {
    title: "Make Default",
    message: "Are you sure you want to make this payment method the default?",
    buttons: [
      { id: "confirm", type: "default", text: "Yes, make default" },
      { id: "cancel", type: "cancel", text: "Cancel" }
    ]
  };

  showConfirmationPopup(popupParams.title, popupParams.message, popupParams.buttons, async function(buttonId) {
    if (buttonId !== 'confirm') return;

    try {
      const res = await fetch(`/api/payment-methods/${paymentMethodId}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken(),
        },
        credentials: 'same-origin',
        body: JSON.stringify({ is_default: true }),
      });

      const data = await res.json();
      if (res.ok && data.ok) {
        showAlert('Payment method made default successfully.', 'success');
        await TabController.refreshCurrentTab();
      } else {
        const errorMsg = data?.is_default?.[0] || data?.non_field_errors?.[0] || data?.error || 'Failed to make default.';
        showAlert(errorMsg, 'error');
      }
    } catch (err) {
      showAlert('Network error while making default payment method.', 'error');
    }
  });
}

function openPaymentMethodOptions(paymentMethodId, containerId) {
  Telegram.WebApp.showPopup({
    title: "Choose an Action",
    message: "What do you want to do with this payment method?",
    buttons: [
      { id: "delete", type: "destructive", text: "Delete" },
      { id: "setDefault", type: "default", text: "Set as Default" },
      { id: "cancel", type: "cancel", text: "Cancel" }
    ]
  }, function(buttonId) {
    if (buttonId === 'delete') {
      removePaymentMethod(paymentMethodId, containerId);
    } else if (buttonId === 'setDefault') {
      makeDefaultPaymentMethod(paymentMethodId, containerId);
    } else {
      console.log('Action canceled');
    }
  });
}


// Render ads view
function renderAds(data) {
  const adsView = document.getElementById('adsView');

  if (!data || !Array.isArray(data) || data.length === 0) return;

  adsView.innerHTML = `
    <div class="mt-4">
      <div class="section-header mb-0">
        <h3>Ad Placements</h3>
        <!-- Button to rotate the table -->
        <button id="rotate-table-btn" class="btn bg-transparent text-primary">
          <i class="fas fa-sync"></i> 
        </button>
      </div>
      <div class="table-responsive rotateable-table pt-6">
        <table class="data-table rotateable-table" id="ads-table">
          <thead>
            <tr>
              <th>Ad</th>
              <th>Preview</th>
              <th>Channel</th>
              <th>Status</th>
              <th>Bid (CPM)</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${data.map(ad =>` 
              <tr>
                <td>
                  <div class="ad-info">
                    <div class="ad-icon status ${ad.status} bg-none"><i class="fas fa-ad"></i></div>
                    <div>
                      <p class="ad-name">${ad.ad_headline}</p>
                      <p class="ad-type">${ad.ad_brand_name || 'None brand'}</p>
                    </div>
                  </div>
                </td>
                <td>
                  <div class="ad-preview" data-deep-link="${ad.content_platform_id}" id="ad-preview-${ad.id}">
                    ${ad.ad_img_url ? `<img src="${ad.ad_img_url}" alt="Ad Preview" class="ad-preview-image" />` : `<i class="fas fa-photo-film status bg-none ${ad.status}"></i>`}
                  </div>
                </td>
                <td>${ad.channel_title ? (ad.channel_title.length > 21 ? ad.channel_title.slice(0, 21) + '…' : ad.channel_title) : 'N/A'}</td>
                <td>
                  <span class="text-muted tooltip-icon status ${ad.status} ${ad.status === 'running' ? 'font-bold' : ''}" data-tooltip="${getStatusTooltip(ad.status)}">
                    ${ad.status_display}
                  </span>
                </td>
                <td>ETB ${(Number(ad.winning_bid_price) || 0).toFixed(2)}</td>
                <td>
                  <div class="action-buttons flex flex-row gap-1" id="action-buttons-${ad.id}">
                    <!-- Action buttons will be dynamically injected here, but we won't need them for opening -->
                  </div>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;

  // Attach event listener for opening ad in Telegram when preview image/icon is clicked
  data.forEach(ad => {
    const adPreview = document.getElementById(`ad-preview-${ad.id}`);
    if (adPreview) {
      adPreview.addEventListener('click', () => {
        openTelegramLink(ad.content_platform_id);  // Open the ad in Telegram when the preview is clicked
      });
    }
  });

  data.forEach(ad => {
    updateActionButtons(ad);
    initTooltips(adsView);
  });

  // Add event listener for the button
  // document.getElementById('rotate-table-btn').addEventListener('click', toggleTableOrientation);

  // Function to toggle the table view
  function toggleTableOrientation() {
    const table = document.querySelector('.data-table.rotateable-table');
    const tableWrapper = document.querySelector('.table-responsive.rotateable-table');
    
    // Toggle landscape-view class for both table and its wrapper
    table.classList.toggle('landscape-view'); 
    tableWrapper.classList.toggle('landscape-view'); 
  }
}

  function openTelegramLink(deepLink) {
    const tg = Telegram.WebApp;

    // Check if we're in the Telegram WebApp environment
    if (tg && tg.openTelegramLink) {
      try {
        // Ensure the deep link is valid (basic check: starts with https://t.me/)
        if (deepLink.startsWith("https://t.me/")) {
          tg.openTelegramLink(deepLink);  // Open link in the Telegram app
        } else {
          throw new Error('Invalid deep link format');
        }
      } catch (error) {
        showAlert('Failed to open the link in Telegram. Please try again.', 'error');
        console.warn('Error opening Telegram link:', error);
      }
    } else {
      // Fallback: If we're not in the Telegram WebApp environment, open in a new tab
      console.warn('Not in Telegram WebApp environment. Attempting to open link in a new tab');
      window.open(deepLink, '_blank'); // Open link in a new tab for non-Telegram WebApp users
    }
  }

  // Function to update action buttons based on ad status
  function updateActionButtons(ad) {
    const actionContainer = document.getElementById(`action-buttons-${ad.id}`);
    let buttonsHTML = '';

    if (ad.status === 'pending') {
      buttonsHTML = `
        <button class="btn bg-transparent text-success approve-btn" data-id="${ad.id}" title="Accept coming Ad">
          <i class="fas fa-check"></i>
        </button>
        <button class="btn bg-transparent text-danger reject-btn" data-id="${ad.id}" title="Reject Coming Ad">
          <i class="fas fa-cancel"></i>
        </button>
      `;
    } else if (ad.status === 'rejected') {
      buttonsHTML = '<span style="color:red;"><i class="fas fa-exclamation-triangle"></i></span>';
    } 
    else if (ad.status === 'paused') {
      // buttonsHTML = `
      //   <button class="btn bg-transparent text-success approve-btn" data-id="${ad.id}" title="Accept coming Ad">
      //     <i class="fas fa-play"></i>
      //   </button>
      // `;
    } else if (ad.status === 'running') {
      buttonsHTML = `
        <button class="btn bg-transparent text-success" disabled title="Ad is live">
          <i class="fas fa-check-circle"></i>
        </button>
      `;
    } else if (ad.status === 'approved') {
      buttonsHTML = `
        <button class="btn bg-transparent text-brand" disabled title="Ad is approved">
          <i class="fas fa-check-circle"></i>
        </button>
      `;
    }

    actionContainer.innerHTML = buttonsHTML;

    // Attach event listeners to approve and reject buttons
    actionContainer.querySelectorAll('.approve-btn').forEach(button => {
      button.addEventListener('click', handleApproveClick);
    });

    actionContainer.querySelectorAll('.reject-btn').forEach(button => {
      button.addEventListener('click', handleRejectClick);
    });
  }

  async function handleApproveClick(event) {
    const adId = event.target.closest('button').dataset.id;
    const ad = { id: adId };  // Create an ad object to pass if needed for confirmation message
    
    // Show confirmation popup before proceeding
    showConfirmationPopup(
      "Approve this ad? This action will make it live.",
      async () => {
        try {
          const response = await fetch(`/api/ad-placements/${adId}/approve/`, {
            method: 'POST',
            headers: { 
              'Content-Type': 'application/json',
              'X-CSRFToken': getCSRFToken()
            },
            credentials: 'same-origin' 
          });

          const result = await response.json();

          if (response.ok) {
            showAlert(result.message, 'success');
            updateActionButtons(result.adplacement);  // Update buttons based on new ad placement status
          } else {
            showAlert(result.message || 'Failed to approve the ad placement', 'error');
          }
        } catch (error) {
          showAlert('Error approving ad placement: ' + error.message, 'error');
        }
      }
    );
  }

  async function handleRejectClick(event) {
    const adId = event.target.closest('button').dataset.id;
    const ad = { id: adId };  // Create an ad object to pass if needed for confirmation message

    // Show confirmation popup before proceeding
    showConfirmationPopup(
      "Are you sure you want to reject this ad? This action will prevent it from running.",
      async () => {
        try {
          const response = await fetch(`/api/ad-placements/${adId}/reject/`, {
            method: 'POST',
            headers: { 
              'Content-Type': 'application/json',
              'X-CSRFToken': getCSRFToken()
            },
            credentials: 'same-origin' 
          });

          const result = await response.json();

          if (response.ok) {
            showAlert(result.message, 'success');
            updateActionButtons(result.adplacement);  // Update buttons based on new ad placement status
          } else {
            showAlert(result.message || 'Failed to reject the ad placement', 'error');
          }
        } catch (error) {
          showAlert('Error rejecting ad placement: ' + error.message, 'error');
        }
      }
    );
  }
  
  // Function to show confirmation popup
  function showConfirmationPopup(message, onConfirm) {
    const popupParams = {
      title: "Confirmation",
      message: message,
      buttons: [
        { id: "confirm", type: "destructive", text: "Yes, Proceed" },
        { id: "cancel", type: "default", text: "Cancel" }
      ]
    };

    Telegram.WebApp.showPopup(popupParams, function (buttonId) {
      if (buttonId === 'confirm') {
        onConfirm();  // Proceed with the action
      }
      // If 'cancel' is clicked, do nothing
    });
}

  function getStatusTooltip(status) {
    switch (status) {
      case 'pending':
        return "Ad placement is waiting for your approval. Approve and start earning.";
      case 'approved':
        return "Ad placement has been approved and is ready to run. Your channel will start earning shortly.";
      case 'rejected':
        return "Ad placement was rejected and will not run.";
      case 'paused':
        return "Ad placement is paused and will not be shown.";
      case 'running':
        return "Ad currently running. Your channel is earning.";
      default:
        return "Status not available.";
    }
  }

  function renderSettings(data) {
    const settingsView = document.getElementById('settingsView');
    if (!settingsView || !data) return;

    const botBtn = document.getElementById("openBot");
    if (!botBtn) return;

    const bot = botBtn.dataset.botLink;

    const tgUser = TelegramWebApp.getUser();
    const username = tgUser?.username || data.username || '—';

    settingsView.innerHTML = `
      <div class="settings-section">
        <h3>User Info</h3>
        <div class="setting-items">
          <div class="setting-item">
            <label>Your Name</label>
            <div 
              class="editable-field" 
              contenteditable="true" 
              data-key="first_name"
              data-placeholder="First name"
            >${data.first_name || ''}</div>
          </div>

          <div class="setting-item">
            <div 
              class="editable-field" 
              contenteditable="true" 
              data-key="last_name"
              data-placeholder="Last name"
            >${data.last_name || ''}</div>
          </div>

          <div class="setting-item">
            <label>Username</label>
            <div class="editable-field disabled" data-key="username">${username}</div>
          </div>

          <div class="setting-item">
            <label>Address</label>
            <div 
              class="editable-field" 
              contenteditable="true" 
              data-key="address"
              data-placeholder="Enter address"
            >${data.address || ''}</div>
          </div>

          <div class="setting-item">
            <label>Email</label>
            <div 
              class="editable-field" 
              contenteditable="true" 
              data-key="email"
              data-placeholder="Email address (optional)"
            >${data.email || ''}</div>
          </div>

          <button id="saveSettings" class="btn btn-checkmark hidden" title="Save Changes">
            <i class="fas fa-check"></i>
          </button>

          <div class="setting-footer mt-4">
            <small class="text-muted">This information is synced with Telegram where applicable.</small>
          </div>
        </div>
      </div>
    `;

    initInlineEditing(data);
  }


  function initInlineEditing(initialData = {}) {
    const editableFields = document.querySelectorAll('.editable-field');
    const saveBtn = document.getElementById('saveSettings');
    const updatedData = {};
    const tg = TelegramWebApp.getInstance();

    editableFields.forEach(field => {
      const key = field.dataset.key;
      const initialValue = (initialData[key] || '').trim();

      // Insert error message element right after the field
      const errorEl = document.createElement('div');
      errorEl.className = 'error-message';
      field.insertAdjacentElement('afterend', errorEl);

      if (!field.classList.contains('disabled')) {
        field.addEventListener('input', () => {
          const newValue = field.textContent.trim();

          togglePlaceholder(field);
          clearFieldError(field); // Clear error on input

          if (newValue !== initialValue) {
            updatedData[key] = newValue;
          } else {
            delete updatedData[key];
          }

          saveBtn.classList.toggle('hidden', Object.keys(updatedData).length === 0);
        });

        field.addEventListener('blur', () => {
          togglePlaceholder(field);
        });
      }

      togglePlaceholder(field);
    });

    saveBtn.addEventListener('click', async () => {
      if (Object.keys(updatedData).length === 0) return;

      const errors = validateFields(updatedData);

      // Clear all old errors
      editableFields.forEach(clearFieldError);

      if (Object.keys(errors).length) {
        Object.entries(errors).forEach(([key, message]) => {
          const field = document.querySelector(`.editable-field[data-key="${key}"]`);
          if (field) showFieldError(field, message);
        });
        return;
      }

      if ('address' in updatedData && updatedData.address === '') updatedData.address = null;
      if ('email' in updatedData && updatedData.email === '') updatedData.email = null;

      try {
        const res = await fetch('/api/settings/user/', {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
          },
          body: JSON.stringify(updatedData)
        });

        if (!res.ok) throw new Error('Failed to update profile');

        showAlert('Profile updated successfully!', 'success');
        await TabController.refreshCurrentTab();
        const tgUser = TelegramWebApp.getUser();
        const usernameField = document.querySelector('.editable-field[data-key="username"]');
        if (tgUser?.username && usernameField) {
          usernameField.textContent = tgUser.username;
        }

        Object.keys(updatedData).forEach(key => delete updatedData[key]);
        saveBtn.classList.add('hidden');
      } catch (err) {
        showAlert('Error updating profile. Please try again.', 'error');
        console.error('Profile update failed:', err);
      }
    });

    function togglePlaceholder(field) {
      if (field.textContent.trim() === '') {
        field.classList.add('empty');
      } else {
        field.classList.remove('empty');
      }
    }

    function showFieldError(field, message) {
      field.classList.add('field-error');
      const errorEl = field.nextElementSibling;
      if (errorEl && errorEl.classList.contains('error-message')) {
        errorEl.textContent = message;
        tg?.HapticFeedback.notificationOccurred('error');
      }
    }

    function clearFieldError(field) {
      field.classList.remove('field-error');
      const errorEl = field.nextElementSibling;
      if (errorEl && errorEl.classList.contains('error-message')) {
        errorEl.textContent = '';
      }
    }

    function validateFields(data) {
      const errors = {};

      if ('first_name' in data) {
        const val = data.first_name.trim();
        if (!val) errors.first_name = 'First name is required.';
        else if (val.length < 2 || val.length > 50)
          errors.first_name = 'First name must be 2–50 characters.';
      }

      if ('last_name' in data) {
        const val = data.last_name.trim();
        if (!val) errors.last_name = 'Last name is required.';
        else if (val.length < 2 || val.length > 50)
          errors.last_name = 'Last name must be 2–50 characters.';
      }

      if ('email' in data && data.email.trim()) {
        const val = data.email.trim();
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (!emailRegex.test(val)) errors.email = 'Invalid email address.';
      }

      if ('address' in data && data.address.trim()) {
        const val = data.address.trim();
        if (val.length > 100) errors.address = 'Address cannot exceed 100 characters.';
      }

      return errors;
    }
  }




  // Public API
  return {
    renderDashboard,
    renderChannels,
    renderPayments,
    renderAds,
    renderSettings,
  
  };
})();

/**
 * Tab Controller Module
 */
const TabController = (function() {
  let currentTab = 'dashboardView';

  const tabDataCache = {
    dashboardView: null,
    channelsView: null,
    paymentView: null,
    adsView: null,
    settingsView: null
  };

  async function loadTabData(tabId) {
    try {
      let data;

      switch (tabId) {
        case 'dashboardView':
          data = await ApiService.getDashboardData();
          DataRenderer.renderDashboard(data);
          break;
        case 'channelsView':
          data = await ApiService.getChannels();
          DataRenderer.renderChannels(data);
          break;
        case 'paymentView':
          data = await ApiService.getPaymentData();
          DataRenderer.renderPayments(data);
          break;
        case 'adsView':
          data = await ApiService.getAdsData();
          DataRenderer.renderAds(data);
          break;
        case 'settingsView':
          data = await ApiService.getSettingsData();
          DataRenderer.renderSettings(data);
          break;
      }
      if (tabId !== 'dashboardView') {
        tabDataCache[tabId] = data;
      }
      const loadingIndicator = document.querySelector(`[data-view="${tabId}"] .loading-indicator`);
      if (loadingIndicator) {
        loadingIndicator.classList.add('hidden');
      }

      return data;
    } catch (error) {
      console.warn(`Error: ${error.message} ${error}`);
      showAlert(`Failed to load ${tabId.replace('View', '')} data`, 'error');

      const loadingIndicator = document.querySelector(`[data-view="${tabId}"] .loading-indicator`);
      if (loadingIndicator) {
        loadingIndicator.classList.add('hidden');
      }

      throw error;
    }
  }

  // **New: showView calls ViewManager to update UI**
  function showView(tabId) {
    ViewManager.switchView(tabId);
  }

  async function switchTab(tabId) {
    if (currentTab === tabId && currentTab != 'dashboardView') return;

    currentTab = tabId;

    // Update UI view & active tab button
    showView(tabId);

    const loadingIndicator = document.querySelector(`[data-view="${tabId}"] .loading-indicator`);
    if (loadingIndicator) {
      loadingIndicator.classList.remove('hidden');
    }

    if (!tabDataCache[tabId]) {
      await loadTabData(tabId);
    } else {
      // Re-render cached data
      switch (tabId) {
        case 'dashboardView':
          DataRenderer.renderDashboard(tabDataCache[tabId]);
          break;
        case 'channelsView':
          DataRenderer.renderChannels(tabDataCache[tabId]);
          break;
        case 'paymentView':
          DataRenderer.renderPayments(tabDataCache[tabId]);
          break;
        case 'adsView':
          DataRenderer.renderAds(tabDataCache[tabId]);
          break;
        case 'settingsView':
          DataRenderer.renderSettings(tabDataCache[tabId]);
      }

      if (loadingIndicator) {
        loadingIndicator.classList.add('hidden');
      }
    }
  }

  function init() {
    document.querySelectorAll('.tab').forEach(tab => {
      const tabId = tab.dataset.view;
      const loadingIndicator = document.createElement('div');
      loadingIndicator.className = 'loading-indicator hidden';
      loadingIndicator.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
      tab.appendChild(loadingIndicator);
    });

    switchTab('dashboardView');

    document.querySelectorAll('.tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const targetView = tab.dataset.view;
        switchTab(targetView);
      });
    });
  }

  return {
    init,
    switchTab,
    refreshCurrentTab: () => {
      tabDataCache[currentTab] = null;
      return loadTabData(currentTab);
    }
  };
})();
 
/**
 * Main Initialization
 */
document.addEventListener("DOMContentLoaded", function() {
  // Initialize all modules
  ViewManager.init();
  TelegramWebApp.init();
  BottomSheet.init();
  ChartModule.init();
  PaymentMethod.init();
  ChannelRegistration.init();
  TabController.init();



  const container = document.body;

  window.switchView = function(tabId) {
  
    TabController.switchTab(tabId);
  
  };

  initTooltips();
  // Set up swipe to refresh on the views container
  setupSwipeRefresh({
    container: document.querySelector('.views'),
    onRefresh: async () => {
      try {
        await TabController.refreshCurrentTab(); 
      } catch (error) {
        showAlert("Swipe refresh failed. Please try again.", "error");
      }
    }
  });
  
});

