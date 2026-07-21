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
        <el-button v-if="capabilitySession?.verified" size="small" plain class="report-nav-btn" @click="openCapabilityReport">
          查看能力报告
        </el-button>
        <el-button type="danger" size="small" plain @click="goBack">退出</el-button>
      </div>
    </div>

    <!-- 能力证据轨道：代码正确不再等于学习完成 -->
    <div class="evidence-rail" aria-label="能力验证进度">
      <div class="rail-thesis">
        <span class="rail-kicker">能力证据</span>
        <strong>{{ railHeadline }}</strong>
      </div>
      <div class="rail-stages">
        <div
          v-for="(stage, index) in capabilityStages"
          :key="stage.key"
          :class="['rail-stage', phaseState(index)]"
        >
          <span class="stage-index">{{ String(index + 1).padStart(2, '0') }}</span>
          <span class="stage-copy"><b>{{ stage.title }}</b><small>{{ stage.caption }}</small></span>
        </div>
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

              <div v-if="capabilityStatus === 'repair_pending'" class="repair-brief">
                <div class="repair-label">故障修复现场</div>
                <h4>代码中已注入一个可复现故障</h4>
                <p>{{ capabilitySession?.mutation_description }}</p>
                <el-input
                  v-model="repairExplanation"
                  type="textarea"
                  :rows="3"
                  maxlength="3000"
                  show-word-limit
                  placeholder="先说明故障根因和修复思路，再点击右侧“验证修复”"
                />
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
          <el-button size="small" @click="resetCode" :disabled="capabilityStatus === 'repair_pending'">
            <el-icon><RefreshRight /></el-icon> 重置代码
          </el-button>
          <el-button size="small" type="primary" @click="runCode" :loading="running">
            <el-icon><VideoPlay /></el-icon> 运行代码
          </el-button>
          <el-button size="small" type="success" @click="handlePrimarySubmit" :loading="submitting">
            <el-icon><Finished /></el-icon> {{ primaryActionLabel }}
          </el-button>
        </div>
        <!-- Monaco 编辑器 -->
        <div class="editor-wrapper" ref="editorRef"></div>
      </div>
    </div>

    <!-- ===== 原理答辩 / 能力报告 ===== -->
    <el-dialog
      v-model="showCapabilityDialog"
      width="820px"
      class="capability-dialog"
      :close-on-click-modal="false"
      :show-close="capabilityView !== 'defense'"
      destroy-on-close
    >
      <template #header>
        <div class="dialog-heading">
          <span>{{ capabilityView === 'report' ? '能力证据报告' : '代码已通过，能力尚未验证' }}</span>
          <small v-if="capabilityView === 'defense'">回答必须对应你刚才提交的代码，不能只复述概念。</small>
        </div>
      </template>

      <div v-if="capabilityView === 'defense'" class="defense-panel">
        <div class="defense-intro">
          <b>限时文字答辩</b>
          <span>系统依据你的代码结构与课程能力目标生成以下问题。</span>
        </div>
        <div v-for="(question, index) in defenseQuestions" :key="question.id" class="defense-question">
          <div class="question-meta">
            <span>问题 {{ index + 1 }}</span>
            <em>{{ question.focus }}</em>
          </div>
          <p>{{ question.prompt }}</p>
          <el-input
            v-model="defenseAnswers[question.id]"
            type="textarea"
            :rows="3"
            maxlength="1000"
            show-word-limit
            placeholder="结合变量、分支或方法名，说明你的具体实现"
          />
          <small class="question-source">能力依据：{{ question.source }}</small>
        </div>
        <div class="ai-declaration">
          <div><b>AI使用声明</b><small>声明本身不扣分，用于让过程证据完整。</small></div>
          <el-select v-model="aiUsage" style="width: 220px">
            <el-option label="未使用AI" value="未使用AI" />
            <el-option label="AI提供了提示" value="AI提供了提示" />
            <el-option label="AI参与生成或修改" value="AI参与生成或修改" />
          </el-select>
        </div>
        <div v-if="defenseFeedback" class="defense-feedback">
          本次答辩得分 <b>{{ defenseFeedback.defense_score }}</b>。需要达到60分，请补充缺失的设计依据后重试。
        </div>
        <div class="dialog-actions">
          <el-button type="primary" size="large" :loading="defenseSubmitting" @click="submitDefense">
            提交答辩并进入故障修复
          </el-button>
        </div>
      </div>

      <div v-else-if="capabilityReport" class="capability-report">
        <div class="report-verdict">
          <div class="score-seal"><strong>{{ capabilityReport.total_score }}</strong><span>综合证据分</span></div>
          <div><span class="verified-badge">能力已验证</span><h3>{{ capabilityReport.summary }}</h3></div>
        </div>
        <div class="dimension-grid">
          <div v-for="(score, label) in capabilityReport.dimensions" :key="label" class="dimension-card">
            <span>{{ label }}</span><strong>{{ score }}</strong>
            <el-progress :percentage="score" :show-text="false" :stroke-width="6" />
          </div>
        </div>
        <div class="evidence-ledger">
          <h4>可复核证据</h4>
          <div><span>代码验证</span><b>自带测试全部通过</b></div>
          <div><span>答辩验证</span><b>{{ capabilityReport.defense_evidence?.length || 0 }} 个代码绑定问题</b></div>
          <div><span>知识依据</span><b>{{ capabilityReport.knowledge_sources?.[0] || '课程知识库' }}</b></div>
          <div><span>迁移验证</span><b>已定位并修复注入故障</b></div>
          <div><span>过程记录</span><b>{{ capabilityReport.process_evidence?.run_attempts || 0 }} 次运行 · {{ capabilityReport.process_evidence?.edit_snapshots || 0 }} 个编辑快照</b></div>
          <p>{{ capabilityReport.process_evidence?.note }}</p>
        </div>
        <div class="next-challenge"><span>下一步挑战</span>{{ capabilityReport.next_step }}</div>
      </div>
    </el-dialog>

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
import { MODULES } from '../config/flagshipExercises'
import { useStatStore } from '../stores/statStore'
import { copyToClipboard } from '../utils/clipboard'
import {
  startCapabilitySession,
  recordCapabilityEvents,
  markCapabilityCodePassed,
  submitCapabilityDefense,
  submitCapabilityRepair,
} from '../api/capability'

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

