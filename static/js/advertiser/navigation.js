/**
 * Navigation component
 * Handles mobile menu, dropdowns, and sidebar navigation
 */

document.addEventListener("DOMContentLoaded", () => {
  // Mobile menu toggle
  const mobileMenuToggle = document.querySelector(".mobile-menu-toggle")
  const navList = document.querySelector(".nav-list")

  if (mobileMenuToggle && navList) {
    // Create mobile menu
    const mobileMenu = document.createElement("div")
    mobileMenu.className = "mobile-menu"

    const mobileMenuHeader = document.createElement("div")
    mobileMenuHeader.className = "mobile-menu-header"

    const logoClone = document.querySelector(".logo").cloneNode(true)

    const mobileMenuClose = document.createElement("button")
    mobileMenuClose.className = "mobile-menu-close"
    mobileMenuClose.setAttribute("aria-label", "Close menu")
    mobileMenuClose.innerHTML = '<i class="fas fa-times"></i>'

    mobileMenuHeader.appendChild(logoClone)
    mobileMenuHeader.appendChild(mobileMenuClose)

    const mobileMenuContent = document.createElement("div")
    mobileMenuContent.className = "mobile-menu-content"

    const mobileNavList = document.createElement("ul")
    mobileNavList.className = "mobile-nav-list"

    // Clone nav items
    const navItems = navList.querySelectorAll("li")
    navItems.forEach((item) => {
      const mobileNavItem = document.createElement("li")
      const link = item.querySelector("a").cloneNode(true)
      mobileNavItem.appendChild(link)
      mobileNavList.appendChild(mobileNavItem)
    })

    mobileMenuContent.appendChild(mobileNavList)

    mobileMenu.appendChild(mobileMenuHeader)
    mobileMenu.appendChild(mobileMenuContent)

    document.body.appendChild(mobileMenu)

    // Toggle mobile menu
    mobileMenuToggle.addEventListener("click", () => {
      mobileMenu.classList.add("active")
      document.body.style.overflow = "hidden"
    })

    // Close mobile menu
    mobileMenuClose.addEventListener("click", () => {
      mobileMenu.classList.remove("active")
      document.body.style.overflow = ""
    })

    // Close mobile menu when clicking outside
    document.addEventListener("click", (event) => {
      if (
        mobileMenu.classList.contains("active") &&
        !mobileMenu.contains(event.target) &&
        !mobileMenuToggle.contains(event.target)
      ) {
        mobileMenu.classList.remove("active")
        document.body.style.overflow = ""
      }
    })
  }

  // Sidebar navigation
  const sidebarToggle = document.querySelector(".sidebar-toggle")
  const sidebar = document.querySelector(".sidebar")
  const sidebarClose = document.querySelector(".sidebar-close")

  if (sidebarToggle && sidebar) {
    // Toggle sidebar
    sidebarToggle.addEventListener("click", () => {
      sidebar.classList.toggle("active")
    })

    // Close sidebar
    if (sidebarClose) {
      sidebarClose.addEventListener("click", () => {
        sidebar.classList.remove("active")
      })
    }

    // Close sidebar when clicking outside on mobile
    document.addEventListener("click", (event) => {
      if (
        window.innerWidth < 1024 &&
        sidebar.classList.contains("active") &&
        !sidebar.contains(event.target) &&
        !sidebarToggle.contains(event.target)
      ) {
        sidebar.classList.remove("active")
      }
    })

    // Handle sidebar dropdowns
    const dropdownToggles = sidebar.querySelectorAll(".dropdown-toggle")

    dropdownToggles.forEach((toggle) => {
      toggle.addEventListener("click", (event) => {
        event.preventDefault()

        const parent = toggle.parentElement
        const dropdownMenu = parent.querySelector(".dropdown-menu")

        // Close other dropdowns
        dropdownToggles.forEach((otherToggle) => {
          if (otherToggle !== toggle) {
            const otherParent = otherToggle.parentElement
            const otherDropdownMenu = otherParent.querySelector(".dropdown-menu")
            otherDropdownMenu.style.display = "none"
            otherToggle.classList.remove("active")
            otherToggle.querySelector(".dropdown-icon").style.transform = "rotate(0deg)"
          }
        })

        // Toggle current dropdown
        if (dropdownMenu.style.display === "block") {
          dropdownMenu.style.display = "none"
          toggle.classList.remove("active")
          toggle.querySelector(".dropdown-icon").style.transform = "rotate(0deg)"
        } else {
          dropdownMenu.style.display = "block"
          toggle.classList.add("active")
          toggle.querySelector(".dropdown-icon").style.transform = "rotate(180deg)"
        }
      })
    })
  }

  // User dropdown
  const userDropdownToggle = document.querySelector(".user-dropdown-toggle")
  const userDropdownMenu = document.querySelector(".user-dropdown .dropdown-menu")

  if (userDropdownToggle && userDropdownMenu) {
    userDropdownToggle.addEventListener("click", (event) => {
      event.stopPropagation()
      userDropdownMenu.classList.toggle("show")
    })

    document.addEventListener("click", (event) => {
      if (!userDropdownToggle.contains(event.target) && !userDropdownMenu.contains(event.target)) {
        userDropdownMenu.classList.remove("show")
      }
    })
  }

  // Notifications dropdown
  const notificationsBtn = document.querySelector(".notifications");

  if (notificationsBtn) {
      // Create notifications dropdown
      const notificationsDropdown = document.createElement("div");
      notificationsDropdown.className = "dropdown-menu notifications-dropdown";

      const notificationsHeader = document.createElement("div");
      notificationsHeader.className = "notifications-header";
      notificationsHeader.innerHTML = `
          <h4>Notifications</h4>
          <a href="#" class="mark-all-read">Mark all as read</a>
      `;

      const notificationsList = document.createElement("div");
      notificationsList.className = "notifications-list";

      const notificationsFooter = document.createElement("div");
      notificationsFooter.className = "notifications-footer";
      notificationsFooter.innerHTML = `
          <a href="#notifications">View all notifications</a>
      `;

      notificationsDropdown.appendChild(notificationsHeader);
      notificationsDropdown.appendChild(notificationsList);
      notificationsDropdown.appendChild(notificationsFooter);
      notificationsBtn.appendChild(notificationsDropdown);

      const typeIcons = {
          campaign_approved: "fas fa-bullhorn",
          performance_update: "fas fa-chart-line",
          payment_processed: "fas fa-wallet",
          custom: "fas fa-bell"
      };

      
      function formatTime(createdAt) {
          const now = new Date();
          const date = new Date(createdAt);
          const diffMs = now - date;
          const diffMins = Math.round(diffMs / 60000);
          if (diffMins < 1) return "Just now";
          if (diffMins < 60) return `${diffMins} minute${diffMins === 1 ? "" : "s"} ago`;
          const diffHours = Math.round(diffMins / 60);
          if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? "" : "s"} ago`;
          const diffDays = Math.round(diffHours / 24);
          return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`;
      }

      // Function to fetch notifications
      async function fetchNotifications() {
          try {
              const response = await apiFetch("/api/notifications/", { method: "GET" });
              return response; // Array of notifications
          } catch (err) {
              console.error("Failed to fetch notifications:", err);
              toastError("Failed to load notifications.");
              return [];
          }
      }

      // Function to fetch unread count and update badge
      async function updateUnreadCount() {
          try {
              const response = await apiFetch("/api/notifications/unread-count/", { method: "GET" });
              const badge = notificationsBtn.querySelector(".badge");
              const unreadCount = response.unread_count || 0;
              if (badge) {
                  badge.textContent = unreadCount;
                  badge.style.display = unreadCount > 0 ? "inline-block" : "none";
              }
          } catch (err) {
              console.error("Failed to fetch unread count:", err);
          }
      }

      // Function to render notifications
      function renderNotifications(notifications) {
          notificationsList.innerHTML = ""; // Clear existing
          notifications.forEach((notification) => {
              const notificationItem = document.createElement("div");
              notificationItem.className = `notification-item ${notification.is_read ? "read" : "unread"}`;
              notificationItem.dataset.id = notification.id; // Store ID for API calls

              const iconClass = typeIcons[notification.type] || "fas fa-bell";
              const timeAgo = formatTime(notification.created_at);

              notificationItem.innerHTML = `
                  <div class="notification-icon">
                      <i class="${iconClass}"></i>
                  </div>
                  <div class="notification-content">
                      <h5>${escapeHtml(notification.title)}</h5>
                      <p>${escapeHtml(notification.message)}</p>
                      <span class="notification-time">${timeAgo}</span>
                  </div>
                  <button class="notification-action" aria-label="Mark as ${notification.is_read ? "unread" : "read"}">
                      <i class="fas fa-circle"></i>
                  </button>
              `;

              notificationsList.appendChild(notificationItem);
          });

          // Attach event listeners to notification actions
          notificationsList.querySelectorAll(".notification-action").forEach((action) => {
              action.addEventListener("click", async (event) => {
                  event.stopPropagation();
                  const notificationItem = action.closest(".notification-item");
                  const notificationId = notificationItem.dataset.id;
                  const isRead = notificationItem.classList.contains("read");

                  try {
                      const endpoint = isRead
                          ? `/api/notifications/${notificationId}/mark-unread/`
                          : `/api/notifications/${notificationId}/mark-read/`;
                      await apiFetch(endpoint, { method: "PATCH" });

                      // Toggle read/unread state
                      notificationItem.classList.toggle("read", !isRead);
                      notificationItem.classList.toggle("unread", isRead);
                      action.setAttribute("aria-label", `Mark as ${isRead ? "read" : "unread"}`);

                      // Update badge
                      await updateUnreadCount();
                  } catch (err) {
                      console.error(`Failed to mark notification ${notificationId}:`, err);
                      toastError(`Failed to mark notification as ${isRead ? "unread" : "read"}.`);
                  }
              });
          });
      }

      // Function to load and render notifications
      async function loadNotifications() {
          const notifications = await fetchNotifications();
          renderNotifications(notifications);
          await updateUnreadCount();
      }

      // Initial load
      loadNotifications();

      // Toggle notifications dropdown
      notificationsBtn.addEventListener("click", (event) => {
          event.stopPropagation();
          notificationsDropdown.classList.toggle("show");
          if (notificationsDropdown.classList.contains("show")) {
              loadNotifications(); // Refresh on open
          }
      });

      // Close dropdown when clicking outside
      document.addEventListener("click", (event) => {
          if (!notificationsBtn.contains(event.target)) {
              notificationsDropdown.classList.remove("show");
          }
      });

      // Mark all as read
      const markAllReadBtn = notificationsDropdown.querySelector(".mark-all-read");
      if (markAllReadBtn) {
          markAllReadBtn.addEventListener("click", async (event) => {
              event.preventDefault();
              event.stopPropagation();
              try {
                  await apiFetch("/api/notifications/mark-all-read/", { method: "PATCH" });
                  const unreadItems = notificationsList.querySelectorAll(".notification-item.unread");
                  unreadItems.forEach((item) => {
                      item.classList.remove("unread");
                      item.classList.add("read");
                      const action = item.querySelector(".notification-action");
                      if (action) action.setAttribute("aria-label", "Mark as unread");
                  });
                  await updateUnreadCount();
                  toastSuccess("All notifications marked as read!");
              } catch (err) {
                  console.error("Failed to mark all notifications as read:", err);
                  toastError("Failed to mark all notifications as read.");
              }
          });
      }
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

  function getCookie(name) {
    const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return v ? v.pop() : "";
  }

  function escapeHtml(str) {
      const div = document.createElement("div");
      div.textContent = str;
      return div.innerHTML;
  }

  function toastError(msg) {

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
})
