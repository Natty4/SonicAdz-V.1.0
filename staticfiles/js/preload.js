// ===== PRELOADER & BACKGROUND EFFECTS =====
document.addEventListener('DOMContentLoaded', () => {
    // Generate stars
    const starsContainer = document.getElementById('stars');
    for (let i = 0; i < 200; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        star.style.width = `${Math.random() * 3}px`;
        star.style.height = star.style.width;
        star.style.left = `${Math.random() * 100}%`;  // Changed to % for consistency
        star.style.top = `${Math.random() * 100}%`;   // Changed to % for consistency
        star.style.setProperty('--duration', `${2 + Math.random() * 3}s`);
        starsContainer.appendChild(star);
    }



    // Add shooting stars
    function createShootingStar() {
        const shootingStar = document.createElement('div');
        shootingStar.className = 'shooting-star';
        shootingStar.style.left = `${Math.random() * 20}%`;
        shootingStar.style.top = `${Math.random() * 100}%`;
        starsContainer.appendChild(shootingStar);
        
        setTimeout(() => {
            shootingStar.remove();
        }, 1000);
    }

    setInterval(createShootingStar, 2000);

    // // Hide preloader when page loads
    // window.addEventListener('load', () => {
    // const preloader = document.getElementById('preloader');


    // setTimeout(() => {
    //     // Zoom the portal preloader
    //     preloader.classList.add('zoom-out');

    //     // After zoom animation ends, remove preloader & reveal content
    //     setTimeout(() => {
    //     preloader.remove();
    //     document.body.style.overflow = '';
    //     }, 1500); // match zoom duration
    // }, 1500); // Optional delay before zoom begins
    // });

    // Parallax effect for sonic elements
    window.addEventListener("scroll", () => {
    const scrolled = window.pageYOffset
    const sonicElements = document.querySelectorAll(".sonic-floating-ring-1, .sonic-floating-ring-2, .sonic-floating-ring-3")

    sonicElements.forEach((element, index) => {
        const speed = 0.3 + index * 0.1
        const yPos = -(scrolled * speed)
        element.style.transform = `translateY(${yPos}px) rotate(${scrolled * 0.1}deg)`
    })

    // Speed lines effect
    const speedLines = document.querySelector(".speed-lines")
    if (speedLines) {
        speedLines.style.backgroundPosition = `${scrolled * 0.5}px ${scrolled * 0.3}px, ${-scrolled * 0.3}px ${scrolled * 0.5}px`
    }
    })

    function spawnSparks() {
    const container = document.querySelector('.portal-ring .spark-container');
    if (!container) return;

    for (let i = 0; i < 20; i++) {
        const spark = document.createElement('div');
        spark.className = 'spark';

        const angle = Math.random() * 360;
        const radius = 80 + Math.random() * 20; // around the ring
        const x = 90 + Math.cos(angle * Math.PI / 180) * radius;
        const y = 90 + Math.sin(angle * Math.PI / 180) * radius;

        spark.style.left = `${x}px`;
        spark.style.top = `${y}px`;
        spark.style.animationDuration = `${1.5 + Math.random()}s`;

        container.appendChild(spark);

        // Remove spark after animation
        setTimeout(() => spark.remove(), 2000);
    }
    }

    // Spawn periodically
    setInterval(spawnSparks, 500);



    // Smooth scrolling for navigation
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });



    // TOOLTIP

    const tooltipIcons = document.querySelectorAll('.tooltip-icon');

    tooltipIcons.forEach(icon => {
        icon.addEventListener('mouseenter', () => {
            const tooltipText = icon.getAttribute('data-tooltip');

            // Create a temporary element to measure the tooltip size
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
            document.body.removeChild(tempTooltip); // Cleanup

            const spaceLeft = iconRect.left;
            const spaceRight = window.innerWidth - iconRect.right;
            const spaceTop = iconRect.top;
            const spaceBottom = window.innerHeight - iconRect.bottom;

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
                // Not enough space above → show below
                icon.style.setProperty('--tooltip-top', '100%');
                icon.style.setProperty('--tooltip-bottom', 'auto');
            } else {
                // Enough space above → show above
                icon.style.setProperty('--tooltip-top', 'auto');
                icon.style.setProperty('--tooltip-bottom', '100%');
            }
        });

        icon.addEventListener('mouseleave', () => {
            // Clear custom positioning
            icon.style.removeProperty('--tooltip-left');
            icon.style.removeProperty('--tooltip-transform');
            icon.style.removeProperty('--tooltip-top');
            icon.style.removeProperty('--tooltip-bottom');
        });
    });
});