// ===== 能力真实性验证闭环 =====
const capabilitySession = ref(null)
const showCapabilityDialog = ref(false)
const capabilityView = ref('defense')
const defenseAnswers = reactive({})
const defenseSubmitting = ref(false)
const defenseFeedback = ref(null)
const aiUsage = ref('未使用AI')
const repairExplanation = ref('')
const capabilityReport = ref(null)
const eventQueue = []
let eventFlushTimer = null
let lastEditEventAt = 0
let suppressEditorEvent = false

const capabilityStatus = computed(() => capabilitySession.value?.status || 'coding')
const defenseQuestions = computed(() => capabilitySession.value?.defense_questions || [])
const capabilityStages = [
  { key: 'code', title: '功能正确', caption: '测试只是入场券' },
  { key: 'defense', title: '原理答辩', caption: '解释本人代码' },
  { key: 'repair', title: '故障修复', caption: '证明迁移能力' },
  { key: 'report', title: '能力验证', caption: '形成证据报告' },
]
const phaseIndex = computed(() => ({
  coding: 0,
  defense_pending: 1,
  repair_pending: 2,
  verified: 3,
}[capabilityStatus.value] ?? 0))
const railHeadline = computed(() => ({
  coding: '先让代码正确，再证明能力属于你',
  defense_pending: '代码正确，等待原理答辩',
  repair_pending: '答辩通过，正在验证故障修复能力',
  verified: '代码、理解与迁移证据均已成立',
}[capabilityStatus.value] || '建立可复核的学习证据'))
const primaryActionLabel = computed(() => {
  if (capabilityStatus.value === 'repair_pending') return '验证修复'
  if (capabilityStatus.value === 'verified') return '查看能力报告'
  return '提交代码'
})

