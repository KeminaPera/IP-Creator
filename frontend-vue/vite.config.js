import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    host: '127.0.0.1',  // 强制绑定IPv4，避免IPv6-only问题
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        timeout: 180000,  // 3分钟，匹配最长API超时
        proxyTimeout: 180000,  // 代理超时
      },
      '/datasets': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        timeout: 60000,  // 1分钟
        proxyTimeout: 60000,
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
})
