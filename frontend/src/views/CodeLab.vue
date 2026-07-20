<template>
  <div class="code-lab-page">
    <!-- ===== 顶部面包屑导航 ===== -->
    <div class="lab-navbar">
      <div class="nav-left">
        <el-breadcrumb separator=">">
          <el-breadcrumb-item :to="{ name: 'ModuleSelect' }">
            <el-icon><HomeFilled /></el-icon> 首页
          </el-breadcrumb-item>
          <el-breadcrumb-item :to="{ name: 'TaskList', params: { moduleId: currentModuleId } }">
            {{ currentModuleName }}
          </el-breadcrumb-item>
          <el-breadcrumb-item>
            关卡{{ currentTaskId }}：{{ currentProblem.title || '加载中...' }}
          </el-breadcrumb-item>
        </el-breadcrumb>
      </div>
      <div class="nav-right">
        <el-button type="danger" size="small" plain @click="goBack">退出</el-button>
      </div>
    </div>

    <!-- ===== 可拖拽分割的主体容器 ===== -->
    <div class="lab-main" ref="mainRef">
      <!-- 左侧面板 (45%) -->
      <div class="left-panel" :style="{ flex: `0 0 ${leftWidth}%` }">
        <!-- 题目卡片 -->
        <div class="problem-card">
          <div class="card-header">
            <span class="card-title">📝 {{ currentProblem.title || '题目描述' }}</span>
            <el-tag v-if="currentProblem.knowledge" type="warning" size="small">{{ currentProblem.knowledge }}</el-tag>
          </div>
          <div class="card-body" ref="problemBodyRef">
            <template v-if="currentProblem.description">
              <div class="problem-section">
                <h4>题目描述</h4>
                <div class="problem-text">{{ currentProblem.description }}</div>
              </div>
              <div class="problem-section" v-if="currentProblem.input_output">
                <h4>输入输出说明</h4>
                <div class="problem-text">{{ currentProblem.input_output }}</div>
              </div>
              <div class="problem-section" v-if="currentProblem.samples?.length">
                <h4>样例</h4>
                <div v-for="(s, i) in currentProblem.samples" :key="i" class="sample-block">
                  <div class="sample-row" v-if="s.input"><span class="sample-label">输入：</span><code>{{ s.input }}</code></div>
                  <div class="sample-row" v-if="s.output"><span class="sample-label">输出：</span><code>{{ s.output }}</code></div>
                </div>
              </div>
              <!-- AI 错误解析区域 -->
              <div v-if="aiAnalysis" class="ai-analysis-box">
                <div class="ai-header"><span>🤖 AI 错误解析</span></div>
                <div class="ai-content">{{ aiAnalysis }}</div>
              </div>

              <!-- 渐进提示区域 -->
              <div v-if="aiHint && !aiAnalysis" class="hint-box">
                <div class="hint-header"><span>💡 提示</span><span class="failure-badge" v-if="consecutiveFailures > 0">第{{ consecutiveFailures }}次尝试</span></div>
                <div class="hint-content">{{ aiHint }}</div>
              </div>

              <!-- 连续3次失败：查看答案按钮 -->
              <div v-if="showViewAnswer" class="view-answer-area">
                <el-divider />
                <div class="view-answer-tip">
                  <el-icon><WarningFilled /></el-icon>
                  已经尝试 {{ consecutiveFailures }} 次了，需要帮助吗？
                </div>
                <el-button type="warning" @click="fetchAnswer" :loading="loadingAnswer">
                  <el-icon><View /></el-icon> 查看参考答案
                </el-button>
              </div>
            </template>
            <el-empty v-else description="加载题目中..." :image-size="60" />
          </div>
        </div>

        <!-- 运行结果终端 -->
        <div class="terminal-panel">
          <div class="terminal-header">
            <span>⬛ 运行终端</span>
            <el-button size="small" text @click="clearTerminal">清空</el-button>
          </div>
          <div class="terminal-body" ref="terminalRef">
            <div v-if="running" class="terminal-running">
              <el-icon class="is-loading"><Loading /></el-icon> 代码执行中...
            </div>
            <div v-else-if="terminalContent.length === 0" class="terminal-empty">点击「运行代码」查看输出</div>
            <div v-for="(line, i) in terminalContent" :key="i" :class="['terminal-line', line.type]">
              {{ line.text }}
            </div>
          </div>
        </div>
      </div>

      <!-- 可拖拽分割线 -->
      <div class="splitter-bar" @mousedown="startDrag">
        <div class="splitter-handle"><span>⟨⟩</span></div>
      </div>

      <!-- 右侧面板 (55%) -->
      <div class="right-panel" :style="{ flex: `0 0 ${100 - leftWidth - 1}%` }">
        <!-- 操作栏 -->
        <div class="toolbar">
          <el-select v-model="language" size="small" style="width:130px" disabled>
            <el-option v-for="l in LANGUAGES" :key="l.value" :label="l.label" :value="l.value" />
          </el-select>
          <div class="toolbar-spacer" />
          <el-button size="small" @click="resetCode">
            <el-icon><RefreshRight /></el-icon> 重置代码
          </el-button>
          <el-button size="small" type="primary" @click="runCode" :loading="running">
            <el-icon><VideoPlay /></el-icon> 运行代码
          </el-button>
          <el-button size="small" type="success" @click="submitCode" :loading="submitting">
            <el-icon><Finished /></el-icon> 提交答案
          </el-button>
        </div>
        <!-- Monaco 编辑器 -->
        <div class="editor-wrapper" ref="editorRef"></div>
      </div>
    </div>

    <!-- ===== 参考答案弹窗 ===== -->
    <el-dialog
      v-model="showAnswerDialog"
      title="📝 参考答案"
      width="750px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div v-if="answerData" class="answer-body">
        <!-- 解题思路 -->
        <div class="answer-section" v-if="answerData.approach">
          <h4>💭 解题思路</h4>
          <p>{{ answerData.approach }}</p>
        </div>

        <!-- 参考代码 -->
        <div class="answer-section" v-if="answerData.answer_code">
          <h4>📋 参考代码</h4>
          <div class="answer-code-wrapper">
            <pre class="answer-code">{{ answerData.answer_code }}</pre>
            <el-button size="small" class="copy-answer-btn" @click="copyAnswerCode">
              <el-icon><CopyDocument /></el-icon> 复制
            </el-button>
          </div>
        </div>

        <!-- 代码解释 -->
        <div class="answer-section" v-if="answerData.explanations?.length">
          <h4>🔍 关键代码解释</h4>
          <div v-for="(exp, i) in answerData.explanations" :key="i" class="explanation-item">
            <code class="exp-code">{{ exp.code }}</code>
            <p class="exp-text">{{ exp.explanation }}</p>
          </div>
        </div>
      </div>
      <div v-else-if="loadingAnswer" style="text-align:center;padding:30px">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <p>正在生成参考答案...</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as monaco from 'monaco-editor'
