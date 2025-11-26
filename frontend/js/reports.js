/**
 * 報告列表頁面 JavaScript
 */

let currentPage = 1;
let currentSearch = '';

document.addEventListener('DOMContentLoaded', () => {
    loadReports();
    
    // 搜尋 Enter 鍵
    document.getElementById('search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchReports();
    });
});

async function loadReports(page = 1) {
    currentPage = page;
    const tbody = document.getElementById('reports-tbody');
    tbody.innerHTML = '<tr><td colspan="5" class="loading">載入中...</td></tr>';
    
    try {
        const params = new URLSearchParams({
            page: page,
            per_page: 20
        });
        
        if (currentSearch) {
            params.append('search', currentSearch);
        }
        
        const data = await api(`/reports?${params}`);
        
        if (!data.reports.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="loading">尚無報告</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.reports.map(report => `
            <tr>
                <td>${report.id}</td>
                <td>
                    <a href="report_detail.html?id=${report.id}">${escapeHtml(report.site_url || report.file_name || '未知')}</a>
                    ${report.notes ? '<span title="有備註">📝</span>' : ''}
                </td>
                <td>${formatDate(report.imported_at)}</td>
                <td>
                    ${report.stats.High ? `<span class="stat-badge high">${report.stats.High} High</span>` : ''}
                    ${report.stats.Medium ? `<span class="stat-badge medium">${report.stats.Medium} Med</span>` : ''}
                    ${report.stats.Low ? `<span class="stat-badge low">${report.stats.Low} Low</span>` : ''}
                    ${report.stats.Informational ? `<span class="stat-badge info">${report.stats.Informational} Info</span>` : ''}
                </td>
                <td>
                    <button class="btn btn-xs" onclick="viewReport(${report.id})">查看</button>
                    <button class="btn btn-xs btn-danger" onclick="deleteReport(${report.id})">刪除</button>
                </td>
            </tr>
        `).join('');
        
        // 更新分頁
        updatePagination(data.current_page, data.pages, data.total);
        
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="5" class="loading">載入失敗: ${error.message}</td></tr>`;
        showToast('載入報告失敗', 'error');
    }
}

function updatePagination(current, total, count) {
    const container = document.getElementById('pagination');
    
    if (total <= 1) {
        container.innerHTML = `<span style="color: var(--text-muted);">共 ${count} 筆</span>`;
        return;
    }
    
    let html = `<span style="color: var(--text-muted); margin-right: 16px;">共 ${count} 筆</span>`;
    
    // 上一頁
    html += `<button class="btn btn-sm" ${current === 1 ? 'disabled' : ''} onclick="loadReports(${current - 1})">←</button>`;
    
    // 頁碼
    for (let i = 1; i <= total; i++) {
        if (i === 1 || i === total || (i >= current - 2 && i <= current + 2)) {
            html += `<button class="btn btn-sm ${i === current ? 'active' : ''}" onclick="loadReports(${i})">${i}</button>`;
        } else if (i === current - 3 || i === current + 3) {
            html += '<span style="color: var(--text-muted);">...</span>';
        }
    }
    
    // 下一頁
    html += `<button class="btn btn-sm" ${current === total ? 'disabled' : ''} onclick="loadReports(${current + 1})">→</button>`;
    
    container.innerHTML = html;
}

function searchReports() {
    currentSearch = document.getElementById('search-input').value.trim();
    loadReports(1);
}

function applyFilters() {
    // 篩選功能可以在這裡擴展
    loadReports(1);
}

function resetFilters() {
    document.getElementById('filter-severity').value = '';
    document.getElementById('filter-status').value = '';
    document.getElementById('search-input').value = '';
    currentSearch = '';
    loadReports(1);
}

function viewReport(id) {
    window.location.href = `report_detail.html?id=${id}`;
}

async function deleteReport(id) {
    if (!confirm('確定要刪除此報告嗎？此操作無法復原。')) {
        return;
    }
    
    try {
        await api(`/reports/${id}`, { method: 'DELETE' });
        showToast('報告已刪除');
        loadReports(currentPage);
    } catch (error) {
        showToast('刪除失敗: ' + error.message, 'error');
    }
}
