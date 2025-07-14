<template>
  <div class="map-container">
    <div id="amap-container" style="width: 100%; height: 100%;"></div>
    <div v-if="loading" class="map-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>地图加载中...</span>
    </div>
    <div v-else-if="!mapInitialized" class="map-error">
      <el-icon><WarningFilled /></el-icon>
      <h4>地图暂时无法加载</h4>
      <p>请配置高德地图API密钥后刷新页面</p>
      <div class="config-steps">
        <p><strong>配置步骤：</strong></p>
        <ol>
          <li>访问 <a href="https://console.amap.com" target="_blank">高德开放平台</a></li>
          <li>申请Web服务类型的API Key</li>
          <li>在项目根目录的.env文件中设置：<br>
              <code>VITE_AMAP_KEY="您的API密钥"</code><br>
              <code>VITE_AMAP_SECRET="您的安全密钥"</code>（如果配置了安全密钥）
          </li>
          <li>重启开发服务器</li>
        </ol>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { Loading, WarningFilled } from '@element-plus/icons-vue'

// Props定义
const props = defineProps({
  itineraryData: {
    type: Array,
    default: () => []
  },
  centerLocation: {
    type: Object,
    default: () => ({ lng: 116.397428, lat: 39.90923 }) // 默认北京
  }
})

// 响应式数据
const loading = ref(true)
const map = ref(null)
const markers = ref([])
const mapInitialized = ref(false)

/**
 * 初始化高德地图
 * 创建地图实例并设置基本配置
 */
const initMap = () => {
  // 检查API密钥是否已配置
  const apiKey = import.meta.env.VITE_AMAP_KEY
  const apiSecret = import.meta.env.VITE_AMAP_SECRET
  
  console.log('API Key:', apiKey) // 调试日志
  console.log('API Secret:', apiSecret) // 调试日志
  
  if (!apiKey || apiKey === 'YOUR_AMAP_KEY_HERE') {
    console.warn('高德地图API密钥尚未配置，请在.env文件中设置VITE_AMAP_KEY')
    loading.value = false
    mapInitialized.value = false
    return
  }

  if (typeof AMap === 'undefined') {
    console.error('高德地图API未加载，请检查API密钥配置')
    loading.value = false
    mapInitialized.value = false
    return
  }

  // 如果配置了安全密钥，设置安全验证
  if (apiSecret && apiSecret !== 'YOUR_AMAP_SECRET_HERE') {
    try {
      window._AMapSecurityConfig = {
        securityJsCode: apiSecret,
      }
      console.log('高德地图安全密钥已配置')
    } catch (error) {
      console.warn('安全密钥配置失败:', error)
    }
  }

  try {
    // 创建地图实例
    map.value = new AMap.Map('amap-container', {
      zoom: 12,
      center: [props.centerLocation.lng, props.centerLocation.lat],
      mapStyle: 'amap://styles/normal', // 标准地图样式
      viewMode: '2D',
      features: ['bg', 'point', 'road', 'building'], // 显示基础地图要素
      resizeEnable: true,
      rotateEnable: false,
      pitchEnable: false,
      zoomEnable: true,
      dragEnable: true
    })

    // 添加地图控件
    addMapControls()
    
    loading.value = false
    mapInitialized.value = true
    console.log('地图初始化成功')
    
    // 如果有初始行程数据，立即添加标记
    if (props.itineraryData.length > 0) {
      updateMapMarkers(props.itineraryData)
    }
  } catch (error) {
    console.error('地图初始化失败:', error)
    loading.value = false
    mapInitialized.value = false
  }
}

/**
 * 添加地图控件
 * 包括缩放控件、比例尺等
 */
const addMapControls = () => {
  if (!map.value) return

  // 添加缩放控件
  const toolbar = new AMap.ToolBar({
    position: {
      top: '10px',
      right: '10px'
    }
  })
  map.value.addControl(toolbar)

  // 添加比例尺控件
  const scale = new AMap.Scale({
    position: {
      bottom: '10px',
      left: '10px'
    }
  })
  map.value.addControl(scale)
}