import { MODULES } from '../config/exercises'
import { useStatStore } from '../stores/statStore'
import { copyToClipboard } from '../utils/clipboard'

const router = useRouter()
const statStore = useStatStore()
const route = useRoute()

// ===== 从路由参数获取当前模块和关卡 =====
const currentModuleId = computed(() => parseInt(route.params.moduleId))
const currentTaskId = computed(() => route.params.taskId)
const currentModule = computed(() => MODULES.find(m => m.id === currentModuleId.value))
const currentModuleName = computed(() => currentModule.value?.name || '')
const currentTask = computed(() => {
  if (!currentModule.value) return null
  return currentModule.value.tasks.find(t => t.id === currentTaskId.value)
})

// ===== 编程语言 =====
const LANGUAGES = [{ label: 'Python', value: 'python' }]

// ===== 代码区域标记（由后端预处理脚本注入，前端不再自动生成） =====
const CODE_START = '# ==========你的代码开始=========='
const CODE_END = '# ==========你的代码结束=========='

// ===== 状态 =====
const language = ref('python')
const code = ref('')
const running = ref(false)
const submitting = ref(false)
const terminalContent = ref([])
const aiAnalysis = ref('')
const leftWidth = ref(45)
const currentProblem = reactive({
  title: '', knowledge: '', description: '',
  input_output: '', samples: [],
})

