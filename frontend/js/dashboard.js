/**
 * 儀表板頁面 JavaScript
 */

document.addEventListener('DOMContentLoaded', loadDashboard);

async function loadDashboard() {
    try {
        const data = await api('/dashboard/stats');
        
        // 更新統計卡片
        document.getElementById('stat-reports').textContent = data.total_reports;
        document.getElementById('stat-vulns').textContent = data.total_vulnerabilities;
        document.getElementById('stat-instances').textContent = data.total_instances;
        document.getElementById('stat-fixed').textContent = data.status_stats.fixed || 0;
        
        // 更新嚴重等級圖表
        updateSeverityChart(data.severity_stats);
        
        // 更新修復狀態圓環圖
        updateStatusDonut(data.status_stats);
        
        // 更新最近報告
        updateRecentReports(data.recent_reports);
        
    } catch (error) {
        showToast('載入儀表板失敗: ' + error.message, 'error');
    }
}

function updateSeverityChart(stats) {
    const total = Object.values(stats).reduce((a, b) => a + b, 0) || 1;
    
    const severities = ['High', 'Medium', 'Low', 'Informational'];
    const barIds = ['bar-high', 'bar-medium', 'bar-low', 'bar-info'];
    const countIds = ['count-high', 'count-medium', 'count-low', 'count-info'];
    
    severities.forEach((sev, i) => {
        const count = stats[sev] || 0;
        const percent = (count / total) * 100;
        
        // 動畫效果
        setTimeout(() => {
            document.getElementById(barIds[i]).style.width = `${percent}%`;
        }, i * 100);
        
        document.getElementById(countIds[i]).textContent = count;
    });
}

function updateStatusDonut(stats) {
    const total = stats.total || 1;
    const fixed = stats.fixed || 0;
    const progress = stats.in_progress || 0;
    const pending = stats.pending || 0;
    
    const circumference = 2 * Math.PI * 40; // r=40
    
    // 計算各段長度
    const fixedLen = (fixed / total) * circumference;
    const progressLen = (progress / total) * circumference;
    const pendingLen = (pending / total) * circumference;
    
    // 更新 SVG
    const donutFixed = document.getElementById('donut-fixed');
    const donutProgress = document.getElementById('donut-progress');
    const donutPending = document.getElementById('donut-pending');
    
    // 設定動畫
    setTimeout(() => {
        donutFixed.style.strokeDasharray = `${fixedLen} ${circumference}`;
        donutFixed.style.strokeDashoffset = '0';
    }, 100);
    
    setTimeout(() => {
        donutProgress.style.strokeDasharray = `${progressLen} ${circumference}`;
        donutProgress.style.strokeDashoffset = `-${fixedLen}`;
    }, 200);
    
    setTimeout(() => {
        donutPending.style.strokeDasharray = `${pendingLen} ${circumference}`;
        donutPending.style.strokeDashoffset = `-${fixedLen + progressLen}`;
    }, 300);
    
    // 更新百分比
    const percent = Math.round((fixed / total) * 100);
    document.getElementById('donut-percent').textContent = `${percent}%`;
}

function updateRecentReports(reports) {
    const container = document.getElementById('recent-reports');
    
    if (!reports.length) {
        container.innerHTML = '<div class="empty-state"><p>尚無報告</p></div>';
        return;
    }
    
    container.innerHTML = reports.map(report => `
        <a href="report_detail.html?id=${report.id}" class="report-item">
            <div class="report-item-info">
                <div class="report-item-url">${escapeHtml(report.site_url || '未知網站')}</div>
                <div class="report-item-time">${formatDate(report.imported_at)}</div>
            </div>
            <div class="report-item-stats">
                ${report.stats.High ? `<span class="stat-badge high">${report.stats.High}</span>` : ''}
                ${report.stats.Medium ? `<span class="stat-badge medium">${report.stats.Medium}</span>` : ''}
                ${report.stats.Low ? `<span class="stat-badge low">${report.stats.Low}</span>` : ''}
                ${report.stats.Informational ? `<span class="stat-badge info">${report.stats.Informational}</span>` : ''}
            </div>
        </a>
    `).join('');
}
