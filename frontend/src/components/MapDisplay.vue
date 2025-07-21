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

  try {
    // 创建地图实例
    map.value = new AMap.Map('amap-container', {
      zoom: 10.5,
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
          const lng = parseFloat(location.lng)
          const lat = parseFloat(location.lat)
          
          console.log(`地理编码结果 "${placeName}":`, { lng, lat, status, result })
          
          // 严格验证地理编码返回的坐标
          if (!isValidCoordinate(lng, lat)) {
            console.error(`地理编码返回无效坐标 "${placeName}":`, { lng, lat })
            reject(new Error(`地点 "${placeName}" 的坐标无效: lng=${lng}, lat=${lat}`))
            return
          }
          
          // 检查坐标是否在合理的中国范围内
          if (lng < 70 || lng > 140 || lat < 15 || lat > 60) {
            console.warn(`地点 "${placeName}" 的坐标超出中国范围:`, { lng, lat })
            // 不直接拒绝，但给出警告，可能是海外地点
          }
          
          resolve({
            lng: lng,
            lat: lat,
            address: result.geocodes[0].formattedAddress
          })
        } else {
          console.error(`地理编码失败 "${placeName}":`, { status, result })
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
    
    // 先尝试简单重置
    try {
      map.value.setZoom(10)
      map.value.setCenter([116.397428, 39.90923]) // 回到默认位置（北京）
      
      // 清除所有可能有问题的对象
      clearRoute()
      clearMarkers()
      
      console.log('地图状态重置成功')
      return true
    } catch (simpleResetError) {
      console.warn('简单重置失败，尝试完全重新初始化地图:', simpleResetError)
      
      // 如果简单重置失败，说明地图状态已完全损坏，需要重新初始化
      return reinitializeMap()
    }
  } catch (error) {
    console.error('地图状态重置失败:', error)
    return false
  }
}

/**
 * 智能地图重新初始化
 * 保存现有数据并在重新初始化后恢复
 */
const smartReinitializeMap = () => {
  try {
    console.log('开始智能重新初始化地图')
    
    // 保存现有数据
    const savedData = {
      hasRoute: !!routePolyline.value,
      hasMarkers: markers.value.length > 0,
      routeData: props.routeData,
      itineraryData: props.itineraryData
    }
    
    console.log('保存的数据:', savedData)
    
    // 执行重新初始化
    if (reinitializeMap()) {
      // 延迟恢复数据
      setTimeout(() => {
        try {
          console.log('开始恢复地图数据')
          
          // 恢复行程标记
          if (savedData.hasMarkers && savedData.itineraryData) {
            console.log('恢复行程标记')
            updateMapMarkers(savedData.itineraryData)
          }
          
          // 恢复路径
          if (savedData.hasRoute && savedData.routeData) {
            console.log('恢复路径数据')
            drawRoute(savedData.routeData)
          }
          
          console.log('地图数据恢复完成')
        } catch (restoreError) {
          console.error('恢复地图数据失败:', restoreError)
        }
      }, 1500) // 给地图更多时间完全初始化
      
      return true
    }
    
    return false
  } catch (error) {
    console.error('智能重新初始化失败:', error)
    return false
  }
}

/**
 * 完全重新初始化地图
 * 当地图状态完全损坏时使用
 */
const reinitializeMap = () => {
  try {
    console.log('开始重新初始化地图')
    
    // 清除现有地图实例
    if (map.value) {
      try {
        map.value.destroy()
      } catch (destroyError) {
        console.warn('销毁地图实例时出错:', destroyError)
      }
      map.value = null
    }
    
    // 清空相关状态
    markers.value = []
    routePolyline.value = null
    mapInitialized.value = false
    
    // 重新创建地图实例
    setTimeout(() => {
      try {
        // 创建新的地图实例
        map.value = new AMap.Map('amap-container', {
          zoom: 12,
          center: [116.397428, 39.90923], // 默认北京
          mapStyle: 'amap://styles/normal',
          viewMode: '2D',
          features: ['bg', 'point', 'road', 'building'],
          resizeEnable: true,
          rotateEnable: true,
          pitchEnable: false,
          zoomEnable: true,
          dragEnable: true,
          keyboardEnable: true,
          doubleClickZoom: true,
          scrollWheel: true
        })
        
        // 添加地图控件
        addMapControls()
        
        mapInitialized.value = true
        console.log('地图重新初始化成功')
        
        return true
      } catch (reinitError) {
        console.error('重新初始化地图失败:', reinitError)
        mapInitialized.value = false
        return false
      }
    }, 100)
    
    return true
  } catch (error) {
    console.error('重新初始化地图过程失败:', error)
    return false
  }
}

/**
 * 检查地图是否处于可操作状态
 * @returns {boolean} 地图是否可操作
 */
const isMapReady = () => {
  if (!map.value || !mapInitialized.value) {
    console.log('地图检查失败: 地图实例或初始化状态异常')
    return false
  }
  
  try {
    // 尝试获取地图缩放级别
    const zoom = map.value.getZoom()
    const isValidZoom = !isNaN(zoom) && zoom > 0
    
    if (!isValidZoom) {
      console.warn('地图缩放级别异常:', zoom)
      return false
    }
    
    // 尝试获取地图中心点（安全检查）
    try {
      const center = map.value.getCenter()
      if (!center) {
        console.warn('地图中心点为空')
        return false
      }
      
      // 检查中心点坐标是否有效
      const centerLng = center.lng
      const centerLat = center.lat
      
      if (isNaN(centerLng) || isNaN(centerLat) || !isFinite(centerLng) || !isFinite(centerLat)) {
        console.warn('地图中心点坐标异常:', { lng: centerLng, lat: centerLat })
        return false
      }
      
      return true
    } catch (centerError) {
      console.warn('获取地图中心点失败:', centerError)
      return false
    }
    
  } catch (error) {
    console.warn('地图状态检查失败:', error)
    return false
  }
}

/**
 * 更宽松的地图状态检查（仅检查基本可用性）
 * @returns {boolean} 地图基本是否可用
 */
const isMapBasicallyReady = () => {
  try {
    return !!(map.value && mapInitialized.value && typeof map.value.setCenter === 'function')
  } catch (error) {
    console.warn('基本地图状态检查失败:', error)
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

  // 详细打印完整的路径数据
  console.log('=== 完整的路径数据 ===')
  console.log('routeData:', JSON.stringify(routeData, null, 2))
  console.log('routeData 类型:', typeof routeData)
  console.log('routeData.start_point:', routeData.start_point)
  console.log('routeData.end_point:', routeData.end_point)
  console.log('routeData.route_info:', routeData.route_info)
  
  if (routeData.start_point) {
    console.log('起点经度类型:', typeof routeData.start_point.longitude, '值:', routeData.start_point.longitude)
    console.log('起点纬度类型:', typeof routeData.start_point.latitude, '值:', routeData.start_point.latitude)
  }
  
  if (routeData.end_point) {
    console.log('终点经度类型:', typeof routeData.end_point.longitude, '值:', routeData.end_point.longitude)
    console.log('终点纬度类型:', typeof routeData.end_point.latitude, '值:', routeData.end_point.latitude)
  }
  console.log('=== 路径数据打印结束 ===')

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
    if (!routeInfo) {
      console.warn('路径信息为空，绘制简单路径')
      drawSimpleRoute(routeData)
      return
    }

    const pathPoints = []
    
    // 首先添加起点
    pathPoints.push([startLng, startLat])
    map.value.setCenter([startLng, startLat])
    // 根据不同的模式处理路径点
    if (routeData.mode === 'transit' && routeInfo.transits && routeInfo.transits.length > 0) {
      // 对于公交模式，遍历所有路段
      routeInfo.transits[0].segments.forEach((segment, transitIndex) => {
        console.log(`处理公交路段 ${transitIndex + 1}/${routeInfo.transits[0].segments.length}`)
        
        // 处理segments中的各类型路段
        if (segment) {
            // 处理步行路段
            if (segment.walking && segment.walking.steps) {
              console.log(1)
              processSteps(segment.walking.steps, pathPoints, 'walking')
            }
            
            // 处理公交路段
            if (segment.bus && segment.bus.buslines) {
              processSteps(segment.bus.buslines, pathPoints, 'bus')
            }
            
            // 处理地铁路段
            if (segment.railway && segment.railway.steps) {
              processSteps(segment.railway.steps, pathPoints, 'railway')
            }

        }
      })
    } else if (routeInfo.paths && routeInfo.paths.length > 0) {
      // 处理其他模式的路径
      const path = routeInfo.paths[0]
      if (path.steps && path.steps.length > 0) {
        processSteps(path.steps, pathPoints, routeData.mode)
      }
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

    // 直接添加标记，不调整地图视野（避免与已设置的城市中心冲突）
    console.log('路径绘制完成，添加起终点标记')
    
    // 延迟添加标记，确保路径线已经绘制完成
    setTimeout(() => {
      if (isMapBasicallyReady()) {
        addRouteMarkers(routeData)
      } else {
        console.warn('地图状态异常，跳过标记添加')
      }
    }, 300)

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
    
    // 直接添加标记，不调整地图视野（保持已设置的城市中心）
    console.log('简单路径绘制完成，添加起终点标记')
    
    // 延迟添加标记，确保路径线已经绘制完成
    setTimeout(() => {
      if (isMapBasicallyReady()) {
        addRouteMarkers(routeData)
      } else {
        console.warn('地图状态异常，跳过标记添加')
      }
    }, 200)
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
        }),
        zIndex: 120
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
        }),
        zIndex: 110
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

