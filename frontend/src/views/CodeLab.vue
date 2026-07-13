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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as monaco from 'monaco-editor'
import { MODULES } from '../config/exercises'
import { useStatStore } from '../stores/statStore'

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

// ===== 代码区域标记 =====
const CODE_START = '# ==========你的代码开始=========='
const CODE_END = '# ==========你的代码结束=========='

/**
 * 给初始代码模板注入标记行
 * 学生在两行标记之间编写代码，后端评测只提取该区间的代码
 */
function inject_markers(starter) {
  const lines = starter.split('\n')
  const out = []
  let has_func = false
  for (const line of lines) {
    out.push(line)
    // 在第一个函数定义的冒号后面插入标记
    if (!has_func && (line.trim().startsWith('def ') || line.trim().startsWith('class ')) && line.trim().endsWith(':')) {
      has_func = true
      const indent = line.match(/^(\s*)/)[1] + '    '
      out.push(indent + CODE_START)
      out.push('')
      out.push(indent + CODE_END)
    }
  }
  if (!has_func) {
    out.push(CODE_START)
    out.push(CODE_END)
  }
  return out.join('\n')
}

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
      // 加载带标记的初始代码
      const starter = ex.starter_code || t.starter || '# TODO'
      code.value = inject_markers(starter)
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

// ===== 初始化 Monaco 编辑器 =====
onMounted(() => {
  initEditor()
  loadCurrentTask()
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
})

onBeforeUnmount(() => {
  editor?.dispose()
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
})

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
  running.value = true; aiAnalysis.value = ''
  terminalContent.value = [{ type: 'info', text: '>>> 正在执行 Python 代码...' }]
  scrollTerminal()
  try {
    const res = await fetch('/api/learning/code-run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + localStorage.getItem('token'),
      },
      body: JSON.stringify({ code: code.value, language: language.value }),
    })
    const data = await res.json()
    const result = data.data || data
    if (result.output) result.output.split('\n').forEach(l => terminalContent.value.push({ type: 'out', text: l }))
    if (result.error) result.error.split('\n').forEach(l => terminalContent.value.push({ type: 'err', text: l }))
    if (result.ai_analysis) aiAnalysis.value = result.ai_analysis
    if (!result.output && !result.error) terminalContent.value.push({ type: 'info', text: '>>> 执行完毕，无输出。' })
  } catch (e) {
    terminalContent.value.push({ type: 'err', text: `请求失败: ${e.message}` })
  } finally { running.value = false; scrollTerminal() }
}

// ===== 提交答案（预留后端判题对接） =====
async function submitCode() {
  if (!code.value.trim()) { ElMessage.warning('请先编写代码'); return }
  submitting.value = true
  try {
    // TODO: 对接后端判题 POST /api/learning/code-submit { problem_id, code, language }
    // 响应格式: { passed, total, test_results: [...], ai_feedback }
    const res = await fetch('/api/learning/code-run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + localStorage.getItem('token'),
      },
      body: JSON.stringify({ code: code.value, language: language.value }),
    })
    const data = await res.json()
    const result = data.data || data
    terminalContent.value = [{ type: 'info', text: '=== 提交结果 ===' }]
    if (result.output) result.output.split('\n').forEach(l => terminalContent.value.push({ type: 'out', text: l }))
    if (result.error) { terminalContent.value.push({ type: 'info', text: '=== 运行错误 ===' }); result.error.split('\n').forEach(l => terminalContent.value.push({ type: 'err', text: l })) }
    if (result.ai_analysis) aiAnalysis.value = result.ai_analysis

    // ===== 提交成功后刷新统计数据 + 学习动态 =====
    // 模拟评分（后续对接真实判题系统后替换为后端返回的 score/total）
    const mockScore = Math.floor(Math.random() * 4) + 6 // 6-10 随机
    const knowledge = currentProblem.knowledge || currentTask.value?.title || '综合'
    await statStore.refreshStatData({ score: mockScore, total: 10, knowledge })

    ElMessage.success('提交完成！统计数据已更新')
  } catch (e) { ElMessage.error('提交失败: ' + (e.message || '网络错误')) }
  finally { submitting.value = false; scrollTerminal() }
}

// ===== 重置代码 =====
function resetCode() {
  loadCurrentTask()
  ElMessage.info('代码已重置为初始模板')
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
