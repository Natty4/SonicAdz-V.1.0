// ===== PRELOADER & BACKGROUND EFFECTS =====
document.addEventListener('DOMContentLoaded', () => {
// Generate stars
// const starsContainer = document.getElementById('stars');
// for (let i = 0; i < 200; i++) {
//     const star = document.createElement('div');
//     star.className = 'star';
//     star.style.width = `${Math.random() * 3}px`;
//     star.style.height = star.style.width;
//     star.style.left = `${Math.random() * 100}%`;  // Changed to % for consistency
//     star.style.top = `${Math.random() * 100}%`;   // Changed to % for consistency
//     star.style.setProperty('--duration', `${2 + Math.random() * 3}s`);
//     starsContainer.appendChild(star);
// }



// Add shooting stars
// function createShootingStar() {
//     const shootingStar = document.createElement('div');
//     shootingStar.className = 'shooting-star';
//     shootingStar.style.left = `${Math.random() * 20}%`;
//     shootingStar.style.top = `${Math.random() * 100}%`;
//     starsContainer.appendChild(shootingStar);
    
//     setTimeout(() => {
//         shootingStar.remove();
//     }, 1000);
// }

// setInterval(createShootingStar, 2000);

// Hide preloader when page loads
// window.addEventListener('load', () => {
//   const preloader = document.getElementById('preloader');


//   setTimeout(() => {
//     // Zoom the portal preloader
//     preloader.classList.add('zoom-out');

//     // After zoom animation ends, remove preloader & reveal content
//     setTimeout(() => {
//       preloader.remove();
//       document.body.style.overflow = '';
//     }, 1500); // match zoom duration
//   }, 1500); // Optional delay before zoom begins
// });

// Parallax effect for sonic elements
// window.addEventListener("scroll", () => {
//   const scrolled = window.pageYOffset
//   const sonicElements = document.querySelectorAll(".sonic-floating-ring-1, .sonic-floating-ring-2, .sonic-floating-ring-3")

//   sonicElements.forEach((element, index) => {
//     const speed = 0.3 + index * 0.1
//     const yPos = -(scrolled * speed)
//     element.style.transform = `translateY(${yPos}px) rotate(${scrolled * 0.1}deg)`
//   })

//   // Speed lines effect
//   const speedLines = document.querySelector(".speed-lines")
//   if (speedLines) {
//     speedLines.style.backgroundPosition = `${scrolled * 0.5}px ${scrolled * 0.3}px, ${-scrolled * 0.3}px ${scrolled * 0.5}px`
//   }
// })

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



function animateStepsOnScroll() {
    const steps = document.querySelectorAll('.step-card');
    const flowAd = document.querySelector('.flow-ad');
    let animationStarted = false; // prevent retriggering

    const observer = new IntersectionObserver((entries, observerInstance) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting && !animationStarted) {
                animationStarted = true;

                // Animate step cards with delay
                steps.forEach((step, index) => {
                    step.style.transition = 'transform 0.6s ease, opacity 0.6s ease';
                    setTimeout(() => {
                        step.style.transform = 'translateY(100)';
                        step.style.opacity = '1';
                    }, index * 200);
                });

                // Start flow animation after a slight delay
                setTimeout(() => {
                    flowAd.style.animation = 'flowAd 4s linear infinite';
                    trackFlowAdMovement();
                }, 800);
            }
        });
    }, { threshold: 0.1 });

    observer.observe(document.querySelector('.how-it-works'));

    // Reset the flow-ad color at the start of each animation loop
    flowAd.addEventListener('animationiteration', () => {
        flowAd.style.background = 'linear-gradient(135deg, var(--sonic-red), var(--sonic-yellow))';
    });
}

