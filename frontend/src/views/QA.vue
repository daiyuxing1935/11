<template>
  <div class="qa-page">
    <div class="qa-layout">
      <!-- 左侧：聊天区域 -->
      <div class="chat-column">
        <el-card shadow="hover" class="chat-card">
          <template #header><div class="page-title"><el-icon><ChatDotRound /></el-icon> AI智能体学科专属答疑</div></template>
          <div class="chat-messages" ref="chatBox" @click="handleCodeBlockAction">
            <div v-if="messages.length === 0" class="welcome-msg">
              <el-icon :size="48" color="#409EFF"><Cpu /></el-icon>
              <h3>AI智能体学科智能答疑助手</h3>
              <p>专注于AI智能体学科：基础概念、大模型原理、提示词工程、框架开发、算法逻辑、多智能体应用</p>
              <div class="quick-questions">
                <el-tag v-for="q in quickQuestions" :key="q" @click="quickAsk(q)" class="quick-tag">{{ q }}</el-tag>
              </div>
            </div>
            <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
              <div class="msg-avatar"><el-icon :size="24"><component :is="msg.role === 'user' ? 'UserFilled' : 'Cpu'" /></el-icon></div>
              <div class="msg-body">
                <!-- 深度思考过程 -->
                <div v-if="msg.thinking" class="thinking-block">
                  <div class="thinking-header" @click="msg.thinkingExpanded = !msg.thinkingExpanded">
                    <el-icon :size="14"><component :is="msg.thinkingExpanded ? 'ArrowDown' : 'ArrowRight'" /></el-icon>
                    <span>深度思考过程</span>
                    <span class="thinking-tag">思考</span>
                  </div>
                  <div v-show="msg.thinkingExpanded !== false" class="thinking-content">
                    <div v-html="renderMarkdown(msg.thinking)"></div>
                  </div>
                </div>
                <!-- 联网搜索结果 -->
                <div v-if="msg.searchResults && msg.searchResults.length" class="search-results-block">
                  <div class="search-header">
                    <el-icon color="#409EFF"><Search /></el-icon>
                    <span v-if="msg.searchQuery">搜索「{{ msg.searchQuery }}」</span>
                    <span v-else>搜索到 {{ msg.searchResults.length }} 条相关结果</span>
                  </div>
                  <div class="search-result-list">
                    <a
                      v-for="(r, i) in msg.searchResults"
                      :key="i"
                      :href="r.url"
                      target="_blank"
                      class="search-result-item"
                    >
                      <div class="sr-title">{{ r.title }}</div>
                      <div class="sr-snippet" v-if="r.snippet">{{ r.snippet }}</div>
                      <div class="sr-url">{{ r.url }}</div>
                    </a>
                  </div>
                </div>
                <!-- 正式回答 -->
                <div class="msg-content" v-html="renderMarkdown(msg.answer || msg.content)"></div>
                <div v-if="msg.role === 'assistant' && (msg.answer || msg.content) && currentQaId && idx === messages.length - 1" class="feedback-btns">
                  <el-button size="small" text :type="feedbackGiven ? 'primary' : ''" @click="giveFeedback(1)" :disabled="feedbackGiven">
                    <el-icon><Check /></el-icon> 有用
                  </el-button>
                  <el-button size="small" text @click="giveFeedback(-1)" :disabled="feedbackGiven">
                    <el-icon><Close /></el-icon> 无用
                  </el-button>
                </div>
              </div>
            </div>
          </div>
          <div class="chat-input">
            <div class="input-options">
              <el-tooltip content="清空当前对话，开始新会话" placement="top">
                <el-button size="small" @click="newConversation" :disabled="sending">
                  <el-icon><Plus /></el-icon> 新建对话
                </el-button>
              </el-tooltip>
              <el-tooltip content="开启后将引导AI进行更深入的逐步推理分析" placement="top">
                <el-button size="small" :type="deepThinking ? 'warning' : ''" :plain="!deepThinking" @click="deepThinking = !deepThinking">
                  <el-icon><View /></el-icon> 深度思考 {{ deepThinking ? 'ON' : 'OFF' }}
                </el-button>
              </el-tooltip>
              <el-tooltip content="开启后将联网搜索最新资料辅助回答" placement="top">
                <el-button size="small" :type="enableSearch ? 'success' : ''" :plain="!enableSearch" @click="enableSearch = !enableSearch" style="margin-left:4px" :loading="enableSearch && sending">
                  <el-icon><Search /></el-icon> 联网搜索 {{ enableSearch ? 'ON' : 'OFF' }}
                </el-button>
              </el-tooltip>
              <el-tooltip content="上传PDF/PPTX/图片等文件，自动识别内容" placement="top">
                <el-button size="small" @click="triggerUpload" :disabled="sending" style="margin-left:4px">
                  <el-icon><Upload /></el-icon> 上传文件
                </el-button>
              </el-tooltip>
              <input ref="fileInput" type="file" @change="handleFileSelect" style="display:none"
                accept=".pdf,.pptx,.docx,.xlsx,.png,.jpg,.jpeg,.gif,.bmp,.webp,.txt,.md,.py,.js,.ts,.json,.csv,.html,.css,.xml,.java,.c,.cpp,.sql" />
            </div>
            <div v-if="uploadedFile" class="file-tag">
              <el-tag type="info" closable @close="removeFile" size="small">
                <el-icon><Document /></el-icon>
                {{ uploadedFile.name }} <span v-if="uploading">(解析中...)</span><span v-else>({{ fileType }})</span>
              </el-tag>
            </div>
            <el-input v-model="inputText" placeholder="输入AI智能体学科相关问题..." @keyup.enter="sendMessage" size="large" class="text-input" :disabled="sending" />
            <div class="send-area">
              <el-button v-if="!sending" type="primary" size="large" @click="sendMessage" :disabled="!inputText.trim() && !uploadedFile">
                <el-icon><Promotion /></el-icon> {{ uploadedFile && !inputText.trim() ? '发送文件' : '提问' }}
              </el-button>
              <el-button v-else type="danger" size="large" @click="stopStreaming">
                <el-icon><CircleClose /></el-icon> 停止生成
              </el-button>
            </div>
          </div>
        </el-card>
      </div>
      <!-- 右侧：问答历史（窄列，固定） -->
      <div class="history-column">
        <el-card shadow="hover" class="history-card">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span><el-icon><Clock /></el-icon> 历史</span>
              <el-popconfirm
                v-if="history.length > 0"
                title="确定要清空所有问答历史吗？此操作不可恢复。"
                confirm-button-text="确认清空"
                cancel-button-text="取消"
                @confirm="handleClearHistory"
              >
                <template #reference>
                  <el-button type="danger" size="small" text>清空全部</el-button>
                </template>
              </el-popconfirm>
            </div>
          </template>
          <div class="history-list">
            <div v-for="h in history" :key="h.id" class="history-item" @click="loadHistory(h)">
              <div style="display:flex;justify-content:space-between;align-items:flex-start">
                <div style="flex:1;min-width:0">
                  <div class="h-question">{{ h.question.slice(0, 40) }}{{ h.question.length > 40 ? '...' : '' }}</div>
                  <div class="h-meta">{{ h.created_at?.slice(0,16) }} · {{ h.explanation_level }}</div>
                </div>
                <el-popconfirm
                  title="确定删除这条记录？"
                  confirm-button-text="删除"
                  cancel-button-text="取消"
                  @confirm.stop="handleDeleteHistory(h.id)"
                >
                  <template #reference>
                    <el-button size="small" text type="danger" @click.stop>
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-popconfirm>
              </div>
            </div>
          </div>
          <el-empty v-if="history.length === 0" description="暂无记录" :image-size="50" />
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { askQuestionStream, getQAHistory, deleteQAHistory, clearQAHistory, saveQA, uploadFile, submitFeedback } from '../api/qa'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { recordStudyVisit } from '../api/learning'
import { copyToClipboard } from '../utils/clipboard'

