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
        <div class="sidebar-item new-chat" @click="startNewChat">
          <el-icon><Edit /></el-icon>
          <span v-if="sidebarExpanded" class="sidebar-item-text">新对话</span>
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
        <el-input
          v-model="searchQuery"
          placeholder="请输入您的旅行需求，例如：北京3天游..."
          class="search-input"
          size="large"
          @keyup.enter="handleSearch"
        >
          <template #suffix>
            <el-button 
              type="primary" 
              :icon="Search" 
              @click="handleSearch"
              :loading="loading"
              circle
            />
          </template>
        </el-input>
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
            <div v-if="messages.length === 0" class="welcome-message">
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
            
            <div v-for="message in messages" :key="message.id" class="message-item">
              <div :class="['message-bubble', message.type]">
                <div class="message-content">{{ message.content }}</div>
                <div class="message-time">{{ formatTime(message.timestamp) }}</div>
              </div>
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
              <el-tooltip content="刷新地图" placement="top">
                <el-button size="small" :icon="Refresh" @click="refreshMap" circle />
              </el-tooltip>
            </div>
          </div>
          
          <div class="map-container">
            <MapDisplay 
              :itinerary-data="currentItinerary" 
              :center-location="mapCenter"
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
import { Search, Menu, Edit, Document, MapLocation, Location, ChatLineRound, Star, Refresh, CloseBold } from '@element-plus/icons-vue'
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
    MapDisplay
  },
  setup() {
    const searchQuery = ref('')
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
      
      if (currentChatId.value) {
        // 更新现有对话
        const chatIndex = chatHistory.value.findIndex(chat => chat.id === currentChatId.value)
        if (chatIndex !== -1) {
          chatHistory.value[chatIndex] = {
            ...chatHistory.value[chatIndex],
            messages: [...messages.value],
            itinerary: [...currentItinerary.value],
            mapCenter: { ...mapCenter.value },
            lastUpdated: Date.now(),
            title: chatTitle
          }
        }
      } else {
        // 创建新对话
        const newChat = {
          id: Date.now(),
          title: chatTitle,
          messages: [...messages.value],
          itinerary: [...currentItinerary.value],
          mapCenter: { ...mapCenter.value },
          lastUpdated: Date.now()
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

    // 开始新对话
    const startNewChat = () => {
      saveCurrentChat()
      messages.value = []
      currentItinerary.value = []
      mapCenter.value = { lng: 116.397428, lat: 39.90923 }
      currentChatId.value = null
      searchQuery.value = ''
    }

    // 加载指定对话
    const loadChat = (chatId) => {
      const chat = chatHistory.value.find(c => c.id === chatId)
      if (chat) {
        messages.value = [...chat.messages]
        currentItinerary.value = chat.itinerary || []
        mapCenter.value = chat.mapCenter || { lng: 116.397428, lat: 39.90923 }
        currentChatId.value = chatId
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

    // 处理搜索
    const handleSearch = async () => {
      if (!searchQuery.value.trim()) return

      const userQuery = searchQuery.value
      addMessage(userQuery, 'user')
      
      // 从查询中更新地图中心
      updateMapCenterFromQuery(userQuery)
      
      searchQuery.value = ''
      loading.value = true

      try {
        // 调用后端API
        const response = await axios.post('http://localhost:8000/api/trip/suggest', {
          destination: userQuery,
          duration: null,
          budget: null,
          interests: []
        })

        const recommendations = response.data.recommendations
        const suggestions = recommendations.join('\n• ')
        addMessage(`为您推荐以下旅行建议：\n• ${suggestions}`, 'assistant')
        
        // 解析行程数据并更新地图
        const itinerary = parseItineraryFromRecommendations(recommendations)
        currentItinerary.value = itinerary
        
        // 保存到历史记录
        saveCurrentChat()
      } catch (error) {
        console.error('API调用失败:', error)
        addMessage('抱歉，获取旅行建议时出现错误。请稍后再试。', 'assistant')
      } finally {
        loading.value = false
      }
    }

    // 组件挂载时加载历史记录
    loadChatHistory()

    return {
      searchQuery,
      messages,
      loading,
      messagesContainer,
      sidebarExpanded,
      chatHistory,
      currentChatId,
      mapDisplayRef,
      currentItinerary,
      mapCenter,
      handleSearch,
      formatTime,
      formatDate,
      toggleSidebar,
      startNewChat,
      loadChat,
      deleteChat,
      refreshMap,
      Search,
      Refresh
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

.search-input {
  width: 100%;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 25px;
  padding: 6px 6px 6px 20px;
  border: 2px solid #e8eaed;
  transition: all 0.3s;
  background-color: #f8f9fa;
  display: flex;
  align-items: center;
  min-height: 46px;
}

.search-input :deep(.el-input__wrapper:hover) {
  border-color: #dadce0;
  background-color: #ffffff;
}

.search-input :deep(.el-input__wrapper.is-focus) {
  border-color: #1a73e8;
  background-color: #ffffff;
  box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2);
}

.search-input :deep(.el-input__suffix) {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  padding: 0;
}

.search-input :deep(.el-button.is-circle) {
  width: 34px;
  height: 34px;
  min-height: 34px;
  padding: 0;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  border: none;
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