function trackFlowAdMovement() {
    const flowAd = document.querySelector('.flow-ad');
    const steps = document.querySelectorAll('.step-card');

    function updateHighlight() {
        const flowRect = flowAd.getBoundingClientRect();

        steps.forEach((step) => {
            const stepRect = step.getBoundingClientRect();

            const flowMidX = flowRect.left + flowRect.width / 2;
            const stepMidX = stepRect.left + stepRect.width / 2;

            const distance = Math.abs(flowMidX - stepMidX);

            // Highlight if flowAd is close (adjust range as needed)
            if (distance < 80) {
                step.classList.add('highlighted');

                // Remove the highlight after a short time
                setTimeout(() => {
                    step.classList.remove('highlighted');
                }, 500); // Duration of glow
            }
        });

        requestAnimationFrame(updateHighlight); 
    }

    requestAnimationFrame(updateHighlight);
}


// Elements
const launchButton = document.getElementById('launch-button');
const portalContainer = document.getElementById('portal-container');
const adPreview = document.getElementById('ad-preview');
const networkContainer = document.getElementById('telegram-network');
const cpmSlider = document.getElementById('cpm-slider');
const cpmValue = document.getElementById('cpm-value');
const demoBtns = document.querySelectorAll('.demo-btn');
const getStart = document.getElementById('get_started');


// State
let selectedNiches = [];
let selectedLanguage = null;
let maxCPM = 5;


// CPM Slider
cpmSlider.addEventListener('input', () => {
    maxCPM = parseFloat(cpmSlider.value);
    cpmValue.textContent = maxCPM.toFixed(1);
    checkLaunchReady();
});

// Niche selection (max 3)
document.querySelectorAll('#niche-badges .badge').forEach(badge => {
    badge.addEventListener('click', () => {
        const niche = badge.dataset.niche;
        
        if (badge.classList.contains('selected')) {
            badge.classList.remove('selected');
            selectedNiches = selectedNiches.filter(n => n !== niche);
        } else {
            if (selectedNiches.length < 3) {
                badge.classList.add('selected');
                selectedNiches.push(niche);
            }
        }
        
        checkLaunchReady();
    });
});

// Language selection
document.querySelectorAll('#language-badges .badge').forEach(badge => {
    badge.addEventListener('click', () => {
        document.querySelectorAll('#language-badges .badge').forEach(b => b.classList.remove('selected'));
        badge.classList.add('selected');
        selectedLanguage = badge.dataset.language;
        checkLaunchReady();
    });
});

// Check if ready to launch
function checkLaunchReady() {
    launchButton.disabled = !(selectedNiches.length > 0 && selectedLanguage);
}


function resetDemo() {
    isDemoRunning = false;
    reachedNodes = [];

    // Remove network nodes
    document.querySelectorAll('.network-node').forEach(node => node.remove());

    // Remove ads
    document.querySelectorAll('.ad').forEach(ad => ad.remove());

    // Reset stats
    document.getElementById('channels-matched').textContent = '0';
    document.getElementById('delivery-speed').textContent = '0ms';
    document.getElementById('match-accuracy').textContent = '0%';

    // Hide network UI
    networkContainer.style.opacity = '0';
    networkContainer.style.zIndex = '0';
    networkContainer.style.backgroundColor = 'transparent';

    // Reset ad preview
    adPreview.style.transform = 'translateY(-50%) scale(0)';
    adPreview.style.opacity = '0';

    // Remove portal zoom class
    const portal = document.querySelector('.sonic-portal');
    if (portal) portal.classList.remove('zooming-out');

    // Deselect language/niche buttons
    document.querySelectorAll('.badge.selected').forEach(btn => btn.classList.remove('selected'));

    // Reset CPM slider
    const cpmInput = document.getElementById('cpm-slider');
    if (cpmInput) {
        cpmInput.value = 5;
        maxCPM = parseInt(cpmInput.value);
    }

    // Clear any messages
    const status = document.querySelector('.status-message');
    if (status) status.textContent = '';

    // Reset button
    launchButton.disabled = true;
    launchButton.classList.remove('bounce', 'shake');
    launchButton.innerHTML = '<i class="fas fa-rocket"></i>  Launch Ad Campaign';
}

// Demo button scroll to demo section
demoBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        resetDemo();
        document.getElementById('demo').scrollIntoView({
            behavior: 'smooth'
        });
    });
});

