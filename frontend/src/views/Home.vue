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
            <div class="history-item-title">{{ chat.title }}</div>
            <div class="history-item-time">{{ formatDate(chat.lastUpdated) }}</div>
          </div>
          
          <div v-if="chatHistory.length === 0" class="no-history">
            暂无历史对话
          </div>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <div class="chat-container">
        <!-- 搜索输入框 -->
        <div class="search-container">
          <el-input
            v-model="searchQuery"
            placeholder="请输入您的旅行需求..."
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

        <!-- 聊天消息区域 -->
        <div class="messages-container" ref="messagesContainer">
          <div v-if="messages.length === 0" class="welcome-message">
            <h2>欢迎使用 Trip Copilot</h2>
            <p>您的智能旅行助手，为您规划完美的旅程</p>
          </div>
          
          <div v-for="message in messages" :key="message.id" class="message-item">
            <div :class="['message-bubble', message.type]">
              <div class="message-content">{{ message.content }}</div>
              <div class="message-time">{{ formatTime(message.timestamp) }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, nextTick } from 'vue'
import { Search, Menu, Edit } from '@element-plus/icons-vue'
import axios from 'axios'

export default {
  name: 'Home',
  components: {
    Search,
    Menu,
    Edit
  },
  setup() {
    const searchQuery = ref('')
    const messages = ref([])
    const loading = ref(false)
    const messagesContainer = ref(null)
    const sidebarExpanded = ref(false)
    const chatHistory = ref([])
    const currentChatId = ref(null)

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
      currentChatId.value = null
      searchQuery.value = ''
    }

    // 加载指定对话
    const loadChat = (chatId) => {
      const chat = chatHistory.value.find(c => c.id === chatId)
      if (chat) {
        messages.value = [...chat.messages]
        currentChatId.value = chatId
        scrollToBottom()
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

    // 处理搜索
    const handleSearch = async () => {
      if (!searchQuery.value.trim()) return

      const userQuery = searchQuery.value
      addMessage(userQuery, 'user')
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

        const suggestions = response.data.recommendations.join('\n• ')
        addMessage(`为您推荐以下旅行建议：\n• ${suggestions}`, 'assistant')
        
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
      handleSearch,
      formatTime,
      formatDate,
      toggleSidebar,
      startNewChat,
      loadChat,
      Search
    }
  }
}
</script>

<style scoped>
.home-container {
  display: flex;
  height: 100vh;
  background-color: #fafbfc;
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
}

.history-item:hover {
  background-color: #f8f9fa;
  border-color: #e8eaed;
}

.history-item.active {
  background-color: #e8f0fe;
  border-color: #1a73e8;
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
  justify-content: center;
  align-items: center;
  padding: 40px;
  background-color: #fafbfc;
}

.chat-container {
  width: 100%;
  max-width: 800px;
  height: 100%;
  background-color: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24);
  border: 1px solid #e8eaed;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 搜索容器 */
.search-container {
  padding: 20px;
  border-bottom: 1px solid #e8eaed;
  background-color: #ffffff;
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
  margin-top: 100px;
  color: #5f6368;
}

.welcome-message h2 {
  font-size: 28px;
  margin-bottom: 12px;
  color: #202124;
  font-weight: 400;
}

.welcome-message p {
  font-size: 16px;
  color: #5f6368;
}

/* 消息样式 */
.message-item {
  display: flex;
  margin-bottom: 16px;
}

.message-bubble {
  max-width: 70%;
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
}

.message-time {
  font-size: 12px;
  opacity: 0.7;
  margin-top: 4px;
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
</style>
