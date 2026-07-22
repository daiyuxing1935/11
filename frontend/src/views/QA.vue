<template>
  <div class="qa-page">
    <div class="qa-layout">
      <aside :class="['conversation-sidebar', { collapsed: historyCollapsed }]">
        <button class="conversation-toggle" :title="historyCollapsed ? '展开历史记录' : '收起历史记录'" @click="toggleHistory">
          <el-icon><component :is="historyCollapsed ? 'Expand' : 'Fold'" /></el-icon>
        </button>
        <template v-if="!historyCollapsed">
          <button class="new-chat-button" :disabled="sending" @click="newConversation">
            <el-icon><CirclePlus /></el-icon><span>新建对话</span>
          </button>
          <div class="conversation-caption">最近对话</div>
          <div class="conversation-list">
            <button
              v-for="item in conversations"
              :key="item.id"
              :class="['conversation-item', { active: item.id === conversationId }]"
              @click="openConversation(item.id)"
            >
              <span class="conversation-copy"><b>{{ item.title || '新对话' }}</b><small>{{ item.summary || '还没有消息' }}</small></span>
              <el-icon class="conversation-delete" title="删除会话" @click.stop="removeConversation(item.id)"><Delete /></el-icon>
            </button>
            <div v-if="!conversations.length" class="conversation-empty">暂无历史对话</div>
          </div>
        </template>
      </aside>

      <div class="chat-column">
        <el-card shadow="never" class="chat-card">
          <div class="chat-messages" ref="chatBox" @click="handleCodeBlockAction">
            <div v-if="messages.length === 0" class="welcome-msg">
              <div class="welcome-orb"><el-icon :size="32"><Cpu /></el-icon></div>
              <h3>今天想一起解决什么？</h3>
              <p>我会结合你的学习记录、长期记忆与当前进度回答。</p>
              <div class="quick-questions">
                <el-tag v-for="q in quickQuestions" :key="q" @click="quickAsk(q)" class="quick-tag">{{ q }}</el-tag>
              </div>
            </div>
            <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
              <div class="msg-avatar"><el-icon :size="24"><component :is="msg.role === 'user' ? 'UserFilled' : 'Cpu'" /></el-icon></div>
              <div class="msg-body">
                <div v-if="msg.role === 'assistant' && msg.learningContext" class="learning-context-block">
                  <el-icon><Guide /></el-icon>
                  <span>依据学习路径：第 {{ msg.learningContext.day }} 项 · {{ msg.learningContext.topic }}</span>
                  <button v-if="msg.learningContext.lab_id" @click="openContextLab(msg.learningContext)">打开实验 {{ msg.learningContext.lab_id }}</button>
                </div>
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
                <!-- RAG 知识库暂不可用提示 -->
                <div v-if="msg.ragUnavailable" class="rag-unavailable-block">
                  <el-icon color="#E6A23C"><WarningFilled /></el-icon>
                  <span>{{ msg.ragUnavailable }}</span>
                </div>
                <!-- RAG 知识库来源 -->
                <div v-if="msg.ragSources && msg.ragSources.length" class="rag-sources-block">
                  <div class="rag-sources-header">
                    <el-icon color="#67C23A"><Collection /></el-icon>
                    <span>参考知识库（{{ msg.ragSources.length }} 条来源）</span>
                  </div>
                  <div class="rag-source-list">
                    <div v-for="(s, i) in msg.ragSources" :key="i" class="rag-source-item">
                      <span class="rag-source-icon">{{ s.source_type === 'pdf' ? '📖' : '📝' }}</span>
                      <span class="rag-source-title">{{ s.title }}</span>
                      <span v-if="s.section" class="rag-source-section">— {{ s.section }}</span>
                      <span v-if="s.page" class="rag-source-page">(第{{ s.page }}页)</span>
                    </div>
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
            <div v-if="uploadedFile" class="file-tag">
              <el-tag type="info" closable @close="removeFile" size="small">
                <el-icon><Document /></el-icon>
                {{ uploadedFile.name }} <span v-if="uploading">(解析中...)</span><span v-else>({{ fileType }})</span>
              </el-tag>
            </div>
            <textarea
              v-model="inputText"
              rows="2"
              placeholder="给 AI 导师发送消息"
              :disabled="sending"
              @keydown.enter.exact.prevent="sendMessage"
            ></textarea>
            <div class="composer-toolbar">
              <div class="composer-left">
                <el-tooltip content="上传文件" placement="top">
                  <button class="round-tool" :disabled="sending" aria-label="上传文件" @click="triggerUpload"><el-icon><Paperclip /></el-icon></button>
                </el-tooltip>
                <el-popover placement="top-start" :width="240" trigger="click" popper-class="qa-tool-popover">
                  <template #reference><button class="round-tool" aria-label="更多能力"><el-icon><Operation /></el-icon></button></template>
                  <div class="capability-menu">
                    <button @click="useRag = !useRag"><el-icon><Collection /></el-icon><span><b>知识库答疑</b><small>{{ useRag ? '已开启' : '点击开启' }}</small></span><em :class="{ on: useRag }"></em></button>
                    <button disabled><el-icon><MagicStick /></el-icon><span><b>生成个性化资源</b><small>即将开放</small></span></button>
                    <button disabled><el-icon><Reading /></el-icon><span><b>生成复习卡片</b><small>即将开放</small></span></button>
                  </div>
                </el-popover>
                <button :class="['mode-chip', { active: deepThinking }]" @click="deepThinking = !deepThinking"><el-icon><View /></el-icon>深度思考</button>
                <button :class="['mode-chip', { active: enableSearch }]" @click="enableSearch = !enableSearch"><el-icon><Search /></el-icon>联网搜索</button>
              </div>
              <button v-if="!sending" class="send-button" :disabled="!inputText.trim() && !uploadedFile" aria-label="发送" @click="sendMessage"><el-icon><Promotion /></el-icon></button>
              <button v-else class="send-button stop" aria-label="停止生成" @click="stopStreaming"><el-icon><CircleClose /></el-icon></button>
            </div>
            <input ref="fileInput" type="file" @change="handleFileSelect" class="hidden-file-input"
              accept=".pdf,.pptx,.docx,.xlsx,.png,.jpg,.jpeg,.gif,.bmp,.webp,.txt,.md,.py,.js,.ts,.json,.csv,.html,.css,.xml,.java,.c,.cpp,.sql" />
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { askQuestionStream, saveQA, uploadFile, submitFeedback, startConversation, getCurrentConversation, getConversations, getConversation, deleteConversation } from '../api/qa'
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
const deepThinking = ref(true)
const enableSearch = ref(true)
const useRag = ref(true)
const conversations = ref([])
const historyCollapsed = ref(localStorage.getItem('qa_history_collapsed') === 'true')
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
const ragSourcesData = ref(null)
const ragUnavailableMsg = ref('')
const conversationId = ref(null)