getStart.addEventListener('click', () => {

    document.getElementById('cta').scrollIntoView({
        behavior: 'smooth'
    });
});

launchButton.addEventListener('click', () => {
    if (isDemoRunning) {
        // If already running, reset the demo
        resetDemo();

        // Optional: update button UI
        launchButton.innerHTML = '<i class="fas fa-rocket"></i> Launch Ad Campaign';
        return;
    }

    // If not running, start the demo
    if (launchButton.disabled) {
        launchButton.classList.add('shake');
        setTimeout(() => launchButton.classList.remove('shake'), 500);
        return;
    }

    launchButton.classList.add('bounce');

    isDemoRunning = true;
    reachedNodes = [];

    // Update button UI to indicate "Reset"
    launchButton.innerHTML = '<i class="fas fa-cycle"></i> Reset Demo';

    // Show ad preview entering portal
    adPreview.style.transform = 'translateY(-50%) scale(1)';
    adPreview.style.opacity = '1';

    // Start delivery animation after a delay
    setTimeout(() => {
        startDeliveryAnimation();
    }, 2000);
});

function startDeliveryAnimation() {

    adPreview.style.transform = 'translateY(-50%) scale(0)';
    adPreview.style.opacity = '0';

    setTimeout(() => {
        const portal = document.querySelector('.sonic-portal');
        if (portal) {
            portal.classList.add('zooming-out');
        }
    }, 100);

    setTimeout(() => {
        // Show network background
        networkContainer.style.opacity = '1';
        networkContainer.style.backgroundColor = '#001122';
        networkContainer.style.zIndex = '11';

        createNetwork();

        setTimeout(() => {
            const nodes = document.querySelectorAll('.network-node');
            nodes.forEach((node, index) => {
                setTimeout(() => {
                    node.classList.add('active');
                }, index * 10);
            });

            const totalActivationTime = nodes.length * 10;
            setTimeout(() => {
                startMarkingReachedNodes();
            }, totalActivationTime + 200);
        }, 100);

        animateCounter('channels-matched', Math.floor(Math.random() * 30) + 20);
        animateCounter('delivery-speed', Math.floor(10 + maxCPM * 8), 'ms');
        animateCounter('match-accuracy', Math.floor(80 + maxCPM * 3), '%');

        setTimeout(() => {
            launchAds();
        }, 1000);

    }, 1000);
}

function startMarkingReachedNodes() {
    const allNodes = Array.from(document.querySelectorAll('.network-node'));
    const shuffled = allNodes.sort(() => 0.5 - Math.random());

    const percentage = Math.random() * 0.2 + 0.75; // 75% to 95%
    const totalToReach = Math.floor(allNodes.length * percentage);

    const counterDisplay = document.getElementById('reached-count');
    let currentReachedCount = 0;

    const availablePlaces = [
        "Addis Ababa", "Adama", "Arbaminch", "Hawassa", "Jima", "Mekele", "Bahirdar",
        "Axum", "Assossa", "Singapore", "Seoul", "Paris", "Cape Town",
        "Istanbul", "Moscow", "Gambela", "Semera", "Rome", "Nirobi"
    ];
    const usedPlaces = new Set();
    const maxPins = 6 + Math.floor(Math.random() * 7); // 6–12 pins max
    let pinCount = 0;

    for (let i = 0; i < totalToReach; i++) {
        const jitterDelay = i * (30 + Math.floor(Math.random() * 30)); // 30–60ms delay

        setTimeout(() => {
            const node = shuffled[i];
            if (!node) return;

            if (Math.random() < 0.2) return; // 20% chance to skip

            node.classList.add('reached');
            currentReachedCount++;
            counterDisplay.textContent = currentReachedCount;

            // Randomly show a pin with a place name (only a few & not repeated)
            if (pinCount < maxPins && Math.random() < 0.5 && availablePlaces.length > 0) {
                const placeIndex = Math.floor(Math.random() * availablePlaces.length);
                const place = availablePlaces.splice(placeIndex, 1)[0]; // remove from list

                if (!usedPlaces.has(place)) {
                    usedPlaces.add(place);
                    pinCount++;

                    const pin = document.createElement('div');
                    pin.className = 'location-pin';
                    pin.innerHTML = `<i class="fas fa-map-marker-alt"></i><span class="place-name">${place}</span>`;
                    node.appendChild(pin);

                    // Fade out and remove after 4–6 seconds
                    setTimeout(() => {
                        // pin.style.opacity = '0';
                        // pin.style.transform = 'translate(-50%, -10px) scale(0.8)';
                        // setTimeout(() => pin.remove(), 1000); // remove after fade
                    }, 4000 + Math.random() * 2000);
                }
            }

        }, jitterDelay);
    }

    reachedNodes = shuffled.slice(0, totalToReach).map(node => node.dataset.id);
}


