/**
 * 報告詳情頁面 JavaScript
 */

let reportData = null;
let selectedInstances = new Set();
let REPORT_ID = null;

document.addEventListener('DOMContentLoaded', () => {
    // 從 URL 參數取得 report_id
    const urlParams = new URLSearchParams(window.location.search);
    REPORT_ID = urlParams.get('id');
    if (!REPORT_ID) {
        showToast('缺少報告 ID', 'error');
        window.location.href = 'reports.html';
        return;
    }
    loadReportDetail();
});

async function loadReportDetail() {
    try {
        reportData = await api(`/reports/${REPORT_ID}`);
        
        // 更新標題
        document.getElementById('report-title').textContent = reportData.site_url || '報告詳情';
        
        // 更新資訊卡片
        document.getElementById('info-site-url').textContent = reportData.site_url || '-';
        document.getElementById('info-imported-at').textContent = formatDate(reportData.imported_at);
        document.getElementById('info-summary').textContent = reportData.summary_sequences || '-';
        document.getElementById('info-details').textContent = reportData.sequence_details || '-';
        
        // 更新備註
        document.getElementById('report-notes').value = reportData.notes || '';
        
        // 建構漏洞樹
        buildVulnTree(reportData.vulnerabilities);
        
        // 填充漏洞表格
        populateInstancesTable(reportData.vulnerabilities);
        
    } catch (error) {
        showToast('載入報告失敗: ' + error.message, 'error');
    }
}

// ==================== 漏洞樹 ====================

function buildVulnTree(vulnerabilities) {
    const container = document.getElementById('vuln-tree');
    
    if (!vulnerabilities.length) {
        container.innerHTML = '<div class="empty-state"><p>此報告無漏洞</p></div>';
        return;
    }
    
    // 按嚴重等級分組
    const grouped = {};
    const severityOrder = ['High', 'Medium', 'Low', 'Informational'];
    
    vulnerabilities.forEach(vuln => {
        if (!grouped[vuln.severity]) {
            grouped[vuln.severity] = [];
        }
        grouped[vuln.severity].push(vuln);
    });
    
    let html = '';
    severityOrder.forEach(severity => {
        if (!grouped[severity]) return;
        
        const vulns = grouped[severity];
        const totalInstances = vulns.reduce((sum, v) => sum + v.instance_count, 0);
        
        html += `
            <div class="tree-node">
                <div class="tree-node-header" onclick="toggleTreeNode(this)">
                    <span class="tree-toggle expanded">▶</span>
                    <span class="tree-icon">${getSeverityEmoji(severity)}</span>
                    <span class="tree-label">${severity}</span>
                    <span class="tree-count">${totalInstances}</span>
                </div>
                <div class="tree-children">
        `;
        
        vulns.forEach(vuln => {
            html += `
                <div class="tree-node">
                    <div class="tree-node-header" onclick="toggleTreeNode(this)" data-vuln-id="${vuln.id}">
                        <span class="tree-toggle expanded">▶</span>
                        <span class="tree-icon">📄</span>
                        <span class="tree-label" title="${escapeHtml(vuln.title)}">${truncate(vuln.title, 30)}</span>
                        <span class="tree-count">${vuln.instance_count}</span>
                    </div>
                    <div class="tree-children">
            `;
            
            vuln.instances.forEach(inst => {
                html += `
                    <div class="tree-node">
                        <div class="tree-node-header" onclick="selectInstance(${inst.id}, this)" data-instance-id="${inst.id}">
                            <span class="tree-toggle" style="visibility:hidden">▶</span>
                            <span class="tree-icon">${getStatusEmoji(inst.fix_status)}</span>
                            <span class="tree-label" title="${escapeHtml(inst.url)}">${truncate(inst.url, 40)}</span>
                        </div>
                    </div>
                `;
            });
            
            html += '</div></div>';
        });
        
        html += '</div></div>';
    });
    
    container.innerHTML = html;
}

function toggleTreeNode(header) {
    const toggle = header.querySelector('.tree-toggle');
    const children = header.nextElementSibling;
    
    if (children && children.classList.contains('tree-children')) {
        children.classList.toggle('collapsed');
        toggle.classList.toggle('expanded');
    }
}

function expandAll() {
    document.querySelectorAll('.tree-children').forEach(el => el.classList.remove('collapsed'));
    document.querySelectorAll('.tree-toggle').forEach(el => el.classList.add('expanded'));
}

function collapseAll() {
    document.querySelectorAll('.tree-children').forEach(el => el.classList.add('collapsed'));
    document.querySelectorAll('.tree-toggle').forEach(el => el.classList.remove('expanded'));
}

