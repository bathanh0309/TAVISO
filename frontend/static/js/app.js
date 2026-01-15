/**
 * TAVISO - Traffic Violation Detection System
 * Frontend JavaScript
 */

const CONFIG = {
    API_BASE: '',
    REFRESH_INTERVAL: 3000,
    HISTORY_PAGE_SIZE: 20
};

let currentPage = 1;
let lastViolationId = 0;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('TAVISO Dashboard starting...');

    // Ensure stream loads with cache-busting
    const streamImg = document.getElementById('video-stream');
    if (streamImg) {
        streamImg.src = `/stream?t=${Date.now()}`;
        console.log('Stream initialized:', streamImg.src);
    }

    refreshData();
    setInterval(refreshData, CONFIG.REFRESH_INTERVAL);
});

// Refresh all data
async function refreshData() {
    try {
        await Promise.all([
            loadRealtimeViolations(),
            loadViolationHistory()
        ]);
    } catch (error) {
        console.error('Error:', error);
    }
}

// Load realtime violations
async function loadRealtimeViolations() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/violations/realtime?limit=10`);
        const data = await response.json();
        const tbody = document.getElementById('realtime-tbody');

        if (!data.violations || data.violations.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="no-data">Chưa có vi phạm</td></tr>`;
            return;
        }

        let html = '';
        data.violations.forEach(v => {
            html += `
                <tr>
                    <td>${v.date}</td>
                    <td>${v.time}</td>
                    <td><strong>${v.license_plate}</strong></td>
                    <td>${v.violation_type_vi}</td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    } catch (error) {
        console.error('Error loading realtime:', error);
    }
}

// Load history
async function loadViolationHistory() {
    try {
        const offset = (currentPage - 1) * CONFIG.HISTORY_PAGE_SIZE;
        const response = await fetch(
            `${CONFIG.API_BASE}/api/violations?limit=${CONFIG.HISTORY_PAGE_SIZE}&offset=${offset}`
        );
        const violations = await response.json();
        const tbody = document.getElementById('history-tbody');

        if (violations.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="no-data">Không có dữ liệu</td></tr>`;
            updatePagination(0);
            return;
        }

        let html = '';
        violations.forEach(v => {
            html += `
                <tr>
                    <td>${v.id}</td>
                    <td>${v.date}</td>
                    <td>${v.time}</td>
                    <td><strong>${v.license_plate}</strong></td>
                    <td>${v.violation_type_vi}</td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
        updatePagination(violations.length);
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

// Pagination
function updatePagination(itemsLoaded) {
    const pageInfo = document.getElementById('page-info');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');

    pageInfo.innerHTML = `Trang <strong>${currentPage}</strong>`;
    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = itemsLoaded < CONFIG.HISTORY_PAGE_SIZE;
}

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        loadViolationHistory();
    }
}

function nextPage() {
    currentPage++;
    loadViolationHistory();
}

// Export
window.refreshData = refreshData;
window.prevPage = prevPage;
window.nextPage = nextPage;
