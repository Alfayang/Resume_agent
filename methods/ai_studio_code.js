import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // 使用 '/api' 作为代理标识
      '/api': {
        // 目标是你的后端服务器地址
        target: 'http://127.0.0.1:8002', 
        // 允许跨域
        changeOrigin: true,
        // 重写路径，去掉 '/api'
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});