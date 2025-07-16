<template>
  <div class="home-container">
    <!-- 侧边栏 -->
    <div :class="['sidebar', { expanded: sidebarExpanded }]">
      <div class="sidebar-header">
        <el-icon class="menu-icon" @click="toggleSidebar">
          <Menu />
        </el-icon>
        <div v-if="sidebarExpanded" class="sidebar-title">Trip Copilot</div>
      </div>
      
      <div class="sidebar-content">
        <div class="sidebar-item new-chat" @click="handleNewChatClick" :class="{ loading: newChatLoading }">
          <el-icon v-if="!newChatLoading"><Edit /></el-icon>
          <el-icon v-else class="is-loading"><Loading /></el-icon>
          <span v-if="sidebarExpanded" class="sidebar-item-text">
            {{ newChatLoading ? '初始化中...' : '新对话' }}
          </span>
        </div>
        
        <!-- 历史对话列表 -->
        <div v-if="sidebarExpanded" class="chat-history">
          <div class="history-title">最近对话</div>
          <div 
            v-for="chat in chatHistory" 
            :key="chat.id"
            :class="['history-item', { active: currentChatId === chat.id }]"
            @click="loadChat(chat.id)"
          >
            <div class="history-item-content">
              <div class="history-item-title">{{ chat.title }}</div>
              <div class="history-item-time">{{ formatDate(chat.lastUpdated) }}</div>
            </div>
            <el-button 
              class="delete-chat-btn" 
              type="text" 
              size="small"
              @click.stop="deleteChat(chat.id)"
              title="删除对话"
            >
              ×
            </el-button>
          </div>
          
          <div v-if="chatHistory.length === 0" class="no-history">
            暂无历史对话
          </div>
        </div>
      </div>
    </div>

    <!-- 主内容区 - 两栏布局 -->
    <div class="main-content">
      <!-- 搜索输入框 -->
      <div class="search-container">
        <div class="search-form">
          <el-input
            v-model="searchQuery"
            placeholder="请输入旅行目的地，例如：北京、上海..."
            class="destination-input"
            size="large"
            @keyup.enter="handleSearch"
          >
            <template #prepend>目的地</template>
          </el-input>
          
          <el-input-number
            v-model="tripDuration"
            :min="1"
            :max="30"
            placeholder="天数"
            class="duration-input"
            size="large"
            controls-position="right"
          >
            <template #prepend>天数</template>
          </el-input-number>
          
          <el-button 
            type="primary" 
            :icon="Search" 
            @click="handleSearch"
            :loading="loading"
            size="large"
            class="search-btn"
          >
            开始规划
          </el-button>
        </div>
      </div>

      <!-- 两栏内容区 -->
      <div class="content-columns">
        <!-- 左侧栏 - 行程规划文字描述 -->
        <div class="left-column itinerary-panel">
          <div class="panel-header">
            <h3>
              <el-icon><Document /></el-icon>
              旅行规划
            </h3>
          </div>
          
          <div class="messages-container" ref="messagesContainer">
            <!-- 欢迎界面 -->
            <div v-if="!currentPlan && messages.length === 0" class="welcome-message">
              <div class="welcome-icon">
                <el-icon><Location /></el-icon>
              </div>
              <h2>欢迎使用 Trip Copilot</h2>
              <p>您的智能旅行助手，为您规划完美的旅程</p>
              <div class="feature-tips">
                <div class="tip-item">
                  <el-icon><ChatLineRound /></el-icon>
                  <span>智能行程规划</span>
                </div>
                <div class="tip-item">
                  <el-icon><MapLocation /></el-icon>
                  <span>地图可视化</span>
                </div>
                <div class="tip-item">
                  <el-icon><Star /></el-icon>
                  <span>个性化推荐</span>
                </div>
              </div>
            </div>
            
            <!-- 结构化行程显示 -->
            <div v-if="currentPlan" class="itinerary-display">
              <div class="itinerary-header">
                <h3>{{ currentPlan.destination }}{{ currentPlan.total_days }}日游</h3>
                <div class="itinerary-summary">
                  <span>共{{ currentPlan.total_days }}天</span>
                  <span>{{ getTotalPlaces() }}个景点</span>
                </div>
              </div>
              
              <div class="itinerary-days">
                <div 
                  v-for="dayPlan in currentPlan.itinerary" 
                  :key="dayPlan.day"
                  :class="['day-item', { active: selectedDay === dayPlan.day }]"
                  @click="selectDay(dayPlan.day)"
                >
                  <div class="day-header">
                    <div class="day-number">第{{ dayPlan.day }}天</div>
                    <div class="day-theme">{{ dayPlan.theme }}</div>
                  </div>
                  
                  <div class="day-places">
                    <div 
                      v-for="(place, index) in dayPlan.places" 
                      :key="index"
                      class="place-item"
                    >
                      <div class="place-marker">{{ index + 1 }}</div>
                      <div class="place-info">
                        <div class="place-name">{{ place.name }}</div>
                        <div v-if="place.longitude && place.latitude" class="place-coords">
                          <el-icon><LocationFilled /></el-icon>
                          <span>{{ place.latitude.toFixed(4) }}, {{ place.longitude.toFixed(4) }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- 行程规划状态下的对话消息显示 -->
              <div v-if="messages.length > 0" class="chat-messages-in-plan">
                <div class="chat-messages-header">
                  <h4>对话记录</h4>
                </div>
                <div class="chat-messages-list">
                  <div v-for="message in messages" :key="message.id" class="message-item">
                    <div :class="['message-bubble', message.type]">
                      <div class="message-content">{{ message.content }}</div>
                      <div class="message-time">{{ formatTime(message.timestamp) }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 传统消息显示（兼容旧功能） -->
            <div v-if="!currentPlan && messages.length > 0">
              <div v-for="message in messages" :key="message.id" class="message-item">
                <div :class="['message-bubble', message.type]">
                  <div class="message-content">{{ message.content }}</div>
                  <div class="message-time">{{ formatTime(message.timestamp) }}</div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 聊天输入框 -->
          <div class="chat-input-container">
            <div class="chat-input-wrapper">
              <el-input
                v-model="chatInput"
                type="textarea"
                :rows="2"
                placeholder="有关行程的任何问题，我都可以帮您解答..."
                class="chat-input"
                @keyup.enter="handleChatSubmit"
                :disabled="chatLoading"
                resize="none"
                maxlength="500"
                show-word-limit
              />
              <el-button
                type="primary"
                :icon="ChatLineRound"
                @click="handleChatSubmit"
                :loading="chatLoading"
                class="chat-send-btn"
                size="small"
              >
                发送
              </el-button>
            </div>
          </div>
        </div>

        <!-- 右侧栏 - 地图显示 -->
        <div class="right-column map-panel">
          <div class="panel-header">
            <h3>
              <el-icon><MapLocation /></el-icon>
              地图导览
            </h3>
            <div class="map-controls">
              <el-tooltip content="路径规划" placement="top">
                <el-button size="small" :icon="Guide" @click="showRoutePanel = !showRoutePanel" circle />
              </el-tooltip>
              <el-tooltip content="刷新地图" placement="top">
                <el-button size="small" :icon="Refresh" @click="refreshMap" circle />
              </el-tooltip>
            </div>
          </div>
          
          <!-- 路径规划面板 -->
          <div v-if="showRoutePanel" class="route-panel">
            <div class="route-form">
              <div class="route-inputs">
                <el-input
                  v-model="routeForm.start"
                  placeholder="请输入起点"
                  size="small"
                  clearable
                >
                  <template #prefix>
                    <el-icon><LocationFilled /></el-icon>
                  </template>
                </el-input>
                
                <el-input
                  v-model="routeForm.end"
                  placeholder="请输入终点"
                  size="small"
                  clearable
                  style="margin-top: 8px;"
                >
                  <template #prefix>
                    <el-icon><Location /></el-icon>
                  </template>
                </el-input>
              </div>
              
              <div class="route-mode">
                <el-radio-group v-model="routeForm.mode" size="small">
                  <el-radio-button value="driving">驾车</el-radio-button>
                  <el-radio-button value="walking">步行</el-radio-button>
                </el-radio-group>
              </div>
              
              <div class="route-actions">
                <el-button 
                  type="primary" 
                  size="small" 
                  @click="planRoute"
                  :loading="routeLoading"
                  style="width: 100%; margin-bottom: 8px;"
                >
                  规划路线
                </el-button>
                
                <el-button 
                  v-if="currentRoute"
                  type="danger" 
                  size="small" 
                  @click="clearRoute"
                  plain
                  style="width: 100%;"
                >
                  清除路线
                </el-button>
              </div>
            </div>
            
            <!-- 路径信息显示 -->
            <div v-if="routeInfo" class="route-info">
              <div class="route-summary">
                <div class="summary-item">
                  <span class="label">距离:</span>
                  <span class="value">{{ formatDistance(routeInfo.distance) }}</span>
                </div>
                <div class="summary-item">
                  <span class="label">时间:</span>
                  <span class="value">{{ formatDuration(routeInfo.duration) }}</span>
                </div>
                <div class="summary-item">
                  <span class="label">方式:</span>
                  <span class="value">{{ getModeText(routeInfo.mode) }}</span>
                </div>
              </div>
            </div>
          </div>
          
          <div class="map-container">
            <MapDisplay 
              :itinerary-data="currentItinerary" 
              :center-location="mapCenter"
              :route-data="currentRoute"
              ref="mapDisplayRef"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, nextTick } from 'vue'
import { Search, Menu, Edit, Document, MapLocation, Location, ChatLineRound, Star, Refresh, CloseBold, Guide, LocationFilled, Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import MapDisplay from '@/components/MapDisplay.vue'

export default {
  name: 'Home',
  components: {
    Search,
    Menu,
    Edit,
    Document,
    MapLocation,
    Location,
    ChatLineRound,
    Star,
    Refresh,
    CloseBold,
    Guide,
    LocationFilled,
    Loading,
    MapDisplay
  },
  setup() {
    const searchQuery = ref('')
    const tripDuration = ref(3) // 新增：旅行天数
    const messages = ref([])
    const loading = ref(false)
    const messagesContainer = ref(null)
    const sidebarExpanded = ref(false)
    const chatHistory = ref([])
    const currentChatId = ref(null)
    const mapDisplayRef = ref(null)

    // 地图相关数据
    const currentItinerary = ref([])
    const mapCenter = ref({ lng: 116.397428, lat: 39.90923 }) // 默认北京
    
    // 新增：行程规划相关数据
    const currentPlan = ref(null) // 当前行程规划数据
    const selectedDay = ref(1) // 当前选中的天数
    
    // 路径规划相关数据
    const showRoutePanel = ref(false)
    const routeForm = ref({
      start: '',
      end: '',
      mode: 'driving'
    })
    const routeLoading = ref(false)
    const currentRoute = ref(null)
    const routeInfo = ref(null)
    
    // 聊天相关数据
    const chatInput = ref('')
    const chatLoading = ref(false)
    const newChatLoading = ref(false) // 新增：新对话加载状态

    // 初始化时加载历史对话
    const loadChatHistory = () => {
      const saved = localStorage.getItem('tripCopilotChatHistory')
      if (saved) {
        chatHistory.value = JSON.parse(saved)
      }
    }

    // 保存聊天历史
    const saveChatHistory = () => {
      localStorage.setItem('tripCopilotChatHistory', JSON.stringify(chatHistory.value))
    }

    // 保存当前对话
    const saveCurrentChat = () => {
      if (messages.value.length === 0) return

      const chatTitle = messages.value[0]?.content?.substring(0, 30) + '...' || '新对话'
      
      // 准备完整的对话数据，包含地图和行程规划相关数据
      const chatData = {
        messages: [...messages.value],
        itinerary: [...currentItinerary.value],
        mapCenter: { ...mapCenter.value },
        // 新增：保存行程规划数据
        currentPlan: currentPlan.value ? JSON.parse(JSON.stringify(currentPlan.value)) : null,
        // 新增：保存路径规划数据
        currentRoute: currentRoute.value ? JSON.parse(JSON.stringify(currentRoute.value)) : null,
        // 新增：保存当前选中的天数
        selectedDay: selectedDay.value,
        // 新增：保存路径规划表单数据
        routeForm: { ...routeForm.value },
        // 新增：保存搜索查询
        searchQuery: searchQuery.value,
        lastUpdated: Date.now(),
        title: chatTitle
      }
      
      if (currentChatId.value) {
        // 更新现有对话
        const chatIndex = chatHistory.value.findIndex(chat => chat.id === currentChatId.value)
        if (chatIndex !== -1) {
          chatHistory.value[chatIndex] = {
            ...chatHistory.value[chatIndex],
            ...chatData
          }
        }
      } else {
        // 创建新对话
        const newChat = {
          id: Date.now(),
          ...chatData
        }
        chatHistory.value.unshift(newChat)
        currentChatId.value = newChat.id
      }
      
      saveChatHistory()
    }

    // 切换侧边栏
    const toggleSidebar = () => {
      sidebarExpanded.value = !sidebarExpanded.value
    }

    // 处理新对话按钮点击
    const handleNewChatClick = () => {
      if (newChatLoading.value) {
        return // 防止重复点击
      }
      startNewChat()
    }

    // 开始新对话
    const startNewChat = async () => {
      newChatLoading.value = true
      
      try {
        // 先保存当前对话
        saveCurrentChat()
        
        // 清空所有状态数据
        messages.value = []
        currentItinerary.value = []
        mapCenter.value = { lng: 116.397428, lat: 39.90923 }
        currentPlan.value = null
        currentRoute.value = null
        selectedDay.value = 1
        routeForm.value = {
          start: '',
          end: '',
          mode: 'driving'
        }
        currentChatId.value = null
        searchQuery.value = ''
        tripDuration.value = 3
        
        // 通知地图组件清空数据
        await nextTick()
        if (mapDisplayRef.value && mapDisplayRef.value.clearAllData) {
          mapDisplayRef.value.clearAllData()
        }
        
        // 执行路径规划初始化，等待完成
        try {
          await reinitializeMapRoute()
          console.log('新对话初始化完成，路径规划已执行')
        } catch (err) {
          console.warn('路径规划初始化失败，但不影响新对话创建:', err)
        }
        
        ElMessage.success('已创建新对话')
      } catch (error) {
        console.error('新对话初始化失败:', error)
        ElMessage.error('新对话初始化失败，请重试')
      } finally {
        newChatLoading.value = false
      }
    }

    // 加载指定对话
    const loadChat = (chatId) => {
      const chat = chatHistory.value.find(c => c.id === chatId)
      if (chat) {
        // 恢复基本聊天数据
        messages.value = [...chat.messages]
        currentItinerary.value = chat.itinerary || []
        mapCenter.value = chat.mapCenter || { lng: 116.397428, lat: 39.90923 }
        currentChatId.value = chatId
        
        // 新增：恢复行程规划数据
        if (chat.currentPlan) {
          currentPlan.value = JSON.parse(JSON.stringify(chat.currentPlan))
        } else {
          currentPlan.value = null
        }
        
        // 新增：恢复路径规划数据
        if (chat.currentRoute) {
          currentRoute.value = JSON.parse(JSON.stringify(chat.currentRoute))
        } else {
          currentRoute.value = null
        }
        
        // 新增：恢复选中的天数
        selectedDay.value = chat.selectedDay || 1
        
        // 新增：恢复路径规划表单数据
        if (chat.routeForm) {
          routeForm.value = { ...chat.routeForm }
        } else {
          routeForm.value = {
            start: '',
            end: '',
            mode: 'driving'
          }
        }
        
        // 新增：恢复搜索查询
        searchQuery.value = chat.searchQuery || ''
        
        // 等待下一个tick后更新地图
        nextTick(() => {
          // 如果有行程规划数据，更新地图
          if (currentPlan.value) {
            updateMapWithPlan(currentPlan.value)
          }
          
          // 如果有路径数据，在地图上显示
          if (currentRoute.value && mapDisplayRef.value) {
            // 让地图组件显示路径
            if (mapDisplayRef.value.showRoute) {
              mapDisplayRef.value.showRoute(currentRoute.value)
            }
          }
        })
        
        scrollToBottom()
      }
    }

    // 删除对话
    const deleteChat = (chatId) => {
      const chatIndex = chatHistory.value.findIndex(c => c.id === chatId)
      if (chatIndex !== -1) {
        // 如果删除的是当前对话，则开始新对话
        if (currentChatId.value === chatId) {
          startNewChat()
        }
        
        // 从历史记录中移除
        chatHistory.value.splice(chatIndex, 1)
        saveChatHistory()
      }
    }

    // 刷新地图
    const refreshMap = () => {
      if (mapDisplayRef.value) {
        // 触发地图重新渲染
        nextTick(() => {
          if (currentItinerary.value.length > 0) {
            // 重新设置行程数据
            const temp = [...currentItinerary.value]
            currentItinerary.value = []
            nextTick(() => {
              currentItinerary.value = temp
            })
          }
        })
      }
    }

    // 格式化时间
    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit'
      })
    }

    // 格式化日期
    const formatDate = (timestamp) => {
      const date = new Date(timestamp)
      const now = new Date()
      const diffTime = now - date
      const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
      
      if (diffDays === 0) {
        return '今天'
      } else if (diffDays === 1) {
        return '昨天'
      } else if (diffDays < 7) {
        return `${diffDays}天前`
      } else {
        return date.toLocaleDateString('zh-CN')
      }
    }

    // 滚动到底部
    const scrollToBottom = () => {
      nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
        }
      })
    }

    // 添加消息
    const addMessage = (content, type = 'user') => {
      const message = {
        id: Date.now(),
        content,
        type,
        timestamp: Date.now()
      }
      messages.value.push(message)
      scrollToBottom()
    }

    /**
     * 解析AI返回的行程建议并提取地理位置信息
     * @param {Array} recommendations - AI返回的推荐列表
     * @returns {Array} 包含位置信息的行程数组
     */
    const parseItineraryFromRecommendations = (recommendations) => {
      return recommendations.map((recommendation, index) => {
        // 从推荐文本中提取可能的地点信息
        return {
          id: index + 1,
          description: recommendation,
          place: extractMainLocation(recommendation)
        }
      })
    }

    /**
     * 从推荐文本中提取主要地点
     * @param {string} text - 推荐文本
     * @returns {string} 提取的地点名称
     */
    const extractMainLocation = (text) => {
      // 尝试从文本中提取地点名称的正则表达式
      const patterns = [
        /(?:参观|游览|前往|访问)([^，。！？\n]{2,12})(?:景区|景点|公园|博物馆|寺庙|古镇|山|湖|河|街|路|广场|院|宫|塔|楼|城)/,
        /([^，。！？\n]{2,12})(?:景区|景点|公园|博物馆|寺庙|古镇|山|湖|河|街|路|广场|院|宫|塔|楼|城)/,
        /在([^，。！？\n]{2,12})(?:停留|游玩|参观|体验)/,
        /([^，。！？\n]{2,12})(?:是|为|有着|拥有).{0,20}(?:著名|知名|有名)/
      ]
      
      for (const pattern of patterns) {
        const match = text.match(pattern)
        if (match && match[1]) {
          return match[1].trim()
        }
      }
      
      // 如果没有找到明确的地点，返回文本的前几个字符
      const cleanText = text.replace(/^\d+\.?\s*/, '').trim()
      return cleanText.length > 15 ? cleanText.substring(0, 12) + '...' : cleanText
    }

    /**
     * 从用户查询中提取目的地信息并设置地图中心
     * @param {string} query - 用户查询
     */
    const updateMapCenterFromQuery = (query) => {
      // 简单的城市坐标映射
      const cityCoordinates = {
        '北京': { lng: 116.407526, lat: 39.90403 },
        '上海': { lng: 121.473701, lat: 31.230416 },
        '广州': { lng: 113.264434, lat: 23.129162 },
        '深圳': { lng: 114.085947, lat: 22.547 },
        '杭州': { lng: 120.153576, lat: 30.287459 },
        '南京': { lng: 118.767413, lat: 32.041544 },
        '成都': { lng: 104.065735, lat: 30.659462 },
        '西安': { lng: 108.948024, lat: 34.263161 },
        '重庆': { lng: 106.504962, lat: 29.533155 },
        '武汉': { lng: 114.298572, lat: 30.584355 },
        '天津': { lng: 117.190182, lat: 39.125596 },
        '苏州': { lng: 120.619585, lat: 31.317987 },
        '青岛': { lng: 120.355173, lat: 36.082982 },
        '长沙': { lng: 112.982279, lat: 28.19409 },
        '大连': { lng: 121.618622, lat: 38.91459 },
        '厦门': { lng: 118.11022, lat: 24.490474 },
        '福州': { lng: 119.306239, lat: 26.075302 },
        '哈尔滨': { lng: 126.642464, lat: 45.756967 },
        '济南': { lng: 117.000923, lat: 36.675807 },
        '昆明': { lng: 102.712251, lat: 25.040609 },
        '沈阳': { lng: 123.429096, lat: 41.796767 },
        '石家庄': { lng: 114.502461, lat: 38.045474 },
        '合肥': { lng: 117.283042, lat: 31.86119 },
        '郑州': { lng: 113.665412, lat: 34.757975 },
        '太原': { lng: 112.549248, lat: 37.857014 },
        '南昌': { lng: 115.892151, lat: 28.676493 },
        '贵阳': { lng: 106.713478, lat: 26.578343 },
        '南宁': { lng: 108.320004, lat: 22.82402 },
        '海口': { lng: 110.35051, lat: 20.018971 },
        '兰州': { lng: 103.823557, lat: 36.058039 },
        '银川': { lng: 106.27406, lat: 38.466637 },
        '西宁': { lng: 101.778916, lat: 36.623178 },
        '乌鲁木齐': { lng: 87.617733, lat: 43.792818 },
        '拉萨': { lng: 91.132212, lat: 29.660361 }
      }
      
      // 查找查询中是否包含已知城市
      for (const [city, coords] of Object.entries(cityCoordinates)) {
        if (query.includes(city)) {
          mapCenter.value = coords
          return
        }
      }
    }

    // 路径规划相关函数
    
    /**
     * 规划路线
     */
    const planRoute = async (isAutoInit = false) => {
      if (!routeForm.value.start.trim() || !routeForm.value.end.trim()) {
        if (!isAutoInit) {
          ElMessage.warning('请输入起点和终点')
        }
        return
      }

      routeLoading.value = true
      
      try {
        const response = await axios.post('http://localhost:8000/api/trip/path', {
          start: routeForm.value.start,
          end: routeForm.value.end,
          mode: routeForm.value.mode
        })

        if (response.data.success) {
          const pathData = response.data.path_data
          if (!isAutoInit) {
            console.log('收到路径数据:', pathData)
          }
          
          // 验证路径数据中的坐标
          const startLng = parseFloat(pathData.start_point.longitude)
          const startLat = parseFloat(pathData.start_point.latitude)
          const endLng = parseFloat(pathData.end_point.longitude)
          const endLat = parseFloat(pathData.end_point.latitude)
          
          // 检查坐标有效性
          if (isNaN(startLng) || isNaN(startLat) || isNaN(endLng) || isNaN(endLat)) {
            console.error('路径数据中包含无效坐标:', {
              start: { lng: startLng, lat: startLat },
              end: { lng: endLng, lat: endLat }
            })
            if (!isAutoInit) {
              ElMessage.error('路径数据中包含无效坐标')
            }
            return
          }
          
          // 更新路径数据，确保坐标为数值类型
          currentRoute.value = {
            ...pathData,
            start_point: {
              ...pathData.start_point,
              longitude: startLng,
              latitude: startLat
            },
            end_point: {
              ...pathData.end_point,
              longitude: endLng,
              latitude: endLat
            }
          }
          
          // 更新路径信息
          const routeData = pathData.route_info
          if (routeData && routeData.paths && routeData.paths.length > 0) {
            const path = routeData.paths[0]
            routeInfo.value = {
              distance: path.distance,
              duration: path.duration,
              mode: pathData.mode
            }
            if (!isAutoInit) {
              console.log('路径信息更新:', routeInfo.value)
            }
          }
          
          // 更新地图中心
          if (isAutoInit) {
            // 自动初始化时设置地图中心为北京
            mapCenter.value = {
              lng: 116.407526,
              lat: 39.90403
            }
            if (!isAutoInit) {
              console.log('地图中心设置为北京:', mapCenter.value)
            }
          } else {
            // 手动规划时设置地图中心到起点
            mapCenter.value = {
              lng: startLng,
              lat: startLat
            }
            console.log('地图中心更新到起点:', mapCenter.value)
          }
          
          // 只有非自动初始化时才添加消息到聊天和显示成功提示
          if (!isAutoInit) {
            const routeMessage = `路径规划完成：\n从 ${pathData.start_point.name} 到 ${pathData.end_point.name}\n` +
              `距离：${formatDistance(routeInfo.value.distance)}\n` +
              `预计时间：${formatDuration(routeInfo.value.duration)}\n` +
              `出行方式：${getModeText(routeInfo.value.mode)}`
            
            addMessage(routeMessage, 'assistant')
            ElMessage.success('路径规划成功')
          } else {
            // 自动初始化时只在控制台输出
            console.log('地图路径规划自动初始化成功')
          }
        } else {
          console.error('路径规划失败:', response.data.error_message)
          if (!isAutoInit) {
            ElMessage.error(response.data.error_message || '路径规划失败')
          }
        }
      } catch (error) {
        console.error('路径规划失败:', error)
        if (!isAutoInit) {
          ElMessage.error('路径规划失败，请检查网络连接')
        }
      } finally {
        routeLoading.value = false
      }
    }

    /**
     * 格式化距离
     */
    const formatDistance = (distance) => {
      if (!distance) return '未知'
      const dist = parseInt(distance)
      if (dist >= 1000) {
        return (dist / 1000).toFixed(1) + ' 公里'
      }
      return dist + ' 米'
    }

    /**
     * 格式化时长
     */
    const formatDuration = (duration) => {
      if (!duration) return '未知'
      const dur = parseInt(duration)
      const hours = Math.floor(dur / 3600)
      const minutes = Math.floor((dur % 3600) / 60)
      
      if (hours > 0) {
        return `${hours}小时${minutes}分钟`
      }
      return `${minutes}分钟`
    }

    /**
     * 获取出行方式文本
     */
    const getModeText = (mode) => {
      const modeMap = {
        'driving': '驾车',
        'walking': '步行'
      }
      return modeMap[mode] || mode
    }

    /**
     * 清除路径
     */
    const clearRoute = () => {
      currentRoute.value = null
      routeInfo.value = null
      routeForm.value.start = ''
      routeForm.value.end = ''
      addMessage('已清除路径规划', 'assistant')
      ElMessage.success('路径已清除')
    }

    // 聊天处理函数
    
    /**
     * 处理聊天提交
     */
    const handleChatSubmit = async () => {
      if (!chatInput.value.trim()) {
        ElMessage.warning('请输入您的问题')
        return
      }
      
      const userMessage = chatInput.value.trim()
      chatInput.value = ''
      chatLoading.value = true
      
      // 添加用户消息
      addMessage(userMessage, 'user')
      
      try {
        // 构建上下文数据
        const contextData = {
          currentPlan: currentPlan.value,
          currentRoute: currentRoute.value,
          selectedDay: selectedDay.value,
          routeForm: routeForm.value,
          searchQuery: searchQuery.value,
          mapCenter: mapCenter.value
        }
        
        // 发送到AI聊天API
        const response = await axios.post('http://localhost:8000/api/chat', {
          message: userMessage,
          context: JSON.stringify(contextData)
        })
        
        if (response.data.success) {
          addMessage(response.data.reply, 'assistant')
        } else {
          addMessage('抱歉，我暂时无法回答您的问题，请稍后再试。', 'assistant')
        }
      } catch (error) {
        console.error('聊天API调用失败:', error)
        addMessage('抱歉，服务暂时不可用，请稍后再试。', 'assistant')
      } finally {
        chatLoading.value = false
        // 保存对话到历史记录
        saveCurrentChat()
      }
    }

    // 处理搜索 - 重构为行程规划
    const handleSearch = async () => {
      if (!searchQuery.value.trim()) {
        ElMessage.warning('请输入目的地')
        return
      }
      
      if (!tripDuration.value || tripDuration.value < 1) {
        ElMessage.warning('请输入有效的旅行天数')
        return
      }

      const destination = searchQuery.value.trim()
      const duration = tripDuration.value
      
      // 添加用户消息（用于兼容历史记录）
      addMessage(`我想去${destination}玩${duration}天，请帮我规划行程`, 'user')
      
      // 从查询中更新地图中心
      updateMapCenterFromQuery(destination)
      
      loading.value = true

      try {
        // 调用新的行程规划API
        const response = await axios.post('http://localhost:8000/api/trip/plan', {
          destination: destination,
          duration: duration
        })

        if (response.data.success && response.data.plan_data) {
          const planData = response.data.plan_data
          currentPlan.value = planData
          selectedDay.value = 1 // 默认选中第一天
          
          // 更新地图数据
          updateMapWithPlan(planData)
          
          // 添加成功消息
          addMessage(`已为您规划${destination}${duration}天的详细行程，请查看左侧面板和右侧地图`, 'assistant')
          
          ElMessage.success('行程规划完成！')
        } else {
          throw new Error(response.data.error_message || '行程规划失败')
        }
        
        // 保存到历史记录
        saveCurrentChat()
      } catch (error) {
        console.error('行程规划API调用失败:', error)
        addMessage('抱歉，行程规划时出现错误。请稍后再试。', 'assistant')
        ElMessage.error('行程规划失败，请重试')
      } finally {
        loading.value = false
      }
    }

    /**
     * 选择某一天的行程
     */
    const selectDay = (day) => {
      selectedDay.value = day
      if (currentPlan.value) {
        updateMapForDay(day)
      }
    }
    
    /**
     * 更新地图显示指定天数的行程
     */
    const updateMapForDay = (day) => {
      if (!currentPlan.value || !currentPlan.value.itinerary) {
        console.warn('没有行程数据')
        return
      }
      
      const dayPlan = currentPlan.value.itinerary.find(d => d.day === day)
      if (!dayPlan) {
        console.warn(`找不到第${day}天的行程`)
        return
      }
      
      // 验证并过滤当天的地点数据
      const dayPlaces = []
      let invalidCount = 0
      
      if (dayPlan.places && Array.isArray(dayPlan.places)) {
        dayPlan.places.forEach(place => {
          const validPlace = validateAndConvertCoordinates(place)
          if (validPlace) {
            dayPlaces.push(validPlace)
          } else {
            invalidCount++
          }
        })
      }
      
      console.log(`第${day}天: 有效地点 ${dayPlaces.length} 个，无效地点 ${invalidCount} 个`)
      
      // 更新地图组件的数据
      if (mapDisplayRef.value && dayPlaces.length > 0) {
        mapDisplayRef.value.updateDayRoute(dayPlaces, day)
        
        // 更新地图中心到当天第一个地点
        mapCenter.value = {
          lng: dayPlaces[0].longitude,
          lat: dayPlaces[0].latitude
        }
      } else if (dayPlaces.length === 0) {
        console.warn(`第${day}天没有有效的地点坐标`)
      }
    }
    
    /**
     * 验证并转换坐标
     */
    const validateAndConvertCoordinates = (place) => {
      const lng = parseFloat(place.longitude)
      const lat = parseFloat(place.latitude)
      
      // 验证坐标有效性
      if (isNaN(lng) || isNaN(lat) || !isFinite(lng) || !isFinite(lat)) {
        console.warn(`地点 "${place.name}" 坐标无效:`, { longitude: place.longitude, latitude: place.latitude })
        return null
      }
      
      // 检查坐标范围
      if (lng < -180 || lng > 180 || lat < -90 || lat > 90) {
        console.warn(`地点 "${place.name}" 坐标超出范围:`, { lng, lat })
        return null
      }
      
      // 排除0,0坐标
      if (lng === 0 && lat === 0) {
        console.warn(`地点 "${place.name}" 坐标为原点，可能无效`)
        return null
      }
      
      return {
        ...place,
        longitude: lng,
        latitude: lat
      }
    }

    /**
     * 根据行程规划更新地图
     */
    const updateMapWithPlan = (planData) => {
      if (!planData || !planData.itinerary) {
        console.warn('行程规划数据为空')
        return
      }
      
      // 收集所有地点并验证坐标
      const allPlaces = []
      let invalidPlaces = 0
      
      planData.itinerary.forEach(dayPlan => {
        if (dayPlan.places && Array.isArray(dayPlan.places)) {
          dayPlan.places.forEach(place => {
            const validPlace = validateAndConvertCoordinates(place)
            if (validPlace) {
              allPlaces.push({
                ...validPlace,
                day: dayPlan.day
              })
            } else {
              invalidPlaces++
            }
          })
        }
      })
      
      console.log(`处理完成: 有效地点 ${allPlaces.length} 个，无效地点 ${invalidPlaces} 个`)
      
      // 更新当前行程数据
      currentItinerary.value = allPlaces
      
      // 如果有有效地点，更新地图中心到第一个地点
      if (allPlaces.length > 0) {
        const firstPlace = allPlaces[0]
        mapCenter.value = {
          lng: firstPlace.longitude,
          lat: firstPlace.latitude
        }
        console.log('地图中心已更新到:', mapCenter.value, '地点:', firstPlace.name)
      } else {
        console.warn('没有有效的地点坐标，保持默认地图中心')
        ElMessage.warning('部分地点坐标无效，地图显示可能不完整')
      }
      
      // 默认显示第一天的路线
      nextTick(() => {
        updateMapForDay(1)
      })
    }
    
    /**
     * 获取总地点数
     */
    const getTotalPlaces = () => {
      if (!currentPlan.value || !currentPlan.value.itinerary) return 0
      
      return currentPlan.value.itinerary.reduce((total, dayPlan) => {
        return total + (dayPlan.places ? dayPlan.places.length : 0)
      }, 0)
    }

    // 组件挂载时加载历史记录和自动规划路线
    loadChatHistory()
    
    // 自动规划南开大学津南校区到八里台校区的路线
    const autoInitRoute = async () => {
      // 设置起点和终点
      routeForm.value.start = '南开大学津南校区'
      routeForm.value.end = '南开大学八里台校区'
      routeForm.value.mode = 'driving'
      
      // 初次调用时保持路径规划面板隐藏
      showRoutePanel.value = false
      
      // 延迟一秒后自动调用路径规划，传入 true 表示这是自动初始化
      setTimeout(async () => {
        await planRoute(true)
      }, 1000)
    }
    
    // 新增：重新初始化地图路径规划（用于新对话时）
    const reinitializeMapRoute = async () => {
      console.log('开始重新初始化地图路径规划...')
      
      // 重置路径规划表单到默认状态
      routeForm.value.start = '南开大学津南校区'
      routeForm.value.end = '南开大学八里台校区'
      routeForm.value.mode = 'driving'
      
      // 确保路径规划面板保持隐藏状态
      showRoutePanel.value = false
      
      try {
        // 等待一小段时间确保地图组件已清空
        await new Promise(resolve => setTimeout(resolve, 500))
        
        // 执行自动路径规划
        await planRoute(true)
        
        console.log('地图路径规划重新初始化完成')
      } catch (error) {
        console.error('重新初始化地图路径规划失败:', error)
        // 即使失败也不显示错误消息，因为这是后台操作
      }
    }
    
    // 在组件挂载后执行自动路线规划
    nextTick(() => {
      autoInitRoute()
    })

    return {
      searchQuery,
      tripDuration,
      messages,
      loading,
      messagesContainer,
      sidebarExpanded,
      chatHistory,
      currentChatId,
      mapDisplayRef,
      currentItinerary,
      mapCenter,
      // 行程规划相关
      currentPlan,
      selectedDay,
      selectDay,
      updateMapWithPlan,
      getTotalPlaces,
      // 路径规划相关
      showRoutePanel,
      routeForm,
      routeLoading,
      currentRoute,
      routeInfo,
      planRoute,
      formatDistance,
      formatDuration,
      getModeText,
      clearRoute,
      // 聊天相关
      chatInput,
      chatLoading,
      newChatLoading,
      handleChatSubmit,
      // 功能函数
      handleSearch,
      formatTime,
      formatDate,
      toggleSidebar,
      handleNewChatClick,
      startNewChat,
      loadChat,
      deleteChat,
      refreshMap,
      reinitializeMapRoute,
      // 图标组件
      Search,
      Menu,
      Edit,
      Document,
      MapLocation,
      Location,
      ChatLineRound,
      Star,
      Refresh,
      CloseBold,
      Guide,
      LocationFilled,
      Loading
    }
  }
}
</script>


