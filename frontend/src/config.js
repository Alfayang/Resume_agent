// API配置
export const API_CONFIG = {
  BASE_URL: '/api', // 使用代理路径
  ENDPOINTS: {
    GENERATE: '/generate',
    DEBUG: '/debug',
    HEALTH: '/health',
    STATE: '/state', // 注意，这里没有斜杠开头
    STREAM_STATE: '/stream/state',
    QUICK_STATE: '/quick/state',
    MEMORY_CLEAR: '/memory/clear',
    INTERRUPT: '/interrupt',
    INTERRUPT_CHECK: '/interrupt/check',
    INTERRUPT_STATUS: '/interrupt/status'
  },
  
  // 请求配置
  REQUEST_CONFIG: {
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: 30000 // 30秒超时
  }
};

// 获取完整的API URL
export const getApiUrl = (endpoint) => {
  // 确保不会出现双斜杠
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};

// 默认导出
export default API_CONFIG; 