/**
 * TAVISO - Da Nang Traffic Monitoring System
 * Frontend JavaScript
 */

// ========== CONFIGURATION ==========
const CONFIG = {
    API_BASE: '',
    UPDATE_INTERVAL: 3000, // 3 seconds
    REALTIME_LIMIT: 5,
    ITEMS_PER_PAGE: 15,
    RETRY_DELAY: 2000,
    FPS_UPDATE_INTERVAL: 1000
};

// ========== STATE ==========
const state = {
    currentPage: 1,
    lastUpdateTime: null,
    frameCount: 0,
    lastFpsUpdate: Date.now(),
    isStreamConnected: false
};

// ========== INITIALIZATION ==========
document.addEventListener('DOMContentLoaded', function () {
    console.log('🚀 TAVISO System Initialized');

    // Load initial data
    refreshData();

    // Auto-refresh data
    setInterval(refreshData, CONFIG.UPDATE_INTERVAL);

    // Setup stream monitoring
    setupStreamErrorHandling();

    // FPS counter
    setInterval(updateFPS, CONFIG.FPS_UPDATE_INTERVAL);

    console.log('✓ All systems ready');
});

// ========== DATA FETCHING ==========

/**
 * Refresh all data from API
 */
async function refreshData() {
    try {
        await Promise.all([
            fetchStats(),
            fetchRealtimePlates(),
            fetchHistoryPlates()
        ]);

        updateLastUpdateTime();
    } catch (error) {
        console.error('❌ Error refreshing data:', error);
    }
}

/**
 * Fetch statistics from API
 */