function selectInstance(instanceId, element) {
    // 移除其他選中狀態
    document.querySelectorAll('.tree-node-header.selected').forEach(el => el.classList.remove('selected'));
    element.classList.add('selected');
    
    // 找到對應的實例資料
    let instance = null;
    let vulnInfo = null;
    
    for (const vuln of reportData.vulnerabilities) {
        for (const inst of vuln.instances) {
            if (inst.id === instanceId) {
                instance = inst;
                vulnInfo = vuln;
                break;
            }
        }
        if (instance) break;
    }
    
    if (instance) {
        showInstanceDetail(instance, vulnInfo);
    }
}

function showInstanceDetail(instance, vulnInfo) {
    const container = document.getElementById('detail-content');
    const descText = vulnInfo.description || '無描述';
    
    container.innerHTML = `
        <div style="margin-bottom: var(--space-lg);">
            <span class="severity-badge ${vulnInfo.severity}">${getSeverityEmoji(vulnInfo.severity)} ${vulnInfo.severity}</span>
            <span class="status-badge ${instance.fix_status}" style="margin-left: 8px;">
                ${getStatusEmoji(instance.fix_status)} ${getStatusLabel(instance.fix_status)}
            </span>
        </div>
        
        <h4 style="margin-bottom: var(--space-sm);">${escapeHtml(vulnInfo.title)}</h4>
        <div class="desc-with-zoom">
            <p style="color: var(--text-secondary);">${escapeHtml(descText)}</p>
            //<button class="zoom-btn" onclick="openZoomModal('Description', '${escapeHtml(descText).replace(/'/g, "\\'")}')">🔍</button>
        </div>
        
        <div class="form-group" style="margin-top: var(--space-lg);">
            <label>URL</label>
            <div style="font-family: var(--font-mono); word-break: break-all; background: var(--bg-tertiary); padding: var(--space-sm); border-radius: var(--radius-sm);">
                ${escapeHtml(instance.url)}
            </div>
        </div>
        
        ${instance.method ? `
        <div class="form-group">
            <label>方法</label>
            <div>${escapeHtml(instance.method)}</div>
        </div>` : ''}
        
        ${instance.parameter ? `
        <div class="form-group">
            <label>Parameter</label>
            <div style="font-family: var(--font-mono);">${escapeHtml(instance.parameter)}</div>
        </div>` : ''}
        
        ${instance.attack ? `
        <div class="form-group">
            <label>攻擊</label>
            <div style="font-family: var(--font-mono); white-space: pre-wrap; background: var(--bg-tertiary); padding: var(--space-sm); border-radius: var(--radius-sm);">${escapeHtml(instance.attack)}</div>
        </div>` : ''}
        
        ${instance.evidence ? `
        <div class="form-group">
            <label>Evidence</label>
            <div style="font-family: var(--font-mono); white-space: pre-wrap; background: var(--bg-tertiary); padding: var(--space-sm); border-radius: var(--radius-sm); max-height: 200px; overflow-y: auto;">${escapeHtml(instance.evidence)}</div>
        </div>` : ''}
        
        ${instance.other_info ? `
        <div class="form-group">
            <label>Other Info</label>
            <div style="white-space: pre-wrap;">${escapeHtml(instance.other_info)}</div>
        </div>` : ''}
        
        ${instance.fix_notes ? `
        <div class="form-group">
            <label>修復備註</label>
            <div style="background: rgba(63, 185, 80, 0.1); padding: var(--space-sm); border-radius: var(--radius-sm);">${escapeHtml(instance.fix_notes)}</div>
        </div>` : ''}
        
        ${instance.fixed_by ? `
        <div class="form-group">
            <label>修復者</label>
            <div>${escapeHtml(instance.fixed_by)}</div>
        </div>` : ''}
        
        ${instance.fixed_at ? `
        <div class="form-group">
            <label>修復時間</label>
            <div>${formatDate(instance.fixed_at)}</div>
        </div>` : ''}
        
        <div style="margin-top: var(--space-lg);">
            <button class="btn btn-primary" onclick="openStatusModal(${instance.id})">更新狀態</button>
        </div>
    `;
}

// ==================== 漏洞表格 ====================