/**
 * 清除所有地图标记
 */
const clearMarkers = () => {
  if (markers.value.length > 0) {
    map.value.remove(markers.value)
    markers.value = []
  }
}

/**
 * 根据地名获取地理坐标
 * @param {string} placeName - 地点名称
 * @returns {Promise<Object>} 返回包含经纬度的对象
 */
const geocodePlace = (placeName) => {
  return new Promise((resolve, reject) => {
    if (typeof AMap === 'undefined') {
      reject(new Error('高德地图API未加载'))
      return
    }

    AMap.plugin('AMap.Geocoder', () => {
      const geocoder = new AMap.Geocoder({
        city: '全国'
      })
      
      geocoder.getLocation(placeName, (status, result) => {
        if (status === 'complete' && result.geocodes.length > 0) {
          const location = result.geocodes[0].location
          resolve({
            lng: location.lng,
            lat: location.lat,
            address: result.geocodes[0].formattedAddress
          })
        } else {
          reject(new Error(`无法找到地点: ${placeName}`))
        }
      })
    })
  })
}

/**
 * 更新地图标记
 * 根据行程数据在地图上添加或更新标记点
 * @param {Array} itinerary - 行程数据数组
 */
const updateMapMarkers = async (itinerary) => {
  if (!map.value || !itinerary || itinerary.length === 0) {
    return
  }

  // 清除现有标记
  clearMarkers()

  const newMarkers = []
  const validLocations = []

  // 处理每个行程点
  for (let i = 0; i < itinerary.length; i++) {
    const item = itinerary[i]
    let placeName = ''
    
    // 从行程描述中提取地点名称（简单的关键词提取）
    if (typeof item === 'string') {
      placeName = extractPlaceNameFromText(item)
    } else if (item.place) {
      placeName = item.place
    } else if (item.location) {
      placeName = item.location
    }

    if (!placeName) continue

    try {
      // 获取地理坐标
      const location = await geocodePlace(placeName)
      validLocations.push(location)

      // 创建标记
      const marker = new AMap.Marker({
        position: [location.lng, location.lat],
        title: placeName,
        content: `<div class="custom-marker">
          <div class="marker-number">${i + 1}</div>
        </div>`,
        anchor: 'center'
      })

      // 添加信息窗体
      const infoWindow = new AMap.InfoWindow({
        content: `
          <div class="info-window">
            <h4>${placeName}</h4>
            <p>${typeof item === 'string' ? item : item.description || '暂无描述'}</p>
            <small>经度: ${location.lng.toFixed(6)}, 纬度: ${location.lat.toFixed(6)}</small>
          </div>
        `,
        offset: new AMap.Pixel(0, -30)
      })

      // 绑定点击事件
      marker.on('click', () => {
        infoWindow.open(map.value, marker.getPosition())
      })

      newMarkers.push(marker)
    } catch (error) {
      console.warn(`无法获取地点 "${placeName}" 的坐标:`, error.message)
    }
  }

  // 添加标记到地图
  if (newMarkers.length > 0) {
    map.value.add(newMarkers)
    markers.value = newMarkers

    // 调整视野以包含所有标记
    if (validLocations.length > 1) {
      const bounds = new AMap.Bounds()
      validLocations.forEach(location => {
        bounds.extend([location.lng, location.lat])
      })
      map.value.setBounds(bounds, false, [20, 20, 20, 20])
    } else if (validLocations.length === 1) {
      map.value.setCenter([validLocations[0].lng, validLocations[0].lat])
      map.value.setZoom(14)
    }
  }
}

/**
 * 从文本中提取地点名称的简单方法
 * @param {string} text - 包含地点信息的文本
 * @returns {string} 提取的地点名称
 */
