import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    vue(),
    {
      name: 'html-transform',
      transformIndexHtml(html) {
        // 替换HTML中的API Key和安全密钥占位符
        const amapKey = process.env.VITE_AMAP_KEY || 'YOUR_AMAP_KEY_HERE'
        const amapSecret = process.env.VITE_AMAP_SECRET || 'YOUR_AMAP_SECRET_HERE'
        
        return html
          .replace('VITE_AMAP_KEY_PLACEHOLDER', amapKey)
          .replace('VITE_AMAP_SECRET_PLACEHOLDER', amapSecret)
      }
    }
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    host: '0.0.0.0'
  },
  build: {
    outDir: 'dist'
  }
})
