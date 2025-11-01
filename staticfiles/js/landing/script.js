// Mobile Menu Toggle
const mobileMenuBtn = document.getElementById("mobileMenuBtn")
const navLinks = document.getElementById("navLinks")

mobileMenuBtn.addEventListener("click", () => {
  mobileMenuBtn.classList.toggle("active")
  navLinks.classList.toggle("active")
})

// Close mobile menu when clicking on a link
navLinks.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    mobileMenuBtn.classList.remove("active")
    navLinks.classList.remove("active")
  })
})

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault()
    const target = document.querySelector(this.getAttribute("href"))
    if (target) {
      target.scrollIntoView({
        behavior: "smooth",
        block: "start",
      })
    } else if (this.getAttribute("href") === "#contact") {
      e.preventDefault()
      const overlay = document.getElementById("loadingOverlay");
      overlay.classList.add("active");
      setTimeout(() => {
        window.location.href = "https://t.me/sonicAdzBot"
      }, 1000);
    } else if (this.getAttribute("href") === "#privacy" || this.getAttribute("href") === "#terms") {
      e.preventDefault()
      const overlay = document.getElementById("loadingOverlay");
      overlay.classList.add("active");
      setTimeout(() => {
        window.location.href = "https://telegra.ph/SonicAdz-Terms-and-Conditions--Privacy-Policy-08-13";
      }, 1000);
    }
  });
}); 


// Intersection Observer for scroll animations
const observerOptions = {
  threshold: 0.1,
  rootMargin: "0px 0px -100px 0px",
}

const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = "1"
      entry.target.style.transform = "translateY(0)"
    }
  })
}, observerOptions)

// Observe all glass cards and sections
document.querySelectorAll(".glass-card, .value-prop-content, .value-prop-visual").forEach((el) => {
  observer.observe(el)
})

// CTA Button Click Handlers (placeholder functionality)
document.getElementById("advertiseBtn").addEventListener("click", () => {
  const overlay = document.getElementById("loadingOverlay");

  overlay.classList.add("active");
  setTimeout(() => {
    window.location.href = "/advertiser";
  }, 1000);
});

document.getElementById("monetizeBtn").addEventListener("click", () => {
  const overlay = document.getElementById("loadingOverlay");

  overlay.classList.add("active");
  setTimeout(() => {
    window.location.href = "https://t.me/sonicAdzBot/sGo";
  }, 1000);
});


// Parallax effect for background orbs
let scrollY = 0

window.addEventListener("scroll", () => {
  scrollY = window.scrollY

  const orbs = document.querySelectorAll(".gradient-orb")
  orbs.forEach((orb, index) => {
    const speed = (index + 1) * 0.1
    orb.style.transform = `translate(${scrollY * speed}px, ${scrollY * speed}px)`
  })
})

// Add hover effect to feature cards
const featureCards = document.querySelectorAll(".feature-card")
featureCards.forEach((card) => {
  card.addEventListener("mouseenter", function () {
    this.style.zIndex = "10"
  })

  card.addEventListener("mouseleave", function () {
    this.style.zIndex = "1"
  })
})

// Dynamic gradient animation on CTA buttons
const ctaButtons = document.querySelectorAll(".cta-btn")
ctaButtons.forEach((btn) => {
  btn.addEventListener("mousemove", (e) => {
    const rect = btn.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    btn.style.setProperty("--mouse-x", `${x}px`)
    btn.style.setProperty("--mouse-y", `${y}px`)
  })
})

// Add active state to navigation based on scroll position
const sections = document.querySelectorAll("section[id]")
const navItems = document.querySelectorAll(".nav-links a")

window.addEventListener("scroll", () => {
  let current = ""

  sections.forEach((section) => {
    const sectionTop = section.offsetTop
    const sectionHeight = section.clientHeight
    if (scrollY >= sectionTop - 200) {
      current = section.getAttribute("id")
    }
  })

  navItems.forEach((item) => {
    item.classList.remove("active")
    if (item.getAttribute("href").slice(1) === current) {
      item.classList.add("active")
    }
  })
})

// Performance optimization: Debounce scroll events
function debounce(func, wait) {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

// Apply debounce to scroll handler
const debouncedScroll = debounce(() => {
  // Additional scroll-based animations can be added here
}, 10)

window.addEventListener("scroll", debouncedScroll)

// Demo View Toggle
const toggleButtons = document.querySelectorAll(".toggle-btn")
const demoViews = document.querySelectorAll(".demo-view")

toggleButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const targetView = btn.getAttribute("data-view")

    // Update button states
    toggleButtons.forEach((b) => b.classList.remove("active"))
    btn.classList.add("active")

    // Update view visibility
    demoViews.forEach((view) => {
      view.classList.remove("active")
      if (view.id === `${targetView}-view`) {
        view.classList.add("active")
      }
    })
  })
})

// Campaign Creation Demo
const createCampaignBtn = document.getElementById("createCampaignBtn")
if (createCampaignBtn) {
  createCampaignBtn.addEventListener("click", () => {
    // Animate the matching card
    const matchingCard = document.querySelector(".matching-card")
    const aiIcon = document.querySelector(".ai-icon")
    const matchingText = document.querySelector(".matching-text")

    // Reset animation
    aiIcon.style.animation = "none"
    setTimeout(() => {
      aiIcon.style.animation = "pulse 2s ease-in-out infinite"
    }, 10)

    // Simulate matching process
    matchingText.textContent = "Analyzing..."
    setTimeout(() => {
      matchingText.textContent = "Matching complete!"
    }, 2000)

    
  })
}

// Animate metrics on scroll
const metricsObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const metricValue = entry.target.querySelector(".metric-value")
        if (metricValue) {
          animateValue(metricValue)
        }
      }
    })
  },
  { threshold: 0.5 },
)

document.querySelectorAll(".metric-card").forEach((card) => {
  metricsObserver.observe(card)
})

// Animate number counting
function animateValue(element) {
  const text = element.textContent
  const hasComma = text.includes(",")
  const numericValue = Number.parseInt(text.replace(/[^0-9]/g, ""))

  if (isNaN(numericValue)) return

  const duration = 1500
  const steps = 60
  const increment = numericValue / steps
  let current = 0
  let step = 0

  const timer = setInterval(() => {
    current += increment
    step++

    if (step >= steps) {
      current = numericValue
      clearInterval(timer)
    }

    const formatted = hasComma ? Math.floor(current).toLocaleString() : Math.floor(current)
    element.textContent = text.replace(/[0-9,]+/, formatted)
  }, duration / steps)
}

// Animate earnings amount
const earningsObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const earningsAmount = entry.target.querySelector(".earnings-amount")
        if (earningsAmount) {
          animateEarnings(earningsAmount)
        }
      }
    })
  },
  { threshold: 0.5 },
)

document.querySelectorAll(".earnings-card").forEach((card) => {
  earningsObserver.observe(card)
})

function animateEarnings(element) {
  const text = element.textContent
  const numericValue = Number.parseFloat(text.replace(/[^0-9.]/g, ""))

  if (isNaN(numericValue)) return

  const duration = 2000
  const steps = 60
  const increment = numericValue / steps
  let current = 0
  let step = 0

  const timer = setInterval(() => {
    current += increment
    step++

    if (step >= steps) {
      current = numericValue
      clearInterval(timer)
    }

    element.textContent = `ETB${current.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ",")}`
  }, duration / steps)
}

  

