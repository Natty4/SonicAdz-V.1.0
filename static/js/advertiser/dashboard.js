document.addEventListener("DOMContentLoaded", () => {
  const API = {
    campaigns: "/api/advertiser/campaigns/",
    campaignSubmit: id => `/api/advertiser/campaigns/${id}/submit/`,
    campaignPause: id => `/api/advertiser/campaigns/${id}/pause/`,
    campaignResume: id => `/api/advertiser/campaigns/${id}/resume/`,
    campaignStop: id => `/api/advertiser/campaigns/${id}/stop/`,
    campaignDetail: id => `/api/advertiser/campaigns/${id}/`,
    balanceSummary: "/api/advertiser/balance/summary/",
    balanceDepositRequest: "/api/payments/deposit/request/",
    balanceDepositConfirm: "/api/payments/deposit/confirm/",
    performance: "/api/advertiser/performance/",
    performanceSummary: "/api/advertiser/performance/summary/",
    performanceByCategory: "/api/advertiser/performance/summary/?group_by=category",
    performanceByLanguage: "/api/advertiser/performance/summary/?group_by=language",
    categories: "/api/categories/",
    languages: "/api/languages/"
  };

  // Chart instances
  let impressionsChart = null, spendChart = null, campaignPerfChart = null, languageChart = null;

  // Global object to hold ad content
  let adContent = null;
  let currentCampaignStatus = null;

  // Pagination, sorting, and filtering state
  let currentPage = 1;
  const itemsPerPage = 10;
  let sortColumn = 'name';
  let sortDirection = 'asc';
  let filterName = '';
  let filterStatus = 'all';

  // Helpers
  function getCookie(name) {
    const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return v ? v.pop() : "";
  }

  async function apiFetch(url, options = {}) {
      const csrftoken = getCookie("csrftoken");
      const headers = { ...options.headers };  

      if (!(options.body instanceof FormData)) {
          headers["Content-Type"] = "application/json";
      }
    

      headers["X-CSRFToken"] = csrftoken;

      try {
          const res = await fetch(url, {
              credentials: "same-origin",
              ...options,
              headers,  
          });

          if (!res.ok) {
              const text = await res.text().catch(() => null);
              throw new Error(text || res.statusText || `HTTP ${res.status}`);
          }

          if (res.status === 204) return null;

          const contentType = res.headers.get("content-type") || "";
          if (contentType.includes("application/json")) return res.json();
          return res.text();
      } catch (err) {
          console.error(`API error for ${url}:`, err);
          throw err;
      }
  }

  function showLoading() { document.getElementById("loading-overlay").classList.add('active'); }
  function hideLoading() { document.getElementById("loading-overlay").classList.remove('active'); }

  function toastError(msg) {
    const errorMessages = {
      "Failed to load languages or categories": "Unable to load language or category options. Please try again.",
      "Failed to submit campaign": "Could not save the campaign. Please check your inputs and try again.",
      "A campaign named": "A campaign with this name already exists for this status. Please choose a different name.",
      "Ad content can only be updated": "Ad content can only be updated for campaigns in DRAFT or STOPPED status.",
      "Failed to fetch campaign": "Unable to load campaign details. Please try again.",
      "Failed to delete": "Could not delete the campaign. Please try again.",
      "Failed to load campaign performance": "Unable to load campaign performance data. Please try again.",
      "Failed to load dashboard": "Unable to load the dashboard data. Please try again.",
      "Failed to update period": "Unable to update the time period. Please try again.",
      "Submit failed": "Could not submit the campaign. Please check your balance or try again.",
      "No eligible channels found for campaign": "No channels match your campaign's budget, CPM, or targeting rules (languages/categories). Please update these settings and try submitting again.",
      "Submit after top-up failed": "Could not submit the campaign after topping up. Please try again.",
      "Top-up failed": "Unable to process the top-up. Please check your payment details and try again.",
      "pause failed": "Could not pause the campaign. Please try again.",
      "resume failed": "Could not resume the campaign. Please try again.",
      "stop failed": "Could not stop the campaign. Please try again.",
      "HTTP 400": "There was an issue with your request. Please check your inputs and try again.",
      "HTTP 401": "Please log in again to continue.",
      "HTTP 403": "You don't have permission to perform this action. Contact support if this is an error.",
      "HTTP 404": "The requested resource was not found. Please try again or contact support.",
      "HTTP 500": "Something went wrong on our end. Please try again later."
    };
    let friendlyMsg = msg;
    for (const [key, value] of Object.entries(errorMessages)) {
      if (msg.includes(key)) {
        friendlyMsg = value;
        break;
      }
    }
    const el = document.createElement("div");
    el.className = "alert alert-error";
    el.textContent = friendlyMsg;
    const container = document.querySelector('.alert-messages');
    container.prepend(el);
    setTimeout(() => el.remove(), 6000);
  }

  function toastSuccess(msg) {
    const el = document.createElement("div");
    el.className = "alert alert-success";
    el.textContent = msg;
    const container = document.querySelector('.alert-messages');
    container.prepend(el);
    setTimeout(() => el.remove(), 6000);
  }

  function showInlineError(fieldId, message) {
    const errorElement = document.getElementById(`${fieldId}-error`);
    if (errorElement) {
      errorElement.textContent = message;
      errorElement.style.display = message ? "block" : "none";
    }
  }

  function clearInlineErrors() {
    const errorElements = document.querySelectorAll(".error-message");
    errorElements.forEach(el => {
      el.textContent = "";
      el.style.display = "none";
    });
  }

  function formatNumber(n) {
    if (n === null || n === undefined) return "-";
    if (typeof n === "number") return n.toLocaleString();
    if (!isNaN(Number(n))) return Number(n).toLocaleString();
    return n;
  }

  function destroyChart(c) { if (c && typeof c.destroy === "function") c.destroy(); }

  function escapeHtml(s) {
    if (s === undefined || s === null) return "";
    return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  }

  function formatDate(dateStr) {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    return isNaN(date) ? "-" : date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  function aggregatePerformanceData(rows) {
    const aggregated = {};
    rows.forEach(r => {
      const date = r.date || "Unknown";
      if (!aggregated[date]) {
        aggregated[date] = { date, impressions: 0, cost: 0, clicks: 0 };
      }
      aggregated[date].impressions += Number(r.impressions || 0);
      aggregated[date].cost += Number(r.cost || 0);
      aggregated[date].clicks += Number(r.clicks || 0);
    });
    return Object.values(aggregated).sort((a, b) => new Date(a.date) - new Date(b.date));
  }

  // Tab Navigation
  function switchTab(tabId) {
    document.querySelectorAll(".nav-tab").forEach(tab => tab.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));
    document.querySelector(`.nav-tab[data-tab="${tabId}"]`).classList.add("active");
    document.getElementById(tabId).classList.add("active");
  }

  document.querySelectorAll(".nav-tab").forEach(tab => {
    tab.addEventListener("click", (e) => {
      e.preventDefault();
      switchTab(tab.dataset.tab);
    });
  });

  let currentStep = 1;
  let showAdFormOnStep2 = false;
  let currentCampaignCpm = null;

  const modal = document.getElementById("campaignModal");
  const openBtn = document.querySelectorAll(".create-campaign-btn");
  const closeBtn = modal?.querySelector(".close-modal");
  const backBtn = document.getElementById("campaignBackBtn");
  const nextBtn = document.getElementById("campaignNextBtn");
  const submitBtn = document.getElementById("campaignSubmitBtn");
  const form = document.getElementById("campaign-form");

  if (openBtn) {openBtn.forEach(btn => {
      btn.addEventListener("click", () => {
        openCreateCampaignModal();
      });
    });
  }
  if (closeBtn) closeBtn.addEventListener("click", () => closeModal("campaignModal"));
  if (backBtn) backBtn.addEventListener("click", () => {
    if (currentStep > 1) {
      currentStep--;
      showStep(currentStep);
    }
  });
  if (nextBtn) nextBtn.addEventListener("click", validateAndGoNext);
  if (submitBtn) submitBtn.addEventListener("click", () => submitCampaign());
  if (form) form.addEventListener("submit", (e) => { e.preventDefault(); submitCampaign(); });

  const addAdBtn = document.getElementById("addAdBtn");
  if (addAdBtn) addAdBtn.addEventListener("click", addAd);

  document.querySelectorAll(".close-modal").forEach(btn => {
    btn.addEventListener("click", () => {
      const modal = btn.closest(".modal");
      if (modal) closeModal(modal.id);
    });
  });


  async function openCreateCampaignModal() {
    resetCampaignForm();
    document.getElementById("campaignModalTitle").textContent = "Create Campaign";
    submitBtn.textContent = "Create Campaign";
    currentCampaignStatus = null;
    showAdFormOnStep2 = true;
    clearInlineErrors();
    await loadLanguagesAndCategories();
    showStep(1);
    openModal("campaignModal");
  }

  async function loadLanguagesAndCategories() {
    try {
      const [langs, cats] = await Promise.all([
        apiFetch("/api/languages/"),
        apiFetch("/api/categories/")
      ]);
      const langContainer = document.getElementById("cs_languages");
      const catContainer = document.getElementById("cs_categories");
      if (langContainer && Array.isArray(langs)) {
        langContainer.innerHTML = "";
        langs.forEach(l => {
          const id = `lang_${l.id}`;
          const wrapper = document.createElement("div");
          wrapper.className = "checkbox-pill-group";
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          checkbox.id = id;
          checkbox.value = l.id;
          checkbox.name = "languages";
          const label = document.createElement("label");
          label.setAttribute("for", id);
          label.textContent = l.name;
          wrapper.appendChild(checkbox);
          wrapper.appendChild(label);
          langContainer.appendChild(wrapper);
        });
      }
      if (catContainer && Array.isArray(cats)) {
        catContainer.innerHTML = "";
        cats.forEach(c => {
          const id = `cat_${c.id}`;
          const wrapper = document.createElement("div");
          wrapper.className = "checkbox-pill-group";
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          checkbox.id = id;
          checkbox.value = c.id;
          checkbox.name = "categories";
          const label = document.createElement("label");
          label.setAttribute("for", id);
          label.textContent = c.name;
          wrapper.appendChild(checkbox);
          wrapper.appendChild(label);
          catContainer.appendChild(wrapper);
        });
      }
    } catch (err) {
      toastError("Failed to load languages or categories: " + err.message);
    }
  }

  function showStep(step) {
    currentStep = step;
    document.querySelectorAll(".campaign-step").forEach(el => el.classList.add("hidden"));
    document.getElementById(`campaignStep${step}`).classList.remove("hidden");
    const isEditMode = form.dataset.campaignId !== "";
    const isEditableStatus = isEditMode && ["draft", "stopped"].includes(currentCampaignStatus);
    backBtn.style.display = step === 1 ? "none" : "inline-block";
    nextBtn.style.display = step === 2 ? "none" : "inline-block";
    submitBtn.style.display = (isEditMode || step === 2) ? "inline-block" : "none";
    if (step === 2 && !isEditMode) {
      submitBtn.disabled = !adContent;
    } else {
      submitBtn.disabled = false;
    }
    document.getElementById("stepLabel").textContent = isEditMode ? "Edit Campaign" : `Step ${step} of 2`;
    if (step === 2) {
      renderAdCard(currentCampaignStatus);
      if (isEditMode && adContent && !showAdFormOnStep2) {
        hideAdForm();
      } else if (isEditableStatus && showAdFormOnStep2) {
        showAdForm();
      } else if (!isEditMode || !adContent) {
        showAdForm();
      } else {
        hideAdForm();
      }
    } else {
      hideAdForm();
    }
  }

  function resetCampaignForm() {
    const f = document.getElementById("campaign-form");
    if (!f) return;
    f.dataset.campaignId = "";
    f.reset();
    adContent = null;
    currentCampaignStatus = null;
    currentCampaignCpm = null;
    showAdFormOnStep2 = false;
    const adList = document.getElementById("ad-cards-list");
    if (adList) adList.innerHTML = "";
    clearInlineErrors();
    showAdForm();
    if (submitBtn) submitBtn.disabled = true;
  }

  function openModal(id) {
    document.body.classList.add('no-scroll');
    const m = document.getElementById(id);
    m?.classList.add("active");
    m?.setAttribute("aria-hidden", "false");
  }

  function closeModal(id) {
    document.body.classList.remove('no-scroll');
    const m = document.getElementById(id);
    m?.classList.remove("active");
    m?.setAttribute("aria-hidden", "true");
    if (id === "campaignModal") resetCampaignForm();
  }

  function isValidUrl(string) {
    try {
      new URL(string);
      return true;
    } catch (_) {
      return false;
    }
  }

  function showAdForm() {
    const adForm = document.querySelector("#campaignStep2 .form-row");
    if (adForm) adForm.style.display = "block";
    const addAdBtn = document.getElementById("addAdBtn");
    if (addAdBtn) addAdBtn.style.display = "inline-block";
  }

  function hideAdForm() {
    const adForm = document.querySelector("#campaignStep2 .form-row");
    if (adForm) adForm.style.display = "none";
    const addAdBtn = document.getElementById("addAdBtn");
    if (addAdBtn) addAdBtn.style.display = "none";
  }

  let socialLinks = [];

  // Add event listener for adding social links
  const platformConfig = {
    X: { template: 'https://x.com/', domains: ['x.com', 'twitter.com'] },
    Instagram: { template: 'https://www.instagram.com/', domains: ['instagram.com'] },
    TikTok: { template: 'https://www.tiktok.com/', domains: ['tiktok.com'] },
    Facebook: { template: 'https://www.facebook.com/', domains: ['facebook.com'] },
    YouTube: { template: 'https://www.youtube.com/', domains: ['youtube.com'] },
    Website: { template: 'https://', domains: [] },
    Other: { template: 'https://', domains: [] }
  };

  // Add event listener for adding social links
  const addSocialLinkBtn = document.getElementById("addSocialLinkBtn");
  if (addSocialLinkBtn) {
    addSocialLinkBtn.addEventListener("click", addSocialLinkField);
  }

  function addSocialLinkField() {
    const container = document.getElementById("social-links-container");
    const linkCount = container.querySelectorAll(".social-link-row:not(:last-child)").length;
    if (linkCount >= 3) {
      showInlineError("social-links", "Maximum of 3 social links allowed.");
      return;
    }
    const newRow = document.createElement("div");
    newRow.className = "social-link-row mb-2";
    newRow.innerHTML = `
      <div class="social-platform-icons">
        <i class="fa-brands fa-x-twitter social-icon" data-platform="X" title="X"></i>
        <i class="fab fa-instagram social-icon" data-platform="Instagram" title="Instagram"></i>
        <i class="fab fa-tiktok social-icon" data-platform="TikTok" title="TikTok"></i>
        <i class="fab fa-facebook social-icon" data-platform="Facebook" title="Facebook"></i>
        <i class="fab fa-youtube social-icon" data-platform="YouTube" title="YouTube"></i>
        <i class="fas fa-globe social-icon" data-platform="Website" title="Website"></i>
        <i class="fas fa-link social-icon" data-platform="Other" title="Other"></i>
        <input type="hidden" class="social-platform" name="social_platform_${linkCount + 1}">
      </div>
      <input type="url" class="social-url" name="social_url_${linkCount + 1}" placeholder="https://...">
      <button type="button" class="remove-social-link btn btn-danger btn-sm"><i class="fas fa-times"></i></button>
    `;
    container.insertBefore(newRow, container.lastElementChild);
    newRow.querySelectorAll(".social-icon").forEach(icon => {
      icon.addEventListener("click", () => {
        const row = icon.closest(".social-link-row");
        const platformInput = row.querySelector(".social-platform");
        const urlInput = row.querySelector(".social-url");
        const currentPlatform = platformInput.value;
        row.querySelectorAll(".social-icon").forEach(i => i.classList.remove("active"));
        row.querySelectorAll(".social-icon").forEach(i => i.classList.add("hidden"));
        if (currentPlatform !== icon.dataset.platform) {
          icon.classList.add("active");
          icon.classList.remove("hidden");
          platformInput.value = icon.dataset.platform;
          if (!urlInput.value || urlInput.value === platformConfig[currentPlatform]?.template) {
            urlInput.value = platformConfig[icon.dataset.platform].template;
          }
        } else {
          platformInput.value = "";
          urlInput.value = "";
          row.querySelectorAll(".social-icon").forEach(i => i.classList.remove("hidden"));
        }
      });
    });
    newRow.querySelector(".remove-social-link").addEventListener("click", () => {
      newRow.remove();
      clearInlineErrors();
    });
  }

 function validateSocialLink(platform, url) {
  if (!platform || !url) return true;
  const config = platformConfig[platform];
  if (!config.domains.length) return true;
  try {
    const parsedUrl = new URL(url);
    const hostname = parsedUrl.hostname.toLowerCase();
    return config.domains.some(domain => hostname === domain || hostname.endsWith('.' + domain));
  } catch {
    return false;
  }
}

function addAd() {
  const headline = document.getElementById("adHeadline").value.trim();
  const text_content = document.getElementById("adText").value.trim();
  const brand_name = document.getElementById("adBrandName").value.trim();
  const img_url = document.getElementById("adImageUrl").value.trim();
  const file = document.getElementById("adFile").files[0];
  
  socialLinks = [];
  const socialRows = document.querySelectorAll("#social-links-container .social-link-row:not(:last-child)");
  socialRows.forEach(row => {
    const platform = row.querySelector(".social-platform").value;
    const url = row.querySelector(".social-url").value.trim();
    if (platform && url) {
      socialLinks.push({ platform, url });
    }
  });

  clearInlineErrors();
  let hasError = false;

  if (!headline) {
    showInlineError("adHeadline", "Please enter a headline for your ad.");
    hasError = true;
  } else if (headline.length > 25) {
    showInlineError("adHeadline", "Headline must be 25 characters or less.");
    hasError = true;
  }
  if (!text_content) {
    showInlineError("adText", "Please enter text content for your ad.");
    hasError = true;
  } else if (text_content.length > 200) {
    showInlineError("adText", "Text content must be 200 characters or less.");
    hasError = true;
  }
  if (!img_url && !file) {
    showInlineError("adImageUrl", "Please provide an image URL or upload a file.");
    hasError = true;
  } else if (img_url && !isValidUrl(img_url)) {
    showInlineError("adImageUrl", "Please enter a valid image or video URL.");
    hasError = true;
  }
  if (brand_name && brand_name.length > 50) {
    showInlineError("adBrandName", "Brand name must be 50 characters or less.");
    hasError = true;
  }
  if (socialLinks.length > 3) {
    showInlineError("social-links", "Maximum of 3 social links allowed.");
    hasError = true;
  }
  socialLinks.forEach((link, index) => {
    if (!link.platform) {
      showInlineError("social-links", `Please select a platform for social link ${index + 1}.`);
      hasError = true;
    }
    if (!isValidUrl(link.url)) {
      showInlineError("social-links", `Invalid URL for ${link.platform}: ${link.url}`);
      hasError = true;
    } else if (!validateSocialLink(link.platform, link.url)) {
      showInlineError("social-links", `URL for ${link.platform} must be from ${platformConfig[link.platform].domains.join(' or ')}`);
      hasError = true;
    }
  });

  if (hasError) return;

  adContent = {
    headline: headline || "",
    text_content: text_content || "",
    brand_name: brand_name || "",
    img_url: file ? "" : (img_url || ""),
    file: file || null,
    social_links: socialLinks
  };

  renderAdCard(currentCampaignStatus);
  hideAdForm();
  document.getElementById("adHeadline").value = "";
  document.getElementById("adText").value = "";
  document.getElementById("adBrandName").value = "";
  document.getElementById("adImageUrl").value = "";
  document.getElementById("adFile").value = "";
  // Manually reset social links without resetting the whole form
  socialLinks = [];
  const socialContainer = document.getElementById("social-links-container");
  if (socialContainer) {
    socialContainer.innerHTML = `
      <div class="social-link-row mb-2" style="justify-content: flex-end;">
        <button type="button" id="addSocialLinkBtn" class="btn btn-outline btn-sm"><i class="fas fa-plus"></i> Add Social Link</button>
      </div>
    `;
    socialContainer.querySelector("#addSocialLinkBtn").addEventListener("click", addSocialLinkField);
  }
  submitBtn.disabled = false;
}

  function renderAdCard(campaignStatus) {
    const list = document.getElementById("ad-cards-list");
    list.innerHTML = "";
    if (!adContent) return;
    const isEditable = ["draft", "stopped"].includes(campaignStatus);
    const imgSrc = adContent.img_url || (adContent.file ? URL.createObjectURL(adContent.file) : "/static/images/placeholder.png");
    const platformIcons = {
      X: 'fa-brands fa-x-twitter',
      Instagram: 'fab fa-instagram',
      TikTok: 'fab fa-tiktok',
      Facebook: 'fab fa-facebook',
      YouTube: 'fab fa-youtube',
      Website: 'fas fa-globe',
      Other: 'fas fa-link'
    };
    let socialLinksHtml = '';
    if (adContent.social_links && adContent.social_links.length) {
      socialLinksHtml = '<div class="social-links-list"><p>Social Links:</p><ul>';
      adContent.social_links.forEach(link => {
        socialLinksHtml += `<li><i class="${platformIcons[link.platform]}"></i> <a href="${escapeHtml(link.url)}" target="_blank">${escapeHtml(link.url)}</a></li>`;
      });
      socialLinksHtml += '</ul></div>';
    }
    const card = document.createElement("div");
    card.className = "ad-card mb-2 p-2 border rounded";
    card.innerHTML = `
      <div class="metric-value" style="max-height: 160px; overflow: hidden;">
        <img id="ad-image-preview" src="${escapeHtml(imgSrc)}" alt="${escapeHtml(adContent.headline)}">
        ${isEditable ? `
          <div class="image-options">
            <input id="ad-image-file" type="file" accept="image/*">
            <input id="ad-image-url" type="url" placeholder="Or paste image URL" value="${escapeHtml(adContent.img_url)}">
            <div id="ad-image-url-error" class="error-message"></div>
          </div>
        ` : ''}
      </div>
      <div class="content p-3">
        ${isEditable ? `
          <div class="editable">
            <h5 class="editable-text">${escapeHtml(adContent.headline)}</h5>
            <input id="ad-headline" class="editable-field" type="text" value="${escapeHtml(adContent.headline)}" maxlength="25" placeholder="Headline">
            <div id="ad-headline-error" class="error-message"></div>
          </div>
          <div class="editable">
            <p class="editable-text">${escapeHtml(adContent.text_content)}</p>
            <textarea id="ad-text" class="editable-field" maxlength="200" placeholder="Ad text">${escapeHtml(adContent.text_content)}</textarea>
            <div id="ad-text-error" class="error-message"></div>
          </div>
          <div class="editable">
            <p class="editable-text">${adContent.brand_name ? `Brand: ${escapeHtml(adContent.brand_name)}` : 'Add brand name'}</p>
            <input id="ad-brand-name" class="editable-field" type="text" value="${escapeHtml(adContent.brand_name)}" maxlength="50" placeholder="Brand name (optional)">
            <div id="ad-brand-name-error" class="error-message"></div>
          </div>
          <div class="editable">
            <p class="editable-text">Social Links:</p>
            <div id="edit-social-links-container">
              ${adContent.social_links && adContent.social_links.length ? adContent.social_links.map((link, index) => `
                <div class="social-link-row mb-2">
                  <div class="social-platform-icons">
                    <i class="fa-brands fa-x-twitter social-icon ${link.platform === 'X' ? 'active' : 'hidden'}" data-platform="X" title="X"></i>
                    <i class="fab fa-instagram social-icon ${link.platform === 'Instagram' ? 'active' : 'hidden'}" data-platform="Instagram" title="Instagram"></i>
                    <i class="fab fa-tiktok social-icon ${link.platform === 'TikTok' ? 'active' : 'hidden'}" data-platform="TikTok" title="TikTok"></i>
                    <i class="fab fa-facebook social-icon ${link.platform === 'Facebook' ? 'active' : 'hidden'}" data-platform="Facebook" title="Facebook"></i>
                    <i class="fab fa-youtube social-icon ${link.platform === 'YouTube' ? 'active' : 'hidden'}" data-platform="YouTube" title="YouTube"></i>
                    <i class="fas fa-globe social-icon ${link.platform === 'Website' ? 'active' : 'hidden'}" data-platform="Website" title="Website"></i>
                    <i class="fas fa-link social-icon ${link.platform === 'Other' ? 'active' : 'hidden'}" data-platform="Other" title="Other"></i>
                    <input type="hidden" class="social-platform" name="social_platform_${index + 1}" value="${link.platform}">
                  </div>
                  <input type="url" class="social-url" name="social_url_${index + 1}" value="${escapeHtml(link.url)}" placeholder="https://...">
                  <button type="button" class="remove-social-link btn btn-danger btn-sm"><i class="fas fa-times"></i></button>
                </div>
              `).join('') : ''}
              <div class="social-link-row mb-2" style="justify-content: flex-end;">
                <button type="button" id="addEditSocialLinkBtn" class="btn btn-outline btn-sm"><i class="fas fa-plus"></i> Add Social Link</button>
              </div>
            </div>
            <div id="social-links-error" class="error-message"></div>
          </div>
          <div class="action-buttons mt-2">
            <button type="button" class="btn btn-primary btn-sm" id="saveAdBtn">Save Ad</button>
            <button type="button" class="btn btn-danger btn-sm" onclick="window.removeAd()">Remove Ad</button>
          </div>
        ` : `
          <h5>${escapeHtml(adContent.headline)}</h5>
          <p>${escapeHtml(adContent.text_content)}</p>
          ${adContent.brand_name ? `<p>Brand: ${escapeHtml(adContent.brand_name)}</p>` : ''}
          ${socialLinksHtml}
        `}
      </div>
    `;
    list.appendChild(card);
    if (isEditable) {
      card.querySelectorAll(".editable").forEach(el => {
        el.addEventListener("click", () => {
          el.classList.toggle("active");
          const input = el.querySelector(".editable-field");
          if (input) input.focus();
        });
      });
      const imageContainer = card.querySelector(".metric-value");
      imageContainer.addEventListener("click", () => {
        imageContainer.classList.toggle("active");
      });
      const updateAdContent = () => {
        const headline = document.getElementById("ad-headline").value.trim();
        const text_content = document.getElementById("ad-text").value.trim();
        const brand_name = document.getElementById("ad-brand-name").value.trim();
        const img_url = document.getElementById("ad-image-url").value.trim();
        const file = document.getElementById("ad-image-file").files[0];
        const socialRows = document.querySelectorAll("#edit-social-links-container .social-link-row:not(:last-child)");
        socialLinks = [];
        socialRows.forEach(row => {
          const platform = row.querySelector(".social-platform").value;
          const url = row.querySelector(".social-url").value.trim();
          if (platform && url) {
            socialLinks.push({ platform, url });
          }
        });
        clearInlineErrors();
        let hasError = false;
        if (!headline) {
          showInlineError("ad-headline", "Please enter a headline.");
          hasError = true;
        } else if (headline.length > 25) {
          showInlineError("ad-headline", "Headline must be 25 characters or less.");
          hasError = true;
        }
        if (!text_content) {
          showInlineError("ad-text", "Please enter ad text.");
          hasError = true;
        } else if (text_content.length > 200) {
          showInlineError("ad-text", "Text must be 200 characters or less.");
          hasError = true;
        }
        if (brand_name && brand_name.length > 50) {
          showInlineError("ad-brand-name", "Brand name must be 50 characters or less.");
          hasError = true;
        }
        if (!img_url && !file && !adContent.img_url && !adContent.file) {
          showInlineError("ad-image-url", "Please provide an image URL or upload a file.");
          hasError = true;
        } else if (img_url && !isValidUrl(img_url)) {
          showInlineError("ad-image-url", "Please enter a valid image URL.");
          hasError = true;
        }
        if (socialLinks.length > 3) {
          showInlineError("social-links", "Maximum of 3 social links allowed.");
          hasError = true;
        }
        socialLinks.forEach((link, index) => {
          if (!link.platform) {
            showInlineError("social-links", `Please select a platform for social link ${index + 1}.`);
            hasError = true;
          }
          if (!isValidUrl(link.url)) {
            showInlineError("social-links", `Invalid URL for ${link.platform}: ${link.url}`);
            hasError = true;
          } else if (!validateSocialLink(link.platform, link.url)) {
            showInlineError("social-links", `URL for ${link.platform} must be from ${platformConfig[link.platform].domains.join(' or ')}`);
            hasError = true;
          }
        });
        if (hasError) return false;
        adContent = {
          headline,
          text_content,
          brand_name,
          img_url: file ? "" : (img_url || adContent.img_url),
          file: file || adContent.file,
          social_links: socialLinks
        };
        const imgPreview = document.getElementById("ad-image-preview");
        if (file) {
          imgPreview.src = URL.createObjectURL(file);
        } else if (img_url) {
          imgPreview.src = img_url;
        }
        return true;
      };
      document.getElementById("ad-headline").addEventListener("input", updateAdContent);
      document.getElementById("ad-text").addEventListener("input", updateAdContent);
      document.getElementById("ad-brand-name").addEventListener("input", updateAdContent);
      document.getElementById("ad-image-url").addEventListener("input", updateAdContent);
      document.getElementById("ad-image-file").addEventListener("change", updateAdContent);
      // Initialize social link icons
      document.querySelectorAll("#edit-social-links-container .social-icon").forEach(icon => {
        icon.addEventListener("click", () => {
          const row = icon.closest(".social-link-row");
          const platformInput = row.querySelector(".social-platform");
          const urlInput = row.querySelector(".social-url");
          const currentPlatform = platformInput.value;
          row.querySelectorAll(".social-icon").forEach(i => i.classList.remove("active"));
          row.querySelectorAll(".social-icon").forEach(i => i.classList.add("hidden"));
          if (currentPlatform !== icon.dataset.platform) {
            icon.classList.add("active");
            icon.classList.remove("hidden");
            platformInput.value = icon.dataset.platform;
            if (!urlInput.value || urlInput.value === platformConfig[currentPlatform]?.template) {
              urlInput.value = platformConfig[icon.dataset.platform].template;
            }
          } else {
            platformInput.value = "";
            urlInput.value = "";
            row.querySelectorAll(".social-icon").forEach(i => i.classList.remove("hidden"));
          }
          updateAdContent();
        });
      });
      document.querySelectorAll("#edit-social-links-container .social-url").forEach(input => {
        input.addEventListener("input", updateAdContent);
      });
      document.querySelectorAll("#edit-social-links-container .remove-social-link").forEach(btn => {
        btn.addEventListener("click", () => {
          btn.closest(".social-link-row").remove();
          updateAdContent();
        });
      });
      // Attach event listener to "Add Social Link" button
      const addEditSocialLinkBtn = document.getElementById("addEditSocialLinkBtn");
      if (addEditSocialLinkBtn) {
        addEditSocialLinkBtn.addEventListener("click", () => {
          const container = document.getElementById("edit-social-links-container");
          const linkCount = container.querySelectorAll(".social-link-row:not(:last-child)").length;
          if (linkCount >= 3) {
            showInlineError("social-links", "Maximum of 3 social links allowed.");
            return;
          }
          const newRow = document.createElement("div");
          newRow.className = "social-link-row mb-2";
          newRow.innerHTML = `
            <div class="social-platform-icons">
              <i class="fa-brands fa-x-twitter social-icon" data-platform="X" title="X"></i>
              <i class="fab fa-instagram social-icon" data-platform="Instagram" title="Instagram"></i>
              <i class="fab fa-tiktok social-icon" data-platform="TikTok" title="TikTok"></i>
              <i class="fab fa-facebook social-icon" data-platform="Facebook" title="Facebook"></i>
              <i class="fab fa-youtube social-icon" data-platform="YouTube" title="YouTube"></i>
              <i class="fas fa-globe social-icon" data-platform="Website" title="Website"></i>
              <i class="fas fa-link social-icon" data-platform="Other" title="Other"></i>
              <input type="hidden" class="social-platform" name="social_platform_${linkCount + 1}">
            </div>
            <input type="url" class="social-url" name="social_url_${linkCount + 1}" placeholder="https://...">
            <button type="button" class="remove-social-link btn btn-danger btn-sm"><i class="fas fa-times"></i></button>
          `;
          container.insertBefore(newRow, container.lastElementChild);
          newRow.querySelectorAll(".social-icon").forEach(icon => {
            icon.addEventListener("click", () => {
              const row = icon.closest(".social-link-row");
              const platformInput = row.querySelector(".social-platform");
              const urlInput = row.querySelector(".social-url");
              const currentPlatform = platformInput.value;
              row.querySelectorAll(".social-icon").forEach(i => i.classList.remove("active"));
              row.querySelectorAll(".social-icon").forEach(i => i.classList.add("hidden"));
              if (currentPlatform !== icon.dataset.platform) {
                icon.classList.add("active");
                icon.classList.remove("hidden");
                platformInput.value = icon.dataset.platform;
                if (!urlInput.value || urlInput.value === platformConfig[currentPlatform]?.template) {
                  urlInput.value = platformConfig[icon.dataset.platform].template;
                }
              } else {
                platformInput.value = "";
                urlInput.value = "";
                row.querySelectorAll(".social-icon").forEach(i => i.classList.remove("hidden"));
              }
              updateAdContent();
            });
          });
          newRow.querySelector(".remove-social-link").addEventListener("click", () => {
            newRow.remove();
            updateAdContent();
          });
          updateAdContent();
        });
      }
      // Attach event listener to "Save Ad" button
      const saveAdBtn = document.getElementById("saveAdBtn");
      if (saveAdBtn) {
        saveAdBtn.addEventListener("click", async () => {
          if (!updateAdContent()) return; // Validation failed
          const campaignId = form.dataset.campaignId;
          if (!campaignId) {
            // For new campaigns, just update adContent and enable submit
            submitBtn.disabled = false;
            toastSuccess("Ad content saved locally! Submit the campaign to save changes.");
            return;
          }
          try {
            showLoading();
            const campaignData = {
              ad_content_write: {
                headline: adContent.headline,
                text_content: adContent.text_content,
                brand_name: adContent.brand_name,
                img_url: adContent.file ? "" : (adContent.img_url || ""),
                social_links: adContent.social_links || []
              }
            };
            if (adContent.file) {
                const formData = new FormData();
                formData.append("ad_content_write[headline]", adContent.headline);
                formData.append("ad_content_write[text_content]", adContent.text_content);
                formData.append("ad_content_write[brand_name]", adContent.brand_name || "");
                formData.append("ad_content_write[img_url]", "");
                (adContent.social_links || []).forEach((link, i) => {
                    formData.append(`ad_content_write[social_links][${i}][platform]`, link.platform);
                    formData.append(`ad_content_write[social_links][${i}][url]`, link.url);
                });
                formData.append("ad_content_write[media_file]", adContent.file);

                await apiFetch(API.campaignDetail(campaignId), {
                    method: "PATCH",
                    body: formData
                });
            } else {
                await apiFetch(API.campaignDetail(campaignId), {
                    method: "PATCH",
                    body: JSON.stringify({
                        ad_content_write: {
                            headline: adContent.headline,
                            text_content: adContent.text_content,
                            brand_name: adContent.brand_name || "",
                            img_url: adContent.img_url || "",
                            social_links: adContent.social_links || []
                        }
                    })
                });
            }
            toastSuccess("Ad content saved successfully!");
            renderAdCard(campaignStatus); // Re-render to update UI
          } catch (err) {
            let msg = err.message;
            try {
              const errorData = JSON.parse(msg);
              if (errorData.ad_content) {
                showInlineError("ad-headline", errorData.ad_content[0]);
              } else if (errorData.detail) {
                toastError(errorData.detail);
              } else {
                toastError("Failed to save ad content: " + msg);
              }
            } catch (e) {
              toastError("Failed to save ad content: " + msg);
            }
          } finally {
            hideLoading();
          }
        });
      }
    }
    if (currentStep === 2 && !form.dataset.campaignId) {
      submitBtn.disabled = !adContent;
    }
  }

  window.removeAd = function() {
    adContent = null;
    renderAdCard(currentCampaignStatus);
    showAdFormOnStep2 = true;
    showAdForm();
    if (currentStep === 2 && !form.dataset.campaignId) {
      submitBtn.disabled = true;
    }
  };

  function validateAndGoNext() {
    clearInlineErrors();
    let hasError = false;
    const name = document.getElementById("campaignName").value.trim();
    if (!name) {
      showInlineError("campaignName", "Please enter a campaign name.");
      hasError = true;
    }
    const initial_budget = parseFloat(document.getElementById("campaignBudget").value);
    if (isNaN(initial_budget) || initial_budget <= 0) {
      showInlineError("campaignBudget", "Please enter a valid budget amount.");
      hasError = true;
    }
    const cpm = parseFloat(document.getElementById("campaignCpm").value);
    if (isNaN(cpm) || cpm <= 0) {
      showInlineError("campaignCpm", "Please enter a valid CPM value.");
      hasError = true;
    }
    const selectedLanguages = Array.from(document.querySelectorAll("#cs_languages input[type=checkbox]:checked")).map(cb => parseInt(cb.value));
    if (!selectedLanguages.length) {
      showInlineError("cs_languages", "Please select at least one language.");
      hasError = true;
    }
    const selectedCategories = Array.from(document.querySelectorAll("#cs_categories input[type=checkbox]:checked")).map(cb => cb.value);
    if (!selectedCategories.length) {
      showInlineError("cs_categories", "Please select at least one category.");
      hasError = true;
    }
    const start_date = document.getElementById("campaignStartDate").value;
    const end_date = document.getElementById("campaignEndDate").value;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    if (end_date) {
      const endDateObj = new Date(end_date);
      if (endDateObj < today) {
        showInlineError("campaignEndDate", "End date must be today or later.");
        hasError = true;
      }
      if (start_date && endDateObj < new Date(start_date)) {
        showInlineError("campaignEndDate", "End date must be on or after start date.");
        hasError = true;
      }
    }
    if (hasError) return;
    if (currentStep < 2) {
      currentStep++;
      showStep(currentStep);
    }
  }

  let isSubmitting = false;
  async function submitCampaign() {
      if (isSubmitting) return;
      isSubmitting = true;
      submitBtn.disabled = true;
      const originalText = submitBtn.innerHTML;
      submitBtn.innerHTML = `
          <div style="display: inline-flex; align-items: center; gap: 8px;">
              <div class="button-spinner"></div>
              ${submitBtn.textContent.includes('Update') ? 'Updating...' : 'Creating...'}
          </div>
      `;
      submitBtn.disabled = true;
      
      clearInlineErrors();
      let hasError = false;

      const name = document.getElementById("campaignName").value.trim();
      if (!name) {
          showInlineError("campaignName", "Please enter a campaign name.");
          hasError = true;
      }
      const objective = document.getElementById("campaignObjective").value;
      if (!objective) {
          showInlineError("campaignObjective", "Please select a campaign objective.");
          hasError = true;
      }
      const initial_budget = parseFloat(document.getElementById("campaignBudget").value);
      if (isNaN(initial_budget) || initial_budget <= 0) {
          showInlineError("campaignBudget", "Please enter a valid budget amount.");
          hasError = true;
      }
      const cpm = parseFloat(document.getElementById("campaignCpm").value);
      if (isNaN(cpm) || cpm <= 0) {
          showInlineError("campaignCpm", "Please enter a valid CPM value.");
          hasError = true;
      }
      const views_frequency_cap = parseInt(document.getElementById("campaignFrequencyCap").value);
      if (isNaN(views_frequency_cap) || views_frequency_cap < 1) {
          showInlineError("campaignFrequencyCap", "Please enter a valid frequency cap.");
          hasError = true;
      }
      const start_date = document.getElementById("campaignStartDate").value;
      const end_date = document.getElementById("campaignEndDate").value;
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      if (end_date) {
          const endDateObj = new Date(end_date);
          if (endDateObj < today) {
              showInlineError("campaignEndDate", "End date must be today or later.");
              hasError = true;
          }
          if (start_date && endDateObj < new Date(start_date)) {
              showInlineError("campaignEndDate", "End date must be on or after start date.");
              hasError = true;
          }
      }
      const selectedLanguages = Array.from(document.querySelectorAll("#cs_languages input[type=checkbox]:checked")).map(cb => parseInt(cb.value));
      if (!selectedLanguages.length) {
          showInlineError("cs_languages", "Please select at least one language.");
          hasError = true;
      }
      const selectedCategories = Array.from(document.querySelectorAll("#cs_categories input[type=checkbox]:checked")).map(cb => cb.value);
      if (!selectedCategories.length) {
          showInlineError("cs_categories", "Please select at least one category.");
          hasError = true;
      }
      if (form.dataset.campaignId === "" && !adContent) {
          showInlineError("ad-headline", "Please add ad content.");
          hasError = true;
      }
      if (currentCampaignCpm !== null && currentCampaignStatus === 'active') {
          const enteredCpm = parseFloat(document.getElementById("campaignCpm").value);
          if (!isNaN(enteredCpm) && enteredCpm < currentCampaignCpm) {
              showInlineError(
                  "campaignCpm",
                  `CPM cannot be lowered on an active campaign (current: ${currentCampaignCpm.toFixed(2)} ETB).`
              );
              hasError = true;
          }
      }
      
      if (hasError) {
          submitBtn.innerHTML = originalText;
          submitBtn.disabled = false;
          isSubmitting = false;
          return;
      }
      
      try {
          showLoading();
          const isUpdate = form.dataset.campaignId !== "";
          const campaignId = form.dataset.campaignId;
          const isEditableStatus = isUpdate && ["draft", "stopped"].includes(currentCampaignStatus);

          const campaignData = {
              name,
              objective,
              initial_budget,
              cpm,
              views_frequency_cap,
              start_date: start_date || null,
              end_date: end_date || null,
              targeting_languages: selectedLanguages,
              targeting_categories: selectedCategories,
              targeting_regions: { "ET": "Ethiopia" }
          };

          if (!isUpdate && adContent) {
              campaignData.ad_content_write = {
                  headline: adContent.headline || "",
                  text_content: adContent.text_content || "",
                  brand_name: adContent.brand_name || "",
                  img_url: adContent.file ? "" : (adContent.img_url || ""),
                  social_links: adContent.social_links || []
              };
          }

          if (isUpdate && isEditableStatus && adContent) {
              campaignData.ad_content_write = {
                  headline: adContent.headline || "",
                  text_content: adContent.text_content || "",
                  brand_name: adContent.brand_name || "",
                  img_url: adContent.file ? "" : (adContent.img_url || ""),
                  social_links: adContent.social_links || []
              };
          }

          if (adContent && adContent.file) {
              const formData = new FormData();

              formData.append("name", name);
              formData.append("objective", objective);
              formData.append("initial_budget", initial_budget);
              formData.append("cpm", cpm);
              formData.append("views_frequency_cap", views_frequency_cap);
              if (start_date) formData.append("start_date", start_date);
              if (end_date) formData.append("end_date", end_date);
              

              selectedLanguages.forEach(lang => formData.append("targeting_languages", lang));
              selectedCategories.forEach(cat => formData.append("targeting_categories", cat));
              formData.append("targeting_regions", JSON.stringify({ "ET": "Ethiopia" }));


              formData.append("ad_content_write.headline", adContent.headline || "");
              formData.append("ad_content_write.text_content", adContent.text_content || "");
              formData.append("ad_content_write.brand_name", adContent.brand_name || "");
              formData.append("ad_content_write.img_url", "");
              
              // Social links
              (adContent.social_links || []).forEach((link, i) => {
                  formData.append(`ad_content_write.social_links.${i}.platform`, link.platform);
                  formData.append(`ad_content_write.social_links.${i}.url`, link.url);
              });
              
              // File
              formData.append("ad_content_write.media_file", adContent.file);

              await apiFetch(isUpdate ? API.campaignDetail(campaignId) : API.campaigns, {
                  method: isUpdate ? "PATCH" : "POST",
                  body: formData
              });
          } else {
              await apiFetch(isUpdate ? API.campaignDetail(campaignId) : API.campaigns, {
                  method: isUpdate ? "PATCH" : "POST",
                  body: JSON.stringify(campaignData)
              });
          }

          toastSuccess(isUpdate ? "Campaign updated successfully!" : "Campaign created successfully!");
          resetCampaignForm();
          closeModal("campaignModal");
          await loadAll();

      } catch (err) {
          let msg = err.message;
          try {
              const errorData = JSON.parse(msg);
              if (errorData.non_field_errors) {
                  showInlineError("campaignName", errorData.non_field_errors[0]);
              } else if (errorData.ad_content) {
                  showInlineError("ad-headline", errorData.ad_content[0]);
              } else if (errorData.detail) {
                  toastError(errorData.detail);
              } else {
                  for (const [field, errors] of Object.entries(errorData)) {
                      showInlineError(field, errors[0]);
                  }
              }
          } catch (e) {
              toastError("Failed to submit campaign: " + msg);
          }
      } finally {
          hideLoading();
          submitBtn.innerHTML = originalText;
          submitBtn.disabled = false;
          isSubmitting = false;
      }
    }

  async function openEditCampaign(id) {
    try {
      showLoading();
      const campaign = await apiFetch(API.campaignDetail(id));
      resetCampaignForm();
      form.dataset.campaignId = id;
      document.getElementById("campaignModalTitle").textContent = "Edit Campaign";
      submitBtn.textContent = "Update";
      currentCampaignStatus = campaign.status;
      currentCampaignCpm = parseFloat(campaign.cpm) || 0;

      document.getElementById("campaignName").value = campaign.name || "";
      document.getElementById("campaignObjective").value = campaign.objective || "";
      document.getElementById("campaignBudget").value = campaign.initial_budget || "";
      document.getElementById("campaignCpm").value = campaign.cpm || "";
      document.getElementById("campaignStartDate").value = campaign.start_date || "";
      document.getElementById("campaignEndDate").value = campaign.end_date || "";
      document.getElementById("campaignFrequencyCap").value = campaign.views_frequency_cap || 1;
      await loadLanguagesAndCategories();
      if (campaign.targeting_languages) {
        campaign.targeting_languages.forEach(lang => {
          const checkbox = document.querySelector(`#cs_languages input[value="${lang}"]`);
          if (checkbox) checkbox.checked = true;
        });
      }
      if (campaign.targeting_categories) {
        campaign.targeting_categories.forEach(cat => {
          const checkbox = document.querySelector(`#cs_categories input[value="${cat}"]`);
          if (checkbox) checkbox.checked = true;
        });
      }
      adContent = campaign.ad_content ? {
        headline: campaign.ad_content.headline,
        text_content: campaign.ad_content.text_content,
        brand_name: campaign.ad_content.brand_name || "",
        img_url: campaign.ad_content.img_url || "",
        social_links: campaign.ad_content.social_links || [],
        file: null
      } : null;
      socialLinks = campaign.ad_content?.social_links || [];
      const socialContainer = document.getElementById("social-links-container");
      if (socialContainer && socialLinks.length > 0) {
        socialContainer.innerHTML = "";
        socialLinks.forEach((link, index) => {
          const row = document.createElement("div");
          row.className = "social-link-row mb-2";
          row.innerHTML = `
            <div class="social-platform-icons">
              <i class="fa-brands fa-x-twitter social-icon ${link.platform === 'X' ? 'active' : 'hidden'}" data-platform="X" title="X"></i>
              <i class="fab fa-instagram social-icon ${link.platform === 'Instagram' ? 'active' : 'hidden'}" data-platform="Instagram" title="Instagram"></i>
              <i class="fab fa-tiktok social-icon ${link.platform === 'TikTok' ? 'active' : 'hidden'}" data-platform="TikTok" title="TikTok"></i>
              <i class="fab fa-facebook social-icon ${link.platform === 'Facebook' ? 'active' : 'hidden'}" data-platform="Facebook" title="Facebook"></i>
              <i class="fab fa-youtube social-icon ${link.platform === 'YouTube' ? 'active' : 'hidden'}" data-platform="YouTube" title="YouTube"></i>
              <i class="fas fa-globe social-icon ${link.platform === 'Website' ? 'active' : 'hidden'}" data-platform="Website" title="Website"></i>
              <i class="fas fa-link social-icon ${link.platform === 'Other' ? 'active' : 'hidden'}" data-platform="Other" title="Other"></i>
              <input type="hidden" class="social-platform" name="social_platform_${index + 1}" value="${link.platform}">
            </div>
            <input type="url" class="social-url" name="social_url_${index + 1}" value="${escapeHtml(link.url)}" placeholder="https://...">
            <button type="button" class="remove-social-link btn btn-danger btn-sm"><i class="fas fa-times"></i></button>
          `;
          socialContainer.appendChild(row);
          row.querySelectorAll(".social-icon").forEach(icon => {
            icon.addEventListener("click", () => {
              const row = icon.closest(".social-link-row");
              const platformInput = row.querySelector(".social-platform");
              const urlInput = row.querySelector(".social-url");
              const currentPlatform = platformInput.value;
              row.querySelectorAll(".social-icon").forEach(i => i.classList.remove("active"));
              row.querySelectorAll(".social-icon").forEach(i => i.classList.add("hidden"));
              if (currentPlatform !== icon.dataset.platform) {
                icon.classList.add("active");
                icon.classList.remove("hidden");
                platformInput.value = icon.dataset.platform;
                if (!urlInput.value || urlInput.value === platformConfig[currentPlatform]?.template) {
                  urlInput.value = platformConfig[icon.dataset.platform].template;
                }
              } else {
                platformInput.value = "";
                urlInput.value = "";
                row.querySelectorAll(".social-icon").forEach(i => i.classList.remove("hidden"));
              }
            });
          });
          row.querySelector(".remove-social-link").addEventListener("click", () => {
            row.remove();
            clearInlineErrors();
          });
        });
      }
      const addButtonRow = document.createElement("div");
      addButtonRow.className = "social-link-row mb-2";
      addButtonRow.style.justifyContent = "flex-end";
      addButtonRow.innerHTML = `
        <button type="button" id="addSocialLinkBtn" class="btn btn-outline btn-sm"><i class="fas fa-plus"></i> Add Social Link</button>
      `;
      socialContainer.appendChild(addButtonRow);
      addButtonRow.querySelector("#addSocialLinkBtn").addEventListener("click", addSocialLinkField);
      clearInlineErrors();
      showStep(1);
      openModal("campaignModal");
  } catch (err) {
    toastError("Failed to fetch campaign: " + err.message);
  } finally {
    hideLoading();
  }
}

  // Initialize social link icons on page load
  document.querySelectorAll("#social-links-container .social-icon").forEach(icon => {
    icon.addEventListener("click", () => {
      const row = icon.closest(".social-link-row");
      const platformInput = row.querySelector(".social-platform");
      const urlInput = row.querySelector(".social-url");
      const currentPlatform = platformInput.value;
      row.querySelectorAll(".social-icon").forEach(i => i.classList.remove("active"));
      row.querySelectorAll(".social-icon").forEach(i => i.classList.add("hidden"));
      if (currentPlatform !== icon.dataset.platform) {
        icon.classList.add("active");
        icon.classList.remove("hidden");
        platformInput.value = icon.dataset.platform;
        if (!urlInput.value || urlInput.value === platformConfig[currentPlatform]?.template) {
          urlInput.value = platformConfig[icon.dataset.platform].template;
        }
      } else {
        platformInput.value = "";
        urlInput.value = "";
        row.querySelectorAll(".social-icon").forEach(i => i.classList.remove("hidden"));
      }
    });
  });

  document.getElementById("campaignCpm").addEventListener("input", function () {
    if (currentCampaignStatus !== 'active' || currentCampaignCpm === null || currentCampaignCpm <= 0) return;

    const val = parseFloat(this.value);
    const hint = this.parentElement.querySelector(".cpm-hint");
    if (hint) hint.remove();

    if (!isNaN(val) && val < currentCampaignCpm) {
        const el = document.createElement("small");
        el.className = "text-danger cpm-hint";
        el.textContent = `Cannot go below ${currentCampaignCpm.toFixed(2)} ETB for active campaigns`;
        this.after(el);
    }
});

  async function deleteCampaign(campaignId, campaignName) {
    try {
      showLoading();
      await apiFetch(API.campaignDetail(campaignId), { method: "DELETE" });
      toastSuccess("Campaign deleted successfully!");
      await loadAll();
    } catch (err) {
      toastError("Failed to delete: " + err.message);
    } finally {
      hideLoading();
    }
  }

  function openDeleteConfirmModal(campaignId, campaignName) {
    const modal = document.getElementById("deleteConfirmModal");
    const title = document.getElementById("deleteConfirmTitle");
    const confirmBtn = document.getElementById("deleteConfirmBtn");
    title.textContent = `Delete Campaign: ${escapeHtml(campaignName)}`;
    openModal("deleteConfirmModal");
    const onConfirm = async () => {
      try {
        await deleteCampaign(campaignId, campaignName);
        closeModal("deleteConfirmModal");
      } finally {
        confirmBtn.removeEventListener("click", onConfirm);
      }
    };
    confirmBtn.addEventListener("click", onConfirm);
  }

  async function actionCampaign(id, action) {
    const mapping = { pause: API.campaignPause(id), resume: API.campaignResume(id), stop: API.campaignStop(id) };
    try {
      showLoading();
      await apiFetch(mapping[action], { method: "POST" });
      await loadAll();
      toastSuccess(`Campaign ${action}d successfully!`);
    } catch (err) {
      toastError(`${action} failed: ${err.message}`);
    } finally {
      hideLoading();
    }
  }

  async function submitCampaignById(id) {
    try {
      showLoading();
      const campaign = await apiFetch(API.campaignDetail(id));
      await submitWithBalanceCheck(campaign);
    } catch (err) {
      let msg = err.message;
      try {
        const errorData = JSON.parse(msg);
        if (errorData.error && errorData.error.includes("No eligible channels found for campaign")) {
          toastError("No eligible channels found for campaign");
        } else {
          toastError("Submit failed: " + msg);
        }
      } catch (e) {
        toastError("Submit failed: " + msg);
      }
    } finally {
      hideLoading();
    }
  }

  async function submitWithBalanceCheck(campaign) {
    try {
      showLoading();
      const bal = await apiFetch(API.balanceSummary);
      const available = Number(bal.available_balance || bal.available || 0);
      const needed = Number(campaign.initial_budget || 0);
      if (available < needed) {
        openTopupModal(needed - available, async (depositedAmount = 0) => {
          try {
            showLoading();
            await apiFetch(API.campaignSubmit(campaign.id), { method: "POST" });
            await loadAll();
            closeModal("topupModal");
            closeModal("performanceModal");
            toastSuccess("Campaign submitted for review successfully!");
          } catch (err) {
            let msg = err.message;
            try {
              const errorData = JSON.parse(msg);
              if (errorData.error && errorData.error.includes("No eligible channels found for campaign")) {
                toastError("No eligible channels found for campaign");
              } else {
                toastError("Submit after top-up failed: " + msg);
              }
            } catch (e) {
              toastError("Submit after top-up failed: " + msg);
            }
          } finally {
            hideLoading();
          }
        });
        return;
      }
      await apiFetch(API.campaignSubmit(campaign.id), { method: "POST" });
      await loadAll();
      closeModal("performanceModal");
      toastSuccess("Campaign submitted for review successfully!");
    } catch (err) {
      let msg = err.message;
      try {
        const errorData = JSON.parse(msg);
        if (errorData.error && errorData.error.includes("No eligible channels found for campaign")) {
          toastError("No eligible channels found for campaign");
        } else {
          toastError("Submit failed: " + msg);
        }
      } catch (e) {
        toastError("Submit failed: " + msg);
      }
    } finally {
      hideLoading();
    }
  }

  async function openPerformanceModal(campaignId) {
    try {
      showLoading();
      const campaign = await apiFetch(API.campaignDetail(campaignId));
      const params = new URLSearchParams({ 'ad_placement__ad__campaign': campaignId });
      const perfRows = await apiFetch(API.performance + "?" + params.toString());
      const rows = Array.isArray(perfRows) ? perfRows : [];
      let totalSpend = 0, totalImpr = 0, totalClicks = 0;
      if (campaign.status === "draft" || !rows.length) {
        document.getElementById("perf-spend").textContent = "-";
        document.getElementById("perf-impr").textContent = "-";
        document.getElementById("perf-clicks").textContent = "-";
        document.getElementById("perf-ctr").textContent = "-";
      } else {
        rows.forEach(r => {
          totalSpend += Number(r.cost || 0);
          totalImpr += Number(r.impressions || 0);
          totalClicks += Number(r.clicks || 0);
        });
        const ctr = totalImpr ? (totalClicks / totalImpr * 100) : 0;
        document.getElementById("perf-spend").textContent = totalSpend ? formatNumber(totalSpend.toFixed(2)) : "-";
        document.getElementById("perf-impr").textContent = totalImpr ? formatNumber(totalImpr) : "-";
        document.getElementById("perf-clicks").textContent = totalClicks ? formatNumber(totalClicks) : "-";
        document.getElementById("perf-ctr").textContent = ctr ? ctr.toFixed(2) + "%" : "-";
      }
      const labels = rows.length ? rows.map(r => formatDate(r.date)) : ["No Data"];
      const impressions = rows.length ? rows.map(r => r.impressions || 0) : [0];
      destroyChart(campaignPerfChart);
      const ctx = document.getElementById("campaignPerfChart").getContext("2d");
      campaignPerfChart = new Chart(ctx, {
        type: "line",
        data: {
          labels,
          datasets: [{
            label: "Impressions",
            data: impressions,
            borderColor: "rgba(29,155,240,1)",
            fill: true,
            tension: 0.2,
            pointRadius: 3,
            backgroundColor: ctx => {
              const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, ctx.chart.height);
              g.addColorStop(0, 'rgba(29,155,240,0.2)');
              g.addColorStop(1, 'rgba(29,155,240,0)');
              return g;
            }
          }]
        },
        options: {
          responsive: true,
          scales: {
            y: { beginAtZero: true },
            x: { display: rows.length > 0 }
          },
          plugins: {
            legend: { display: rows.length > 0 },
            tooltip: { enabled: rows.length > 0 },
            title: {
              display: !rows.length || campaign.status === "draft",
              text: campaign.status === "draft" ? "No performance data this campaign" : "No performance data available",
              color: "#666",
              padding: 20
            }
          }
        }
      });
      const previewContainer = document.getElementById("perf-ad-preview");
      previewContainer.innerHTML = "";
      let adPreviewContent = "";
      if (campaign.ad_content) {
        const ad = campaign.ad_content;
        const imgSrc = ad.img_url || "https://res.cloudinary.com/dyhszaw1f/image/upload/v1757692592/sonicadz_channels_pp/channel_sonicads.jpg";
        // Generate social links display (platform names only, e.g., "X | Instagram | TikTok")
        const socialLinksDisplay = ad.social_links && ad.social_links.length
          ? ad.social_links.map(link => escapeHtml(link.platform)).join(" | ")
          : "";
        adPreviewContent = `
          <div class="card p-0">
            <span style="width:100%;" class="metric-change status-badge ${escapeHtml(campaign.status)}">${escapeHtml(campaign.status)}</span>
            <div class="metric-value">
              <img src="${escapeHtml(imgSrc)}" alt="${escapeHtml(ad.headline)}" class="prev-ad-img">
            </div>
            <div class="content p-3">
              <div class="metric-label"><strong>${escapeHtml(ad.headline)}</strong></div>
              <div class="metric-label">${escapeHtml(ad.text_content).slice(0, 60)}${escapeHtml(ad.text_content).length > 60 ? '...' : ''}</div>
              ${ad.brand_name ? `<div class="metric-label">${escapeHtml(ad.brand_name)}</div>` : ''}
              ${socialLinksDisplay ? `<div class="metric-label social-links">${socialLinksDisplay}</div>` : ''}
            </div>
          </div>
        `;
      } else {
        adPreviewContent = `
          <div class="card p-3 text-center">
            <i class="fas fa-image fa-3x text-muted"></i>
            <p>No ad content available for this campaign.</p>
            <p>
              <button type="button" class="btn btn-outline btn-sm mt-1" onclick="window.__dashboard.closeModal('performanceModal'); window.__dashboard.openEditCampaign('${escapeHtml(campaignId)}')">
                Add Ad content now <i class="fas fa-arrow-right"></i>
              </button>
            </p>
          </div>
        `;
      }
      const createIconBtn = (iconClass, title, onClick) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "action-btn btn btn-outline btn-sm mt-1";
        btn.title = title;
        const i = document.createElement("i");
        i.className = iconClass;
        btn.appendChild(i);
        btn.addEventListener("click", () => {
          onClick();
        });
        return btn;
      };
      const actionButtonsContainer = document.createElement("div");
      actionButtonsContainer.className = "action-buttons mt-2";
      if (campaign.status === "active") {
        actionButtonsContainer.appendChild(createIconBtn(
          "fas fa-edit",
          `Edit Campaign - ${escapeHtml(campaign.name)}`,
          () => {
            closeModal("performanceModal");
            openEditCampaign(campaignId);
          }
        ));
      } else if (campaign.status === "on_hold") {
        actionButtonsContainer.appendChild(createIconBtn(
          "fas fa-play text-success",
          `Resume Campaign - ${escapeHtml(campaign.name)}`,
          () => actionCampaign(campaignId, "resume")
        ));
        actionButtonsContainer.appendChild(createIconBtn(
          "fas fa-edit",
          `Edit Campaign - ${escapeHtml(campaign.name)}`,
          () => {
            closeModal("performanceModal");
            openEditCampaign(campaignId);
          }
        ));
      } else if (campaign.status === "draft") {
        actionButtonsContainer.appendChild(createIconBtn(
          "fas fa-paper-plane",
          `Submit Campaign - ${escapeHtml(campaign.name)}`,
          () => submitCampaignById(campaignId)
        ));
        actionButtonsContainer.appendChild(createIconBtn(
          "fas fa-edit",
          `Edit Campaign - ${escapeHtml(campaign.name)}`,
          () => {
            closeModal("performanceModal");
            openEditCampaign(campaignId);
          }
        ));
        actionButtonsContainer.appendChild(createIconBtn(
          "fas fa-trash",
          `Delete Campaign - ${escapeHtml(campaign.name)}`,
          () => {
            closeModal("performanceModal");
            openDeleteConfirmModal(campaignId, campaign.name);
          }
        ));
      } else if (["declined", "stopped"].includes(campaign.status)) {
        actionButtonsContainer.appendChild(createIconBtn(
          "fas fa-edit",
          `Edit Campaign - ${escapeHtml(campaign.name)}`,
          () => {
            closeModal("performanceModal");
            openEditCampaign(campaignId);
          }
        ));
        actionButtonsContainer.appendChild(createIconBtn(
          "fas fa-trash",
          `Delete Campaign - ${escapeHtml(campaign.name)}`,
          () => {
            closeModal("performanceModal");
            openDeleteConfirmModal(campaignId, campaign.name);
          }
        ));
      } else if (["scheduled", "in_review"].includes(campaign.status)) {
        actionButtonsContainer.appendChild(createIconBtn(
          "fas fa-trash",
          `Delete Campaign - ${escapeHtml(campaign.name)}`,
          () => {
            closeModal("performanceModal");
            openDeleteConfirmModal(campaignId, campaign.name);
          }
        ));
      } else if (campaign.status === "completed") {
        actionButtonsContainer.appendChild(createIconBtn(
          "fas fa-trash",
          `Delete Campaign - ${escapeHtml(campaign.name)}`,
          () => {
            closeModal("performanceModal");
            openDeleteConfirmModal(campaignId, campaign.name);
          }
        ));
        actionButtonsContainer.appendChild(createIconBtn(
          "fas fa-edit",
          `Edit Campaign - ${escapeHtml(campaign.name)}`,
          () => {
            closeModal("performanceModal");
            openEditCampaign(campaignId);
          }
        ));
        actionButtonsContainer.appendChild(createIconBtn(
          "fas fa-redo",
          `Restart Campaign - ${escapeHtml(campaign.name)}`,
          () => {
            closeModal("performanceModal");
            openEditCampaign(campaignId);
          }
        ));
      }
      previewContainer.innerHTML = adPreviewContent;
      previewContainer.appendChild(actionButtonsContainer);
      openModal("performanceModal");
    } catch (err) {
      console.error("Error loading campaign performance:", err);
      toastError("Failed to load campaign performance: " + err.message);
    } finally {
      hideLoading();
    }
  }


  function openTopupModal(shortfall, afterTopupCallback) {
    const modal = document.getElementById("topupModal");
    openModal("topupModal");
    document.getElementById("topup-amount-input").value = Number(shortfall).toFixed(2);
    document.getElementById("topup-step-1").style.display = "block";
    document.getElementById("topup-step-2").style.display = "none";

    let topupAmount = 0;
    let topupReference = "";
    let mobile = "";
    let paymentType = "telebirr";

    const mobileInput = document.getElementById("mobile-input");
    const proceedBtn = document.getElementById("generate-payment-btn");
    const confirmBtn = document.getElementById("confirm-payment-btn");
    const amountInput = document.getElementById("topup-amount-input");
    const methodRadios = document.querySelectorAll('input[name="payment_type"]');
    const paymentLogo = document.getElementById("payment-logo");
    const paymentDetails = document.getElementById("payment-details");
    const paymentInstruction = document.getElementById("payment-instruction");
    const loadingOverlay = document.getElementById("loading-overlay");
    const buttonSpinner = confirmBtn.querySelector(".button-spinner");
    const proceedSpinner = proceedBtn.querySelector(".button-spinner");

    // Payment method logos
    const paymentLogos = {
      telebirr: "https://upload.wikimedia.org/wikipedia/en/a/a4/Telebirr.png",
      mpesa: "https://upload.wikimedia.org/wikipedia/commons/0/0b/M-PESA.png",
      cbebirr: "https://play-lh.googleusercontent.com/rcSKabjkP2GfX1_I_VXBfhQIPdn_HPXj5kbkDoL4cu5lpvcqPsGmCqfqxaRrSI9h5_A",
      ebirr: "https://coopbankoromia.com.et/wp-content/uploads/2021/04/coopay-ebirr-scaled.jpg"
    };

    // Method-specific instructions
    const methodInstructions = {
      telebirr: "Open your Telebirr app or check your phone for a USSD prompt to authorize your payment.",
      mpesa: "Check your M-Pesa app or phone for a USSD prompt to confirm the payment.",
      cbebirr: "Open your CBE Birr app or follow the USSD prompt on your phone to complete the payment.",
      ebirr: "Use your Coopay E-Birr app or respond to the USSD prompt to authorize your payment."
    };

    function updatePlaceholder() {
      paymentType = document.querySelector('input[name="payment_type"]:checked')?.value || "telebirr";
      if (paymentType === "mpesa") {
        mobileInput.placeholder = "e.g., 07xxxxxxxx or +2547xxxxxxxx";
      } else {
        mobileInput.placeholder = "e.g., 09xxxxxxxx or +2519xxxxxxxx";
      }
    }

    function checkFormValidity() {
      topupAmount = Number(amountInput.value);
      mobile = mobileInput.value.trim();
      paymentType = document.querySelector('input[name="payment_type"]:checked')?.value || "telebirr";
      
      const ethiopianRegex = /^(09\d{8}|07\d{8}|\+251[97]\d{8})$/;
      const mpesaRegex = /^(07\d{8}|01\d{8}|\+254[71]\d{8})$/;
      const isValidPhone = paymentType === "mpesa" ? mpesaRegex.test(mobile) : ethiopianRegex.test(mobile);
      const isValid = topupAmount >= 1 && isValidPhone && paymentType;
      
      proceedBtn.disabled = !isValid;
      proceedBtn.setAttribute("aria-disabled", !isValid ? "true" : "false");
      proceedBtn.classList.toggle('disabled', !isValid);
    }

    // Update payment method visual state
    function updatePaymentMethodStyles() {
      document.querySelectorAll('.method-option').forEach(label => {
        const input = label.querySelector('input');
        label.setAttribute('aria-checked', input.checked);
        if (input.checked) {
          label.classList.add('selected');
        } else {
          label.classList.remove('selected');
        }
      });
    }

    updatePlaceholder();
    amountInput.addEventListener('input', checkFormValidity);
    mobileInput.addEventListener('input', checkFormValidity);
    methodRadios.forEach(radio => {
      radio.addEventListener('change', () => {
        updatePlaceholder();
        checkFormValidity();
        updatePaymentMethodStyles();
      });
    });
    checkFormValidity();
    updatePaymentMethodStyles();

    async function pollPaymentStatus(tx_ref, maxAttempts = 10, interval = 5000) {
      let attempts = 0;
      loadingOverlay.style.display = "flex";
      confirmBtn.disabled = true;
      confirmBtn.setAttribute("aria-disabled", "true");
      confirmBtn.classList.add("disabled");
      buttonSpinner.style.display = "inline-block";

      while (attempts < maxAttempts) {
        try {
          const res = await apiFetch(`/api/payments/deposit/status/${tx_ref}/`, {
            method: "GET",
            query: { amount: topupAmount }
          });
          if (res.status === 'success') {
            loadingOverlay.style.display = "none";
            confirmBtn.disabled = false;
            confirmBtn.setAttribute("aria-disabled", "false");
            confirmBtn.classList.remove("disabled");
            buttonSpinner.style.display = "none";
            confirmBtn.querySelector('.btn-text').textContent = "View Balance";
            if (res.credited) {
              toastSuccess(res.message);
            } else {
              toastError("Payment was successful, but balance update failed. Please contact support.");
            }
            return;
          } else if (res.status === 'failed') {
            loadingOverlay.style.display = "none";
            confirmBtn.disabled = false;
            confirmBtn.setAttribute("aria-disabled", "false");
            confirmBtn.classList.remove("disabled");
            buttonSpinner.style.display = "none";
            confirmBtn.querySelector('.btn-text').textContent = "View Balance";
            toastError("Payment failed. Please try again or contact support.");
            return;
          }
          await new Promise(resolve => setTimeout(resolve, interval));
          attempts++;
        } catch (err) {
          loadingOverlay.style.display = "none";
          confirmBtn.disabled = false;
          confirmBtn.setAttribute("aria-disabled", "false");
          confirmBtn.classList.remove("disabled");
          buttonSpinner.style.display = "none";
          confirmBtn.querySelector('.btn-text').textContent = "View Balance";
          toastError("Unable to check payment status. Please check your balance or contact support.");
          return;
        }
      }
      loadingOverlay.style.display = "none";
      confirmBtn.disabled = false;
      confirmBtn.setAttribute("aria-disabled", "false");
      confirmBtn.classList.remove("disabled");
      buttonSpinner.style.display = "none";
      confirmBtn.querySelector('.btn-text').textContent = "View Balance";
      toastError("Payment is taking longer than expected. Please complete the USSD prompt or check your balance.");
    }

    proceedBtn.onclick = async () => {
      if (!topupAmount || topupAmount < 1) {
        toastError("Please enter an amount greater than zero.");
        return;
      }
      const ethiopianRegex = /^(09\d{8}|07\d{8}|\+251[97]\d{8})$/;
      const mpesaRegex = /^(07\d{8}|01\d{8}|\+254[71]\d{8})$/;
      if (paymentType === "mpesa" && !mpesaRegex.test(mobile)) {
        toastError("Please enter a valid mobile number (e.g., 07xxxxxxxx or +2547xxxxxxxx).");
        return;
      } else if (!ethiopianRegex.test(mobile)) {
        toastError("Please enter a valid mobile number (e.g., 09xxxxxxxx or +2519xxxxxxxx).");
        return;
      }

      try {
        proceedBtn.disabled = true;
        proceedBtn.setAttribute("aria-disabled", "true");
        proceedBtn.setAttribute("aria-busy", "true");
        proceedSpinner.style.display = "inline-block";
        proceedBtn.querySelector('.btn-text').textContent = "Processing...";

        showLoading();
        const res = await apiFetch(API.balanceDepositRequest, {
          method: "POST",
          body: JSON.stringify({ amount: topupAmount, mobile, payment_type: paymentType })
        });

        topupReference = res.reference;

        paymentLogo.src = paymentLogos[paymentType];
        paymentLogo.alt = `${paymentType.charAt(0).toUpperCase() + paymentType.slice(1)} Logo`;
        paymentDetails.textContent = `Amount: ETB ${topupAmount.toFixed(2)} | Reference: ${topupReference}`;
        paymentInstruction.textContent = res.instruction || methodInstructions[paymentType];

        document.getElementById("topup-step-1").style.display = "none";
        document.getElementById("topup-step-2").style.display = "block";

        pollPaymentStatus(topupReference); // Fixed typo: toupupReference -> topupReference
      } catch (err) {
        toastError(err.message || "Sorry, we couldn't start your payment. Please check your details and try again.");
      } finally {
        proceedBtn.disabled = false;
        proceedBtn.setAttribute("aria-disabled", "false");
        proceedBtn.setAttribute("aria-busy", "false");
        proceedSpinner.style.display = "none";
        proceedBtn.querySelector('.btn-text').textContent = "Proceed to Payment";
        hideLoading();
      }
    };

    confirmBtn.onclick = async () => {
      try {
        showLoading();
        buttonSpinner.style.display = "inline-block";
        confirmBtn.disabled = true;
        confirmBtn.setAttribute("aria-disabled", "true");
        confirmBtn.setAttribute("aria-busy", "true");
        confirmBtn.querySelector('.btn-text').textContent = "Fetching Balance...";

        const res = await apiFetch(API.balanceSummary, {
          method: "GET"
        });

        toastSuccess(`Your current balance is ETB ${Number(res.available).toFixed(2)}.`);
        closeModal("topupModal");
        if (typeof afterTopupCallback === "function") {
          afterTopupCallback(topupAmount);
        }
      } catch (err) {
        toastError(err.message || "We couldn't fetch your balance. Please try again or contact support.");
      } finally {
        hideLoading();
        buttonSpinner.style.display = "none";
        confirmBtn.disabled = false;
        confirmBtn.setAttribute("aria-disabled", "false");
        confirmBtn.setAttribute("aria-busy", "false");
        confirmBtn.querySelector('.btn-text').textContent = "View Balance";
      }
    };
  }

  
  
  const chartColors = [
    '#1D9BF0', '#2EC4B6', '#FF6B6B', '#FFD166', '#06D6A0', '#8338EC',
    '#3A86FF', '#EF476F', '#118AB2', '#073B4C'
  ];

  async function loadAll() {
    try {
      showLoading();
      const [summary, perf, campaigns, categoryPerf, languagePerf, balance, languages] = await Promise.all([
        apiFetch(API.performanceSummary + "?period=last30").catch(() => ({})),
        apiFetch(API.performance + "?start_date=&end_date=").catch(() => []),
        apiFetch(API.campaigns).catch(() => []),
        apiFetch(API.performanceByCategory).catch(() => []),
        apiFetch(API.performanceByLanguage).catch(() => []),
        apiFetch(API.balanceSummary).catch(() => ({})),
        apiFetch(API.languages).catch(() => [])
      ]);
      renderTopSummary(summary || {});
      const perfRows = Array.isArray(perf) ? perf : (perf.data || []);
      
      renderCampaignsTable(campaigns.results || [], true);
      renderCampaignsTable(campaigns.results || [], false);
      if (summary.active_campaign_count){
        renderChartsFromPerf(perfRows || []);
        renderCategoryPerformance(categoryPerf || []);
        renderLanguagePerformance(languagePerf || [], languages || []);
      }
      
      renderBillingInfo(balance || {});
    } catch (err) {
      toastError("Failed to load dashboard: " + err.message);
    } finally {
      hideLoading();
    }
  }

  function renderTopSummary(summary) {
    try {
      document.querySelector(".metric-value[data-metric='ads']").textContent = formatNumber(summary.active_campaign_count || 0);
      document.querySelector(".metric-value[data-metric='spend']").textContent = formatNumber(summary.total_cost || summary.total_spent || 0);
      document.querySelector(".metric-value[data-metric='impressions']").textContent = formatNumber(summary.total_impressions || 0);
      document.querySelector(".metric-value[data-metric='clicks']").textContent = formatNumber(summary.total_clicks || 0);
      document.querySelector(".metric-value[data-metric='ctr']").textContent = (summary.ctr || 0) + "%";
    } catch {}
  }

  function renderChartsFromPerf(perfRows) {
    const aggregated = aggregatePerformanceData(perfRows);
    const labels = aggregated.length ? aggregated.map(r => formatDate(r.date)) : ["No Data"];
    const impressions = aggregated.length ? aggregated.map(r => r.impressions || 0) : [0];
    const spends = aggregated.length ? aggregated.map(r => Number(r.cost || 0)) : [0];
    const ctxImpr = document.getElementById("impressionsChart").getContext("2d");
    destroyChart(impressionsChart);
    impressionsChart = new Chart(ctxImpr, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Impressions",
          data: impressions,
          borderColor: "rgba(29,155,240,1)",
          fill: true,
          tension: 0.2,
          pointRadius: 3,
          backgroundColor: ctx => {
            const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, ctx.chart.height);
            g.addColorStop(0, 'rgba(29,155,240,0.2)');
            g.addColorStop(1, 'rgba(29,155,240,0)');
            return g;
          }
        }]
      },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: true },
          x: { display: aggregated.length > 0 }
        },
        plugins: {
          legend: { display: aggregated.length > 0 },
          tooltip: { enabled: aggregated.length > 0 },
          title: {
            display: !aggregated.length,
            text: "No performance data available",
            color: "#666",
            padding: 20
          }
        }
      }
    });
    const ctxSpend = document.getElementById("spentformanceChart").getContext("2d");
    destroyChart(spendChart);
    spendChart = new Chart(ctxSpend, {
      type: "bar",
      data: {
        labels,
        datasets: [{
          label: "Spent (ETB)",
          data: spends,
          backgroundColor: 'rgba(46,196,182,0.9)',
          borderColor: 'rgba(46,196,182,1)',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: true },
          x: { display: aggregated.length > 0 }
        },
        plugins: {
          legend: { display: aggregated.length > 0 },
          tooltip: { enabled: aggregated.length > 0 },
          title: {
            display: !aggregated.length,
            text: "No performance data available",
            color: "#666",
            padding: 20
          }
        }
      }
    });
  }

  function renderCategoryPerformance(categoryPerf) {
    const tbody = document.getElementById("categories-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (!categoryPerf.length) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-brand"><i class="fas fa-spinner fa-spin "> </i> loading</td></tr>`;
      return;
    }
    categoryPerf.forEach(cat => {
      const row = document.createElement("tr");
      const ctr = cat.ctr;
      const convRate = cat.engagement_rate;
      row.innerHTML = `
        <td class="performance-name">${escapeHtml(cat.category || "Unknown")}</td>
        <td>${formatNumber(cat.total_impressions || 0)}</td>
        <td>${ctr.toFixed(2)}%</td>
        <td>${convRate.toFixed(2)}%</td>
      `;
      tbody.appendChild(row);
    });
  }

  function renderLanguagePerformance(languagePerf, languages) {
    const legendContainer = document.getElementById("languageLegend");
    const canvas = document.getElementById("languageChart");
    if (!legendContainer || !canvas) return;

    destroyChart(languageChart);
    legendContainer.innerHTML = "";

    if (!languagePerf.length) {
      legendContainer.innerHTML = `<p class="text-brand"><i class="fas fa-spinner fa-spin "> </i></p>`;
      const ctx = canvas.getContext("2d");
      languageChart = new Chart(ctx, {
        type: "doughnut",
        data: {
          labels: ["No Data"],
          datasets: [{
            data: [1],
            backgroundColor: ['#ccc']
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: false },
            title: {
              display: true,
              text: "No language data available",
              color: "#666",
              padding: 20
            }
          }
        }
      });
      return;
    }

    // Total impressions only from performance data
    const totalImpressions = languagePerf.reduce((sum, lang) => sum + (Number(lang.total_impressions) || 0), 0);

    // Build arrays for chart and legend from languagePerf only
    const labels = [];
    const data = [];
    const backgroundColors = [];
    const percentages = [];

    languagePerf.forEach((lang, index) => {
      const languageName = lang.language || "Unknown";
      const impressions = Number(lang.total_impressions) || 0;
      const percentage = totalImpressions ? ((impressions / totalImpressions) * 100).toFixed(1) : "0";

      labels.push(languageName);
      data.push(impressions);
      backgroundColors.push(chartColors[index % chartColors.length]);
      percentages.push(percentage);

      // Create legend item
      const div = document.createElement("div");
      div.className = "legend-item";
      div.innerHTML = `
        <span class="legend-color" style="background-color: ${backgroundColors[index]};"></span>
        <span class="legend-label">${escapeHtml(languageName)}</span>
        <span class="legend-value">${percentage}%</span>
      `;
      legendContainer.appendChild(div);
    });

    // Render chart
    const ctx = canvas.getContext("2d");
    languageChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{
          data,
          backgroundColor: backgroundColors,
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: context => {
                const label = context.label || "";
                const value = context.raw || 0;
                const percentage = percentages[context.dataIndex];
                return `${label}: ${formatNumber(value)} impressions (${percentage}%)`;
              }
            }
          }
        }
      }
    });
  }

  function filterAndSortCampaigns(campaigns) {
    let filtered = campaigns;
    
    // Filter by name
    if (filterName) {
      filtered = filtered.filter(c => c.name.toLowerCase().includes(filterName.toLowerCase()));
    }
    
    // Filter by status
    if (filterStatus !== 'all') {
      filtered = filtered.filter(c => c.status.toLowerCase() === filterStatus);
    }
    
    // Sort campaigns
    filtered.sort((a, b) => {
      let valA, valB;
      switch (sortColumn) {
        case 'name':
          valA = a.name.toLowerCase();
          valB = b.name.toLowerCase();
          break;
        case 'status':
          valA = a.status.toLowerCase();
          valB = b.status.toLowerCase();
          break;
        case 'start_date':
          valA = a.start_date ? new Date(a.start_date) : new Date(0);
          valB = b.start_date ? new Date(b.start_date) : new Date(0);
          break;
        case 'initial_budget':
          valA = Number(a.initial_budget) || 0;
          valB = Number(b.initial_budget) || 0;
          break;
        case 'total_cost':
          valA = Number(a.total_cost || a.total_spent || 0);
          valB = Number(b.total_cost || b.total_spent || 0);
          break;
        case 'total_impressions':
          valA = Number(a.total_impressions || 0);
          valB = Number(b.total_impressions || 0);
          break;
        case 'ctr':
          valA = a.total_impressions ? (a.total_clicks / a.total_impressions * 100) : 0;
          valB = b.total_impressions ? (b.total_clicks / b.total_impressions * 100) : 0;
          break;
        default:
          valA = a.name.toLowerCase();
          valB = b.name.toLowerCase();
      }
      if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
      if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
    
    return filtered;
  }

  function renderCampaignsTable(campaigns, isOverview = false) {
    const container = isOverview
      ? document.querySelector("#overview .campaigns-table")
      : document.querySelector("#campaigns .campaigns-table");
    if (!container) return;
    
    const tbody = container.querySelector("tbody");
    if (!tbody) return;
    tbody.innerHTML = "";

    // Apply filtering and sorting
    const filteredCampaigns = filterAndSortCampaigns(campaigns);
    
    // Pagination
    const totalItems = filteredCampaigns.length;
    const totalPages = Math.ceil(totalItems / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const campaignsToShow = isOverview
      // sort by status desc, updated_at desc and show top 6
      ? filteredCampaigns.sort((a, b) => {
          if (a.status !== b.status) {
            return a.status < b.status ? -1 : 1;
          }
          return new Date(b.updated_at) - new Date(a.updated_at);
        }).slice(0, 6)
      : filteredCampaigns.slice(startIndex, endIndex);

    if (!campaignsToShow.length) {
      tbody.innerHTML = `<tr>
        No active campaigns available
        <td colspan="">
          <button class="create-campaign-btn btn btn-primary" onclick="window.__dashboard.openCreateCampaignModal();">+ Create Your 1st Campaign</button>
        </td>
      </tr>`;
      if (!isOverview) renderPagination(totalPages);
      return;
    }

    campaignsToShow.forEach(c => {
      const row = document.createElement("tr");
      const ctr = c.total_impressions ? (c.total_clicks / c.total_impressions * 100).toFixed(2) : "0";
      row.setAttribute("onclick", `window.__dashboard.openPerformanceModal('${c.id}')`);
      row.setAttribute("role", "button");
      row.style.cursor = "pointer";
      row.innerHTML = `
        <td>
          <div class="ad-info gap-3">
            <div class="ad-preview">
              ${c.ad_content.img_url ? `<img src="${c.ad_content.img_url}" alt="Ad Preview" class="ad-preview-image" />` : `<i class="fas fa-photo-film status bg-none ${c.status}"></i>`}
            </div>
            <div class="ad-details">
              <p class="ad-name">${escapeHtml(c.name)}</p>
              <p class="ad-type">${escapeHtml(c.ad_content.headline || 'No Ad content')}</p>
            </div>
          </div>
        </td>
          
        <td><span class="status-badge ${escapeHtml(c.status)}">${escapeHtml(c.status)}</span></td>
        <td>${formatDate(c.start_date)}</td>
        <td>${formatNumber(c.initial_budget)}</td>
        <td>
          <div class="action-buttons">
            <button class="action-btn" title="View Performance - ${escapeHtml(c.name)}" onclick="window.__dashboard.openPerformanceModal('${c.id}')"><i class="fas fa-chart-line"></i></button>
          </div>
        </td>
      `;
      tbody.appendChild(row);
    });

    // Render sorting headers and pagination controls (only for campaigns tab, not overview)
    if (!isOverview) {
      renderSortHeaders();
      renderPagination(totalPages);
      setupFilterControls();
    }
  }

  function renderSortHeaders() {
    const table = document.querySelector("#campaigns .campaigns-table");
    if (!table) return;
    const thead = table.querySelector("thead");
    if (!thead) return;
    
    const headers = [
      { id: 'name', label: 'Name' },
      { id: 'status', label: 'Status' },
      { id: 'start_date', label: 'Start Date' },
      { id: 'initial_budget', label: 'Budget' },
      { id: 'actions', label: 'Actions', sortable: false }
    ];

    thead.innerHTML = `
      <tr>
        ${headers.map(h => `
          <th class="${h.sortable !== false ? 'sortable' : ''}" data-sort="${h.id}">
            ${h.label}
            ${h.sortable !== false ? `<span class="sort-icon">${sortColumn === h.id ? (sortDirection === 'asc' ? '↑' : '↓') : '↑↓'}</span>` : ''}
          </th>
        `).join('')}
      </tr>
    `;

    // Add click listeners for sortable headers
    thead.querySelectorAll('.sortable').forEach(th => {
      th.addEventListener('click', () => {
        const column = th.dataset.sort;
        if (sortColumn === column) {
          sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
          sortColumn = column;
          sortDirection = 'asc';
        }
        currentPage = 1; // Reset to first page on sort
        loadAll();
      });
    });
  }

  function renderPagination(totalPages) {
    const paginationContainer = document.querySelector("#campaigns .pagination-controls");
    if (!paginationContainer) return;

    paginationContainer.innerHTML = `
      <div class="pagination">
        <button class="btn btn-outline btn-sm" ${currentPage === 1 ? 'disabled' : ''} onclick="window.__dashboard.prevPage()">Previous</button>
        ${Array.from({ length: totalPages }, (_, i) => i + 1).map(page => `
          <button class="btn btn-outline btn-sm ${page === currentPage ? 'active' : ''}" onclick="window.__dashboard.goToPage(${page})">${page}</button>
        `).join('')}
        <button class="btn btn-outline btn-sm" ${currentPage === totalPages ? 'disabled' : ''} onclick="window.__dashboard.nextPage(${totalPages})">Next</button>
      </div>
    `;
  }

  function setupFilterControls() {
    const filterContainer = document.querySelector("#campaigns .filter-controls");
    if (!filterContainer) return;

    filterContainer.innerHTML = `
      <div class="filter-controls">
        <input type="text" id="campaignFilterName" placeholder="Search by name" value="${escapeHtml(filterName)}">
        <select id="campaignFilterStatus">
          <option value="all" ${filterStatus === 'all' ? 'selected' : ''}>All Statuses</option>
          <option value="active" ${filterStatus === 'active' ? 'selected' : ''}>Active</option>
          <option value="on_hold" ${filterStatus === 'on_hold' ? 'selected' : ''}>On Hold</option>
          <option value="draft" ${filterStatus === 'draft' ? 'selected' : ''}>Draft</option>
          <option value="stopped" ${filterStatus === 'stopped' ? 'selected' : ''}>Stopped</option>
          <option value="declined" ${filterStatus === 'declined' ? 'selected' : ''}>Declined</option>
        </select>
      </div>
    `;

    document.getElementById('campaignFilterName').addEventListener('input', (e) => {
      filterName = e.target.value;
      currentPage = 1; // Reset to first page on filter change
      loadAll();
    });

    document.getElementById('campaignFilterStatus').addEventListener('change', (e) => {
      filterStatus = e.target.value;
      currentPage = 1; // Reset to first page on filter change
      loadAll();
    });
  }

  window.__dashboard = {
    openCreateCampaignModal,
    openEditCampaign,
    openDeleteConfirmModal,
    actionCampaign,
    submitCampaignById,
    openPerformanceModal,
    openTopupModal,
    closeModal,
    switchTab,
    removeAd,
    prevPage: () => {
      if (currentPage > 1) {
        currentPage--;
        loadAll();
      }
    },
    nextPage: (totalPages) => {
      if (currentPage < totalPages) {
        currentPage++;
        loadAll();
      }
    },
    goToPage: (page) => {
      currentPage = page;
      loadAll();
    }
  };

  function renderBillingInfo(balance) {
    document.getElementById("current-balance").textContent = `ETB ${formatNumber(balance.available_balance || balance.available || 0)}`;
    document.getElementById("total-spend").textContent = `ETB ${formatNumber(balance.total_spent || 0)}`;
    document.getElementById("in-escrow").textContent = `ETB ${formatNumber(balance.pending_escrow || balance.locked || 0)}`;
    const tbody = document.getElementById("transactions-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    const transactions = Array.isArray(balance.transactions) ? balance.transactions : [];
    if (!transactions.length) {
      tbody.innerHTML = `<tr><td colspan="5">No transactions available</td></tr>`;
      return;
    }
    const typeMap = {
      deposit: { icon: "fa-plus", color: "green", label: "Deposit" },
      withdrawal: { icon: "fa-minus", color: "red", label: "Withdrawal" },
      debit: { icon: "fa-lock", color: "orange", label: "To Escrow" },
      credit: { icon: "fa-undo", color: "purple", label: "Escrow Refund" },
    };

    transactions.forEach(t => {
      const type = typeMap[t.type] || { icon: "fa-question", color: "gray", label: t.type };
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${formatDate(t.date)}</td>
        <td>
          <span class="transaction-type-label" style="color:${type.color};">
            <i class="fas ${type.icon}"></i> ${type.label}
          </span>
        </td>
        <td>${formatNumber(t.amount || 0)}</td>
        <td title="${t.reference_full || t.reference}">${t.reference}</td>
        <td>${t.status || "-"}</td>
      `;
      tbody.appendChild(row);
    });
  }

  // Initialize
  loadAll();
});