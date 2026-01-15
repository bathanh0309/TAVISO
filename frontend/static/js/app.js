/**
 * TAVISO - Traffic Violation Detection System
 * Frontend JavaScript for violation display
 */

// Configuration
const CONFIG = {
    API_BASE: '',
    REFRESH_INTERVAL: 3000,  // 3 seconds
    HISTORY_PAGE_SIZE: 20
};

// State
let currentPage = 1;
let totalViolations = 0;
let lastViolationId = 0;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('TAVISO Dashboard initializing...');

    // Initial data load
    refreshData();

    // Start auto-refresh
    setInterval(refreshData, CONFIG.REFRESH_INTERVAL);

    // Update clock
    updateClock();
    setInterval(updateClock, 1000);
});

/**
 * Refresh all data
 */
async function refreshData() {
    try {
        await Promise.all([
            loadViolationStats(),
            loadRealtimeViolations(),
            loadViolationHistory()
        ]);
    } catch (error) {
        console.error('Error refreshing data:', error);
    }
}

/**
 * Load violation statistics
 */
async function loadViolationStats() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/violations/stats`);
        if (!response.ok) throw new Error('Failed to fetch stats');

        const stats = await response.json();

        // Update stat cards
        updateElement('total-violations', stats.total_violations);
        updateElement('today-violations', stats.today_violations);
        updateElement('wrong-way-count', stats.wrong_way_count);
        updateElement('speeding-count', stats.speeding_count);

        // Update last violation display
        if (stats.last_violation) {
            const last = stats.last_violation;
            updateElement('last-violation',
                `${last.license_plate} - ${last.violation_type_vi} (${last.time})`
            );
        }

    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

/**
 * Load realtime violations
 */
async function loadRealtimeViolations() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/violations/realtime?limit=10`);
        if (!response.ok) throw new Error('Failed to fetch realtime violations');

        const data = await response.json();
        const tbody = document.getElementById('realtime-tbody');

        if (!data.violations || data.violations.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" class="loading">Chưa có vi phạm nào</td>
                </tr>
            `;
            return;
        }

        let html = '';
        data.violations.forEach((v, index) => {
            const isNew = v.id > lastViolationId;
            html += `
                <tr class="${isNew ? 'new-violation' : ''}">
                    <td>${v.date}</td>
                    <td>${v.time}</td>
                    <td><strong>${v.license_plate}</strong></td>
                    <td>${getViolationBadge(v.violation_type_vi)}</td>
                </tr>
            `;
        });

        tbody.innerHTML = html;

        // Update last violation ID for animation
        if (data.violations.length > 0) {
            lastViolationId = Math.max(lastViolationId, data.violations[0].id);
        }

        totalViolations = data.total_count;

    } catch (error) {
        console.error('Error loading realtime violations:', error);
    }
}

/**
 * Load violation history with pagination
 */
async function loadViolationHistory() {
    try {
        const offset = (currentPage - 1) * CONFIG.HISTORY_PAGE_SIZE;
        const response = await fetch(
            `${CONFIG.API_BASE}/api/violations?limit=${CONFIG.HISTORY_PAGE_SIZE}&offset=${offset}`
        );
        if (!response.ok) throw new Error('Failed to fetch history');

        const violations = await response.json();
        const tbody = document.getElementById('history-tbody');

        if (violations.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="loading">Không có dữ liệu</td>
                </tr>
            `;
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
                    <td>${getViolationBadge(v.violation_type_vi)}</td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
        updatePagination(violations.length);

    } catch (error) {
        console.error('Error loading history:', error);
    }
}

/**
 * Get HTML badge for violation type
 */
function getViolationBadge(violationType) {
    let className = '';

    if (violationType.includes('ngược chiều')) {
        className = 'wrong-way';
    } else if (violationType.includes('tốc độ')) {
        className = 'speeding';
    } else if (violationType.includes('vạch')) {
        className = 'line-crossing';
    }

    return `<span class="violation-badge ${className}">${violationType}</span>`;
}

/**
 * Update pagination controls
 */
function updatePagination(itemsLoaded) {
    const pageInfo = document.getElementById('page-info');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');

    pageInfo.innerHTML = `Trang <strong>${currentPage}</strong>`;

    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = itemsLoaded < CONFIG.HISTORY_PAGE_SIZE;
}

/**
 * Go to previous page
 */
function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        loadViolationHistory();
    }
}

/**
 * Go to next page
 */
function nextPage() {
    currentPage++;
    loadViolationHistory();
}

/**
 * Update element text content
 */
function updateElement(id, value) {
    const el = document.getElementById(id);
    if (el) {
        el.textContent = value;
    }
}

/**
 * Update clock display
 */
function updateClock() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('vi-VN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    updateElement('last-update', timeStr);
}

/**
 * Handle video stream errors
 */
document.getElementById('video-stream')?.addEventListener('error', function () {
    console.error('Video stream error');
    this.alt = 'Camera không khả dụng';
});

// Export functions for global access
window.refreshData = refreshData;
window.prevPage = prevPage;
window.nextPage = nextPage;