// 防抖定时器
let centerUpdateTimer = null

// 监听中心位置变化（添加防抖机制）
watch(() => props.centerLocation, (newCenter) => {
  if (map.value && newCenter) {
    console.log('监听到中心位置变化:', newCenter)
    
    // 验证新的中心位置坐标
    const lng = parseFloat(newCenter.lng)
    const lat = parseFloat(newCenter.lat)
    
    if (!isValidCoordinate(lng, lat)) {
      console.error('新的中心位置坐标无效:', { lng, lat, original: newCenter })
      return
    }
    
    // 清除之前的定时器，实现防抖
    if (centerUpdateTimer) {
      clearTimeout(centerUpdateTimer)
    }
    
    // 延迟执行地图中心更新，避免频繁操作
    centerUpdateTimer = setTimeout(() => {
      updateMapCenterSafely(lng, lat)
    }, 150) // 150ms 防抖
  }
})

// 安全地更新地图中心
const updateMapCenterSafely = (lng, lat) => {
  if (!map.value || !mapInitialized.value) {
    console.log('地图未准备好，跳过中心点更新')
    return
  }
  
  console.log('设置地图中心到:', { lng, lat })
  
  try {
    // 使用基本的地图状态检查（更宽松）
    if (isMapBasicallyReady()) {
      map.value.setCenter([lng, lat])
      console.log('地图中心设置成功')
    } else {
      console.warn('地图基本状态检查失败，跳过中心点设置')
    }
  } catch (error) {
    console.error('设置地图中心失败:', error)
    
    // 只在严重错误时才考虑重新初始化
    if (error.message && (
      error.message.includes('destroyed') || 
      error.message.includes('disposed') ||
      error.message.includes('not initialized')
    )) {
      console.warn('地图实例可能已损坏，考虑重新初始化')
      // 使用智能重新初始化，会保护现有数据
      setTimeout(() => {
        smartReinitializeMap()
      }, 500)
    } else {
      console.warn('地图中心设置失败，但保留现有地图内容（错误可能是临时的）')
    }
  }
}

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

