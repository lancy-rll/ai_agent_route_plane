<template>
  <el-container class="app-container">
    <el-aside width="300px" class="sidebar">
      <div class="logo-section">
        <el-icon size="40" color="#409EFF"><Location /></el-icon>
        <h1 class="logo-text">智能路线规划</h1>
      </div>

      <el-button type="primary" class="new-chat-btn" @click="startNewChat" size="large">
        <el-icon><Plus /></el-icon>
        新建对话
      </el-button>

      <el-divider content-position="left">快捷示例</el-divider>

      <div class="tips-section">
        <el-card shadow="hover" class="tip-card" @click="sendQuickMessage('从北京到上海怎么走最快')">
          <el-icon><Van /></el-icon>
          <span>北京 → 上海</span>
        </el-card>
        <el-card shadow="hover" class="tip-card" @click="sendQuickMessage('天安门附近有什么好餐厅')">
          <el-icon><Food /></el-icon>
          <span>搜索周边 POI</span>
        </el-card>
        <el-card shadow="hover" class="tip-card" @click="sendQuickMessage('推荐一条从成都到重庆的自驾游路线')">
          <el-icon><Camera /></el-icon>
          <span>自驾游路线</span>
        </el-card>
      </div>
    </el-aside>

    <el-main class="main-content">
      <el-header class="chat-header">
        <div class="header-left">
          <el-badge :is-dot="true" :type="wsConnected ? 'success' : 'danger'">
            <el-icon size="24" color="#409EFF"><ChatDotRound /></el-icon>
          </el-badge>
          <span class="header-title">路线规划助手</span>
        </div>
      </el-header>

      <el-card class="messages-container" shadow="never">
        <div class="messages-scroll" ref="messagesContainer">
          <div class="welcome-message" v-if="messages.length === 0">
            <el-icon size="80" color="#409EFF" class="welcome-icon"><Van /></el-icon>
            <h2>欢迎使用智能路线规划助手</h2>
            <p>我可以帮您规划路线、搜索目的地、了解交通信息</p>
          </div>

          <div v-for="(msg, index) in messages" :key="index" class="message-item" :class="msg.role">
            <el-avatar :size="40" :class="msg.role === 'user' ? 'user-avatar' : 'assistant-avatar'">
              {{ msg.role === 'user' ? '👤' : '🤖' }}
            </el-avatar>
            <div class="message-bubble">
              <div v-if="msg.image" class="message-image-wrap">
                <el-image :src="msg.image" class="message-image" fit="contain" :preview-src-list="[msg.image]" />
              </div>
              <div v-if="msg.content" class="message-content" v-html="msg.content"></div>
              <div class="message-time">
                <el-icon><Clock /></el-icon>
                {{ msg.time }}
              </div>
            </div>
          </div>

          <div v-if="routeSelection" class="route-selection">
            <el-card shadow="hover">
              <template #header>
                <div class="card-header">
                  <el-icon color="#409EFF"><Search /></el-icon>
                  <span>{{ routeSelection.message }}</span>
                </div>
              </template>
              <div class="route-list">
                <el-card
                  v-for="route in routeSelection.routes"
                  :key="route.id"
                  class="route-card"
                  :class="{ recommended: route.id === routeSelection.recommended_id }"
                  shadow="hover"
                  @click="selectRoute(route.id)"
                >
                  <div v-if="route.type === 'route'" class="route-info">
                      <div class="route-map">
                        <el-image 
                          v-if="route.map_url" 
                          :src="route.map_url" 
                          class="route-map-image" 
                          fit="cover"
                          :alt="route.summary"
                        />
                        <div v-else class="route-map-placeholder">
                          <el-icon size="32" color="#ccc"><MapLocation /></el-icon>
                        </div>
                      </div>
                      <div class="route-details">
                        <div class="route-summary">{{ route.summary }}</div>
                        <div class="route-meta">
                          <el-tag type="info" size="small">
                            <el-icon><Guide /></el-icon>
                            {{ formatDistance(route.distance) }}
                          </el-tag>
                          <el-tag type="info" size="small">
                            <el-icon><Timer /></el-icon>
                            {{ formatDuration(route.duration) }}
                          </el-tag>
                        </div>
                      </div>
                      <el-tag v-if="route.id === routeSelection.recommended_id" type="success" effect="dark">推荐</el-tag>
                    </div>
                  <div v-else class="poi-info">
                    <el-icon size="40" color="#409EFF"><Location /></el-icon>
                    <div class="poi-details">
                      <div class="poi-name">{{ route.name }}</div>
                      <div class="poi-address">{{ route.address }}</div>
                      <div class="poi-meta">
                        <el-tag v-if="route.distance" type="info" size="small">距离: {{ route.distance }}m</el-tag>
                        <el-tag v-if="route.rating" type="warning" size="small">⭐ {{ route.rating }}</el-tag>
                      </div>
                    </div>
                  </div>
                </el-card>
              </div>
            </el-card>
          </div>

          <div v-if="isLoading" class="loading-message">
            <el-icon class="loading-icon" :size="24">
              <Loading />
            </el-icon>
            <span>正在思考中...</span>
          </div>
        </div>
      </el-card>

      <el-footer class="input-footer">
        <input
          type="file"
          ref="imageInput"
          accept="image/*"
          style="display: none"
          @change="handleImageUpload"
        />

        <div v-if="selectedImage" class="image-preview-container">
          <el-image :src="selectedImage" class="preview-image" fit="cover" />
          <el-button type="danger" size="small" circle class="remove-image-btn" @click="removeImage">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>

        <div class="input-box">
          <el-tooltip content="上传图片" placement="top">
            <el-button
              class="upload-btn"
              :icon="Picture"
              circle
              size="small"
              @click="toggleImageUpload"
            />
          </el-tooltip>
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="1"
            :autosize="{ minRows: 1, maxRows: 4 }"
            placeholder="输入您的问题，或点击左侧图标上传图片..."
            @keydown="handleKeyDown"
            class="chat-input"
          />
          <el-button
            type="primary"
            :icon="Promotion"
            circle
            @click="sendMessage"
            :loading="isLoading"
            :disabled="!inputMessage.trim() && !selectedImage"
            class="send-btn"
          />
        </div>
      </el-footer>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import { marked } from 'marked'
