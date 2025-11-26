/**
 * 前端配置檔案
 * 設定後端 API 的 URL
 */

const API_CONFIG = {
    BASE_URL: '',
    // API 路徑前綴（通常為 '/api'）
    API_PREFIX: '/api'
};

// 取得完整的 API URL
function getApiUrl(endpoint) {
    // 移除開頭的斜線（如果有的話）
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
    return `${API_CONFIG.BASE_URL}${API_CONFIG.API_PREFIX}/${cleanEndpoint}`;
}

// 為了向後兼容，也提供舊的 api 函數格式
const API_BASE = `${API_CONFIG.BASE_URL}${API_CONFIG.API_PREFIX}`;