const TOTAL_NODES = 300;
const MAX_MATCHED_CHANNELS = 6; // Limit to 6 matched channels
const NODES_TO_REACH = Math.floor(TOTAL_NODES * 0.6); // 54 nodes (60%)
const BASE_AD_COUNT = 10;
const MAX_SPEED_MULTIPLIER = 1;

let matchedNodeIndices = [];
let reachedNodes = [];
let isDemoRunning = false;

// Fixed createNetwork function
function createNetwork() {
    const networkContainer = document.getElementById('telegram-network');
    networkContainer.innerHTML = '';
    
    // Create organic layout
    const cols = 20;
    const rows = 15;
    const nodeSize = 20;
    const padding = 25;
    
    const nodePositions = [];
    const connectionCounts = {}
    for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
            if (nodePositions.length >= TOTAL_NODES) break;
            
            const randX = (Math.random() - 0.5) * 30;
            const randY = (Math.random() - 0.5) * 30;
            
            nodePositions.push({
                id: nodePositions.length + 1,
                x: col * (nodeSize + padding) + padding + randX,
                y: row * (nodeSize + padding) + padding + randY,
                width: nodeSize,
                height: nodeSize
            });
        }
    }
    
    matchedNodeIndices = Array.from({length: MAX_MATCHED_CHANNELS}, () =>
        nodePositions[Math.floor(Math.random() * nodePositions.length)].id
    );

    // Create nodes
    nodePositions.forEach(pos => {
        const node = document.createElement('div');
        node.className = 'network-node';
        node.dataset.id = pos.id;
        node.style.width = `${pos.width}px`;
        node.style.height = `${pos.height}px`;
        node.style.left = `${pos.x}px`;
        node.style.top = `${pos.y}px`;
        node.style.position = 'absolute';
        
        const icon = document.createElement('i');
        icon.className = 'fab fa-telegram';
        node.appendChild(icon);
        
        networkContainer.appendChild(node);
    });
    
    nodePositions.forEach(pos => {
        const degree = connectionCounts[pos.id] || 1;
        const size = nodeSize + degree * 1.9;
        pos.width = pos.height = size;
    });


    // Create connections
    const connectionDistance = nodeSize * 3;
    for (let i = 0; i < nodePositions.length; i++) {
        for (let j = i + 1; j < nodePositions.length; j++) {
            const node1 = nodePositions[i];
            const node2 = nodePositions[j];
            
            const distance = Math.sqrt(
                Math.pow(node2.x - node1.x, 2) + 
                Math.pow(node2.y - node1.y, 2)
            );
            
            if (distance < connectionDistance) {
                createConnection(node1, node2);
            }
        }
    }

    
    updateChannelList();

}

function createConnection(fromNode, toNode) {
    const networkContainer = document.getElementById('telegram-network');
    const connection = document.createElement('div');
    connection.className = 'network-connection';
    
    const length = Math.sqrt(
        Math.pow(toNode.x - fromNode.x, 2) + 
        Math.pow(toNode.y - fromNode.y, 2)
    );
    const angle = Math.atan2(
        toNode.y - fromNode.y, 
        toNode.x - fromNode.x
    ) * 180 / Math.PI;
    
    connection.style.width = `${length}px`;
    connection.style.height = '3px';
    connection.style.left = `${fromNode.x + fromNode.width/2}px`;
    connection.style.top = `${fromNode.y + fromNode.height/2}px`;
    connection.style.transform = `rotate(${angle}deg)`;
    connection.style.transformOrigin = '0 0';
    connection.style.opacity = '0.6';
    connection.style.position = 'absolute';
    
    networkContainer.appendChild(connection);
}