import { Plus, Van, Food, Camera, Picture, ChatDotRound, Clock, Search, Guide, Timer, Location, Loading, Close, Promotion, MapLocation } from '@element-plus/icons-vue'

const messages = ref([])
const inputMessage = ref('')
const isLoading = ref(false)
const wsConnected = ref(false)
const routeSelection = ref(null)
const selectedImage = ref(null)
const messagesContainer = ref(null)
const imageInput = ref(null)

let sessionId = null

const formatDistance = (meters) => {
  if (meters >= 1000) {
    return `${(meters / 1000).toFixed(1)} 公里`
  }
  return `${meters} 米`
}

const formatDuration = (seconds) => {
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  if (hours > 0) {
    return `${hours} 小时 ${minutes % 60} 分钟`
  }
  return `${minutes} 分钟`
}

const getCurrentTime = () => {
  const now = new Date()
  return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const addMessage = (role, content) => {
  messages.value.push({
    role,
    content: marked.parse(content),
    time: getCurrentTime()
  })
  scrollToBottom()
}

const startNewChat = () => {
  messages.value = []
  sessionId = null
  routeSelection.value = null
  selectedImage.value = null
}

const sendQuickMessage = (msg) => {
  inputMessage.value = msg
  sendMessage()
}

const toggleImageUpload = () => {
  imageInput.value.click()
}

const handleImageUpload = (e) => {
  const file = e.target.files[0]
  if (file) {
    const reader = new FileReader()
    reader.onload = (event) => {
      selectedImage.value = event.target.result
    }
    reader.readAsDataURL(file)
  }
}

const removeImage = () => {
  selectedImage.value = null
  imageInput.value.value = ''
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() && !selectedImage.value) return

  const query = inputMessage.value.trim()
  const imageSrc = selectedImage.value || null
  const imageBase64 = imageSrc ? imageSrc.split(',')[1] : null

  // 把图片和文字一起存入消息气泡
  messages.value.push({
    role: 'user',
    content: query ? marked.parse(query) : '',
    image: imageSrc,
    time: getCurrentTime()
  })
  scrollToBottom()

  inputMessage.value = ''
  selectedImage.value = null
  if (imageInput.value) imageInput.value.value = ''
  isLoading.value = true
  routeSelection.value = null

  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_query: query,
        image_base64: imageBase64,
        session_id: sessionId
      })
    })

    if (!response.ok) {
      throw new Error('请求失败')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    let assistantMessageIndex = -1
    let fullContent = ''

    while (true) {
      const { done, value } = await reader.read()
      
      if (done) {
        break
      }

      buffer += decoder.decode(value, { stream: true })
      
      while (buffer.includes('\n\n')) {
        const [event, rest] = buffer.split('\n\n', 2)
        buffer = rest

        if (event.startsWith('data: ')) {
          try {
            const data = JSON.parse(event.slice(6))
            
            if (data.type === 'stream') {
              fullContent += data.content
              
              if (assistantMessageIndex === -1) {
                messages.value.push({
                  role: 'assistant',
                  content: marked.parse(fullContent),
                  time: getCurrentTime()
                })
                assistantMessageIndex = messages.value.length - 1
              } else {
                messages.value[assistantMessageIndex].content = marked.parse(fullContent)
              }
              scrollToBottom()
            } else if (data.type === 'end') {
              if (data.session_id) {
                sessionId = data.session_id
              }
              isLoading.value = false
              break
            } else if (data.type === 'pending_selection') {
              if (data.session_id) {
                sessionId = data.session_id
              }
              routeSelection.value = data.data
              addMessage('assistant', data.message)
              isLoading.value = false
              break
            } else if (data.type === 'error') {
              addMessage('assistant', data.content)
              isLoading.value = false
              break
            }
          } catch (e) {
            console.error('解析流式数据失败:', e)
          }
        }
      }
    }
  } catch (error) {
    addMessage('assistant', `抱歉，发生了错误: ${error.message}`)
    isLoading.value = false
  }
}