const extractPlaceNameFromText = (text) => {
  // 使用正则表达式尝试提取地点名称
  const patterns = [
    /(?:前往|游览|参观|访问)([^，。！？\n]{2,10})/,
    /([^，。！？\n]{2,10})(?:景区|景点|公园|博物馆|寺庙|古镇|山|湖|河|街|路|广场)/,
    /在([^，。！？\n]{2,10})(?:停留|游玩|参观)/
  ]
  
  for (const pattern of patterns) {
    const match = text.match(pattern)
    if (match && match[1]) {
      return match[1].trim()
    }
  }
  
  // 如果没有匹配到，返回文本的前几个字符作为地点名称
  const cleanText = text.replace(/[0-9]+\.?\s*/, '').trim()
  return cleanText.length > 20 ? cleanText.substring(0, 15) + '...' : cleanText
}

// 监听行程数据变化
watch(() => props.itineraryData, (newData) => {
  if (map.value && newData) {
    updateMapMarkers(newData)
  }
}, { deep: true })

// 监听中心位置变化
watch(() => props.centerLocation, (newCenter) => {
  if (map.value && newCenter) {
    map.value.setCenter([newCenter.lng, newCenter.lat])
  }
}, { deep: true })

// 组件挂载时初始化地图
onMounted(() => {
  nextTick(() => {
    // 确保DOM元素已渲染再初始化地图
    setTimeout(initMap, 100)
  })
})
</script>

<style scoped>
.map-container {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e8eaed;
}

.map-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  background-color: rgba(255, 255, 255, 0.9);
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 1000;
}

.map-loading .el-icon {
  font-size: 24px;
  color: #1a73e8;
}

.map-loading span {
  color: #5f6368;
  font-size: 14px;
}

.map-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  background-color: rgba(255, 255, 255, 0.95);
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  max-width: 400px;
  width: 90%;
}

.map-error .el-icon {
  font-size: 48px;
  color: #e6a23c;
  margin-bottom: 16px;
}

.map-error h4 {
  margin: 0 0 12px 0;
  color: #202124;
  font-size: 18px;
  font-weight: 600;
}

.map-error p {
  margin: 0 0 20px 0;
  color: #5f6368;
  font-size: 14px;
  line-height: 1.4;
}

.config-steps {
  text-align: left;
  background-color: #f8f9fa;
  padding: 16px;
  border-radius: 8px;
  border-left: 4px solid #1a73e8;
}

.config-steps p {
  margin: 0 0 8px 0;
  font-weight: 600;
  color: #202124;
}

.config-steps ol {
  margin: 8px 0 0 0;
  padding-left: 20px;
  color: #5f6368;
  font-size: 13px;
  line-height: 1.5;
}

.config-steps li {
  margin-bottom: 8px;
}

.config-steps code {
  background-color: #e8f0fe;
  color: #1a73e8;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-family: 'Courier New', monospace;
}

.config-steps a {
  color: #1a73e8;
  text-decoration: none;
}

.config-steps a:hover {
  text-decoration: underline;
}

/* 全局样式，用于地图标记 */
:global(.custom-marker) {
  width: 30px;
  height: 30px;
  background-color: #1a73e8;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #ffffff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
  cursor: pointer;
}

:global(.marker-number) {
  color: white;
  font-size: 12px;
  font-weight: bold;
}

:global(.info-window) {
  padding: 10px;
  max-width: 250px;
}

:global(.info-window h4) {
  margin: 0 0 8px 0;
  color: #202124;
  font-size: 16px;
  font-weight: 600;
}

:global(.info-window p) {
  margin: 0 0 8px 0;
  color: #5f6368;
  font-size: 14px;
  line-height: 1.4;
}

:global(.info-window small) {
  color: #80868b;
  font-size: 12px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .map-container {
    border-radius: 0;
    border-left: none;
    border-right: none;
  }
}
</style>
