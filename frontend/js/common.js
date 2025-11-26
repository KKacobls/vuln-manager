/**
 * 漏洞報告管理系統 - 通用 JavaScript
 */

// ==================== API 工具函數 ====================
// 注意：此檔案需要在 config.js 之後載入

async function api(endpoint, options = {}) {
    // 如果 endpoint 已經是完整 URL，直接使用
    let url = endpoint.startsWith('http') ? endpoint : endpoint;
    
    // 如果不是完整 URL，使用 config.js 的 API_BASE
    if (!url.startsWith('http')) {
        // 確保 endpoint 以 / 開頭
        if (!endpoint.startsWith('/')) {
            endpoint = '/' + endpoint;
        }
        url = API_BASE + endpoint;
    }
    
    const config = {
        method: options.method || 'GET',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    };
    
    // 如果有 body，轉換為 JSON（如果尚未是字串）
    if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
        config.body = JSON.stringify(config.body);
    }
    
    try {
        const response = await fetch(url, config);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || '請求失敗');
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ==================== Toast 通知 ====================

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ==================== Modal 控制 ====================

function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// 點擊背景關閉 Modal
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-backdrop')) {
        e.target.closest('.modal').classList.remove('active');
    }
});

// ESC 鍵關閉 Modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal.active').forEach(modal => {
            modal.classList.remove('active');
        });
    }
});

// ==================== 檔案上傳 ====================

document.addEventListener('DOMContentLoaded', () => {
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const btnImport = document.getElementById('btn-import');
    
    if (btnImport) {
        btnImport.addEventListener('click', () => openModal('import-modal'));
    }
    
    if (uploadZone && fileInput) {
        // 點擊上傳區域
        uploadZone.addEventListener('click', () => fileInput.click());
        
        // 拖放
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });
        
        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });
        
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length) {
                handleFileUpload(files);
            }
        });
        
        // 選擇檔案
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) {
                handleFileUpload(fileInput.files);
            }
        });
    }
});

async function handleFileUpload(files) {
    const progressDiv = document.getElementById('upload-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const resultsDiv = document.getElementById('upload-results');
    
    progressDiv.style.display = 'block';
    resultsDiv.innerHTML = '';
    
    const formData = new FormData();
    
    if (files.length === 1) {
        // 單檔上傳
        formData.append('file', files[0]);
        
        try {
            progressText.textContent = `上傳中: ${files[0].name}`;
            progressFill.style.width = '50%';
            
            const result = await fetch(`${API_BASE}/import`, {
                method: 'POST',
                body: formData
            }).then(r => r.json());
            
            progressFill.style.width = '100%';
            
            if (result.success) {
                progressText.textContent = '上傳成功！';
                showToast(`成功匯入: ${result.site_url}`);
                resultsDiv.innerHTML = `
                    <div class="toast success" style="position: static; animation: none;">
                        ✅ ${files[0].name} - <a href="report_detail.html?id=${result.report_id}">查看報告</a>
                    </div>
                `;
                
                // 刷新頁面資料
                if (typeof loadDashboard === 'function') loadDashboard();
                if (typeof loadReports === 'function') loadReports();
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            progressText.textContent = '上傳失敗';
            showToast(error.message, 'error');
        }
    } else {
        // 多檔上傳
        for (let file of files) {
            formData.append('files', file);
        }
        
        try {
            progressText.textContent = `上傳中: ${files.length} 個檔案`;
            progressFill.style.width = '50%';
            
            const result = await fetch(`${API_BASE}/import/bulk`, {
                method: 'POST',
                body: formData
            }).then(r => r.json());
            
            progressFill.style.width = '100%';
            progressText.textContent = '上傳完成';
            
            let html = '';
            result.imported.forEach(item => {
                html += `<div class="toast success" style="position: static; animation: none; margin-bottom: 8px;">
                    ✅ ${item.file} - <a href="report_detail.html?id=${item.report_id}">查看</a>
                </div>`;
            });
            result.errors.forEach(item => {
                html += `<div class="toast error" style="position: static; animation: none; margin-bottom: 8px;">
                    ❌ ${item.file}: ${item.error}
                </div>`;
            });
            resultsDiv.innerHTML = html;
            
            showToast(`成功匯入 ${result.imported.length} 個, 失敗 ${result.errors.length} 個`);
            
            if (typeof loadDashboard === 'function') loadDashboard();
            if (typeof loadReports === 'function') loadReports();
        } catch (error) {
            progressText.textContent = '上傳失敗';
            showToast(error.message, 'error');
        }
    }
}

// ==================== 工具函數 ====================

function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getSeverityEmoji(severity) {
    const map = {
        'High': '🔴',
        'Medium': '🟠',
        'Low': '🟡',
        'Informational': '🔵'
    };
    return map[severity] || '⚪';
}

function getStatusEmoji(status) {
    const map = {
        'pending': '⏳',
        'in_progress': '🔄',
        'fixed': '✅',
        'wont_fix': '🚫',
        'false_positive': '❌'
    };
    return map[status] || '❓';
}

function getStatusLabel(status) {
    const map = {
        'pending': '待處理',
        'in_progress': '處理中',
        'fixed': '已修復',
        'wont_fix': '不修復',
        'false_positive': '誤報'
    };
    return map[status] || status;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function truncate(str, len = 50) {
    if (!str) return '';
    return str.length > len ? str.substring(0, len) + '...' : str;
}