<style scoped>
.home-container {
  display: flex;
  height: 100vh;
  background-color: #fafbfc;
  overflow: hidden;
}

/* 侧边栏样式 */
.sidebar {
  width: 60px;
  background-color: #ffffff;
  border-right: 1px solid #e8eaed;
  display: flex;
  flex-direction: column;
  padding: 20px 0;
  transition: width 0.3s ease;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  z-index: 1000;
}

.sidebar.expanded {
  width: 280px;
}

.sidebar-header {
  padding: 0 20px;
  margin-bottom: 30px;
  display: flex;
  align-items: center;
  gap: 15px;
}

.menu-icon {
  color: #5f6368;
  font-size: 24px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.menu-icon:hover {
  transform: scale(1.1);
  color: #1a73e8;
}

.sidebar-title {
  color: #202124;
  font-size: 18px;
  font-weight: 600;
  white-space: nowrap;
}

.sidebar-content {
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
  flex: 1;
}

.sidebar-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 12px;
  background-color: #f8f9fa;
  border: 1px solid #e8eaed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  min-height: 44px;
  overflow: hidden;
}

.sidebar.expanded .sidebar-item {
  justify-content: flex-start;
}

.sidebar-item:hover {
  background-color: #e8f0fe;
  border-color: #1a73e8;
  transform: translateX(2px);
}