/**
 * 更新指定天数的路线显示
 * @param {Array} places - 当天的地点列表
 * @param {number} day - 天数
 */
const updateDayRoute = async (places, day) => {
  if (!map.value || !places || places.length === 0) return
  
  try {
    // 清除现有的标记和路线
    clearMarkers()
    clearRoute()
    
    // 验证并过滤有效的地点坐标
    const validPlaces = places.filter(place => {
      if (!place.longitude || !place.latitude) return false
      
      const lng = parseFloat(place.longitude)
      const lat = parseFloat(place.latitude)
      
      // 检查是否为有效数值
      if (isNaN(lng) || isNaN(lat) || !isFinite(lng) || !isFinite(lat)) {
        console.warn(`地点 "${place.name}" 坐标无效:`, { lng, lat })
        return false
      }
      
      // 检查坐标范围
      if (lng < -180 || lng > 180 || lat < -90 || lat > 90) {
        console.warn(`地点 "${place.name}" 坐标超出范围:`, { lng, lat })
        return false
      }
      
      // 更新place对象，确保坐标为数值类型
      place.longitude = lng
      place.latitude = lat
      
      return true
    })
    
    if (validPlaces.length === 0) {
      console.warn(`第${day}天没有有效的地点坐标`)
      return
    }
    
    console.log(`第${day}天有效地点数:`, validPlaces.length)
    
    // 创建地点标记
    validPlaces.forEach((place, index) => {
      try {
        const marker = new AMap.Marker({
          position: [place.longitude, place.latitude],
          title: place.name,
          content: `
            <div class="custom-marker day-${day}">
              <span class="marker-number">${index + 1}</span>
            </div>
          `,
          anchor: 'center'
        })
        
        // 创建信息窗口
        const infoWindow = new AMap.InfoWindow({
          content: `
            <div class="info-window">
              <h4>第${day}天 - 第${index + 1}站</h4>
              <p><strong>${place.name}</strong></p>
              <small>经度: ${place.longitude.toFixed(4)}, 纬度: ${place.latitude.toFixed(4)}</small>
            </div>
          `,
          anchor: 'bottom-center',
          offset: new AMap.Pixel(0, -36)
        })
        
        // 点击标记显示信息窗口
        marker.on('click', () => {
          infoWindow.open(map.value, marker.getPosition())
        })
        
        markers.value.push(marker)
        map.value.add(marker)
        
      } catch (markerError) {
        console.error(`创建地点标记失败 (${place.name}):`, markerError)
      }
    })
    
    // 如果有多个地点，绘制路线
    if (validPlaces.length > 1) {
      await drawDayRoute(validPlaces)
    }
    
    // 只有在没有其他路径规划数据时才调整地图视野
    // 避免与已有的城市中心设置冲突
    if (validPlaces.length > 0 && !props.routeData) {
      // 使用 setTimeout 将 setBounds 操作推迟到下一个事件循环
      // 这给了地图充足的时间来渲染新添加的标记和路线
      setTimeout(() => {
        // 在执行前再次检查地图实例，确保其未被销毁
        if (map.value && isMapBasicallyReady()) {
          try {
            console.log('调整地图视野以显示所有地点 (延迟后执行)');
            const bounds = new AMap.Bounds();
            validPlaces.forEach(place => {
              bounds.extend([place.longitude, place.latitude]);
            });
            // 最后的 [20, 20, 20, 20] 代表上、下、左、右的边距（padding）
            map.value.setBounds(bounds, false, [60, 60, 60, 60]);
          } catch (e) {
            console.error('延迟执行 setBounds 时发生错误:', e);
          }
        }
      }, 100); // 100毫秒的延迟通常足以解决渲染时序问题
    } else {
      console.log('保持现有地图视野（已有路径数据或城市中心）');
    }
    
  } catch (error) {
    console.error('更新当天路线失败:', error)
  }
}