// ===== 连续失败计数 & 提示 & 答案 =====
const consecutiveFailures = ref(0)
const aiHint = ref('')
const showViewAnswer = computed(() => consecutiveFailures.value >= 3)
const showAnswerDialog = ref(false)
const answerData = ref(null)
const loadingAnswer = ref(false)

// ===== DOM 引用 =====
const editorRef = ref(null)
const terminalRef = ref(null)
const problemBodyRef = ref(null)
const mainRef = ref(null)
let editor = null
let isDragging = false

// ===== 加载题 =====
function loadCurrentTask() {
  if (!currentTask.value) return
  const t = currentTask.value
  // 从后端获取题目详情
  fetch(`/api/resources/exercises/${t.id}`, {
    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
  }).then(res => res.json()).then(data => {
    const ex = data.data || data
    if (ex) {
      currentProblem.title = ex.title || t.title
      currentProblem.knowledge = ex.module || currentModuleName.value
      currentProblem.description = ex.description || ''
      currentProblem.input_output = ex.input_output || ''
      // 解析样例
      const samples = []
      const ioText = ex.input_output || ''
      const inputMatches = [...ioText.matchAll(/样例输入[：:]\s*([\s\S]*?)(?=样例输出|$)/g)]
      const outputMatches = [...ioText.matchAll(/样例输出[：:]\s*([\s\S]*?)(?=样例输入|说明|$)/g)]
      for (let i = 0; i < Math.max(inputMatches.length, outputMatches.length); i++) {
        samples.push({
          input: inputMatches[i] ? inputMatches[i][1].trim() : '',
          output: outputMatches[i] ? outputMatches[i][1].trim() : '',
        })
      }
      currentProblem.samples = samples
      // 使用预处理后的骨架代码（已含 CODE_START/CODE_END 标记和测试代码）
      const starter = ex.skeleton_code || ex.starter_code || t.starter || '# TODO'
      code.value = starter
      if (editor) editor.setValue(code.value)
    }
  }).catch(e => {
    // 如果API不可用，使用本地配置数据
    currentProblem.title = t.title
    currentProblem.knowledge = currentModuleName.value
    currentProblem.description = '（题目详情从后端加载）'
    currentProblem.input_output = ''
    currentProblem.samples = []
  })
}

// ===== 初始化 Monaco 编辑器（与计时器合并，见下方） =====

function initEditor() {
  if (!editorRef.value) return
  editor = monaco.editor.create(editorRef.value, {
    value: code.value || '# 加载中...',
    language: 'python',
    theme: 'vs',
    automaticLayout: true,
    fontSize: 14,
    lineNumbers: 'on',
    wordWrap: 'on',
    tabSize: 4,
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
  })
  editor.onDidChangeModelContent(() => { code.value = editor.getValue() })
}

// ===== 分割线拖拽 =====
function startDrag(e) { isDragging = true; e.preventDefault() }
function onDrag(e) {
  if (!isDragging || !mainRef.value) return
  const rect = mainRef.value.getBoundingClientRect()
  let pct = ((e.clientX - rect.left) / rect.width) * 100
  pct = Math.max(25, Math.min(65, pct))
  leftWidth.value = Math.round(pct)
}
function stopDrag() { isDragging = false }

