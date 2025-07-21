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

// 获取天气预报数据
const fetchWeatherData = async (location) => {
  if (!location) {
    error.value = '请选择目的地'
    return
  }

  loading.value = true
  error.value = ''

try {
    const response = await fetch(`http://localhost:8000/api/weather/${encodeURIComponent(location)}`)
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
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 24px;
  margin: 20px;
  box-shadow: var(--el-box-shadow-lighter);
  width: calc(100% - 40px);
  height: auto;
  min-height: 300px;
  display: flex;
  flex-direction: column;
}

.weather-header {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
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
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  padding: 16px 0;
  width: 100%;
}

.forecast-item {
  text-align: center;
  padding: 20px;
  border-radius: 12px;
  background: var(--el-fill-color-lighter);
  transition: all 0.3s;
  box-shadow: var(--el-box-shadow-lighter);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100%;
}

.forecast-item:hover {
  transform: translateY(-2px);
  box-shadow: var(--el-box-shadow-light);
}

.forecast-date {
  font-size: 14px;
  color: var(--el-text-color-primary);
  margin-bottom: 8px;
}

.forecast-icon {
  font-size: 36px;
  color: var(--el-color-primary);
  margin: 16px 0;
}

.forecast-temp {
  margin: 8px 0;
  display: flex;
  justify-content: center;
  gap: 8px;
}

.temp-high {
  color: var(--el-color-danger);
}

.temp-low {
  color: var(--el-color-info);
}

.forecast-desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
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
  margin-top: 8px;
  text-align: center;
  padding: 0 8px;
}

.forecast-details div {
  margin: 4px 0;
}
</style>