function phaseState(index) {
  if (capabilityStatus.value === 'verified') return 'complete'
  if (index < phaseIndex.value) return 'complete'
  if (index === phaseIndex.value) return 'active'
  return 'pending'
}

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
      setEditorValue(starter)
      initCapabilitySession()
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

async function initCapabilitySession() {
  if (!currentTaskId.value) return
  try {
    const session = await startCapabilitySession(currentTaskId.value)
    capabilitySession.value = session
    flushCapabilityEvents()
    capabilityReport.value = session.report || null
    aiUsage.value = session.ai_usage || '未使用AI'
    if (session.status === 'defense_pending') {
      hydrateDefenseAnswers(session)
      capabilityView.value = 'defense'
      showCapabilityDialog.value = true
    } else if (session.status === 'repair_pending' && session.mutation_code) {
      setEditorValue(session.mutation_code)
      repairExplanation.value = session.repair_explanation || ''
      terminalContent.value = [
        { type: 'info', text: '=== 已恢复故障修复现场 ===' },
        { type: 'err', text: session.mutation_description || '请定位并修复注入故障' },
      ]
    }
  } catch (e) {
    console.warn('[Capability] 初始化失败，普通代码评测仍可使用:', e.message)
  }
}

function hydrateDefenseAnswers(session) {
  for (const question of (session.defense_questions || [])) {
    if (!(question.id in defenseAnswers)) defenseAnswers[question.id] = ''
  }
  for (const item of (session.defense_answers || [])) {
    if (item.question_id) defenseAnswers[item.question_id] = item.answer || ''
  }
}

function setEditorValue(value) {
  suppressEditorEvent = true
  code.value = value
  editor?.setValue(value)
  nextTick(() => { suppressEditorEvent = false })
}

function queueCapabilityEvent(type, payload = {}) {
  eventQueue.push({ type, payload })
  if (capabilitySession.value?.id && eventQueue.length >= 8) flushCapabilityEvents()
}

async function flushCapabilityEvents() {
  if (!capabilitySession.value?.id || eventQueue.length === 0) return
  const batch = eventQueue.splice(0, eventQueue.length)
  try {
    await recordCapabilityEvents(capabilitySession.value.id, batch)
  } catch (e) {
    eventQueue.unshift(...batch.slice(-20))
  }
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
  editor.onDidChangeModelContent((event) => {
    code.value = editor.getValue()
    if (suppressEditorEvent) return
    const now = Date.now()
    const delta = event.changes.reduce((sum, change) => sum + Math.abs(change.text.length - change.rangeLength), 0)
    const pasted = event.changes.some(change => change.text.length >= 80)
    if (pasted) queueCapabilityEvent('paste', { length: Math.max(...event.changes.map(change => change.text.length)) })
    if (now - lastEditEventAt >= 2500) {
      queueCapabilityEvent('edit', { delta, length: code.value.length })
      lastEditEventAt = now
    }
  })
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
    queueCapabilityEvent('run', {
      passed: Boolean(result.passed),
      failed: Math.max((result.total || 0) - (result.passed_count || 0), 0),
    })

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
  eventFlushTimer = setInterval(flushCapabilityEvents, 5000)
  // 从服务器同步已通关的习题列表（跨设备同步）
  syncCompletionsFromServer()
})