// ===== 运行代码 =====
async function runCode() {
  if (!code.value.trim()) { ElMessage.warning('请先编写代码'); return }
  running.value = true; aiAnalysis.value = ''; aiHint.value = ''
  terminalContent.value = [{ type: 'info', text: '>>> 正在执行 Python 代码...' }]
  scrollTerminal()
  try {
    // 使用与提交相同的评测端点，确保运行和提交结果一致
    const res = await fetch('/api/learning/code-evaluate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + localStorage.getItem('token'),
      },
      body: JSON.stringify({
        exercise_id: currentTaskId.value || '',
        code: code.value,
        language: language.value
      }),
    })
    const data = await res.json()
    const result = data.data || data

    terminalContent.value = [{ type: 'info', text: '>>> 运行结果 <<<' }]

    // 编译错误
    if (result.compile_error) {
      terminalContent.value.push({ type: 'err', text: result.compile_error })
      consecutiveFailures.value++
    } else if (result.results && result.results.length > 0) {
      // 显示测试结果
      for (const tc of result.results) {
        const icon = tc.passed ? '[PASS]' : '[FAIL]'
        terminalContent.value.push({
          type: tc.passed ? 'out' : 'err',
          text: `${icon} 用例${tc.case_index}: ${tc.description || ''}`
        })
        if (!tc.passed) {
          if (tc.input_args) terminalContent.value.push({ type: 'err', text: `  输入: ${JSON.stringify(tc.input_args)}` })
          if (tc.expected !== undefined) terminalContent.value.push({ type: 'err', text: `  期望: ${JSON.stringify(tc.expected)}` })
          if (tc.actual !== undefined) terminalContent.value.push({ type: 'err', text: `  实际: ${tc.actual || tc.error || '(无返回值)'}` })
        }
      }
      terminalContent.value.push({ type: 'info', text: `通过: ${result.passed_count}/${result.total}` })

      if (result.passed) {
        consecutiveFailures.value = 0
      } else {
        consecutiveFailures.value++
      }
    } else {
      terminalContent.value.push({ type: 'info', text: '代码运行完成。' })
      if (result.passed) {
        consecutiveFailures.value = 0
      }
    }
  } catch (e) {
    consecutiveFailures.value++
    terminalContent.value.push({ type: 'err', text: `请求失败: ${e.message}` })
  } finally { running.value = false; scrollTerminal() }
}

// ===== 计时器 =====
const startTime = ref(Date.now())
const elapsedSeconds = ref(0)
let timerInterval = null

onMounted(async () => {
  initEditor()
  loadCurrentTask()
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  // 开始计时
  startTime.value = Date.now()
  timerInterval = setInterval(() => {
    elapsedSeconds.value = Math.floor((Date.now() - startTime.value) / 1000)
  }, 1000)
  // 从服务器同步已通关的习题列表（跨设备同步）
  syncCompletionsFromServer()
})

onBeforeUnmount(() => {
  editor?.dispose()
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  if (timerInterval) clearInterval(timerInterval)
})

