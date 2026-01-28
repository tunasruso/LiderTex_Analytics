// API Base URL - relative path works for same-origin (Vercel)
// For local dev with separate ports, you might need to adjust or use proxy
const API_BASE = '/api';

// DOM Elements
const els = {
    status: document.getElementById('status-indicator'),
    totalRevenue: document.getElementById('total-revenue'),
    totalTransactions: document.getElementById('total-transactions'),
    topRegion: document.getElementById('top-region'),
    tableBody: document.getElementById('transactions-table-body'),
    trendChartCtx: document.getElementById('trendChart').getContext('2d'),
    regionChartCtx: document.getElementById('regionChart').getContext('2d')
};

// State
let charts = {};

// Helper: Format Currency
const formatCurrency = (num) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(num);
};

// 1. Fetch Health Check
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (response.ok) {
            els.status.textContent = 'System Online';
            els.status.className = 'text-sm px-3 py-1 rounded-full bg-green-100 text-green-800';
            return true;
        }
    } catch (e) {
        console.error('Health check failed', e);
        els.status.textContent = 'System Offline';
        els.status.className = 'text-sm px-3 py-1 rounded-full bg-red-100 text-red-800';
    }
    return false;
}

// 2. Fetch Dashboard Data
async function loadDashboardData() {
    try {
        // Fetch stats
        const statsRes = await fetch(`${API_BASE}/stats`);
        const statsData = await statsRes.json();

        // Fetch recent data list
        const listRes = await fetch(`${API_BASE}/data`);
        const listData = await listRes.json();

        updateKPIs(statsData, listData.length);
        renderCharts(statsData);
        renderTable(listData);

    } catch (error) {
        console.error('Error loading data:', error);
        els.tableBody.innerHTML = `<tr><td colspan="5" class="px-6 py-4 text-center text-red-500">Error loading data. Verify backend connection.</td></tr>`;
    }
}

// 3. Update Metrics
function updateKPIs(stats, count) {
    els.totalRevenue.textContent = formatCurrency(stats.total_revenue || 0);
    els.totalTransactions.textContent = count;

    // Find top region
    if (stats.by_region && stats.by_region.length > 0) {
        // Sort just in case backend didn't
        const top = stats.by_region.sort((a, b) => b.amount - a.amount)[0];
        els.topRegion.textContent = top.region;
    } else {
        els.topRegion.textContent = 'N/A';
    }
}

// 4. Render Charts
function renderCharts(stats) {
    // Destroy existing charts if reloading
    if (charts.trend) charts.trend.destroy();
    if (charts.region) charts.region.destroy();

    // Trend Chart (Line)
    const trendLabels = stats.trend.map(item => item.date);
    const trendValues = stats.trend.map(item => item.amount);

    charts.trend = new Chart(els.trendChartCtx, {
        type: 'line',
        data: {
            labels: trendLabels,
            datasets: [{
                label: 'Sales Revenue',
                data: trendValues,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } }
        }
    });

    // Region Chart (Bar)
    const regLabels = stats.by_region.map(r => r.region);
    const regValues = stats.by_region.map(r => r.amount);

    charts.region = new Chart(els.regionChartCtx, {
        type: 'bar',
        data: {
            labels: regLabels,
            datasets: [{
                label: 'Revenue by Region',
                data: regValues,
                backgroundColor: [
                    '#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

// 5. Render Table
function renderTable(data) {
    if (!data || data.length === 0) {
        els.tableBody.innerHTML = `<tr><td colspan="5" class="px-6 py-4 text-center text-gray-500">No transactions found.</td></tr>`;
        return;
    }

    // Show top 10 recent
    const recent = data.slice(0, 10);

    els.tableBody.innerHTML = recent.map(row => `
        <tr class="hover:bg-gray-50 transition">
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">#${row.id}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${row.date}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">${row.product}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${row.region}</td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-bold text-gray-900">${formatCurrency(row.amount)}</td>
        </tr>
    `).join('');
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    checkHealth().then(isOnline => {
        if (isOnline) {
            loadDashboardData();
        }
    });
});
