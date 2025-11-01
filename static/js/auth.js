document.addEventListener("DOMContentLoaded", () => {
  const page = document.querySelector('.hero');
  // === Telegram Setup ===
  const tg = window?.Telegram?.WebApp;
  const user = tg?.initDataUnsafe?.user;
  applyTelegramTheme();

  if (!tg || !user) {

    page?.remove();
    const errorEl = document.createElement('div');
    errorEl.className = `container mt-8`;

    errorEl.innerHTML = `
        <h2 class="text-brand text-center">SonicAdz.</h2>
        <p style="color:#d01277; margin-top:1.5rem;">You are not authorized to access this page.</p>
        <div class="flex flex-row justify-center">
          <a href="https://t.me/sonicAdzBot/" class="mt-4 ">Back to Telegram</a>
        </div>
    `;
    document.querySelector('main').appendChild(errorEl);
    // window.location.href = "/unauthorized/";
    return;
  } 
    document.documentElement.classList.add("in-telegram");
    tg.ready();
    tg.expand();
    tg.enableClosingConfirmation();
    tg.disableVerticalSwipes();

    tg.onEvent("themeChanged", () => applyTelegramTheme(tg.colorScheme));


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

  // Check Telegram version and platform
  if (tg?.platform !== 'unknown' && !tg?.isVersionAtLeast('6.4')) {
    showWarning(`You're on Telegram ${tg?.platform} v${tg?.version}. Please update for full experience.`);
  }



  // === DOM Elements ===
  const phoneSection = document.getElementById('phoneSection');
  const confirmSection = document.getElementById('confirmSection');
  const phoneInput = document.getElementById('phoneInput');
  const continueBtn = document.getElementById('continueBtn');
  const requestContactBtn = document.getElementById('requestContactBtn');
  const confirmForm = document.getElementById('confirmForm');
  const userNameEl = document.getElementById('userName');
  const phoneError = document.getElementById('phoneError');
  const confirmError = document.getElementById('confirmError');

  const firstNameInput = document.getElementById('firstName');
  const lastNameInput = document.getElementById('lastName');
  const emailInput = document.getElementById('email');
  const confirmPhoneInput = document.getElementById('confirmPhone');
  const termsCheckbox = document.getElementById('termsCheckbox');
  const termsError = document.getElementById('termsError');

  const termsUrl = 'https://telegra.ph/SonicAdz-Terms-and-Conditions--Privacy-Policy-08-13';
  const termsLink = document.getElementById('termsLink');

  userNameEl.textContent = `${user?.first_name || ''} ${user?.last_name || ''}`.trim();

  termsLink.addEventListener('click', (e) => {
    e.preventDefault();

    if (window.Telegram?.WebApp?.openLink) {
      // Open in Telegram's internal browser with Instant View (if available)
      Telegram.WebApp.openLink(termsUrl, { try_instant_view: true });
    } else {
      // Fallback for browsers or unsupported clients
      window.open(termsUrl, '_blank');
    }
  });

 
  // === Utility Functions ===
  function formatPhone(phone) {
    const cleaned = phone.replace(/\D/g, '');
    if (cleaned.startsWith('251') && cleaned.length === 12) return `+${cleaned}`;
    if (cleaned.startsWith('0') && cleaned.length === 10) return `+251${cleaned.slice(1)}`;
    return `+${cleaned}`;
  }

  function isValidPhone(phone) {
    return /^(\+251|0)?(9|7)\d{8}$/.test(phone);
  }

  function isValidEmail(email) {
    return !email || /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email);
  }

  function showError(msg) {
    phoneError.textContent = msg;
  }

  function showConfirmError(msg) {
    confirmError.textContent = msg;
  }

  function clearError() {
    phoneError.textContent = '';
    confirmError.textContent = '';
    termsError.textContent = '';
  }

  function showLoader(show) {
    const loader = document.getElementById('loader');
    if (loader) loader.style.display = show ? 'block' : 'none';
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

  function getCSRFToken() {
    const cookie = document.cookie.split("; ").find(row => row.startsWith("csrftoken="));
    return cookie ? cookie.split("=")[1] : "";
  }

  function showWarning(message) {
    document.getElementById('warning').textContent = message;
  }

  // === Request Contact from Telegram ===
  requestContactBtn.addEventListener('click', async () => {
    try {
      requestContactBtn.disabled = true;
      requestContactBtn.innerHTML = '<span class="spinner"></span> Loading...';

      if (!tg?.isVersionAtLeast("6.9")) {
        throw new Error("Update Telegram to version 6.9+ to share contact.");
      }

      const shared = await new Promise((resolve, reject) => {
        tg?.requestContact((success) => resolve(success));
        setTimeout(() => reject("Contact request timed out."), 10000);
      });

      if (!shared) throw new Error("User cancelled contact sharing.");

      const phone = tg?.initDataUnsafe?.user?.phone_number;
      if (!phone) throw new Error("Telegram didn't return phone. Please enter manually.");

      const formatted = formatPhone(phone);
      phoneInput.value = formatted;
      validatePhoneNumber(formatted);
      continueBtn.disabled = false;
      tg?.HapticFeedback?.notificationOccurred("success");

    } catch (err) {
      tg?.HapticFeedback?.notificationOccurred("error");
      showError(err.message.includes("cancelled")
        ? "Please share your phone to continue or enter it manually."
        : err.message
      );
    } finally {
      requestContactBtn.disabled = false;
      requestContactBtn.innerHTML = '<i class="fas fa-phone"></i> Share via Telegram';
      phoneInput.focus();
    }
  });

  // === Phone Input Validation (Debounced) ===
  let validationTimeout;
  phoneInput.addEventListener("input", (e) => {
    clearTimeout(validationTimeout);
    validationTimeout = setTimeout(() => {
      validatePhoneNumber(e.target.value);
    }, 500);
  });

  function validatePhoneNumber(value) {
    const phone = formatPhone(value.trim());
    if (phone.replace(/\D/g, '').length < 10) {
      continueBtn.disabled = true;
      clearError();
      return false;
    }

    const valid = isValidPhone(phone);
    continueBtn.disabled = !valid;

    if (!valid) showError("Valid formats: 0912345678 or +251912345678 or 07**, 2517**");
    else clearError();

    return valid;
  }

  // === Continue to Confirmation Form ===
  continueBtn.addEventListener("click", () => {
    const phone = formatPhone(phoneInput.value.trim());

    if (!validatePhoneNumber(phone)) return;

    confirmPhoneInput.value = phone;
    firstNameInput.value = user?.first_name || '';
    lastNameInput.value = user?.last_name || '';

    phoneSection.style.display = 'none';
    confirmSection.style.display = 'block';

    setTimeout(() => firstNameInput.focus(), 100);
  });

  // === Submit Confirmation Form ===
  confirmForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const firstName = firstNameInput.value.trim();
    const lastName = lastNameInput.value.trim();
    const phone = confirmPhoneInput.value.trim();
    const email = emailInput.value.trim();
    const termsCheckbox = document.getElementById('termsCheckbox');
    const termsError = document.getElementById('termsError');

    clearError();
    if (!firstName) {
      showConfirmError("First name is required");
      firstNameInput.focus();
      return;
    }
    if (!lastName) {
      showConfirmError("Last name is required");
      lastNameInput.focus();
      return;
    }
    if (!isValidPhone(phone)) {
      showConfirmError("Invalid phone number");
      confirmPhoneInput.focus();
      return;
    }

    if (!isValidEmail(email)) {
      showConfirmError("Invalid email address");
      emailInput.focus();
      return;
    }

    if (!termsCheckbox.checked) {
        termsError.textContent = "You must agree to the terms and privacy policy.";
        tg?.HapticFeedback?.notificationOccurred("error");
        return;
      } else {
        termsError.textContent = "";
    }
    

    const payload = {
      init_data: tg?.initData,
      phone_number: phone,
      first_name: firstName,
      last_name: lastName,
      email: email
    };

    try {
      togglePreloader(true);

      const response = await fetch("/api/auth/telegram/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken()
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (response.ok) {
        tg?.HapticFeedback?.notificationOccurred('success');
        window.location.href = data.redirect_url || "/main/";
      } else {
        showConfirmError(data.error || "Authentication failed");
        setTimeout(() => window.location.href = "/", 3000);
      }
    } catch (error) {
      showConfirmError('Network error, Please try again.');
    } finally {
      togglePreloader(false);
    }
  });

});