function updateChannelList() {
    const channelList = document.querySelector('.channel-list');
    const channelListContainer = document.querySelector('.matched-channels');
    
    channelList.innerHTML = '';

    // Generate 6 unique IDs for matched channels
    const matchedIds = new Set(matchedNodeIndices);


    for (let i = 1; i <= MAX_MATCHED_CHANNELS; i++) {
        const channel = document.createElement('div');
        channel.className = 'channel';
        channel.dataset.id = i;

        const isMatched = matchedIds.has(i);
        const score = isMatched
            ? 90 + Math.floor(Math.random() * 11) // 90–100%
            : 50 + Math.floor(Math.random() * 40); // 50–89%

        channel.innerHTML = `
            <i class="fab fa-telegram"></i>
            <span>Channel ${i}</span>
            <div class="match-score">${score}%</div>
        `;

        channelList.appendChild(channel);
    }
    channelListContainer.style.display = 'grid';


}

// Fixed launchSingleAd with error handling
function launchSingleAd() {
    if (!isDemoRunning || reachedNodes.length >= NODES_TO_REACH) return;
    
    const portal = document.querySelector('.sonic-portal');
    if (!portal) return;
    
    const portalRect = portal.getBoundingClientRect();
    const portalX = portalRect.left + portalRect.width/2;
    const portalY = portalRect.top + portalRect.height/2;
    
    // Get top matched channels (limited to 6)
    const matchedChannels = Array.from(document.querySelectorAll('.channel'))
        .slice(0, MAX_MATCHED_CHANNELS);
    
    // Select next batch of unreached nodes (3-5 nodes per ad)
    const targets = [];
    const targetCount = 3 + Math.floor(Math.random() * 3);
    
    for (let i = 0; i < matchedChannels.length && targets.length < targetCount; i++) {
        const channel = matchedChannels[i];
        const nodeId = channel.dataset.id;
        if (!reachedNodes.includes(nodeId)) {
            targets.push(channel);
            reachedNodes.push(nodeId);
        }
    }
    
    if (targets.length === 0) return;
    
    // Create ad element
    const ad = document.createElement('div');
    ad.className = 'ad-item turbo';
    ad.innerHTML = '<i class="fas fa-bolt"></i>';
    ad.style.left = `${portalX}px`;
    ad.style.top = `${portalY}px`;
    ad.style.position = 'absolute';
    document.body.appendChild(ad);
    
    // Create trail (with null check)
    const trail = document.createElement('div');
    trail.className = 'ad-trail turbo';
    trail.style.position = 'absolute';
    document.body.appendChild(trail);
    
    let currentTarget = 0;
    
    function moveToNextTarget() {
        if (currentTarget >= targets.length || !isDemoRunning) {
            ad.remove();
            trail.remove();
            return;
        }
        
        const targetChannel = targets[currentTarget];
        const targetNode = document.querySelector(`.network-node[data-id="${targetChannel.dataset.id}"]`);
        
        if (!targetNode) {
            currentTarget++;
            moveToNextTarget();
            return;
        }
        
        const targetRect = targetNode.getBoundingClientRect();
        const targetX = targetRect.left + targetRect.width/2;
        const targetY = targetRect.top + targetRect.height/2;
        
        const speedMultiplier = 1 + (MAX_SPEED_MULTIPLIER - 1) * (reachedNodes.length / NODES_TO_REACH);
        
        moveAdToTarget(
            ad, 
            trail, 
            parseFloat(ad.style.left), 
            parseFloat(ad.style.top),
            targetX, 
            targetY, 
            targetNode, 
            () => {
                currentTarget++;
                moveToNextTarget();
            }, 
            speedMultiplier
        );
    }
    
    moveToNextTarget();
    
}

