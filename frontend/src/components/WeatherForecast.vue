<template>
  <div class="weather-forecast">
    <div class="weather-header">
      <h3>
        <el-icon><Sunny /></el-icon>
        天气预报
      </h3>
      <span v-if="location" class="location">{{ location }}</span>
    </div>
    <div v-if="loading" class="weather-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
    <div v-else-if="error" class="weather-error">
      <el-icon><Warning /></el-icon>
      <span>{{ error }}</span>
    </div>
    <div v-else class="forecast-list">
      <div v-for="(day, index) in forecast" :key="index" class="forecast-item">
        <div class="forecast-date">{{ day.date }}</div>
        <div class="forecast-icon">
          <el-icon><component :is="getWeatherIcon(day.description)" /></el-icon>
        </div>
        <div class="forecast-temp">
          <span class="temp-high">{{ day.tempHigh }}°</span>
          <span class="temp-low">{{ day.tempLow }}°</span>
        </div>
        <div class="forecast-desc">{{ day.description }}</div>
        <div class="forecast-details">
          <div>白天风力风向: {{ day.daywind }}{{ day.daypower }}</div>
          <div>晚上风力风向: {{ day.nightwind }}{{ day.nightpower }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>

import { ref, watch } from 'vue'
import { Loading, Warning, Sunny, Cloudy, Lightning, Moon } from '@element-plus/icons-vue'

const props = defineProps({
  location: {
    type: String,
    default: ''
  }
})

const loading = ref(false)
const error = ref('')
const forecast = ref([])

// 根据天气描述返回对应的图标组件名
const getWeatherIcon = (description) => {
  if (!description) return 'Sunny'
  if (description.includes('晴')) return 'Sunny'
  if (description.includes('云') || description.includes('阴')) return 'Cloudy'
  if (description.includes('雨') || description.includes('雪')) return 'Lightning'
  if (description.includes('夜')) return 'Moon'
  return 'Sunny'
}


// 提取城市名（如“重庆的2天行程”只取“重庆”）
const extractCityName = (locationStr) => {
  if (!locationStr) return ''
  // 匹配“xxx的xx行程”或“xxx”
  const match = locationStr.match(/([\u4e00-\u9fa5]+)(?:的.*)?$/)
  return match ? match[1] : locationStr
}

// 获取天气预报数据
const fetchWeatherData = async (location) => {
  const city = extractCityName(location)
  if (!city) {
    error.value = '请选择目的地'
    return
  }

  loading.value = true
  error.value = ''
  try {
    const response = await fetch(`http://localhost:8000/api/weather/${encodeURIComponent(city)}`)
    const data = await response.json()
    console.log(data)
    if (data.success) {
      forecast.value = data.forecasts
    } else {
      error.value = data.error || '获取天气信息失败'
    }
  } catch (e) {
    error.value = '获取天气信息失败'
    console.error('获取天气信息失败:', e)
  } finally {
    loading.value = false
  }
}

// 监听位置变化，更新天气信息
watch(() => props.location, async (newLocation) => {
  if (!newLocation) return
  await fetchWeatherData(newLocation)
}, { immediate: true })
</script>

<style scoped>
.weather-forecast {
  background: linear-gradient(135deg, #f8fbff 0%, #f2f6fa 100%);
  border-radius: 28px;
  padding: 40px 32px 32px 32px;
  margin: 36px auto;
  box-shadow: 0 8px 32px rgba(80,120,200,0.10), 0 2px 12px rgba(0,0,0,0.06), var(--el-box-shadow-lighter);
  border: 1.5px solid #e3eaf2;
  max-width: 820px;
  width: 100%;
  min-width: 320px;
  min-height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: box-shadow 0.3s, border-color 0.3s;
  box-sizing: border-box;
}

.weather-header {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 32px;
  flex-direction: column;
  text-align: center;
  gap: 8px;
}

.weather-header h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  color: var(--el-text-color-primary);
}

.location {
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.weather-loading,
.weather-error {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 100px;
  color: var(--el-text-color-secondary);
}


.forecast-list {
  display: flex;
  flex-direction: row;
  gap: 28px;
  padding: 16px 0;
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
  justify-content: flex-start;
  box-sizing: border-box;
  overflow-x: auto;
  /* 横向滚动条样式 */
  scrollbar-height: thin;
}


.forecast-item {
  text-align: center;
  padding: 24px 18px;
  border-radius: 18px;
  background: var(--el-fill-color-lighter);
  transition: box-shadow 0.3s, transform 0.3s;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06), var(--el-box-shadow-lighter);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100%;
  border: 1px solid var(--el-border-color);
  position: relative;
  overflow: hidden;
  min-width: 160px;
  max-width: 220px;
  flex: 1 1 180px;
}

.forecast-item:hover {
  transform: translateY(-6px) scale(1.03);
  box-shadow: 0 8px 32px rgba(0,0,0,0.12), var(--el-box-shadow-light);
  border-color: var(--el-color-primary);
}

.forecast-date {
  font-size: 15px;
  color: var(--el-color-primary);
  margin-bottom: 10px;
  font-weight: 500;
}

.forecast-icon {
  font-size: 44px;
  color: var(--el-color-primary);
  margin: 18px 0;
  filter: drop-shadow(0 2px 8px rgba(0,0,0,0.08));
}

.forecast-temp {
  margin: 10px 0;
  display: flex;
  justify-content: center;
  gap: 10px;
  font-size: 18px;
}

.temp-high {
  color: var(--el-color-danger);
  font-weight: bold;
}

.temp-low {
  color: var(--el-color-info);
}

.forecast-desc {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin: 6px 0 2px 0;
}

/* 自定义滚动条样式 */
.forecast-list::-webkit-scrollbar {
  height: 6px;
}

.forecast-list::-webkit-scrollbar-track {
  background: var(--el-fill-color-lighter);
  border-radius: 3px;
}

.forecast-list::-webkit-scrollbar-thumb {
  background: var(--el-border-color);
  border-radius: 3px;
}

.forecast-list::-webkit-scrollbar-thumb:hover {
  background: var(--el-border-color-darker);
}

.forecast-details {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 10px;
  text-align: center;
  padding: 0 8px;
  opacity: 0.85;
}

.forecast-details div {
  margin: 4px 0;
}
@media (max-width: 900px) {
  .weather-forecast {
    padding: 12px 2px;
    max-width: 100vw;
    margin: 10px auto;
  }
  .forecast-list {
    gap: 12px;
    padding: 8px 0;
    max-width: 100vw;
    overflow-x: auto;
  }
  .forecast-item {
    padding: 12px 2px;
    border-radius: 12px;
    min-width: 120px;
    max-width: 180px;
    flex: 1 1 120px;
    margin: 0 auto;
  }
  .forecast-icon {
    font-size: 32px;
  }
  .forecast-temp {
    font-size: 14px;
  }
}
</style>