onBeforeUnmount(() => {
  editor?.dispose()
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  if (timerInterval) clearInterval(timerInterval)
  if (eventFlushTimer) clearInterval(eventFlushTimer)
  flushCapabilityEvents()
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
    queueCapabilityEvent('submit', { source: 'code' })
    await flushCapabilityEvents()
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
      terminalContent.value.push({ type: 'out', text: `*** 全部测试通过，功能正确 ***` })
      terminalContent.value.push({ type: 'out', text: `用时: ${timeStr}` })
      terminalContent.value.push({ type: 'info', text: '下一步：完成原理答辩和故障修复，能力才会被标记为已验证。' })

      if (!capabilitySession.value?.id) {
        capabilitySession.value = await startCapabilitySession(currentTaskId.value)
      }
      capabilitySession.value = await markCapabilityCodePassed(capabilitySession.value.id, code.value)
      hydrateDefenseAnswers(capabilitySession.value)
      capabilityView.value = 'defense'
      showCapabilityDialog.value = true
      ElMessage.success(`代码测试通过，用时 ${timeStr}。请继续完成能力验证`)
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

function handlePrimarySubmit() {
  if (capabilityStatus.value === 'repair_pending') return submitRepair()
  if (capabilityStatus.value === 'verified') return openCapabilityReport()
  return submitCode()
}

async function submitDefense() {
  const unanswered = defenseQuestions.value.filter(question => !String(defenseAnswers[question.id] || '').trim())
  if (unanswered.length) {
    ElMessage.warning(`还有 ${unanswered.length} 个问题未回答`)
    return
  }
  defenseSubmitting.value = true
  defenseFeedback.value = null
  try {
    const answers = defenseQuestions.value.map(question => ({
      question_id: question.id,
      answer: defenseAnswers[question.id] || '',
    }))
    const result = await submitCapabilityDefense(capabilitySession.value.id, answers, aiUsage.value)
    capabilitySession.value = result
    if (!result.defense_passed) {
      defenseFeedback.value = result
      return
    }

    setEditorValue(result.mutation_code)
    repairExplanation.value = ''
    showCapabilityDialog.value = false
    terminalContent.value = [
      { type: 'info', text: '=== 原理答辩通过，进入故障修复 ===' },
      { type: 'err', text: result.mutation_description },
      { type: 'info', text: '请运行代码观察故障，说明根因并完成修复。' },
    ]
    ElMessage.success(`答辩得分 ${result.defense_score}，已进入故障修复`)
  } catch (e) {
    ElMessage.error(e.message || '答辩提交失败')
  } finally {
    defenseSubmitting.value = false
  }
}

async function submitRepair() {
  if (repairExplanation.value.trim().length < 20) {
    ElMessage.warning('请先用至少20字说明故障根因和修复思路')
    return
  }
  submitting.value = true
  queueCapabilityEvent('submit', { source: 'repair' })
  await flushCapabilityEvents()
  terminalContent.value = [{ type: 'info', text: '=== 正在复核修复结果与解释证据 ===' }]
  try {
    const result = await submitCapabilityRepair(
      capabilitySession.value.id,
      code.value,
      repairExplanation.value,
    )
    if (!result.repair_passed) {
      terminalContent.value = [
        { type: 'err', text: '修复尚未通过，请根据终端证据继续定位。' },
        { type: 'err', text: result.evaluation?.compile_error || result.evaluation?.output || '测试仍有失败' },
      ]
      ElMessage.warning('修复未通过，能力尚未验证')
      return
    }

    capabilityReport.value = result.report
    capabilitySession.value = {
      ...capabilitySession.value,
      status: 'verified',
      verified: true,
      report: result.report,
    }
    markVerifiedCompletion(result.report)
    capabilityView.value = 'report'
    showCapabilityDialog.value = true
    terminalContent.value = [
      { type: 'out', text: '*** 能力已验证 ***' },
      { type: 'out', text: `综合证据分: ${result.report.total_score}` },
      { type: 'info', text: '代码正确、原理理解和故障修复证据均已成立。' },
    ]
    statStore.refreshAll().catch(() => {})
    ElMessage.success('能力验证完成，已更新学习掌握度')
  } catch (e) {
    terminalContent.value = [{ type: 'err', text: e.message || '修复验证失败' }]
  } finally {
    submitting.value = false
    scrollTerminal()
  }
}

function markVerifiedCompletion(report) {
  try {
    const completed = JSON.parse(localStorage.getItem('code_completed') || '{}')
    const key = `${currentModuleId.value}_${currentTaskId.value}`
    completed[key] = {
      time: `${elapsedSeconds.value}秒`,
      seconds: elapsedSeconds.value,
      verified: true,
      evidenceScore: report.total_score,
      completedAt: new Date().toISOString(),
    }
    localStorage.setItem('code_completed', JSON.stringify(completed))
  } catch (e) { /* local cache is optional */ }
  syncCompletionsFromServer()
}

function openCapabilityReport() {
  capabilityReport.value = capabilitySession.value?.report || capabilityReport.value
  capabilityView.value = 'report'
  showCapabilityDialog.value = true
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
  queueCapabilityEvent('answer_view', { visible: true })
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
.report-nav-btn { color: #dff7ff; border-color: #5a7088; background: transparent; }

/* 能力证据轨道：本页唯一的标志性视觉，像实验仪器的四段读数 */
.evidence-rail {
  min-height: 76px; flex-shrink: 0; display: flex; align-items: stretch;
  background: #101e31; color: #fff; border-top: 1px solid #273b51; border-bottom: 1px solid #263c55;
}
.rail-thesis { width: 290px; padding: 13px 18px; display: flex; flex-direction: column; justify-content: center; border-right: 1px solid #2a3d53; }
.rail-kicker { color: #7fd9f1; font: 600 10px/1.2 'Cascadia Code', Consolas, monospace; letter-spacing: .18em; margin-bottom: 5px; }
.rail-thesis strong { font-size: 14px; line-height: 1.35; color: #f4f8fb; }
.rail-stages { flex: 1; display: grid; grid-template-columns: repeat(4, 1fr); }
.rail-stage { position: relative; padding: 12px 14px; display: flex; align-items: center; gap: 10px; border-right: 1px solid #2a3d53; color: #6f8296; }
.rail-stage::after { content: ''; position: absolute; left: 0; right: 0; bottom: 0; height: 3px; background: transparent; }
.rail-stage.complete { color: #b9f5dc; background: rgba(25, 161, 116, .08); }
.rail-stage.complete::after { background: #37c994; }
.rail-stage.active { color: #fff; background: rgba(74, 177, 227, .12); }
.rail-stage.active::after { background: #55c7f1; box-shadow: 0 -4px 16px rgba(85, 199, 241, .45); }
.stage-index { font: 700 12px/1 'Cascadia Code', Consolas, monospace; color: currentColor; }
.stage-copy { display: flex; flex-direction: column; min-width: 0; }
.stage-copy b { font-size: 13px; font-weight: 650; }
.stage-copy small { margin-top: 3px; font-size: 10px; color: currentColor; opacity: .72; white-space: nowrap; }

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

.repair-brief { margin: 14px 0; padding: 16px; background: #fff8e8; border: 1px solid #efca73; border-left: 4px solid #d49518; border-radius: 7px; }
.repair-brief .repair-label { font: 700 10px/1 'Cascadia Code', Consolas, monospace; letter-spacing: .15em; color: #a06400; text-transform: uppercase; }
.repair-brief h4 { margin: 8px 0 5px; padding: 0; border: 0; font-size: 15px; color: #5c3c00; }
.repair-brief p { margin: 0 0 12px; color: #715721; font-size: 13px; line-height: 1.65; }

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

/* 答辩与报告 */
.dialog-heading { display: flex; flex-direction: column; gap: 5px; }
.dialog-heading span { color: #17263a; font-size: 20px; font-weight: 750; }
.dialog-heading small { color: #6d7b8b; font-size: 12px; font-weight: 400; }
.defense-panel { max-height: 68vh; overflow-y: auto; padding-right: 6px; }
.defense-intro { display: flex; align-items: baseline; gap: 12px; padding: 12px 14px; margin-bottom: 14px; background: #eef8fc; border-left: 3px solid #2badd5; color: #2c5367; }
.defense-intro span { font-size: 12px; }
.defense-question { padding: 16px 0; border-bottom: 1px solid #e7ebf0; }
.question-meta { display: flex; align-items: center; gap: 10px; }
.question-meta span { font: 700 10px/1 'Cascadia Code', Consolas, monospace; color: #147d9e; letter-spacing: .08em; }
.question-meta em { padding: 3px 8px; border-radius: 12px; background: #f0f3f6; color: #627081; font-size: 11px; font-style: normal; }
.defense-question p { margin: 8px 0 10px; color: #26394c; font-size: 14px; line-height: 1.7; }
.question-source { display: block; margin-top: 7px; color: #8b96a3; }
.ai-declaration { margin-top: 18px; padding: 14px; display: flex; justify-content: space-between; align-items: center; background: #f7f8fa; border-radius: 7px; }
.ai-declaration > div { display: flex; flex-direction: column; gap: 4px; color: #26394c; }
.ai-declaration small { color: #8793a0; }
.defense-feedback { margin-top: 14px; padding: 12px; color: #9a5a00; background: #fff5df; border: 1px solid #f0cf8d; border-radius: 6px; }
.dialog-actions { display: flex; justify-content: flex-end; margin-top: 18px; }
.report-verdict { display: flex; align-items: center; gap: 22px; padding: 20px; background: #102136; color: #fff; border-radius: 9px; }
.score-seal { width: 112px; height: 112px; flex: 0 0 112px; border: 2px solid #59d2b1; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; box-shadow: inset 0 0 0 7px rgba(89, 210, 177, .08); }
.score-seal strong { font: 800 38px/1 'Cascadia Code', Consolas, monospace; color: #8ce6ce; }
.score-seal span { margin-top: 6px; font-size: 10px; color: #aac2cf; }
.verified-badge { display: inline-flex; padding: 4px 9px; background: #1f8f71; border-radius: 3px; font-size: 11px; letter-spacing: .08em; }
.report-verdict h3 { max-width: 520px; margin: 10px 0 0; font-size: 16px; line-height: 1.6; font-weight: 550; color: #eef7fa; }
.dimension-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 14px 0; }
.dimension-card { padding: 13px; background: #f7f9fb; border: 1px solid #e2e7ec; border-radius: 7px; display: grid; grid-template-columns: 1fr auto; gap: 9px; }
.dimension-card span { font-size: 11px; color: #677585; }
.dimension-card strong { font: 750 20px/1 'Cascadia Code', Consolas, monospace; color: #173f55; }
.dimension-card :deep(.el-progress) { grid-column: 1 / -1; }
.evidence-ledger { padding: 16px; border: 1px solid #dfe5eb; border-radius: 7px; }
.evidence-ledger h4 { margin: 0 0 10px; color: #20364b; }
.evidence-ledger > div { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed #e2e7eb; font-size: 12px; }
.evidence-ledger > div span { color: #7b8794; }
.evidence-ledger > div b { color: #26394c; font-weight: 600; }
.evidence-ledger p { margin: 10px 0 0; color: #8a96a2; font-size: 11px; }
.next-challenge { margin-top: 12px; padding: 13px 15px; color: #365467; background: #edf7f4; border-left: 3px solid #31a782; font-size: 13px; }
.next-challenge span { margin-right: 10px; color: #187b60; font-weight: 700; }

@media (max-width: 1000px) {
  .rail-thesis { display: none; }
  .stage-copy small { display: none; }
  .dimension-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 720px) {
  .evidence-rail { min-height: 58px; }
  .rail-stage { justify-content: center; padding: 8px 4px; }
  .stage-copy b { font-size: 11px; }
  .stage-index { display: none; }
  .report-verdict { align-items: flex-start; }
  .score-seal { width: 82px; height: 82px; flex-basis: 82px; }
  .score-seal strong { font-size: 28px; }
}
</style>