const router = useRouter()

const messages = ref([])
const inputText = ref('')
const sending = ref(false)
const questionType = ref('text')
const explanationLevel = ref('standard')
const deepThinking = ref(false)
const enableSearch = ref(false)
const history = ref([])
const chatBox = ref(null)
const abortStream = ref(null)
const fileInput = ref(null)
const uploadedFile = ref(null)
const fileText = ref('')
const fileBase64 = ref(null)
const fileType = ref('')
const uploading = ref(false)
const currentQaId = ref(null)
const feedbackGiven = ref(false)
const searchResultsData = ref(null)
const searchQuery = ref('')

const quickQuestions = [
  'AI智能体和大模型有什么区别？',
  '什么是思维链(Chain-of-Thought)提示？',
  'Agent的工具调用(Tool Use)是如何工作的？',
  '多智能体系统如何解决冲突？',
  'LangChain框架的核心组件有哪些？'
]

onMounted(async () => {
  recordStudyVisit()
  try {
    const res = await getQAHistory()
    history.value = (res && res.items) || []

    // 恢复最近一次对话到聊天窗口
    if (history.value.length > 0) {
      const last = history.value[0]
      currentQaId.value = last.id
      messages.value = [
        { role: 'user', content: last.question },
        { role: 'assistant', content: last.answer }
      ]
      await nextTick()
      if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
    }
  } catch(e) {}
})

