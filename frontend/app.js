const searchBtn = document.getElementById('searchBtn');
const searchInput = document.getElementById('searchInput');
const loadingState = document.getElementById('loadingState');
const loadingHeader = document.getElementById('loadingHeader');
const loadingText = document.getElementById('loadingText');
const resultsDashboard = document.getElementById('resultsDashboard');

// Chart instance
let priceChart = null;

const timelineStates = [
    {
        step: 1,
        header: "Spawning Scraper Engine",
        text: "Connecting to headless browser MCP stdio threads..."
    },
    {
        step: 2,
        header: "Running AI Extraction",
        text: "Analyzing DOM payload and schema layers with Groq LLaMA3..."
    },
    {
        step: 3,
        header: "Grounding Market Index",
        text: "Invoking Gemini Search to locate verified store comparisons..."
    },
    {
        step: 4,
        header: "MongoDB Atlas Synthesis",
        text: "Caching session keys and computing historical deviation statistics..."
    }
];

function updateTimeline(activeStep) {
    for (let i = 1; i <= 4; i++) {
        const stepEl = document.getElementById(`step${i}`);
        if (!stepEl) continue;
        
        if (i < activeStep) {
            stepEl.className = "step complete";
        } else if (i === activeStep) {
            stepEl.className = "step active";
        } else {
            stepEl.className = "step";
        }
    }
    
    const state = timelineStates[activeStep - 1];
    if (state) {
        loadingHeader.innerText = state.header;
        loadingText.innerText = state.text;
    }
}

searchBtn.addEventListener('click', async () => {
    const url = searchInput.value.trim();
    if (!url) return;

    // Reset UI
    resultsDashboard.classList.add('hidden');
    loadingState.classList.remove('hidden');
    updateTimeline(1);
    
    // Timeline animation simulation timing offsets
    let currentStep = 1;
    const stepIntervals = [
        setTimeout(() => { currentStep = 2; updateTimeline(2); }, 2000),
        setTimeout(() => { currentStep = 3; updateTimeline(3); }, 4500),
        setTimeout(() => { currentStep = 4; updateTimeline(4); }, 8500)
    ];

    const clearAllIntervals = () => {
        stepIntervals.forEach(clearTimeout);
    };

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        
        const data = await response.json();
        
        clearAllIntervals();
        
        // Fast forward timeline to complete before displaying results
        updateTimeline(5); 
        
        setTimeout(() => {
            loadingState.classList.add('hidden');
            if (data.error) {
                alert(data.error);
                return;
            }
            renderDashboard(data);
        }, 500);

    } catch (error) {
        clearAllIntervals();
        loadingState.classList.add('hidden');
        console.error("Frontend Error:", error);
        alert("Error analyzing link: " + error.message);
    }
});

function formatPriceINR(priceStr) {
    if (!priceStr || priceStr === "Price not listed") return "Price not listed";
    
    const numericValue = parseFloat(String(priceStr).replace(/[^0-9.]/g, ''));
    if (isNaN(numericValue) || numericValue === 0) return String(priceStr);
    
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 0
    }).format(numericValue);
}

function renderDashboard(data) {
    resultsDashboard.classList.remove('hidden');

    // 1. Title
    document.getElementById('productTitle').innerText = data.product_name || "Extracted Deal";

    // 2. Recommendation
    const recNode = document.getElementById('recDecision');
    const decision = data.recommendation.Action || data.recommendation.buy_or_wait_decision || "UNKNOWN";
    recNode.innerText = decision;
    
    const recBadge = document.getElementById('recBadge');
    
    if (decision.toLowerCase().includes('wait')) {
        recNode.style.color = '#f43f5e'; // Accent Rose
        recBadge.innerText = "Inflated Value";
        recBadge.style.color = '#f43f5e';
        recBadge.style.background = 'rgba(244, 63, 94, 0.08)';
    } else {
        recNode.style.color = '#10b981'; // Accent Emerald
        recBadge.innerText = "Value Deal";
        recBadge.style.color = '#10b981';
        recBadge.style.background = 'rgba(16, 185, 129, 0.08)';
    }
    
    document.getElementById('recReasoning').innerText = data.recommendation.Analysis || data.recommendation.reasoning || "No analysis provided.";

    // 3. Store Prices List
    const list = document.getElementById('storePricesList');
    list.innerHTML = '';
    
    const stores = data.extracted_data.stores || [];
    stores.forEach(store => {
        const li = document.createElement('li');
        const formattedPrice = formatPriceINR(store.price);
        
        let storeElement = `<span class="store-name">${store.store}</span>`;
        if (store.url) {
            storeElement = `<a href="${store.url}" target="_blank" class="store-link" title="Click to buy from ${store.store}">
                <span class="store-name">${store.store}</span>
                <svg class="external-link-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width: 14px; height: 14px; margin-left: 4px; display: inline-block; vertical-align: middle;">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                    <polyline points="15 3 21 3 21 9"></polyline>
                    <line x1="10" y1="14" x2="21" y2="3"></line>
                </svg>
            </a>`;
        }
        
        li.innerHTML = `${storeElement} <span class="store-price">${formattedPrice}</span>`;
        list.appendChild(li);
    });

    // 4. Chart.js History Data
    renderChart(data);
}

function renderChart(data) {
    const ctx = document.getElementById('historyChart').getContext('2d');
    
    if (priceChart) {
        priceChart.destroy();
    }

    // Get current best price
    let currentPriceStr = "0";
    if (data.extracted_data.stores && data.extracted_data.stores.length > 0) {
        currentPriceStr = data.extracted_data.stores[0].price;
    }
    const currentNumeric = parseFloat(String(currentPriceStr).replace(/[^0-9.]/g, '')) || 0;

    const hist = data.history_data;
    const avg = (hist && hist.average_price && hist.average_price !== "Unknown") ? hist.average_price : currentNumeric;
    const low = (hist && hist.all_time_lowest_price && hist.all_time_lowest_price !== "Unknown") ? hist.all_time_lowest_price : currentNumeric;

    Chart.defaults.color = '#c084fc';
    Chart.defaults.font.family = "'Inter', sans-serif";

    priceChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['All-Time Lowest', 'Historical Average', 'Current Best Offer'],
            datasets: [{
                label: 'Price in INR',
                data: [low, avg, currentNumeric],
                backgroundColor: [
                    'rgba(0, 240, 255, 0.6)',  // Neon Cyan
                    'rgba(139, 92, 246, 0.6)', // Violet
                    'rgba(255, 0, 127, 0.6)'   // Neon Pink
                ],
                borderColor: [
                    'rgba(0, 240, 255, 1)',
                    'rgba(139, 92, 246, 1)',
                    'rgba(255, 0, 127, 1)'
                ],
                borderWidth: 2,
                borderRadius: 4,
                barPercentage: 0.5,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    grid: { color: 'rgba(255, 0, 127, 0.08)' },
                    ticks: {
                        callback: function(value) {
                            return '₹' + value.toLocaleString('en-IN');
                        }
                    }
                },
                x: {
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    padding: 12,
                    backgroundColor: '#0c0714',
                    borderColor: 'rgba(255, 0, 127, 0.3)',
                    borderWidth: 1.5,
                    titleColor: '#fff',
                    bodyColor: '#c084fc',
                    callbacks: {
                        label: function(context) {
                            return ' Price: ₹' + context.parsed.y.toLocaleString('en-IN');
                        }
                    }
                }
            }
        }
    });
}
