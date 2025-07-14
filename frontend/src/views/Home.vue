<template>
  <div class="home-container">
    <!-- 侧边栏 -->
    <div class="sidebar">
      <div class="sidebar-header">
        <el-icon class="menu-icon">
          <Menu />
        </el-icon>
      </div>
      
      <div class="sidebar-content">
        <div class="sidebar-item">
          <el-icon><Edit /></el-icon>
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

    // 格式化时间
    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit'
      })
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
      } catch (error) {
        console.error('API调用失败:', error)
        addMessage('抱歉，获取旅行建议时出现错误。请稍后再试。', 'assistant')
      } finally {
        loading.value = false
      }
    }

    return {
      searchQuery,
      messages,
      loading,
      messagesContainer,
      handleSearch,
      formatTime,
      Search
    }
  }
}
</script>

<style scoped>
.home-container {
  display: flex;
  height: 100vh;
  background-color: #f5f5f5;
}

/* 侧边栏样式 */
.sidebar {
  width: 60px;
  background-color: #2c3e50;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 0;
}

.sidebar-header {
  margin-bottom: 30px;
}

.menu-icon {
  color: #ecf0f1;
  font-size: 24px;
  cursor: pointer;
}

.sidebar-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.sidebar-item {
  width: 40px;
  height: 40px;
  background-color: #34495e;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.3s;
}

.sidebar-item:hover {
  background-color: #3498db;
}

.sidebar-item .el-icon {
  color: #ecf0f1;
  font-size: 18px;
}

/* 主内容区样式 */
.main-content {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
}

.chat-container {
  width: 100%;
  max-width: 800px;
  height: 100%;
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 搜索容器 */
.search-container {
  padding: 20px;
  border-bottom: 1px solid #eee;
}

.search-input {
  width: 100%;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 25px;
  padding: 8px 20px;
  border: 2px solid #e0e0e0;
  transition: border-color 0.3s;
}

.search-input :deep(.el-input__wrapper:hover) {
  border-color: #3498db;
}

.search-input :deep(.el-input__wrapper.is-focus) {
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
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
  color: #7f8c8d;
}

.welcome-message h2 {
  font-size: 28px;
  margin-bottom: 12px;
  color: #2c3e50;
}

.welcome-message p {
  font-size: 16px;
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
  background-color: #3498db;
  color: white;
  margin-left: auto;
  border-bottom-right-radius: 4px;
}

.message-bubble.assistant {
  background-color: #ecf0f1;
  color: #2c3e50;
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
  background: #f1f1f1;
  border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