async function fetchStats() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/stats`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();

        // Update statistics cards
        updateElement('total-detections', data.total_detections || 0);
        updateElement('today-detections', data.today_detections || 0);
        updateElement('hour-detections', data.this_hour_detections || 0);
        updateElement('unique-plates', data.unique_plates || 0);

        // Update last detection
        if (data.last_detection) {
            const lastTime = formatVietnameseDateTime(data.last_detection);
            updateElement('last-detection', lastTime);
        } else {
            updateElement('last-detection', 'Chưa có dữ liệu');
        }

    } catch (error) {
        console.error('❌ Error fetching stats:', error);
    }
}

/**
 * Fetch real-time plates (last N detections)
 */
async function fetchRealtimePlates() {
    try {
        const response = await fetch(
            `${CONFIG.API_BASE}/api/plates?limit=${CONFIG.REALTIME_LIMIT}&offset=0`
        );

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const plates = await response.json();
        displayRealtimePlates(plates);

    } catch (error) {
        console.error('❌ Error fetching realtime plates:', error);
        showTableError('realtime-tbody', 3, 'Lỗi tải dữ liệu');
    }
}

/**
 * Fetch history plates (paginated)
 */
async function fetchHistoryPlates() {
    try {
        const offset = (state.currentPage - 1) * CONFIG.ITEMS_PER_PAGE;
        const response = await fetch(
            `${CONFIG.API_BASE}/api/plates?limit=${CONFIG.ITEMS_PER_PAGE}&offset=${offset}`
        );

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const plates = await response.json();
        displayHistoryPlates(plates);

    } catch (error) {
        console.error('❌ Error fetching history plates:', error);
        showTableError('history-tbody', 4, 'Lỗi tải dữ liệu');
    }
}

// ========== DATA DISPLAY ==========

/**
 * Display realtime plates in table
 */
function displayRealtimePlates(plates) {
    const tbody = document.getElementById('realtime-tbody');

    if (!plates || plates.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="loading">Chưa có phát hiện gần đây</td></tr>';
        return;
    }

    tbody.innerHTML = plates.map(plate => `
        <tr>
            <td><strong style="color: var(--primary-light); font-size: 1rem;">${escapeHtml(plate.plate_number)}</strong></td>
            <td>${formatVietnameseTime(plate.timestamp)}</td>
            <td>${formatConfidence(plate.confidence)}</td>
        </tr>
    `).join('');
}

/**
 * Display history plates in table
 */
function displayHistoryPlates(plates) {
    const tbody = document.getElementById('history-tbody');

    if (!plates || plates.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="loading">Chưa có dữ liệu lịch sử</td></tr>';
        updatePaginationButtons(0);
        return;
    }

    tbody.innerHTML = plates.map(plate => `
        <tr>
            <td><span style="color: var(--text-muted);">#${plate.id}</span></td>
            <td><strong>${escapeHtml(plate.plate_number)}</strong></td>
            <td>${formatVietnameseDateTime(plate.timestamp)}</td>
            <td>${formatConfidence(plate.confidence)}</td>
        </tr>
    `).join('');

    updatePaginationButtons(plates.length);
}

// ========== FORMATTING UTILITIES ==========

/**
 * Format timestamp to Vietnamese time (HH:mm:ss)
 */
function formatVietnameseTime(timestamp) {
    if (!timestamp) return '--:--:--';

    const date = new Date(timestamp);
    return date.toLocaleTimeString('vi-VN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

/**
 * Format timestamp to Vietnamese datetime
 */
function formatVietnameseDateTime(timestamp) {
    if (!timestamp) return 'Không xác định';

    const date = new Date(timestamp);
    return date.toLocaleString('vi-VN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

/**
 * Format confidence as percentage with color
 */
function formatConfidence(confidence) {
    if (confidence === null || confidence === undefined) return '--';

    const percent = (confidence * 100).toFixed(0);
    let color;

    if (percent >= 80) {
        color = 'var(--accent)';
    } else if (percent >= 60) {
        color = 'var(--warning)';
    } else {
        color = 'var(--danger)';
    }

    return `<span style="color: ${color}; font-weight: 700; font-size: 0.9rem;">${percent}%</span>`;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

// ========== PAGINATION ==========

/**
 * Update pagination button states
 */
function updatePaginationButtons(count) {
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const pageInfo = document.getElementById('page-info');

    if (!prevBtn || !nextBtn || !pageInfo) return;

    prevBtn.disabled = state.currentPage === 1;
    nextBtn.disabled = count < CONFIG.ITEMS_PER_PAGE;

    pageInfo.innerHTML = `Trang <strong>${state.currentPage}</strong>`;
}

/**
 * Navigate to previous page
 */
function prevPage() {
    if (state.currentPage > 1) {
        state.currentPage--;
        fetchHistoryPlates();
    }
}

/**
 * Navigate to next page
 */
function nextPage() {
    state.currentPage++;
    fetchHistoryPlates();
}

// ========== STREAM HANDLING ==========

/**
 * Setup stream error handling and reconnection
 */
function setupStreamErrorHandling() {
    const streamImg = document.getElementById('video-stream');

    if (!streamImg) {
        console.warn('⚠️ Stream image element not found');
        return;
    }

    // Handle stream errors
    streamImg.onerror = function () {
        console.warn('⚠️ Stream connection lost, retrying...');
        state.isStreamConnected = false;

        // Retry after delay
        setTimeout(() => {
            streamImg.src = '/stream?' + Date.now();
        }, CONFIG.RETRY_DELAY);
    };

    // Handle successful stream load
    streamImg.onload = function () {
        if (!state.isStreamConnected) {
            console.log('✓ Stream connected');
            state.isStreamConnected = true;
        }
        state.frameCount++;
    };
}

/**
 * Update FPS counter
 */
function updateFPS() {
    const now = Date.now();
    const elapsed = (now - state.lastFpsUpdate) / 1000;
    const fps = Math.round(state.frameCount / elapsed);

    const fpsElement = document.getElementById('fps-counter');
    if (fpsElement) {
        fpsElement.textContent = `FPS: ${state.isStreamConnected ? fps : '--'}`;
    }

    // Reset counters
    state.frameCount = 0;
    state.lastFpsUpdate = now;
}

// ========== UI UTILITIES ==========

/**
 * Update last update time display
 */
function updateLastUpdateTime() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('vi-VN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });

    updateElement('last-update', timeStr);
    state.lastUpdateTime = now;
}

/**
 * Update element text content safely
 */
function updateElement(id, content) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = content;
    }
}

/**
 * Show error message in table
 */
function showTableError(tbodyId, colspan, message) {
    const tbody = document.getElementById(tbodyId);
    if (tbody) {
        tbody.innerHTML = `<tr><td colspan="${colspan}" class="loading">${escapeHtml(message)}</td></tr>`;
    }
}

// ========== EXPORT FUNCTIONALITY (Optional) ==========

/**
 * Export data to CSV
 */
async function exportToCSV() {
    try {
        const response = await fetch(`${CONFIG.API_BASE}/api/plates?limit=10000&offset=0`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const plates = await response.json();

        // Create CSV content
        let csv = 'ID,Biển số,Thời gian,Độ tin cậy\n';
        plates.forEach(plate => {
            csv += `${plate.id},"${plate.plate_number}","${plate.timestamp}",${plate.confidence}\n`;
        });

        // Download file
        const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `taviso_export_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();

        console.log('✓ Exported to CSV successfully');
    } catch (error) {
        console.error('❌ Export error:', error);
        alert('Lỗi khi xuất dữ liệu. Vui lòng thử lại.');
    }
}

// ========== KEYBOARD SHORTCUTS (Optional) ==========

document.addEventListener('keydown', function (e) {
    // Ctrl/Cmd + R: Refresh data
    if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
        e.preventDefault();
        refreshData();
        console.log('🔄 Manual refresh triggered');
    }

    // Arrow keys for pagination
    if (e.key === 'ArrowLeft') {
        prevPage();
    } else if (e.key === 'ArrowRight') {
        nextPage();
    }
});

// Make functions globally accessible
window.refreshData = refreshData;
window.prevPage = prevPage;
window.nextPage = nextPage;
window.exportToCSV = exportToCSV;