/**
 * 绘制当天的路线
 * @param {Array} places - 地点列表
 */
const drawDayRoute = async (places) => {
  if (!map.value || places.length < 2) return
  
  console.log('开始绘制当天路线，地点数据:', places)
  
  try {
    // 清除之前的路线
    clearRoute()
    
    // 调用后端API获取路径规划
    const response = await fetch('http://localhost:8000/api/trip/itinerary-routes', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        places: places.map(place => ({
          name: place.name,
          longitude: place.longitude,
          latitude: place.latitude
        })),
        mode: 'driving' // 可以根据需要修改出行方式
      })
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const routeResult = await response.json()
    console.log('后端路径规划结果:', routeResult)
    
    if (!routeResult.success || !routeResult.routes_data) {
      console.warn('后端路径规划失败，使用简单连线:', routeResult.error_message)
      drawSimpleDayRoute(places)
      return
    }
    
    // 收集所有路径点
    const allPathPoints = []
    let hasValidRoute = false
    
    // 处理每个路径段
    for (const routeSegment of routeResult.routes_data) {
      const startPoint = [routeSegment.start_point.longitude, routeSegment.start_point.latitude]
      
      // 如果是第一个路径段，添加起点
      if (allPathPoints.length === 0) {
        allPathPoints.push(startPoint)
      }
      
      // 如果有详细路径信息，解析路径点
      if (routeSegment.success && routeSegment.route_info && routeSegment.route_info.paths) {
        const path = routeSegment.route_info.paths[0]
        if (path && path.steps) {
          // 解析路径步骤中的坐标点
          for (const step of path.steps) {
            if (step.polyline && typeof step.polyline === 'string') {
              try {
                const polylinePoints = step.polyline.split(';')
                for (const point of polylinePoints) {
                  if (point && point.includes(',')) {
                    const parts = point.split(',')
                    if (parts.length >= 2) {
                      const lng = parseFloat(parts[0].trim())
                      const lat = parseFloat(parts[1].trim())
                      
                      if (isValidCoordinate(lng, lat)) {
                        allPathPoints.push([lng, lat])
                      }
                    }
                  }
                }
              } catch (e) {
                console.warn('解析polyline失败:', e)
              }
            }
          }
          hasValidRoute = true
        }
      } else {
        // 如果没有详细路径信息，添加直线连接
        console.log(`路径段 ${routeSegment.segment_index} 无详细路径，使用直线`)
      }
      
      // 添加终点
      const endPoint = [routeSegment.end_point.longitude, routeSegment.end_point.latitude]
      allPathPoints.push(endPoint)
    }
    
    // 去重相邻重复点
    const uniquePoints = []
    allPathPoints.forEach((point, index) => {
      if (index === 0 || 
          Math.abs(point[0] - allPathPoints[index - 1][0]) > 0.0001 || 
          Math.abs(point[1] - allPathPoints[index - 1][1]) > 0.0001) {
        uniquePoints.push(point)
      }
    })
    
    console.log(`处理完成: 路径点数 ${uniquePoints.length}, 有效路径: ${hasValidRoute}`)
    
    if (uniquePoints.length < 2) {
      console.warn('路径点数量不足，使用简单连线')
      drawSimpleDayRoute(places)
      return
    }
    
    // 创建路径线
    const polyline = new AMap.Polyline({
      path: uniquePoints,
      strokeColor: hasValidRoute ? '#1890ff' : '#ff9800', // 真实路径用蓝色，回退路径用橙色
      strokeWeight: 4,
      strokeOpacity: 0.8,
      strokeStyle: hasValidRoute ? 'solid' : 'dashed', // 真实路径用实线，回退路径用虚线
      lineJoin: 'round',
      lineCap: 'round'
    })
    
    // 添加到地图
    map.value.add(polyline)
    routePolyline.value = polyline
    
    console.log(`当天路线绘制完成，使用${hasValidRoute ? '真实道路路径' : '混合路径（部分直线）'}`)
    
  } catch (error) {
    console.error('调用后端路径规划API失败:', error)
    console.log('回退到简单连线模式')
    drawSimpleDayRoute(places)
  }
}

