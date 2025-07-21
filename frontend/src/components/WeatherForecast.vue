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
       <!-- 出行建议 -->
        <div class="travel-tips">
          <div class="tips-header">
            <el-icon><InfoFilled /></el-icon>
            <span>出行建议</span>
          </div>
          <ul class="tips-list">
            <li v-for="(tip, tipIndex) in getTravelTips(day.description, day.tempHigh, day.tempLow)" :key="tipIndex">
              {{ tip }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>

import { ref, watch } from 'vue'
import { Loading, Warning, Sunny, Cloudy, Lightning, Moon, InfoFilled } from '@element-plus/icons-vue'

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

// 根据天气描述生成出行建议
const getTravelTips = (description, tempHigh, tempLow) => {
  const tips = []
  
  // 根据天气状况生成建议
  if (description.includes('晴')) {
    tips.push('紫外线较强，建议涂抹防晒霜')
    tips.push('外出请戴墨镜和遮阳帽')
  }
  
  if (description.includes('多云') || description.includes('阴')) {
    tips.push('光线较弱，拍照时注意光线角度')
    tips.push('气温可能忽高忽低，建议穿着薄外套')
  }
  
  if (description.includes('雨')) {
    tips.push('出门请携带雨伞')
    tips.push('注意路滑，请穿防滑鞋')
    tips.push('建议考虑室内景点')
  }
  
  if (description.includes('雪')) {
    tips.push('道路可能湿滑，注意安全')
    tips.push('请穿保暖防水的衣物')
    tips.push('推荐欣赏雪景或考虑室内景点')
  }
  
  if (description.includes('雾') || description.includes('霾')) {
    tips.push('能见度低，驾车注意安全')
    tips.push('建议戴口罩，减少户外活动')
  }
  
  // 根据温度生成建议
  if (tempHigh && tempHigh >= 30) {
    tips.push('天气炎热，注意防暑防晒')
    tips.push('多补充水分，避免中午高温时段外出')
  } else if (tempHigh && tempHigh >= 25) {
    tips.push('温度适宜，适合户外活动')
  }
  
  if (tempLow && tempLow <= 10) {
    tips.push('天气较冷，请注意保暖')
    tips.push('建议穿着厚外套或冲锋衣')
  } else if (tempLow && tempLow <= 5) {
    tips.push('天气寒冷，出行注意保暖')
    tips.push('建议穿羽绒服或厚外套')
  }
  
  // 如果没有具体建议，返回通用建议
  if (tips.length === 0) {
    tips.push('天气适宜，适合游览景点')
    tips.push('建议携带水和适当零食')
  }
  
  // 随机选择2-3条建议返回
  return tips.slice(0, Math.min(3, tips.length))
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
  border-radius: 18px;
  padding: 24px 8px 16px 8px;
  margin: 16px auto;
  /* 去掉外边框和阴影 */
  box-shadow: none;
  border: none;
  max-width: 1000px;
  width: 100%;
  min-width: 320px;
  min-height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
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
  gap: 32px;
  padding: 20px 0;
  width: 100%;
  max-width: 920px;
  margin: 0 auto;
  justify-content: center;
  box-sizing: border-box;
  overflow-x: auto;
  /* 横向滚动条样式 */
  scrollbar-height: thin;
}


.forecast-item {
  text-align: center;
  padding: 16px 8px;
  border-radius: 16px;
  background: var(--el-fill-color-lighter);
  transition: box-shadow 0.3s, transform 0.3s;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06), var(--el-box-shadow-lighter);
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  height: 100%;
  border: 1px solid var(--el-border-color);
  position: relative;
  overflow: hidden;
  min-width: 160px;
  max-width: 220px;
  flex: 1 1 160px;
}

.forecast-item:hover {
  /* 鼠标悬停时无浮动和阴影变化 */
}

.forecast-date {
  font-size: 15px;
  color: var(--el-color-primary);
  margin-bottom: 4px;
  font-weight: 500;
}

.forecast-icon {
  font-size: 44px;
  color: var(--el-color-primary);
  margin: 10px 0 4px 0;
  filter: drop-shadow(0 2px 8px rgba(0,0,0,0.08));
}

.forecast-temp {
  margin: 4px 0 2px 0;
  display: flex;
  justify-content: center;
  gap: 8px;
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
  margin: 2px 0 2px 0;
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
  margin-top: 4px;
  text-align: center;
  padding: 0 4px;
  opacity: 0.85;
}

.forecast-details div {
  margin: 4px 0;
}
/* 出行建议样式 */
.travel-tips {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed var(--el-border-color);
}

.tips-header {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--el-color-primary);
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
}

 .tips-list {
   list-style-type: none;
   padding: 0;
   margin: 0;
   text-align: left;
   font-size: 12px;
   color: var(--el-text-color-secondary);
   max-height: 72px;
   overflow-y: auto;
   scrollbar-width: thin;
 }

 /* 美化建议滚动条 */
 .tips-list::-webkit-scrollbar {
   width: 4px;
   background: var(--el-fill-color-lighter);
 }
 .tips-list::-webkit-scrollbar-thumb {
   background: var(--el-border-color);
   border-radius: 2px;
 }

.tips-list li {
  position: relative;
  padding-left: 12px;
  margin: 4px 0;
  line-height: 1.4;
}

.tips-list li::before {
  content: "•";
  position: absolute;
  left: 0;
  color: var(--el-color-primary);
}
@media (max-width: 900px) {
  .weather-forecast {
    padding: 8px 2px;
    max-width: 100vw;
    margin: 6px auto;
  }
  .forecast-list {
    gap: 8px;
    padding: 4px 0;
    max-width: 100vw;
    overflow-x: auto;
  }
  .forecast-item {
    padding: 8px 2px;
    border-radius: 10px;
    min-width: 100px;
    max-width: 140px;
    flex: 1 1 100px;
    margin: 0 auto;
  }
  .forecast-icon {
    font-size: 28px;
  }
  .forecast-temp {
    font-size: 12px;
  }
}
</style>