// ===== 提交答案 — 真实沙箱评测 =====
async function submitCode() {
  if (!code.value.trim()) { ElMessage.warning('请先编写代码'); return }
  submitting.value = true
  aiAnalysis.value = ''
  aiHint.value = ''
  terminalContent.value = [{ type: 'info', text: '=== 评测提交中... ===' }]
  scrollTerminal()

  try {
    const submitStart = Date.now()
    const res = await fetch('/api/learning/code-evaluate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + localStorage.getItem('token'),
      },
      body: JSON.stringify({
        exercise_id: currentTaskId.value || '',
        code: code.value,
        language: language.value
      }),
    })
    const data = await res.json()
    const result = data.data || data

    terminalContent.value = [{ type: 'info', text: '=== 评测结果 ===' }]

    // 编译/运行错误
    if (result.compile_error) {
      terminalContent.value.push({ type: 'err', text: result.compile_error })
      consecutiveFailures.value++
      ElMessage.error('编译/运行出错，未通过评测')
      submitting.value = false
      scrollTerminal()
      return
    }

    // 测试用例明细
    const submitElapsed = ((Date.now() - submitStart) / 1000).toFixed(1)
    terminalContent.value.push({ type: 'info', text: `通过: ${result.passed_count}/${result.total}  评测耗时: ${submitElapsed}s` })
    terminalContent.value.push({ type: 'info', text: '' })

    for (const tc of (result.results || [])) {
      const icon = tc.passed ? '[PASS]' : '[FAIL]'
      terminalContent.value.push({
        type: tc.passed ? 'out' : 'err',
        text: `${icon} 用例${tc.case_index}: ${tc.description || ''}`
      })
      if (!tc.passed) {
        terminalContent.value.push({ type: 'err', text: `  输入: ${JSON.stringify(tc.input_args)}` })
        terminalContent.value.push({ type: 'err', text: `  期望: ${JSON.stringify(tc.expected)}` })
        terminalContent.value.push({ type: 'err', text: `  实际: ${tc.actual || tc.error || '(无返回值)'}` })
      }
    }

    // 判定
    if (result.passed) {
      consecutiveFailures.value = 0
      const totalSeconds = elapsedSeconds.value
      const timeStr = totalSeconds >= 60
        ? `${Math.floor(totalSeconds / 60)}分${totalSeconds % 60}秒`
        : `${totalSeconds}秒`

      terminalContent.value.push({ type: 'info', text: '' })
      terminalContent.value.push({ type: 'out', text: `*** 全部测试通过！恭喜完成本题！***` })
      terminalContent.value.push({ type: 'out', text: `用时: ${timeStr}` })

      // 标记完成（保存到 localStorage 作为本地缓存 + 服务器已通过 code-evaluate 记录）
      try {
        const completed = JSON.parse(localStorage.getItem('code_completed') || '{}')
        const key = `${currentModuleId.value}_${currentTaskId.value}`
        completed[key] = {
          time: timeStr,
          seconds: totalSeconds,
          passedCount: result.passed_count,
          totalCount: result.total,
          completedAt: new Date().toISOString()
        }
        localStorage.setItem('code_completed', JSON.stringify(completed))
      } catch (e) { /* ignore */ }
      // 同步通关数据到服务器（已在 code-evaluate 中自动记录，此处仅刷新本地缓存）
      syncCompletionsFromServer()

      // 刷新统计（容错：统计接口失败不阻塞主流程）
      try {
        const knowledge = currentProblem.knowledge || currentTask.value?.title || '综合'
        await statStore.refreshStatData({
          score: Math.round(result.passed_count / Math.max(result.total, 1) * 100),
          total: 100, knowledge
        })
      } catch (e) {
        console.warn('统计刷新失败（不影响提交结果）:', e)
      }

      ElMessage.success(`全部测试通过！用时 ${timeStr}`)
    } else {
      consecutiveFailures.value++
      terminalContent.value.push({ type: 'info', text: '' })
      terminalContent.value.push({ type: 'err', text: `还有 ${result.total - result.passed_count} 个用例未通过，请继续修改代码` })
      ElMessage.warning(`${result.passed_count}/${result.total} 用例通过，未完成提交`)
    }
  } catch (e) {
    consecutiveFailures.value++
    terminalContent.value.push({ type: 'err', text: `评测请求失败: ${e.message}` })
    ElMessage.error('评测请求失败，请检查网络后重试')
  }
  finally { submitting.value = false; scrollTerminal() }
}

// ===== 重做本题 =====
function redoTask() {
  resetCode()
  startTime.value = Date.now()
  elapsedSeconds.value = 0
  consecutiveFailures.value = 0
  terminalContent.value = []
  aiAnalysis.value = ''
  aiHint.value = ''
  ElMessage.info('已重置，可以重新开始')
}

// ===== 重置代码 =====
function resetCode() {
  loadCurrentTask()
  consecutiveFailures.value = 0
  aiAnalysis.value = ''
  aiHint.value = ''
  ElMessage.info('代码已重置为初始模板')
}

// ===== 查看答案 =====
async function fetchAnswer() {
  loadingAnswer.value = true
  showAnswerDialog.value = true
  answerData.value = null
  try {
    // 直接使用 exercise_id 让后端加载完整习题数据（含 starter_code + eval_code）
    const res = await fetch('/api/learning/code-answer', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + localStorage.getItem('token'),
      },
      body: JSON.stringify({
        title: currentProblem.title || '',
        description: currentProblem.description || '',
        knowledge: currentProblem.knowledge || '',
        language: language.value,
        code: code.value,
        exercise_id: currentTaskId.value || ''
      }),
    })
    const data = await res.json()
    if (data.code === 200 && data.data) {
      answerData.value = data.data
      // 如果答案经过验证，给出提示
      if (data.data._validated === false) {
        ElMessage.warning('参考答案已生成但沙箱验证未通过，请谨慎参考')
      }
    } else {
      answerData.value = { approach: '参考答案生成失败', answer_code: data.message || '请稍后重试', explanations: [] }
    }
  } catch (e) {
    answerData.value = { approach: '网络请求失败', answer_code: e.message || '请检查网络连接', explanations: [] }
  } finally {
    loadingAnswer.value = false
  }
}