function populateInstancesTable(vulnerabilities) {
    const tbody = document.getElementById('instances-tbody');
    let html = '';
    
    vulnerabilities.forEach(vuln => {
        vuln.instances.forEach(inst => {
            html += `
                <tr>
                    <td><input type="checkbox" class="instance-checkbox" value="${inst.id}" onchange="updateSelection()"></td>
                    <td><span class="severity-badge ${vuln.severity}">${getSeverityEmoji(vuln.severity)}</span></td>
                    <td title="${escapeHtml(vuln.title)}">${truncate(vuln.title, 40)}</td>
                    <td title="${escapeHtml(inst.url)}" style="font-family: var(--font-mono); font-size: 12px;">${truncate(inst.url, 50)}</td>
                    <td><span class="status-badge ${inst.fix_status}">${getStatusEmoji(inst.fix_status)} ${getStatusLabel(inst.fix_status)}</span></td>
                    <td><button class="btn btn-xs" onclick="openStatusModal(${inst.id})">編輯</button></td>
                </tr>
            `;
        });
    });
    
    tbody.innerHTML = html || '<tr><td colspan="6" class="loading">無漏洞實例</td></tr>';
}

function toggleSelectAll() {
    const selectAll = document.getElementById('select-all');
    const checkboxes = document.querySelectorAll('.instance-checkbox');
    
    checkboxes.forEach(cb => {
        cb.checked = selectAll.checked;
    });
    
    updateSelection();
}

function updateSelection() {
    const checkboxes = document.querySelectorAll('.instance-checkbox:checked');
    selectedInstances = new Set(Array.from(checkboxes).map(cb => parseInt(cb.value)));
    
    const batchActions = document.getElementById('batch-actions');
    batchActions.style.display = selectedInstances.size > 0 ? 'flex' : 'none';
}

// ==================== 狀態更新 ====================

function openStatusModal(instanceId) {
    document.getElementById('status-instance-id').value = instanceId;
    
    // 找到對應的實例資料
    for (const vuln of reportData.vulnerabilities) {
        for (const inst of vuln.instances) {
            if (inst.id === instanceId) {
                document.getElementById('status-select').value = inst.fix_status;
                document.getElementById('status-fixed-by').value = inst.fixed_by || '';
                document.getElementById('status-notes').value = inst.fix_notes || '';
                break;
            }
        }
    }
    
    openModal('status-modal');
}

async function submitStatusUpdate() {
    const instanceId = document.getElementById('status-instance-id').value;
    const status = document.getElementById('status-select').value;
    const fixedBy = document.getElementById('status-fixed-by').value;
    const notes = document.getElementById('status-notes').value;
    
    try {
        await api(`/instances/${instanceId}/status`, {
            method: 'PUT',
            body: JSON.stringify({ status, fixed_by: fixedBy, notes })
        });
        
        showToast('狀態已更新');
        closeModal('status-modal');
        loadReportDetail();
    } catch (error) {
        showToast('更新失敗: ' + error.message, 'error');
    }
}

async function batchUpdateStatus() {
    const status = document.getElementById('batch-status').value;
    if (!status) {
        showToast('請選擇狀態', 'warning');
        return;
    }
    
    if (!selectedInstances.size) {
        showToast('請選擇要更新的項目', 'warning');
        return;
    }
    
    try {
        await api('/instances/batch-status', {
            method: 'PUT',
            body: JSON.stringify({
                instance_ids: Array.from(selectedInstances),
                status: status
            })
        });
        
        showToast(`已更新 ${selectedInstances.size} 個項目`);
        document.getElementById('batch-status').value = '';
        loadReportDetail();
    } catch (error) {
        showToast('批次更新失敗: ' + error.message, 'error');
    }
}

// ==================== 報告操作 ====================

async function saveNotes() {
    const notes = document.getElementById('report-notes').value;
    
    try {
        await api(`/reports/${REPORT_ID}/notes`, {
            method: 'PUT',
            body: JSON.stringify({ notes })
        });
        
        showToast('備註已儲存');
    } catch (error) {
        showToast('儲存失敗: ' + error.message, 'error');
    }
}

function exportReport() {
    window.location.href = `${API_BASE}/export/${REPORT_ID}?include_status=true`;
}

async function deleteReport() {
    if (!confirm('確定要刪除此報告嗎？此操作無法復原。')) {
        return;
    }
    
    try {
        await api(`/reports/${REPORT_ID}`, { method: 'DELETE' });
        showToast('報告已刪除');
        window.location.href = 'reports.html';
    } catch (error) {
        showToast('刪除失敗: ' + error.message, 'error');
    }
}

// ==================== 放大鏡功能 ====================

function openZoomModal(title, content) {
    document.getElementById('zoom-title').textContent = title;
    document.getElementById('zoom-content').textContent = content;
    document.getElementById('zoom-modal').classList.add('active');
}

function closeZoomModal(event) {
    if (event.target.classList.contains('zoom-modal') || event.target.classList.contains('zoom-modal-backdrop')) {
        document.getElementById('zoom-modal').classList.remove('active');
    }
}

// ESC 關閉放大鏡
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.getElementById('zoom-modal').classList.remove('active');
    }
});