/**
 * 绘制简单的当天路线（回退方案）
 * @param {Array} places - 地点列表
 */
const drawSimpleDayRoute = (places) => {
  if (!map.value || places.length < 2) return
  
  console.log('绘制简单当天路线')
  
  try {
    // 构建路径点
    const waypoints = places.map(place => [place.longitude, place.latitude])
    
    // 使用坐标绘制简单连线
    const polyline = new AMap.Polyline({
      path: waypoints,
      strokeColor: '#ff6b6b', // 红色表示简单路径
      strokeWeight: 4,
      strokeOpacity: 0.8,
      strokeStyle: 'dashed', // 虚线样式
      lineJoin: 'round',
      lineCap: 'round'
    })
    
    // 清除之前的路线
    clearRoute()
    
    // 添加到地图
    map.value.add(polyline)
    routePolyline.value = polyline
    
    console.log('简单路线绘制完成，使用直线连接')
    
  } catch (error) {
    console.error('绘制简单当天路线失败:', error)
    console.error('错误详情:', {
      message: error.message,
      stack: error.stack
    })
  }
}

/**
 * 清空所有地图数据
 * 清除标记、路径等所有可视化元素
 */
const clearAllData = () => {
  try {
    // 清除所有标记
    clearMarkers()
    
    // 清除路径
    clearRoute()
    
    // 重置地图视野到默认位置
    if (map.value) {
      map.value.setCenter([116.397428, 39.90923]) // 北京
      map.value.setZoom(10)
    }
    
    console.log('地图数据已清空')
  } catch (error) {
    console.error('清空地图数据失败:', error)
  }
}

/**
 * 处理路径步骤并提取坐标点
 * @param {Array} steps - 步骤数组
 * @param {Array} pathPoints - 存储坐标点的数组
 * @param {string} type - 路段类型
 */