async function syncCompletionsFromServer() {
  try {
    const resp = await fetch('/api/learning/code-completions', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
    })
    const data = await resp.json()
    if (data.code === 200 && Array.isArray(data.data)) {
      const completed = JSON.parse(localStorage.getItem('code_completed') || '{}')
      let updated = false
      data.data.forEach(exerciseId => {
        // 用 exercise_id 构建 key（格式：module_taskId，如 "1_5-6"）
        // 也尝试直接匹配
        if (!completed[exerciseId]) {
          // 尝试匹配当前模块下的 key
          const key = `${currentModuleId.value}_${exerciseId}`
          if (!completed[key]) {
            completed[key] = {
              time: '已同步',
              seconds: 0,
              passedCount: 1,
              totalCount: 1,
              completedAt: null,
              synced: true
            }
            updated = true
          }
        }
      })
      if (updated) {
        localStorage.setItem('code_completed', JSON.stringify(completed))
      }
    }
  } catch (e) {
    console.warn('[CodeLab] 同步通关数据失败:', e.message)
  }
}

async function copyAnswerCode() {
  if (!answerData.value?.answer_code) return
  const ok = await copyToClipboard(answerData.value.answer_code)
  ElMessage[ok ? 'success' : 'warning'](ok ? '参考代码已复制到剪贴板' : '复制失败，请手动复制')
}

// ===== 终端操作 =====
function clearTerminal() { terminalContent.value = [] }
function scrollTerminal() { nextTick(() => { if (terminalRef.value) terminalRef.value.scrollTop = terminalRef.value.scrollHeight }) }

function goBack() {
  router.push({ name: 'TaskList', params: { moduleId: currentModuleId.value } })
}
</script>