.sidebar-item.new-chat {
  background-color: #e8f5e8;
  border-color: #34a853;
}

.sidebar-item.new-chat:hover {
  background-color: #d3eddb;
  border-color: #137333;
}

.sidebar-item.new-chat.loading {
  background-color: #fff3cd;
  border-color: #ffc107;
  cursor: wait;
}

.sidebar-item.new-chat.loading:hover {
  background-color: #fff3cd;
  border-color: #ffc107;
  transform: none;
}

.sidebar-item .el-icon {
  color: #5f6368;
  font-size: 16px;
  min-width: 20px;
  max-width: 20px;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sidebar-item .el-icon svg {
  width: 16px;
  height: 16px;
  display: block;
}

.sidebar-item.new-chat .el-icon {
  color: #34a853;
}

.sidebar-item-text {
  color: #202124;
  font-size: 14px;
  white-space: nowrap;
  font-weight: 500;
}

/* 历史对话样式 */
.chat-history {
  flex: 1;
  margin-top: 20px;
}

.history-title {
  color: #5f6368;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 15px;
  padding: 0 12px;
}

.history-item {
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 8px;
  border: 1px solid transparent;
  background-color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.history-item:hover {
  background-color: #f8f9fa;
  border-color: #e8eaed;
}

.history-item.active {
  background-color: #e8f0fe;
  border-color: #1a73e8;
}

.history-item-content {
  flex: 1;
  min-width: 0;
}

.history-item-title {
  color: #202124;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item-time {
  color: #5f6368;
  font-size: 12px;
}

.delete-chat-btn {
  opacity: 0;
  padding: 4px;
  min-height: auto;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
  color: #5f6368;
  flex-shrink: 0;
  font-size: 16px;
  font-weight: bold;
  border: none;
  background: none;
}

.delete-chat-btn:hover {
  color: #ea4335;
  background-color: #fce8e6;
  border-radius: 4px;
}

.history-item:hover .delete-chat-btn {
  opacity: 1;
}

.no-history {
  color: #80868b;
  font-size: 14px;
  text-align: center;
  padding: 20px 12px;
  font-style: italic;
}

/* 主内容区样式 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #fafbfc;
  overflow: hidden;
}

/* 搜索容器 */
.search-container {
  padding: 20px;
  background-color: #ffffff;
  border-bottom: 1px solid #e8eaed;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.search-form {
  display: flex;
  gap: 12px;
  align-items: center;
  width: 100%;
}

.destination-input {
  flex: 2;
}

.duration-input {
  flex: 1;
  min-width: 120px;
}

.search-btn {
  min-width: 100px;
  height: 40px;
}

.destination-input :deep(.el-input__wrapper),
.duration-input :deep(.el-input-number) {
  border-radius: 8px;
  border: 2px solid #e8eaed;
  transition: all 0.3s;
  background-color: #f8f9fa;
}

.destination-input :deep(.el-input__wrapper:hover),
.duration-input :deep(.el-input-number:hover) {
  border-color: #dadce0;
  background-color: #ffffff;
}

.destination-input :deep(.el-input__wrapper.is-focus),
.duration-input :deep(.el-input-number.is-focus) {
  border-color: #1a73e8;
  background-color: #ffffff;
  box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2);
}

/* 行程显示样式 */
.itinerary-display {
  padding: 20px;
  background-color: #ffffff;
}

.itinerary-header {
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 2px solid #f0f0f0;
}

.itinerary-header h3 {
  margin: 0 0 8px 0;
  color: #1a73e8;
  font-size: 18px;
  font-weight: 600;
}

.itinerary-summary {
  display: flex;
  gap: 15px;
  color: #5f6368;
  font-size: 14px;
}

.itinerary-days {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.day-item {
  border: 2px solid #e8eaed;
  border-radius: 12px;
  background-color: #fafbfc;
  cursor: pointer;
  transition: all 0.3s ease;
  overflow: hidden;
}

.day-item:hover {
  border-color: #1a73e8;
  background-color: #f8f9ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(26, 115, 232, 0.15);
}

.day-item.active {
  border-color: #1a73e8;
  background-color: #e8f0fe;
  box-shadow: 0 2px 8px rgba(26, 115, 232, 0.2);
}

.day-header {
  padding: 16px 20px 12px;
  background: linear-gradient(135deg, #1a73e8 0%, #4285f4 100%);
  color: white;
}

.day-item.active .day-header {
  background: linear-gradient(135deg, #137333 0%, #34a853 100%);
}

.day-number {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}

/* 行程规划中的聊天消息样式 */
.chat-messages-in-plan {
  margin-top: 20px;
  border-top: 1px solid #e8eaed;
  padding-top: 15px;
}

.chat-messages-header {
  margin-bottom: 12px;
}

.chat-messages-header h4 {
  color: #202124;
  font-size: 14px;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.chat-messages-header h4::before {
  content: "💬";
  font-size: 16px;
}

.chat-messages-list {
  max-height: 200px;
  overflow-y: auto;
  padding-right: 8px;
}

.chat-messages-list .message-item {
  margin-bottom: 12px;
}

.chat-messages-list .message-bubble {
  max-width: 100%;
  font-size: 13px;
  padding: 8px 12px;
}

.chat-messages-list .message-time {
  font-size: 11px;
}

.day-theme {
  font-size: 14px;
  opacity: 0.9;
  line-height: 1.4;
}

.day-places {
  padding: 16px 20px;
}

.place-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.place-item:last-child {
  border-bottom: none;
}

.place-marker {
  width: 24px;
  height: 24px;
  background: linear-gradient(135deg, #ff6b6b 0%, #ff8e8e 100%);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  min-width: 24px;
  box-shadow: 0 2px 4px rgba(255, 107, 107, 0.3);
}

.place-info {
  flex: 1;
}

.place-name {
  font-size: 15px;
  font-weight: 500;
  color: #202124;
  margin-bottom: 2px;
}

.place-coords {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #5f6368;
}

.place-coords .el-icon {
  font-size: 12px;
}
 

/* 两栏内容区 */
.content-columns {
  display: flex;
  flex: 1;
  gap: 1px;
  background-color: #e8eaed;
  overflow: hidden;
}

/* 左侧栏 - 行程规划 */
.left-column {
  flex: 1;
  background-color: #ffffff;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 右侧栏 - 地图 */
.right-column {
  flex: 1;
  background-color: #ffffff;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 面板头部 */
.panel-header {
  padding: 16px 20px;
  background-color: #f8f9fa;
  border-bottom: 1px solid #e8eaed;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #202124;
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-header h3 .el-icon {
  color: #1a73e8;
  font-size: 18px;
}

.map-controls {
  display: flex;
  gap: 8px;
}

/* 消息容器 */
.messages-container {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.welcome-message {
  text-align: center;
  margin-top: 60px;
  color: #5f6368;
}

.welcome-icon {
  margin-bottom: 20px;
}

.welcome-icon .el-icon {
  font-size: 48px;
  color: #1a73e8;
}

.welcome-message h2 {
  font-size: 24px;
  margin-bottom: 12px;
  color: #202124;
  font-weight: 500;
}

.welcome-message p {
  font-size: 16px;
  color: #5f6368;
  margin-bottom: 30px;
}

.feature-tips {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin-top: 20px;
}

.tip-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #5f6368;
}

.tip-item .el-icon {
  font-size: 24px;
  color: #1a73e8;
}

.tip-item span {
  font-size: 14px;
  font-weight: 500;
}

/* 消息样式 */
.message-item {
  display: flex;
  margin-bottom: 16px;
}

.message-bubble {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 18px;
  position: relative;
}

.message-bubble.user {
  background-color: #1a73e8;
  color: white;
  margin-left: auto;
  border-bottom-right-radius: 4px;
}

.message-bubble.assistant {
  background-color: #f8f9fa;
  color: #202124;
  border: 1px solid #e8eaed;
  margin-right: auto;
  border-bottom-left-radius: 4px;
}

.message-content {
  white-space: pre-line;
  line-height: 1.5;
  font-size: 14px;
}

.message-time {
  font-size: 12px;
  opacity: 0.7;
  margin-top: 4px;
}

/* 地图容器 */
.map-container {
  flex: 1;
  background-color: #f8f9fa;
  overflow: hidden;
}

/* 聊天输入框样式 */
.chat-input-container {
  border-top: 1px solid #e8eaed;
  background-color: #ffffff;
  padding: 12px 15px;
}

.chat-input-wrapper {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
}

.chat-input :deep(.el-textarea__inner) {
  border-radius: 8px;
  border: 1px solid #e8eaed;
  resize: none;
  font-size: 14px;
  line-height: 1.4;
  padding: 8px 12px;
}

.chat-input :deep(.el-textarea__inner):focus {
  border-color: #1a73e8;
  box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2);
}

.chat-send-btn {
  flex-shrink: 0;
  height: 32px;
  padding: 0 16px;
}

/* 滚动条样式 */
.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track {
  background: #f8f9fa;
  border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb {
  background: #dadce0;
  border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background: #bdc1c6;
}

/* 路径规划面板 */
.route-panel {
  border-bottom: 1px solid #e8eaed;
  background-color: #f8f9fa;
}

.route-form {
  padding: 12px 15px;
}

.route-inputs {
  margin-bottom: 12px;
}

.route-mode {
  margin-bottom: 12px;
}

.route-mode :deep(.el-radio-group) {
  width: 100%;
}

.route-mode :deep(.el-radio-button__inner) {
  padding: 8px 12px;
  font-size: 12px;
}

.route-actions {
  margin-bottom: 8px;
}

.route-info {
  padding: 0 15px 12px;
}

.route-summary {
  background: #ffffff;
  border-radius: 6px;
  padding: 10px;
  border: 1px solid #e8eaed;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 13px;
}

.summary-item .label {
  color: #5f6368;
  font-weight: 500;
}

.summary-item .value {
  color: #202124;
  font-weight: 600;
}

.summary-item:not(:last-child) {
  border-bottom: 1px solid #f1f3f4;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .content-columns {
    flex-direction: column;
  }
  
  .left-column,
  .right-column {
    flex: none;
    height: 50%;
  }
  
  .feature-tips {
    flex-direction: column;
    gap: 15px;
  }
  
  .tip-item {
    flex-direction: row;
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .sidebar.expanded {
    width: 250px;
  }
  
  .search-container {
    padding: 15px;
  }
  
  .messages-container {
    padding: 15px;
  }
  
  .panel-header {
    padding: 12px 15px;
  }
  
  .panel-header h3 {
    font-size: 14px;
  }
  
  .welcome-message {
    margin-top: 30px;
  }
  
  .welcome-message h2 {
    font-size: 20px;
  }
  
  .welcome-icon .el-icon {
    font-size: 36px;
  }
}

@media (max-width: 480px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    height: 100vh;
    z-index: 2000;
    transform: translateX(-100%);
  }
  
  .sidebar.expanded {
    transform: translateX(0);
    width: 280px;
  }
  
  .main-content {
    margin-left: 0;
  }
  
  .content-columns {
    gap: 0;
  }
  
  .left-column,
  .right-column {
    border-radius: 0;
  }
}
</style>