const processSteps = (steps, pathPoints, type) => {
  if (!Array.isArray(steps) || !Array.isArray(pathPoints)) {
    console.warn(`处理${type}类型路段时参数无效:`, { steps, pathPoints })
    return
  }

  try {
    console.log(`开始处理${type}类型路段的步骤，共 ${steps.length} 个步骤`)
    let validPointCount = 0
    let invalidPointCount = 0

    steps.forEach((step, stepIndex) => {
      // 检查步骤是否有效
      if (!step || typeof step !== 'object') {
        console.warn(`${type}类型的步骤 ${stepIndex} 无效:`, step)
        return
      }

      // 处理 polyline
      if (step.polyline && typeof step.polyline === 'string') {
        try {
          // 分割 polyline 字符串获取坐标点
          const polylinePoints = step.polyline.split(';')
          
          polylinePoints.forEach((point, pointIndex) => {
            if (!point || !point.includes(',')) {
              invalidPointCount++
              return
            }

            const parts = point.split(',')
            if (parts.length !== 2) {
              invalidPointCount++
              return
            }

            const lngStr = parts[0].trim()
            const latStr = parts[1].trim()

            // 验证坐标字符串格式
            if (!(/^-?\d+\.?\d*$/.test(lngStr) && /^-?\d+\.?\d*$/.test(latStr))) {
              invalidPointCount++
              return
            }

            const lng = parseFloat(lngStr)
            const lat = parseFloat(latStr)

            // 验证坐标值是否有效
            if (isValidCoordinate(lng, lat)) {
              // 检查是否与上一个点重复（如果不是第一个点）
              const lastPoint = pathPoints[pathPoints.length - 1]
              if (!lastPoint || 
                  Math.abs(lng - lastPoint[0]) > 0.0001 || 
                  Math.abs(lat - lastPoint[1]) > 0.0001) {
                pathPoints.push([lng, lat])
                validPointCount++
              }
            } else {
              invalidPointCount++
              if (pointIndex === 0 || pointIndex === polylinePoints.length - 1) {
                console.warn(`${type}类型步骤 ${stepIndex} 的${pointIndex === 0 ? '起点' : '终点'}坐标无效:`, 
                  { lng, lat, original: point })
              }
            }
          })

        } catch (polylineError) {
          console.error(`解析${type}类型步骤 ${stepIndex} 的polyline时出错:`, polylineError)
        }
      }

      // 处理其他可能的坐标信息（如 start_location, end_location）
      if (step.start_location) {
        const startLng = parseFloat(step.start_location.longitude || step.start_location.lng)
        const startLat = parseFloat(step.start_location.latitude || step.start_location.lat)
        
        if (isValidCoordinate(startLng, startLat)) {
          const lastPoint = pathPoints[pathPoints.length - 1]
          if (!lastPoint || 
              Math.abs(startLng - lastPoint[0]) > 0.0001 || 
              Math.abs(startLat - lastPoint[1]) > 0.0001) {
            pathPoints.push([startLng, startLat])
            validPointCount++
          }
        }
      }

      if (step.end_location) {
        const endLng = parseFloat(step.end_location.longitude || step.end_location.lng)
        const endLat = parseFloat(step.end_location.latitude || step.end_location.lat)
        
        if (isValidCoordinate(endLng, endLat)) {
          const lastPoint = pathPoints[pathPoints.length - 1]
          if (!lastPoint || 
              Math.abs(endLng - lastPoint[0]) > 0.0001 || 
              Math.abs(endLat - lastPoint[1]) > 0.0001) {
            pathPoints.push([endLng, endLat])
            validPointCount++
          }
        }
      }
    })

    // 输出处理结果统计
    console.log(`${type}类型路段处理完成:`, {
      总步骤数: steps.length,
      有效坐标点: validPointCount,
      无效坐标点: invalidPointCount,
      当前路径点总数: pathPoints.length
    })

  } catch (error) {
    console.error(`处理${type}类型路段时发生错误:`, error)
  }
}

// 对外暴露方法
defineExpose({
  updateDayRoute,
  clearAllData
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

/* 不同天数的标记样式 */
:global(.custom-marker.day-1) {
  background: linear-gradient(135deg, #1a73e8 0%, #4285f4 100%);
}

:global(.custom-marker.day-2) {
  background: linear-gradient(135deg, #34a853 0%, #4caf50 100%);
}

:global(.custom-marker.day-3) {
  background: linear-gradient(135deg, #ff6b6b 0%, #ff8e8e 100%);
}

:global(.custom-marker.day-4) {
  background: linear-gradient(135deg, #ffa726 0%, #ffb74d 100%);
}

:global(.custom-marker.day-5) {
  background: linear-gradient(135deg, #ab47bc 0%, #ba68c8 100%);
}

:global(.custom-marker.day-6) {
  background: linear-gradient(135deg, #26c6da 0%, #4dd0e1 100%);
}

:global(.custom-marker.day-7) {
  background: linear-gradient(135deg, #66bb6a 0%, #81c784 100%);
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