<style scoped>
.code-lab-page {
  display: flex; flex-direction: column;
  height: calc(100vh - 100px); background: #f5f6f8;
}
/* 顶部导航栏 */
.lab-navbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0 16px; height: 48px; background: #1a1a2e; color: #fff; flex-shrink: 0;
}
.nav-left { display: flex; align-items: center; gap: 8px; }
.nav-right { display: flex; align-items: center; gap: 12px; }
.lab-navbar :deep(.el-breadcrumb__inner) { color: #c0d0e0; font-size: 13px; }
.lab-navbar :deep(.el-breadcrumb__inner.is-link:hover) { color: #409EFF; }
.lab-navbar :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) { color: #fff; font-weight: 600; }

/* 主体容器 */
.lab-main { flex: 1; display: flex; overflow: hidden; }
.left-panel { display: flex; flex-direction: column; overflow: hidden; min-width: 0; }

/* 题目卡片 */
.problem-card { flex: 1; overflow: hidden; display: flex; flex-direction: column; background: #fff; border-right: 1px solid #e4e7ed; }
.card-header { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; border-bottom: 1px solid #e4e7ed; flex-shrink: 0; }
.card-title { font-size: 14px; font-weight: 600; color: #1a1a2e; }
.card-body { flex: 1; overflow-y: auto; padding: 14px; }
.problem-section { margin-bottom: 16px; }
.problem-section h4 { font-size: 13px; font-weight: 600; color: #303133; margin: 0 0 6px; padding-left: 8px; border-left: 3px solid #409EFF; }
.problem-text { font-size: 13px; line-height: 1.8; color: #4a4a4a; white-space: pre-wrap; }
.sample-block { background: #f7f8fa; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; }
.sample-row { font-size: 13px; line-height: 1.8; color: #303133; }
.sample-row code { background: #e8eaed; padding: 2px 6px; border-radius: 3px; font-family: 'Courier New', monospace; font-size: 12px; }
.sample-label { color: #909399; font-size: 12px; }

/* AI错误解析 */
.ai-analysis-box { margin-top: 16px; background: #fef7e0; border: 1px solid #f5dab1; border-radius: 8px; overflow: hidden; }
.ai-header { padding: 8px 12px; background: #fdf3d0; font-size: 13px; font-weight: 600; color: #b88230; }
.ai-content { padding: 10px 14px; font-size: 13px; line-height: 1.7; color: #4a4a4a; white-space: pre-wrap; }

/* 渐进提示 */
.hint-box { margin-top: 12px; background: #e6f7ff; border: 1px solid #91d5ff; border-radius: 8px; overflow: hidden; }
.hint-header { padding: 8px 12px; background: #d6efff; font-size: 13px; font-weight: 600; color: #096dd9; display: flex; justify-content: space-between; align-items: center; }
.hint-content { padding: 10px 14px; font-size: 13px; line-height: 1.7; color: #4a4a4a; white-space: pre-wrap; }
.failure-badge { font-size: 11px; background: #ffa940; color: #fff; padding: 2px 8px; border-radius: 10px; font-weight: 500; }

/* 查看答案区域 */
.view-answer-area { margin-top: 16px; text-align: center; }
.view-answer-tip { display: flex; align-items: center; justify-content: center; gap: 6px; font-size: 13px; color: #e6a23c; margin-bottom: 10px; }

/* 答案弹窗 */
.answer-body { max-height: 65vh; overflow-y: auto; }
.answer-section { margin-bottom: 20px; }
.answer-section h4 { font-size: 14px; font-weight: 600; color: #303133; margin: 0 0 10px; padding-left: 8px; border-left: 3px solid #409EFF; }
.answer-section p { font-size: 13px; line-height: 1.8; color: #4a4a4a; }
.answer-code-wrapper { position: relative; background: #1e1e1e; border-radius: 8px; overflow: hidden; }
.answer-code { padding: 16px; font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace; font-size: 13px; line-height: 1.6; color: #d4d4d4; white-space: pre-wrap; margin: 0; max-height: 350px; overflow-y: auto; }
.copy-answer-btn { position: absolute; top: 8px; right: 8px; opacity: 0.85; }
.copy-answer-btn:hover { opacity: 1; }
.explanation-item { background: #f5f7fa; border-radius: 6px; padding: 10px 14px; margin-bottom: 10px; }
.exp-code { display: block; font-family: 'Consolas', monospace; font-size: 12px; color: #409EFF; background: #e8eaed; padding: 4px 8px; border-radius: 4px; margin-bottom: 6px; word-break: break-all; }
.exp-text { font-size: 13px; line-height: 1.7; color: #606266; margin: 0; }

/* 终端 */
.terminal-panel { height: 200px; flex-shrink: 0; background: #1e1e1e; border-top: 1px solid #333; display: flex; flex-direction: column; }
.terminal-header { display: flex; justify-content: space-between; align-items: center; padding: 6px 12px; background: #2d2d2d; color: #ccc; font-size: 12px; font-weight: 600; flex-shrink: 0; }
.terminal-body { flex: 1; overflow-y: auto; padding: 8px 12px; font-family: 'Courier New', Consolas, monospace; font-size: 13px; }
.terminal-empty { color: #666; padding: 20px; text-align: center; }
.terminal-running { color: #409EFF; display: flex; align-items: center; gap: 8px; }
.terminal-line { line-height: 1.5; white-space: pre-wrap; word-break: break-all; }
.terminal-line.info { color: #a0a0a0; }
.terminal-line.out { color: #4ec9b0; }
.terminal-line.err { color: #f44747; }

/* 分割线 */
.splitter-bar { width: 6px; flex-shrink: 0; background: #e4e7ed; cursor: col-resize; display: flex; align-items: center; justify-content: center; transition: background .2s; }
.splitter-bar:hover { background: #409EFF; }
.splitter-handle { width: 20px; height: 40px; background: #fff; border: 1px solid #d9d9d9; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #bbb; user-select: none; }

/* 右面板 */
.right-panel { display: flex; flex-direction: column; overflow: hidden; min-width: 0; }
.toolbar { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #fff; border-bottom: 1px solid #e4e7ed; flex-shrink: 0; }
.toolbar-spacer { flex: 1; }
.editor-wrapper { flex: 1; overflow: hidden; }
</style>
