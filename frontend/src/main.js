import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import Home from './views/Home.vue'

// 动态加载高德地图API
function loadAmapScript() {
  return new Promise((resolve, reject) => {
    // 检查是否已经加载过高德地图API
    if (window.AMap) {
      resolve();
      return;
    }

    const amapKey = import.meta.env.VITE_AMAP_KEY;
    const amapSecret = import.meta.env.VITE_AMAP_SECRET;
    
    if (!amapKey) {
      reject(new Error('高德地图API Key未配置'));
      return;
    }

    const amapUrl = `https://webapi.amap.com/maps?v=2.0&key=${amapKey}&securityJsCode=${amapSecret}&plugin=AMap.Scale,AMap.ToolBar,AMap.Geolocation,AMap.Geocoder,AMap.Driving,AMap.Walking,AMap.Transfer`;
    
    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = amapUrl;
    script.onload = () => {
      console.log('高德地图API加载成功');
      resolve();
    };
    script.onerror = () => {
      reject(new Error('高德地图API加载失败'));
    };
    document.head.appendChild(script);
  });
}

// 全局暴露高德地图加载函数
window.loadAmapScript = loadAmapScript;

const routes = [
  { path: '/', name: 'Home', component: Home }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const app = createApp(App)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(ElementPlus)
app.use(router)
app.mount('#app')