function escapeHtml(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

// 自定义 marked 渲染器：为代码块添加复制和运行按钮
const SUPPORTED_LANGS = ['python', 'py', 'python3', 'javascript', 'js', 'node', 'c', 'cpp', 'c++', 'cplusplus', 'java']
const mdRenderer = new marked.Renderer()
mdRenderer.code = function(code, infostring) {
  const lang = infostring || 'plaintext'
  const isSupported = SUPPORTED_LANGS.includes(lang.toLowerCase())
  const runBtn = isSupported
    ? `<button class="code-toolbar-btn run-btn" data-action="run" data-lang="${lang}" title="运行代码">
         <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
         运行
       </button>`
    : ''
  return `<div class="code-block-wrapper">
    <div class="code-toolbar">
      <span class="code-lang-tag">${lang}</span>
      <div class="code-toolbar-actions">
        <button class="code-toolbar-btn copy-btn" data-action="copy" title="复制代码">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          复制
        </button>
        ${runBtn}
      </div>
    </div>
    <pre><code class="language-${lang}">${escapeHtml(code)}</code></pre>
  </div>`
}

function renderMarkdown(text) {
  if (!text) return ''
  return marked(text, { breaks: true, renderer: mdRenderer })
}

function handleCodeBlockAction(e) {
  const btn = e.target.closest('.code-toolbar-btn')
  if (!btn) return
  const wrapper = btn.closest('.code-block-wrapper')
  const codeEl = wrapper?.querySelector('code')
  const code = codeEl?.textContent || ''
  if (btn.dataset.action === 'copy') {
    copyToClipboard(code).then(ok => {
      ElMessage[ok ? 'success' : 'warning'](ok ? '代码已复制到剪贴板' : '复制失败，请手动复制')
    })
  } else if (btn.dataset.action === 'run') {
    const lang = btn.dataset.lang || 'python'
    sessionStorage.setItem('qa-run-code', code)
    sessionStorage.setItem('qa-run-lang', lang)
    router.push('/code-runner')
  }
}

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFileSelect(e) {
  const file = e.target.files?.[0]
  if (!file) return
  uploadedFile.value = file
  uploading.value = true
  try {
    const result = await uploadFile(file)
    fileText.value = result.text
    fileBase64.value = result.base64 || null
    fileType.value = result.file_type
    ElMessage.success(`${result.file_type} 解析完成`)
  } catch (err) {
    ElMessage.error(err.message || '文件解析失败')
    uploadedFile.value = null
  } finally {
    uploading.value = false
    // 重置input，允许重复选择同一文件
    if (fileInput.value) fileInput.value.value = ''
  }
}

function removeFile() {
  uploadedFile.value = null
  fileText.value = ''
  fileBase64.value = null
  fileType.value = ''
}

function newConversation() {
  messages.value = []
  currentQaId.value = null
  feedbackGiven.value = false
  removeFile()
}

async function giveFeedback(rating) {
  if (!currentQaId.value || feedbackGiven.value) return
  try {
    await submitFeedback({ qa_history_id: currentQaId.value, rating })
    feedbackGiven.value = true
    ElMessage.success(rating === 1 ? '感谢反馈！已记录为有用回答' : '感谢反馈！我们会持续改进')
  } catch (err) {
    ElMessage.error('反馈提交失败')
  }
}

async function sendMessage() {
  const hasFile = fileText.value && uploadedFile.value
  if ((!inputText.value.trim() && !hasFile) || sending.value) return
  const q = inputText.value.trim() || (hasFile ? `请提取以下文件的核心要点` : '')
  const isFileOnly = hasFile && !inputText.value.trim()

  // 用户消息仅显示文件信息，不展示文件内容
  let displayContent
  if (hasFile) {
    displayContent = `📎 **${uploadedFile.value.name}** (${fileType.value})`
    if (q && !isFileOnly) displayContent += `\n\n${q}`
  } else {
    displayContent = q
  }
  messages.value.push({ role: 'user', content: displayContent })
  inputText.value = ''
  sending.value = true

  // 添加空的助手消息占位，流式填充内容
  messages.value.push({ role: 'assistant', content: '' })
  const assistantIdx = messages.value.length - 1

  const scrollToBottom = () => {
    nextTick(() => {
      if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
    })
  }
  scrollToBottom()

  const file_text_sent = hasFile ? fileText.value : null
  const file_base64_sent = hasFile ? fileBase64.value : null

  // 构建对话历史（不包含当前用户消息和空的助手占位）
  const conversationHistory = messages.value.slice(0, -2).map(m => ({
    role: m.role,
    content: m.content
  }))

  searchResultsData.value = null
  searchQuery.value = ''

  abortStream.value = askQuestionStream(
    {
      question: q,
      question_type: questionType.value,
      explanation_level: explanationLevel.value,
      deep_thinking: deepThinking.value,
      enable_search: enableSearch.value,
      file_text: file_text_sent,
      file_base64: file_base64_sent,
      history: conversationHistory
    },
    {
      onSearchResults(results, sq) {
        searchResultsData.value = results
        searchQuery.value = sq
        if (messages.value[assistantIdx]) {
          messages.value[assistantIdx] = {
            ...messages.value[assistantIdx],
            searchResults: results,
            searchQuery: sq
          }
        }
      },
      onChunk(chunkText, fullAnswer) {
        const msg = _buildAssistantMsg(fullAnswer)
        if (searchResultsData.value) {
          msg.searchResults = searchResultsData.value
          msg.searchQuery = searchQuery.value
        }
        messages.value[assistantIdx] = msg
        scrollToBottom()
      },
      onDone(fullAnswer) {
        const msg = _buildAssistantMsg(fullAnswer)
        if (searchResultsData.value) {
          msg.searchResults = searchResultsData.value
          msg.searchQuery = searchQuery.value
        }
        messages.value[assistantIdx] = msg
        sending.value = false
        abortStream.value = null
        scrollToBottom()
        if (hasFile) removeFile()
        feedbackGiven.value = false
        saveQA({
          question: q,
          answer: fullAnswer,
          question_type: questionType.value,
          explanation_level: explanationLevel.value
        }).then((result) => {
          if (result && result.id) currentQaId.value = result.id
          getQAHistory().then(res => { history.value = (res && res.items) || [] }).catch(() => {})
        }).catch(() => {})
      },
      onError(err) {
        messages.value[assistantIdx] = { role: 'assistant', content: `❌ **出错了**: ${err.message}` }
        sending.value = false
        abortStream.value = null
        ElMessage.error(err.message || '流式请求失败')
      }
    }
  )
}

function _buildAssistantMsg(fullText) {
  // 解析深度思考内容：【思考过程】...【回答】...
  if (deepThinking.value) {
    const thinkMatch = fullText.match(/【思考过程】\s*([\s\S]*?)\s*【回答】\s*([\s\S]*)/)
    if (thinkMatch) {
      return {
        role: 'assistant',
        thinking: thinkMatch[1].trim(),
        answer: thinkMatch[2].trim(),
        thinkingExpanded: true  // 默认展开
      }
    }
    // 如果还没输出【回答】标签，检查是否已经开始输出思考过程
    const partialThink = fullText.match(/【思考过程】\s*([\s\S]*)/)
    if (partialThink && !fullText.includes('【回答】')) {
      return {
        role: 'assistant',
        thinking: partialThink[1].trim(),
        answer: '',
        thinkingExpanded: true
      }
    }
  }
  // 非深度思考模式或解析失败 → 全部作为回答
  return { role: 'assistant', content: fullText }
}

function stopStreaming() {
  if (abortStream.value) {
    abortStream.value()
    abortStream.value = null
    sending.value = false
  }
}

function quickAsk(q) {
  inputText.value = q
  sendMessage()
}

function loadHistory(h) {
  currentQaId.value = h.id
  feedbackGiven.value = false
  messages.value = [
    { role: 'user', content: h.question },
    { role: 'assistant', content: h.answer }
  ]
  nextTick(() => { if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight })
}

async function handleDeleteHistory(id) {
  try {
    await deleteQAHistory(id)
    // 从本地列表中移除
    history.value = history.value.filter(h => h.id !== id)
    // 如果删除的是当前显示的对话，清空聊天区
    if (currentQaId.value === id) {
      newConversation()
    }
    ElMessage.success('已删除')
  } catch(e) {
    ElMessage.error('删除失败，请重试')
  }
}

async function handleClearHistory() {
  try {
    await clearQAHistory()
    history.value = []
    newConversation()
    ElMessage.success('已清空全部问答历史')
  } catch(e) {
    ElMessage.error('清空失败，请重试')
  }
}
</script>

<style scoped>
.qa-page { height: calc(100vh - 80px); overflow: hidden; }
.qa-layout { display: flex; gap: 16px; height: 100%; }
.chat-column { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.history-column { width: 260px; flex-shrink: 0; }

.page-title { display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: bold; }

/* 聊天卡片：flex布局，input固定在底部 */
.chat-card { height: 100%; display: flex; flex-direction: column; }
.chat-card :deep(.el-card__header) { flex-shrink: 0; }
.chat-card :deep(.el-card__body) { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.chat-messages { flex: 1; overflow-y: auto; padding: 8px 0; }
.chat-input { flex-shrink: 0; border-top: 1px solid #f0f0f0; padding-top: 10px; margin-top: 8px; }

/* 历史卡片：固定不滚动 */
.history-card { height: 100%; display: flex; flex-direction: column; }
.history-card :deep(.el-card__header) { flex-shrink: 0; }
.history-card :deep(.el-card__body) { flex: 1; overflow-y: auto; }
.history-list { flex: 1; overflow-y: auto; }

.welcome-msg { text-align: center; padding: 40px 20px; }
.welcome-msg h3 { margin: 12px 0 8px; color: #303133; }
.welcome-msg p { color: #909399; font-size: 14px; margin-bottom: 16px; }
.quick-tag { cursor: pointer; margin: 4px; }
.quick-tag:hover { background: #409EFF; color: #fff; }
.message { display: flex; gap: 10px; padding: 12px 0; border-bottom: 1px solid #f5f5f5; }
.message.user { justify-content: flex-end; }
.message.user .msg-avatar { order: 10; }
.message.user .msg-body { flex: 0 1 auto; }
.message.assistant .msg-content { background: #e6f7ff; border-radius: 0 12px 12px 12px; }
.message.user .msg-content { background: #f0f0f0; border-radius: 12px 0 12px 12px; width: fit-content; }
.msg-content { padding: 12px 16px; max-width: 75%; line-height: 1.7; font-size: 14px; word-break: break-word; }
.msg-content :deep(p) { margin: 4px 0; }
.msg-content :deep(pre) { background: #282c34; color: #abb2bf; padding: 12px; border-radius: 8px; overflow-x: auto; font-size: 13px; }
.msg-content :deep(code) { background: #f5f5f5; padding: 2px 6px; border-radius: 4px; font-size: 13px; }
.msg-content :deep(pre code) { background: none; padding: 0; }

/* 代码块工具栏（复制+运行按钮） */
.msg-content :deep(.code-block-wrapper) {
  position: relative;
  margin: 10px 0;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #3a3f4b;
}
.msg-content :deep(.code-toolbar) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px;
  background: #21252b;
  border-bottom: 1px solid #3a3f4b;
  font-size: 12px;
}
.msg-content :deep(.code-lang-tag) {
  color: #abb2bf;
  font-size: 11px;
  font-family: 'Consolas', monospace;
  text-transform: lowercase;
}
.msg-content :deep(.code-toolbar-actions) {
  display: flex;
  gap: 6px;
}
.msg-content :deep(.code-toolbar-btn) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border: 1px solid #555;
  border-radius: 4px;
  background: transparent;
  color: #abb2bf;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
  line-height: 1;
}
.msg-content :deep(.code-toolbar-btn:hover) {
  background: #3a3f4b;
  color: #fff;
}
.msg-content :deep(.code-toolbar-btn.copy-btn:hover) {
  border-color: #409EFF;
  color: #409EFF;
}
.msg-content :deep(.code-toolbar-btn.run-btn:hover) {
  border-color: #67C23A;
  color: #67C23A;
}
.msg-content :deep(.code-block-wrapper pre) {
  margin: 0;
  border-radius: 0;
  border-top-left-radius: 0;
  border-top-right-radius: 0;
}

.feedback-btns { margin-top: 4px; padding-left: 2px; }
.feedback-btns .el-button { font-size: 12px; padding: 2px 8px; }
.input-options { margin-bottom: 8px; display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }
.file-tag { margin-bottom: 6px; }
.send-area { margin-top: 8px; }
.text-input { margin: 8px 0; }
.history-item { padding: 8px 10px; border-bottom: 1px solid #f5f5f5; cursor: pointer; }
.history-item:hover { background: #f5f7fa; }
.h-question { font-size: 12px; color: #303133; line-height: 1.4; }
.h-meta { font-size: 11px; color: #c0c4cc; margin-top: 3px; }

/* 深度思考 */
.msg-body { min-width: 0; }
.message.user .msg-body { display: flex; flex-direction: column; align-items: flex-end; }
.message.assistant .msg-body { flex: 1; }
.thinking-block {
  margin-bottom: 8px;
  border: 1px solid #e8d5a3;
  border-radius: 8px;
  overflow: hidden;
  background: #fffdf5;
}
.thinking-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  color: #b8860b;
  font-weight: 500;
  user-select: none;
}
.thinking-header:hover { background: #fff8e1; }
.thinking-tag {
  margin-left: auto;
  font-size: 11px;
  background: #fef3c7;
  color: #b45309;
  padding: 1px 8px;
  border-radius: 10px;
}
.thinking-content {
  padding: 8px 14px 12px;
  font-size: 12px;
  color: #8b7355;
  line-height: 1.7;
  border-top: 1px solid #f0e4c0;
  max-height: 400px;
  overflow-y: auto;
}
.thinking-content :deep(h1),
.thinking-content :deep(h2),
.thinking-content :deep(h3) { font-size: 13px; color: #b8860b; }
.thinking-content :deep(p) { margin: 4px 0; }
.thinking-content :deep(code) { font-size: 11px; background: #fef9e7; color: #b45309; }
.thinking-content :deep(pre) { font-size: 11px; background: #fffbeb; }

/* 联网搜索结果 */
.search-results-block {
  margin-bottom: 10px;
  background: #f0f7ff;
  border: 1px solid #b3d8ff;
  border-radius: 8px;
  overflow: hidden;
}
.search-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 500;
  color: #409EFF;
  background: #e8f3ff;
}
.search-result-list { padding: 4px 8px 8px; max-height: 300px; overflow-y: auto; }
.search-result-item {
  display: block;
  padding: 8px 10px;
  margin: 4px 0;
  border-radius: 6px;
  text-decoration: none;
  transition: background .15s;
}
.search-result-item:hover { background: #fff; }
.sr-title {
  font-size: 13px;
  font-weight: 500;
  color: #1a66cc;
  margin-bottom: 2px;
}
.sr-snippet {
  font-size: 12px;
  color: #606266;
  line-height: 1.5;
  margin-bottom: 2px;
}
.sr-url {
  font-size: 11px;
  color: #67C23A;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
