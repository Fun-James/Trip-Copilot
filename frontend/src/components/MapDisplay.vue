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
  },
  routeData: {
    type: Object,
    default: () => null
  }
})

// 响应式数据
const loading = ref(true)
const map = ref(null)
const markers = ref([])
const mapInitialized = ref(false)
const routePolyline = ref(null)

/**
 * 初始化高德地图
 * 创建地图实例并设置基本配置
 */
const initMap = () => {
  if (typeof AMap === 'undefined') {
    console.error('高德地图API未加载')
    loading.value = false
    mapInitialized.value = false
    return
  }

  // 检查API密钥是否已配置
  const apiSecret = import.meta.env.VITE_AMAP_SECRET
  
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
      rotateEnable: true,    // 允许旋转
      pitchEnable: false,    // 禁用倾斜
      zoomEnable: true,      // 允许缩放
      dragEnable: true,      // 允许拖拽
      keyboardEnable: true,  // 允许键盘操作
      doubleClickZoom: true, // 允许双击缩放
      scrollWheel: true      // 允许滚轮缩放
    })

    // 添加地图控件
    addMapControls()
    
    loading.value = false
    mapInitialized.value = true
    console.log('地图初始化成功，拖拽功能已启用')
    
    // 如果有初始行程数据，立即添加标记
    if (props.itineraryData.length > 0) {
      updateMapMarkers(props.itineraryData)
    }
    
    // 如果有路径数据，立即绘制
    if (props.routeData) {
      drawRoute(props.routeData)
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
 * 清除路径
 */
const clearRoute = () => {
  if (routePolyline.value) {
    map.value.remove(routePolyline.value)
    routePolyline.value = null
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
 * 验证坐标是否有效
 * @param {number} lng - 经度
 * @param {number} lat - 纬度
 * @returns {boolean} 坐标是否有效
 */
const isValidCoordinate = (lng, lat) => {
  // 检查是否为数字
  if (typeof lng !== 'number' || typeof lat !== 'number') {
    return false
  }
  
  // 检查是否为NaN
  if (isNaN(lng) || isNaN(lat)) {
    return false
  }
  
  // 检查是否为有限数
  if (!isFinite(lng) || !isFinite(lat)) {
    return false
  }
  
  // 检查经纬度范围
  if (lng < -180 || lng > 180 || lat < -90 || lat > 90) {
    return false
  }
  
  // 排除明显错误的0,0坐标（除非确实在几内亚湾）
  if (lng === 0 && lat === 0) {
    return false
  }
  
  // 中国地区坐标范围检查（更严格的验证）
  // 经度范围：73°E 到 135°E，纬度范围：18°N 到 54°N
  if (lng >= 70 && lng <= 140 && lat >= 15 && lat <= 60) {
    return true
  }
  
  // 对于其他地区，使用基本验证
  return Math.abs(lng) > 0.001 && Math.abs(lat) > 0.001
}

/**
 * 等待地图稳定状态
 * @returns {Promise} 等待地图稳定的Promise
 */
const waitForMapStable = () => {
  return new Promise((resolve) => {
    if (!map.value) {
      resolve()
      return
    }
    
    // 等待地图的idle事件，表示地图已经稳定
    const onMapIdle = () => {
      map.value.off('complete', onMapIdle)
      resolve()
    }
    
    // 监听地图完成事件，如果地图已经ready则立即resolve
    if (map.value.getStatus && map.value.getStatus().dragEnable !== undefined) {
      resolve()
    } else {
      map.value.on('complete', onMapIdle)
      // 添加超时保护
      setTimeout(() => {
        map.value.off('complete', onMapIdle)
        resolve()
      }, 1000)
    }
  })
}

/**
 * 重置地图状态
 * 当地图状态被破坏时，尝试恢复地图的基本功能
 */
const resetMapState = () => {
  if (!map.value) return
  
  try {
    console.log('尝试重置地图状态')
    // 重新设置基本配置
    map.value.setZoom(10)
    map.value.setCenter([116.397428, 39.90923]) // 回到默认位置（北京）
    
    // 清除所有可能有问题的对象
    clearRoute()
    clearMarkers()
    
    console.log('地图状态重置成功')
    return true
  } catch (error) {
    console.error('地图状态重置失败:', error)
    return false
  }
}

/**
 * 检查地图是否处于可操作状态
 * @returns {boolean} 地图是否可操作
 */
const isMapReady = () => {
  if (!map.value || !mapInitialized.value) {
    return false
  }
  
  try {
    // 尝试获取地图缩放级别而不是中心点，因为中心点可能被破坏
    const zoom = map.value.getZoom()
    return !isNaN(zoom) && zoom > 0
  } catch (error) {
    console.warn('地图状态检查失败:', error)
    return false
  }
}

/**
 * 绘制路径
 * @param {Object} routeData - 路径数据
 */
const drawRoute = async (routeData) => {
  if (!map.value || !routeData) {
    console.log('地图或路径数据为空')
    return
  }

  // 检查地图状态，如果异常则尝试重置
  if (!isMapReady()) {
    console.warn('地图未准备就绪，尝试重置地图状态')
    if (!resetMapState()) {
      console.error('地图重置失败，无法绘制路径')
      return
    }
    // 重置后再等待一下
    await new Promise(resolve => setTimeout(resolve, 500))
  }

  console.log('开始绘制路径，路径数据:', routeData)

  // 清除之前的路径
  clearRoute()

  // 等待地图稳定
  await waitForMapStable()

  try {
    // 验证起点和终点坐标
    const startLng = parseFloat(routeData.start_point.longitude)
    const startLat = parseFloat(routeData.start_point.latitude)
    const endLng = parseFloat(routeData.end_point.longitude)
    const endLat = parseFloat(routeData.end_point.latitude)

    if (!isValidCoordinate(startLng, startLat)) {
      console.error('起点坐标无效:', { lng: startLng, lat: startLat })
      return
    }

    if (!isValidCoordinate(endLng, endLat)) {
      console.error('终点坐标无效:', { lng: endLng, lat: endLat })
      return
    }

    const routeInfo = routeData.route_info
    if (!routeInfo || !routeInfo.paths || routeInfo.paths.length === 0) {
      console.warn('路径信息为空，绘制简单路径')
      drawSimpleRoute(routeData)
      return
    }

    const path = routeInfo.paths[0]
    console.log('路径详情:', path)

    // 收集所有路径点
    const pathPoints = []
    
    // 首先添加起点
    pathPoints.push([startLng, startLat])

    // 如果有详细步骤，解析polyline
    if (path.steps && path.steps.length > 0) {
      path.steps.forEach((step, stepIndex) => {
        if (step.polyline && typeof step.polyline === 'string') {
          try {
            // 解析polyline字符串为坐标点
            const polylinePoints = step.polyline.split(';')
            console.log(`步骤 ${stepIndex} polyline点数:`, polylinePoints.length)
            
            let validPointsInStep = 0
            polylinePoints.forEach(point => {
              if (point && point.includes(',')) {
                const parts = point.split(',')
                if (parts.length >= 2) {
                  const lngStr = parts[0].trim()
                  const latStr = parts[1].trim()
                  
                  // 确保字符串不为空且不包含非数字字符
                  if (lngStr && latStr && /^-?\d+\.?\d*$/.test(lngStr) && /^-?\d+\.?\d*$/.test(latStr)) {
                    const lng = parseFloat(lngStr)
                    const lat = parseFloat(latStr)
                    
                    // 严格验证每个坐标点
                    if (isValidCoordinate(lng, lat)) {
                      pathPoints.push([lng, lat])
                      validPointsInStep++
                    } else {
                      console.warn('跳过无效坐标点:', { lng, lat, original: point })
                    }
                  } else {
                    console.warn('跳过格式错误的坐标:', { lngStr, latStr, original: point })
                  }
                }
              }
            })
            console.log(`步骤 ${stepIndex} 有效坐标点数:`, validPointsInStep)
          } catch (e) {
            console.warn(`解析步骤 ${stepIndex} polyline失败:`, e)
          }
        }
      })
    }

    // 最后添加终点
    pathPoints.push([endLng, endLat])

    // 去重相邻重复点
    const uniquePoints = []
    pathPoints.forEach((point, index) => {
      if (index === 0 || 
          point[0] !== pathPoints[index - 1][0] || 
          point[1] !== pathPoints[index - 1][1]) {
        uniquePoints.push(point)
      }
    })

    console.log('有效路径点数量:', uniquePoints.length)

    if (uniquePoints.length < 2) {
      console.warn('路径点数量不足，绘制简单路径')
      drawSimpleRoute(routeData)
      return
    }

    // 创建路径线
    try {
      routePolyline.value = new AMap.Polyline({
        path: uniquePoints,
        strokeColor: '#1890ff',    // 路径颜色
        strokeWeight: 6,           // 路径宽度
        strokeOpacity: 0.8,        // 路径透明度
        strokeStyle: 'solid',      // 路径样式
        lineJoin: 'round',         // 拐点样式
        lineCap: 'round'           // 端点样式
      })

      // 添加到地图
      map.value.add(routePolyline.value)
      console.log('路径线已添加到地图')
    } catch (polylineError) {
      console.error('创建路径线失败:', polylineError)
      drawSimpleRoute(routeData)
      return
    }

    // 先设置地图视野，再添加标记
    // 计算路径的中心点和合适的缩放级别
    try {
      const centerLng = (startLng + endLng) / 2
      const centerLat = (startLat + endLat) / 2
      
      // 计算距离来确定合适的缩放级别
      const distance = Math.sqrt(
        Math.pow(endLng - startLng, 2) + Math.pow(endLat - startLat, 2)
      )
      
      // 根据距离设置缩放级别
      let zoomLevel = 10
      if (distance < 0.01) {
        zoomLevel = 14  // 很近的距离
      } else if (distance < 0.1) {
        zoomLevel = 12  // 中等距离
      } else if (distance < 1) {
        zoomLevel = 10  // 较远距离
      } else {
        zoomLevel = 8   // 很远的距离
      }
      
      console.log('设置地图视野:', { 
        center: [centerLng, centerLat], 
        zoom: zoomLevel, 
        distance 
      })
      
      // 使用更安全的方式设置地图视野
      map.value.setCenter([centerLng, centerLat])
      map.value.setZoom(zoomLevel)
      
      // 等待地图调整完成后再添加标记
      setTimeout(() => {
        if (isMapReady()) {
          addRouteMarkers(routeData)
        }
      }, 500)
      
    } catch (viewError) {
      console.error('设置地图视野失败:', viewError)
      // 直接添加标记，不调整视野
      setTimeout(() => {
        if (isMapReady()) {
          addRouteMarkers(routeData)
        }
      }, 200)
    }

  } catch (error) {
    console.error('绘制路径失败:', error)
    // 发生错误时绘制简单路径
    drawSimpleRoute(routeData)
  }
}

/**
 * 绘制简单路径（直线）
 * @param {Object} routeData - 路径数据
 */
const drawSimpleRoute = (routeData) => {
  console.log('绘制简单路径')
  
  try {
    const startLng = parseFloat(routeData.start_point.longitude)
    const startLat = parseFloat(routeData.start_point.latitude)
    const endLng = parseFloat(routeData.end_point.longitude)
    const endLat = parseFloat(routeData.end_point.latitude)

    // 验证坐标
    if (!isValidCoordinate(startLng, startLat)) {
      console.error('简单路径: 起点坐标无效')
      return
    }

    if (!isValidCoordinate(endLng, endLat)) {
      console.error('简单路径: 终点坐标无效')
      return
    }

    const startPoint = [startLng, startLat]
    const endPoint = [endLng, endLat]
    
    // 创建简单的直线路径
    try {
      routePolyline.value = new AMap.Polyline({
        path: [startPoint, endPoint],
        strokeColor: '#ff6b6b',    // 使用不同颜色表示简单路径
        strokeWeight: 4,
        strokeOpacity: 0.8,
        strokeStyle: 'dashed',     // 虚线样式
        lineJoin: 'round',
        lineCap: 'round'
      })

      // 添加到地图
      map.value.add(routePolyline.value)
    } catch (polylineError) {
      console.error('创建简单路径线失败:', polylineError)
      return
    }
    
    // 调整视野
    try {
      const centerLng = (startLng + endLng) / 2
      const centerLat = (startLat + endLat) / 2
      
      // 计算距离来确定合适的缩放级别
      const distance = Math.sqrt(
        Math.pow(endLng - startLng, 2) + Math.pow(endLat - startLat, 2)
      )
      
      // 根据距离设置缩放级别
      let zoomLevel = 10
      if (distance < 0.01) {
        zoomLevel = 14
      } else if (distance < 0.1) {
        zoomLevel = 12
      } else if (distance < 1) {
        zoomLevel = 10
      } else {
        zoomLevel = 8
      }
      
      console.log('简单路径设置视野:', { 
        center: [centerLng, centerLat], 
        zoom: zoomLevel 
      })
      
      map.value.setCenter([centerLng, centerLat])
      map.value.setZoom(zoomLevel)
      
      // 等待视野调整完成后再添加标记
      setTimeout(() => {
        addRouteMarkers(routeData)
      }, 300)
      
    } catch (viewError) {
      console.error('设置简单路径视野失败:', viewError)
      // 直接添加标记
      addRouteMarkers(routeData)
    }
  } catch (error) {
    console.error('绘制简单路径失败:', error)
  }
}

/**
 * 添加路径起点和终点标记
 * @param {Object} routeData - 路径数据
 */
const addRouteMarkers = (routeData) => {
  if (!map.value || !routeData) {
    console.warn('地图或路径数据为空，无法添加标记')
    return
  }

  try {
    const startLng = parseFloat(routeData.start_point.longitude)
    const startLat = parseFloat(routeData.start_point.latitude)
    const endLng = parseFloat(routeData.end_point.longitude)
    const endLat = parseFloat(routeData.end_point.latitude)

    // 验证坐标
    if (!isValidCoordinate(startLng, startLat)) {
      console.error('起点标记: 坐标无效', { lng: startLng, lat: startLat })
      return
    }

    if (!isValidCoordinate(endLng, endLat)) {
      console.error('终点标记: 坐标无效', { lng: endLng, lat: endLat })
      return
    }

    const startPoint = routeData.start_point
    const endPoint = routeData.end_point

    // 清除现有标记
    clearMarkers()

    console.log('添加路径标记:', { 
      startPoint: { name: startPoint.name, lng: startLng, lat: startLat },
      endPoint: { name: endPoint.name, lng: endLng, lat: endLat }
    })

    // 创建标记数组
    const newMarkers = []

    // 创建起点标记
    try {
      const startMarker = new AMap.Marker({
        position: [startLng, startLat],
        title: `起点：${startPoint.name}`,
        icon: new AMap.Icon({
          image: 'https://webapi.amap.com/theme/v1.3/markers/n/start.png',
          size: new AMap.Size(25, 34),
          imageSize: new AMap.Size(25, 34)
        })
      })

      // 为起点标记添加信息窗口
      startMarker.on('click', () => {
        try {
          const infoWindow = new AMap.InfoWindow({
            content: `<div style="padding: 8px;"><strong>起点</strong><br>${startPoint.name}</div>`,
            offset: new AMap.Pixel(0, -30)
          })
          infoWindow.open(map.value, startMarker.getPosition())
        } catch (infoError) {
          console.warn('创建起点信息窗口失败:', infoError)
        }
      })

      newMarkers.push(startMarker)
    } catch (startMarkerError) {
      console.error('创建起点标记失败:', startMarkerError)
    }

    // 创建终点标记
    try {
      const endMarker = new AMap.Marker({
        position: [endLng, endLat],
        title: `终点：${endPoint.name}`,
        icon: new AMap.Icon({
          image: 'https://webapi.amap.com/theme/v1.3/markers/n/end.png',
          size: new AMap.Size(25, 34),
          imageSize: new AMap.Size(25, 34)
        })
      })

      // 为终点标记添加信息窗口
      endMarker.on('click', () => {
        try {
          const infoWindow = new AMap.InfoWindow({
            content: `<div style="padding: 8px;"><strong>终点</strong><br>${endPoint.name}</div>`,
            offset: new AMap.Pixel(0, -30)
          })
          infoWindow.open(map.value, endMarker.getPosition())
        } catch (infoError) {
          console.warn('创建终点信息窗口失败:', infoError)
        }
      })

      newMarkers.push(endMarker)
    } catch (endMarkerError) {
      console.error('创建终点标记失败:', endMarkerError)
    }

    // 添加标记到地图
    if (newMarkers.length > 0) {
      try {
        map.value.add(newMarkers)
        markers.value = newMarkers
        console.log(`成功添加 ${newMarkers.length} 个路径标记`)
      } catch (addMarkersError) {
        console.error('添加标记到地图失败:', addMarkersError)
      }
    } else {
      console.warn('没有有效的标记可以添加')
    }

  } catch (error) {
    console.error('添加路径标记失败:', error)
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

// 监听路径数据变化
watch(() => props.routeData, async (newRouteData, oldRouteData) => {
  console.log('路径数据变化:', { newRouteData, oldRouteData })
  
  // 如果没有新的路径数据，清除现有路径
  if (!newRouteData) {
    console.log('清除路径和标记')
    clearRoute()
    clearMarkers()
    return
  }
  
  // 等待地图完全初始化
  if (!map.value || !mapInitialized.value) {
    console.log('地图未初始化，等待初始化完成')
    const maxRetries = 10
    let retryCount = 0
    
    const retryDraw = async () => {
      retryCount++
      if (map.value && mapInitialized.value) {
        console.log('地图初始化完成，开始绘制路径')
        try {
          await drawRoute(newRouteData)
        } catch (error) {
          console.error('绘制路径时出错:', error)
          // 尝试重置地图状态后再次绘制
          if (resetMapState()) {
            setTimeout(() => drawRoute(newRouteData), 1000)
          }
        }
      } else if (retryCount < maxRetries) {
        console.log(`地图仍未初始化，第 ${retryCount} 次重试`)
        setTimeout(retryDraw, 500)
      } else {
        console.warn('地图初始化超时，停止重试')
      }
    }
    
    setTimeout(retryDraw, 500)
    return
  }
  
  // 地图已初始化，立即处理
  try {
    console.log('开始绘制新路径')
    await drawRoute(newRouteData)
  } catch (error) {
    console.error('绘制路径过程中出错:', error)
    // 尝试重置地图状态后再次绘制
    if (resetMapState()) {
      setTimeout(() => drawRoute(newRouteData), 1000)
    }
  }
}, { deep: true, immediate: false })

// 组件挂载时初始化地图
onMounted(() => {
  nextTick(async () => {
    try {
      // 动态加载高德地图API
      if (window.loadAmapScript) {
        await window.loadAmapScript()
      }
      // 确保DOM元素已渲染再初始化地图
      setTimeout(initMap, 100)
    } catch (error) {
      console.error('高德地图API加载失败:', error)
      loading.value = false
      mapInitialized.value = false
    }
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