const selectRoute = async (routeId) => {
  if (!sessionId) return

  isLoading.value = true
  try {
    const response = await fetch('/api/select-route', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        session_id: sessionId,
        selected_route_id: routeId
      })
    })

    const result = await response.json()

    routeSelection.value = null
    if (result.response) {
      addMessage('assistant', result.response)
    }
  } catch (error) {
    addMessage('assistant', `选择路线时出错: ${error.message}`)
  } finally {
    isLoading.value = false
  }
}

const handleKeyDown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

onMounted(() => {
  scrollToBottom()
})
</script>

<style scoped>
.app-container {
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.sidebar {
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 2px 0 10px rgba(0, 0, 0, 0.1);
  padding: 24px;
  display: flex;
  flex-direction: column;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.logo-text {
  font-size: 22px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
}

.new-chat-btn {
  width: 100%;
  margin-bottom: 16px;
}

.tips-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tip-card {
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 10px;
}

.tip-card:hover {
  transform: translateX(4px);
  border-color: #409EFF;
}

.main-content {
  padding: 0;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.header-right {
  display: flex;
  gap: 8px;
}

.messages-container {
  flex: 1;
  overflow: hidden;
  border-radius: 0;
  background: #f5f7fa;
}

.messages-scroll {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
}

.welcome-message {
  text-align: center;
  padding: 80px 20px;
}

.welcome-icon {
  margin-bottom: 24px;
  animation: bounce 2s ease-in-out infinite;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.welcome-message h2 {
  font-size: 28px;
  margin-bottom: 12px;
  color: #303133;
}

.welcome-message p {
  color: #909399;
  font-size: 16px;
}

.message-item {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-item.user {
  flex-direction: row-reverse;
}

.user-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.assistant-avatar {
  background: linear-gradient(135deg, #409EFF 0%, #67C23A 100%);
}

.message-bubble {
  max-width: 70%;
}

.message-content {
  padding: 16px 20px;
  background: white;
  border-radius: 16px;
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  line-height: 1.7;
}

.message-item.user .message-content {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom-left-radius: 16px;
  border-bottom-right-radius: 4px;
}

.message-content :deep(p) {
  margin: 8px 0;
}

.message-content :deep(code) {
  background: rgba(0, 0, 0, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}

.message-item.user .message-content :deep(code) {
  background: rgba(255, 255, 255, 0.2);
}

.message-content :deep(ul),
.message-content :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.message-content :deep(li) {
  margin: 4px 0;
}

.message-time {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 4px;
}

.message-item.user .message-time {
  text-align: right;
  justify-content: flex-end;
}

.route-selection {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.route-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.route-card {
  cursor: pointer;
  transition: all 0.3s ease;
}

.route-card:hover {
  transform: translateX(4px);
}

.route-card.recommended {
  border: 2px solid #67C23A;
}

.route-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.route-map {
  width: 120px;
  height: 80px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
}

.route-map-image {
  width: 100%;
  height: 100%;
}

.route-map-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}

.poi-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.route-details,
.poi-details {
  flex: 1;
}

.route-summary,
.poi-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #303133;
}

.route-meta,
.poi-meta {
  display: flex;
  gap: 12px;
}

.poi-address {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.loading-message {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  color: #909399;
}

.loading-icon {
  animation: rotate 1s linear infinite;
  color: #409EFF;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.input-footer {
  padding: 20px 24px;
  background: white;
  border-top: 1px solid #e4e7ed;
}

.image-preview-container {
  position: relative;
  display: inline-block;
  margin-bottom: 12px;
}

.preview-image {
  width: 150px;
  height: 110px;
  border-radius: 8px;
  border: 2px solid #409EFF;
}

.image-preview-container .el-button {
  position: absolute;
  top: -10px;
  right: -10px;
}

.chat-input {
  width: 100%;
}
</style>
