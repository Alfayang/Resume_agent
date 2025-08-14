// src/config.js (示例)

export const API_CONFIG = {
  BASE_URL: '/api', // 使用代理路径
  ENDPOINTS: {
    GENERATE: '/generate',
    STATE: '/state', // 注意，这里没有斜杠开头
    // ... 其他端点
  },
  // ...
};

export function getApiUrl(endpoint) {
  // 确保不会出现双斜杠
  return `${API_CONFIG.BASE_URL}${endpoint}`;
}