const quickQuestions = [
  '你对我有什么认识？',
  'AI智能体和大模型有什么区别？',
  '什么是思维链(Chain-of-Thought)提示？',
  'Agent的工具调用(Tool Use)是如何工作的？',
  '多智能体系统如何解决冲突？',
  'LangChain框架的核心组件有哪些？'
]

onMounted(async () => {
  recordStudyVisit()
  try {
    const conversation = await getCurrentConversation()
    conversationId.value = conversation?.id || null
    messages.value = Array.isArray(conversation?.messages) ? conversation.messages : []
    conversations.value = await getConversations() || []

    if (messages.value.length > 0) {
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

async function newConversation() {
  messages.value = []
  currentQaId.value = null
  feedbackGiven.value = false
  removeFile()
  try {
    const conversation = await startConversation()
    conversationId.value = conversation?.id || null
    conversations.value = await getConversations() || []
  } catch (_) {
    conversationId.value = null
  }
}

function toggleHistory() {
  historyCollapsed.value = !historyCollapsed.value
  localStorage.setItem('qa_history_collapsed', String(historyCollapsed.value))
}

async function openConversation(id) {
  if (sending.value || id === conversationId.value) return
  try {
    const conversation = await getConversation(id)
    conversationId.value = conversation?.id || id
    messages.value = Array.isArray(conversation?.messages) ? conversation.messages : []
    currentQaId.value = null
    feedbackGiven.value = false
    await nextTick()
    if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
  } catch (_) {
    ElMessage.error('会话加载失败')
  }
}

async function removeConversation(id) {
  try {
    await deleteConversation(id)
    conversations.value = conversations.value.filter(item => item.id !== id)
    if (conversationId.value === id) await newConversation()
    ElMessage.success('会话已删除')
  } catch (_) {
    ElMessage.error('会话删除失败')
  }
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
  let activeLearningContext = null

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
  ragSourcesData.value = null

  abortStream.value = askQuestionStream(
    {
      question: q,
      question_type: questionType.value,
      explanation_level: explanationLevel.value,
      deep_thinking: deepThinking.value,
      enable_search: enableSearch.value,
      use_rag: useRag.value,
      file_text: file_text_sent,
      file_base64: file_base64_sent,
      history: conversationHistory,
      conversation_id: conversationId.value
    },
    {
      onLearningContext(context) {
        activeLearningContext = context
        if (messages.value[assistantIdx]) {
          messages.value[assistantIdx] = {
            ...messages.value[assistantIdx],
            learningContext: context
          }
        }
      },
      onRagSources(sources) {
        ragSourcesData.value = sources
        ragUnavailableMsg.value = ''
        if (messages.value[assistantIdx]) {
          messages.value[assistantIdx] = {
            ...messages.value[assistantIdx],
            ragSources: sources,
            ragUnavailable: null
          }
        }
      },
      onRagUnavailable(message) {
        ragUnavailableMsg.value = message
        if (messages.value[assistantIdx]) {
          messages.value[assistantIdx] = {
            ...messages.value[assistantIdx],
            ragUnavailable: message
          }
        }
      },
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
        if (activeLearningContext) msg.learningContext = activeLearningContext
        if (ragUnavailableMsg.value) {
          msg.ragUnavailable = ragUnavailableMsg.value
        }
        if (ragSourcesData.value) {
          msg.ragSources = ragSourcesData.value
        }
        if (searchResultsData.value) {
          msg.searchResults = searchResultsData.value
          msg.searchQuery = searchQuery.value
        }
        messages.value[assistantIdx] = msg
        scrollToBottom()
      },
      onDone(fullAnswer) {
        const msg = _buildAssistantMsg(fullAnswer)
        if (activeLearningContext) msg.learningContext = activeLearningContext
        if (ragUnavailableMsg.value) {
          msg.ragUnavailable = ragUnavailableMsg.value
        }
        if (ragSourcesData.value) {
          msg.ragSources = ragSourcesData.value
        }
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
          explanation_level: explanationLevel.value,
          conversation_id: conversationId.value
        }).then((result) => {
          if (result && result.id) currentQaId.value = result.id
          getConversations().then(res => { conversations.value = res || [] }).catch(() => {})
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

function openContextLab(context) {
  if (!context?.lab_id) return
  router.push(`/code-lab/${String(context.lab_id).split('-')[0]}/${context.lab_id}`)
}

</script>

<style scoped>
.qa-page { height: 100%; min-height: 0; overflow: hidden; }
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

/* 隐藏文件输入框（兼容所有浏览器的安全策略） */
.hidden-file-input {
  position: absolute;
  width: 0.1px;
  height: 0.1px;
  opacity: 0;
  overflow: hidden;
  z-index: -1;
}

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
/* RAG 知识库暂不可用 */
.rag-unavailable-block {
  margin-bottom: 10px;
  background: #fef8e7;
  border: 1px solid #f5dab1;
  border-radius: 8px;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #b88230;
}
/* RAG 知识库来源 */
.rag-sources-block {
  margin-bottom: 10px;
  background: #f0fdf4;
  border: 1px solid #b7e4c7;
  border-radius: 8px;
  overflow: hidden;
}
.rag-sources-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 500;
  color: #67C23A;
  background: #e8f8ef;
}
.rag-source-list { padding: 4px 8px 8px; max-height: 200px; overflow-y: auto; }
.rag-source-item {
  display: flex;
  align-items: baseline;
  gap: 4px;
  padding: 6px 10px;
  margin: 2px 0;
  border-radius: 4px;
  font-size: 12px;
  color: #606266;
}
.rag-source-icon { flex-shrink: 0; }
.rag-source-title { font-weight: 500; color: #2e7d32; }
.rag-source-section { color: #909399; }
.rag-source-page { color: #b0b3bb; font-size: 11px; }
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
.learning-context-block {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 10px;
  padding: 8px 10px;
  border: 1px solid #cfd7ff;
  border-radius: 9px;
  color: #4052a5;
  background: #f3f5ff;
  font-size: 12px;
}
.learning-context-block span { min-width: 0; flex: 1; }
.learning-context-block button {
  flex: 0 0 auto;
  padding: 4px 8px;
  border: 1px solid #aebaf5;
  border-radius: 7px;
  color: #4058c5;
  background: #fff;
  font-size: 10px;
  cursor: pointer;
}
.learning-context-block button:hover { border-color: #7186ec; background: #e9edff; }

/* DeepSeek 风格的紧凑对话工作区 */
.qa-page{height:100%!important;min-height:0;overflow:hidden}
.qa-layout{position:relative;display:flex;height:100%;gap:0!important;overflow:hidden;border:0;border-radius:0;background:#fff;box-shadow:none}
.conversation-sidebar{position:relative;width:252px;min-width:252px;display:flex;flex-direction:column;padding:14px 10px 10px;border-right:1px solid #e8ebf1;background:#f7f8fa;transition:width .24s,min-width .24s,padding .24s}
.conversation-sidebar.collapsed{width:48px;min-width:48px;padding:14px 7px}
.conversation-toggle{display:grid;width:34px;height:34px;place-items:center;align-self:flex-end;border:1px solid #dce1e9;border-radius:10px;color:#59667b;background:#fff;cursor:pointer}
.conversation-sidebar.collapsed .conversation-toggle{align-self:center}
.new-chat-button{height:42px;display:flex;align-items:center;justify-content:center;gap:9px;margin-top:14px;border:1px solid #dfe3ea;border-radius:12px;color:#28354c;background:#fff;font-size:13px;font-weight:650;cursor:pointer;box-shadow:0 3px 10px rgba(31,45,79,.04)}
.new-chat-button:hover{border-color:#aab5ed;background:#f6f7ff}
.conversation-caption{margin:20px 8px 8px;color:#9aa3b2;font-size:10px;font-weight:750;letter-spacing:.08em}
.conversation-list{min-height:0;flex:1;overflow-y:auto}
.conversation-item{width:100%;display:flex;align-items:center;gap:7px;margin:2px 0;padding:9px 8px;border:0;border-radius:9px;color:#344056;background:transparent;text-align:left;cursor:pointer}
.conversation-item:hover,.conversation-item.active{background:#e9ebf1}.conversation-item.active{color:#4052c5}
.conversation-copy{min-width:0;flex:1}.conversation-copy b,.conversation-copy small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.conversation-copy b{font-size:12px}.conversation-copy small{margin-top:4px;color:#9099a8;font-size:9px}
.conversation-delete{opacity:0;color:#9aa2b0}.conversation-item:hover .conversation-delete{opacity:1}.conversation-delete:hover{color:#e05e6b}.conversation-empty{padding:24px 8px;color:#a2aab8;font-size:11px;text-align:center}
.chat-column{min-height:0;flex:1;min-width:0}.chat-card{height:100%;min-height:0;border:0!important;border-radius:0!important;background:#fff}.chat-card :deep(.el-card__body){min-height:0;padding:0!important}
.chat-messages{min-height:0;padding:18px clamp(14px,3vw,44px) 12px!important;overscroll-behavior:contain;scrollbar-gutter:stable}
.welcome-msg{padding:clamp(55px,11vh,120px) 20px 32px}.welcome-orb{display:grid;width:62px;height:62px;margin:0 auto;place-items:center;border-radius:20px;color:#fff;background:linear-gradient(145deg,#6073ee,#55a7df);box-shadow:0 14px 30px rgba(74,104,211,.2)}.welcome-msg h3{font-size:22px}.welcome-msg p{margin-bottom:24px}
.chat-input{margin:0 clamp(12px,3vw,44px) 12px!important;padding:12px 14px 10px!important;border:1px solid #dfe3ea!important;border-radius:18px;background:#fff;box-shadow:0 10px 28px rgba(35,49,84,.09)}
.chat-input:focus-within{border-color:#9ba8ed!important;box-shadow:0 10px 30px rgba(66,83,185,.13)}
.chat-input textarea{display:block;width:100%;min-height:46px;max-height:132px;resize:none;border:0;outline:0;color:#202b3e;background:transparent;font:14px/1.6 inherit}
.chat-input textarea::placeholder{color:#a9b0bd}.composer-toolbar{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:5px}.composer-left{display:flex;align-items:center;gap:7px;min-width:0;flex-wrap:wrap}
.round-tool{display:grid;width:30px;height:30px;place-items:center;border:1px solid #e1e5eb;border-radius:9px;color:#4d596d;background:#fff;cursor:pointer}.round-tool:hover{background:#f3f5f9}.mode-chip{height:30px;display:flex;align-items:center;gap:5px;padding:0 10px;border:1px solid #e0e4ea;border-radius:15px;color:#5f6a7c;background:#fff;font-size:11px;cursor:pointer}.mode-chip.active{border-color:#a9b9ff;color:#3f63dc;background:#f0f4ff}
.send-button{display:grid;width:34px;height:34px;flex:0 0 34px;place-items:center;border:0;border-radius:50%;color:#fff;background:#6275ee;cursor:pointer}.send-button:disabled{color:#aeb5c2;background:#eceff3;cursor:not-allowed}.send-button.stop{background:#e65f6b}.file-tag{margin:0 0 7px}.capability-menu{display:grid;gap:4px}.capability-menu button{display:flex;align-items:center;gap:9px;width:100%;padding:9px;border:0;border-radius:9px;color:#344056;background:transparent;text-align:left;cursor:pointer}.capability-menu button:hover:not(:disabled){background:#f2f4f9}.capability-menu button:disabled{opacity:.48;cursor:not-allowed}.capability-menu button>span{min-width:0;flex:1}.capability-menu b,.capability-menu small{display:block}.capability-menu b{font-size:12px}.capability-menu small{margin-top:3px;color:#98a1af;font-size:9px}.capability-menu em{width:8px;height:8px;border-radius:50%;background:#c8ced8}.capability-menu em.on{background:#4f72e8;box-shadow:0 0 0 4px rgba(79,114,232,.12)}
@media(max-width:900px){.conversation-sidebar{position:absolute;z-index:10;inset:0 auto 0 0;box-shadow:10px 0 28px rgba(25,37,69,.14)}.conversation-sidebar.collapsed{position:relative;box-shadow:none}.chat-messages{padding-inline:16px!important}.chat-input{margin-inline:12px!important}.mode-chip{padding-inline:7px;font-size:10px}}
@media(max-width:900px){.qa-page{height:auto!important;min-height:calc(100dvh - 112px)}}
</style>