// Fixed moveAdToTarget with error handling
function moveAdToTarget(ad, trail, startX, startY, endX, endY, targetNode, callback, speedMultiplier = 1) {
    const duration = 300 / speedMultiplier;
    const startTime = performance.now();
    
    function animate(currentTime) {
        if (!isDemoRunning) {
            if (ad && ad.parentNode) ad.remove();
            if (trail && trail.parentNode) trail.remove();
            return;
        }
        
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const currentX = startX + (endX - startX) * progress;
        const currentY = startY + (endY - startY) * progress;
        
        if (ad) {
            ad.style.left = `${currentX}px`;
            ad.style.top = `${currentY}px`;
        }
        
        if (trail) {
            trail.style.left = `${currentX}px`;
            trail.style.top = `${currentY}px`;
            trail.style.opacity = 1 - progress;
        }
        
        if (progress < 1) {
            requestAnimationFrame(animate);
        } else {
            if (callback) callback();
        }
    }
    
    requestAnimationFrame(animate);
}

// Fixed launchAds function
function launchAds() {
    if (isDemoRunning) return;

    isDemoRunning = true; 
    reachedNodes = [];
    
    // Update UI
    document.getElementById('match-accuracy').textContent = '0%';
    document.getElementById('channels-matched').textContent = '0';
    
    // Reset nodes
    document.querySelectorAll('.network-node').forEach(node => {
        node.classList.remove('reached');
        node.innerHTML = '<i class="fab fa-telegram"></i>';
    });
    
    const adCount = BASE_AD_COUNT + Math.floor(NODES_TO_REACH / 4);
    
    for (let i = 0; i < adCount; i++) {
        setTimeout(() => {
            if (isDemoRunning && reachedNodes.length < NODES_TO_REACH) {
                launchSingleAd();
            }
        }, i * 300);
    }
    

    const statsInterval = setInterval(updateStats, 100);
    
    setTimeout(() => {
        isDemoRunning = false;
        clearInterval(statsInterval);

        // Final update
        updateStats();
    }, adCount * 500);
}

function updateStats() {
    const ratio = reachedNodes.length / NODES_TO_REACH;
    const accuracy = Math.min(100, Math.floor(ratio * (85 + Math.random() * 10))); // 85–95%
    const speed = Math.max(10, 100 - reachedNodes.length);
    
    document.getElementById('channels-matched').textContent = reachedNodes.length;
    document.getElementById('delivery-speed').textContent = `${speed}ms`;
    document.getElementById('match-accuracy').textContent = `${accuracy}%`;

    
}


// Move ad to target node
function moveAdToTarget(ad, trail, startX, startY, endX, endY, targetNode) {
    const distance = Math.sqrt(Math.pow(endX - startX, 2) + Math.pow(endY - startY, 2));
    const angle = Math.atan2(endY - startY, endX - startX);
    
    // Set trail position
    trail.style.left = `${startX}px`;
    trail.style.top = `${startY}px`;
    trail.style.width = '0px';
    trail.style.transform = `rotate(${angle}rad)`;
    
    // Animation
    let progress = 0;
    const speed = 0.02;
    const duration = 1000 - (maxCPM * 80); // Faster delivery with higher CPM
    
    function animate() {
        progress += speed;
        
        if (progress >= 1) {
            // Reached target
            ad.style.left = `${endX}px`;
            ad.style.top = `${endY}px`;
            ad.style.transform = 'translate(-50%, -50%) scale(0)';
            
            // Create delivered ad marker
            const delivered = document.createElement('div');
            delivered.className = 'delivered-ad';
            delivered.style.left = `${endX}px`;
            delivered.style.top = `${endY}px`;
            document.body.appendChild(delivered);
            
            // Show delivered marker
            setTimeout(() => {
                delivered.style.transform = 'translate(-50%, -50%) scale(1)';
                
                // Highlight the target node
                targetNode.classList.add('reached');
                
                // Zoom out effect
                setTimeout(() => {
                    const networkRect = networkContainer.getBoundingClientRect();
                    const networkCenterX = networkRect.left + networkRect.width / 2;
                    const networkCenterY = networkRect.top + networkRect.height / 2;
                    
                    // Create zoom out overlay
                    const zoomOut = document.createElement('div');
                    zoomOut.className = 'zoom-out-overlay';
                    zoomOut.style.position = 'fixed';
                    zoomOut.style.left = `${endX}px`;
                    zoomOut.style.top = `${endY}px`;
                    zoomOut.style.width = '0';
                    zoomOut.style.height = '0';
                    zoomOut.style.borderRadius = '50%';
                    zoomOut.style.background = 'rgba(0, 174, 255, 0.1)';
                    zoomOut.style.transform = 'translate(-50%, -50%)';
                    zoomOut.style.zIndex = '100';
                    document.body.appendChild(zoomOut);
                    
                    // Animate zoom out
                    const finalSize = Math.max(window.innerWidth, window.innerHeight) * 2;
                    const animation = zoomOut.animate([
                        { width: '0', height: '0', opacity: 1 },
                        { width: `${finalSize}px`, height: `${finalSize}px`, opacity: 0 }
                    ], {
                        duration: 1000,
                        easing: 'ease-out'
                    });
                    
                    animation.onfinish = () => {
                        zoomOut.remove();
                        delivered.remove();
                    };
                }, 500);
            }, 100);
            
            // Remove elements after animation
            setTimeout(() => {
                ad.remove();
                trail.remove();
            }, 1000);
            
            return;
        }
        
        const currentX = startX + (endX - startX) * progress;
        const currentY = startY + (endY - startY) * progress;
        
        ad.style.left = `${currentX}px`;
        ad.style.top = `${currentY}px`;
        
        // Update trail
        trail.style.width = `${distance * progress}px`;
        
        requestAnimationFrame(animate);
    }
    
    animate();
}

// Animate counter
function animateCounter(id, target, suffix = '') {
    const element = document.getElementById(id);
    let current = 0;
    const increment = target / 20;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            element.textContent = target + suffix;
            clearInterval(timer);
        } else {
            element.textContent = Math.floor(current) + suffix;
        }
    }, 50);
}

    animateStepsOnScroll();
    
    // Set initial styles for steps
    document.querySelectorAll('.step-card').forEach(step => {
        step.style.transform = 'translateY(30px)';
        step.style.opacity = '0';
        step.style.transition = 'all 0.5s ease';
    });
    
    // Pause/resume flow animation on hover
    const flowAd = document.querySelector('.flow-ad');
    const steps = document.querySelectorAll('.step-card');
    flowAd.addEventListener('mouseenter', () => {
        flowAd.style.animationPlayState = 'paused';
    });
    
    flowAd.addEventListener('mouseleave', () => {
        flowAd.style.animationPlayState = 'running';
    });

    steps.forEach(step => {
        step.addEventListener('mouseenter', () => {
            // pause flow animation
            flowAd.style.animationPlayState = 'paused';
            step.style.boxShadow = '0 10px 30px rgba(0, 174, 255, 0.3);';
        });
        
        step.addEventListener('mouseleave', () => {
            // resume flow animation
            flowAd.style.animationPlayState = 'running';
            step.style.boxShadow = 'none';
        });
    });


    const hamburger = document.getElementById('hamburger');
    const navLinks = document.querySelector('.nav-links');
    const navItems = document.querySelectorAll('.nav-links a');

    hamburger.addEventListener('click', () => {
        navLinks.classList.toggle('nav-active');
        hamburger.classList.toggle('open');
    });

    // Auto-close menu on nav item click (for mobile)
    navItems.forEach(link => {
        link.addEventListener('click', () => {
            if (navLinks.classList.contains('nav-active')) {
                navLinks.classList.remove('nav-active');
                hamburger.classList.remove('open');
            }
        });
    });
    
});