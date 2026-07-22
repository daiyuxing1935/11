<template>
  <div class="ide-page" v-loading="loading" element-loading-background="rgba(8, 13, 24, .86)">
    <header class="ide-topbar">
      <div class="brand-area">
        <button class="icon-button" title="返回关卡列表" @click="goBack"><el-icon><ArrowLeft /></el-icon></button>
        <div class="brand-mark">A</div>
        <div class="project-heading">
          <strong>{{ workspace?.project_name || 'Agent Lab' }}</strong>
          <span>{{ course.module || 'Agent 工程实战' }} · {{ course.title || '加载中' }}</span>
        </div>
      </div>
      <div class="top-actions">
        <div class="layout-switcher" role="group" aria-label="工作台布局">
          <button :class="{ active: layoutMode === 'standard' }" title="标准布局：文件、编辑器和编程搭档" @click="setLayout('standard')"><span class="layout-glyph standard"></span></button>
          <button :class="{ active: layoutMode === 'project' }" title="项目布局：只显示资源管理器和代码区域" @click="setLayout('project')"><span class="layout-glyph project"></span></button>
          <button :class="{ active: layoutMode === 'focus' }" title="专注布局：只显示编辑器" @click="setLayout('focus')"><span class="layout-glyph focus"></span></button>
          <button :class="{ active: layoutMode === 'pair' }" title="搭档布局：编辑器和 Agent 双栏" @click="setLayout('pair')"><span class="layout-glyph pair"></span></button>
        </div>
        <button
          class="environment-pill"
          :class="{ ready: workspace?.virtual_env }"
          :disabled="terminalRunning || workspace?.virtual_env"
          :title="workspace?.virtual_env ? '当前项目环境可用' : '点击为当前项目创建 .venv'"
          @click="setupEnvironment"
        >
          <i :class="{ online: workspace?.virtual_env }"></i>
          {{ workspace?.virtual_env ? '.venv 已就绪' : terminalRunning ? '正在创建环境…' : '一键创建环境' }}
        </button>
        <button class="ghost-action" @click="resetProject"><el-icon><RefreshRight /></el-icon> 新建项目</button>
        <button class="primary-action" :disabled="capabilityBusy" @click="handleTopAction">
          <el-icon><CircleCheck /></el-icon>{{ topActionLabel }}
        </button>
      </div>
    </header>

    <main :class="['workbench', `layout-${layoutMode}`]">
      <aside class="activity-bar">
        <button :class="{ active: ['standard', 'project'].includes(layoutMode) && leftMode === 'files' }" title="项目文件" @click="showLeftPanel('files')"><el-icon><FolderOpened /></el-icon></button>
        <button :class="{ active: layoutMode === 'standard' && leftMode === 'guide' }" title="引导教程" @click="showLeftPanel('guide')"><el-icon><Reading /></el-icon></button>
        <button title="运行终端" @click="showTerminal"><el-icon><Monitor /></el-icon></button>
      </aside>

      <aside class="side-panel">
        <template v-if="leftMode === 'files'">
          <div class="panel-title">
            <span>项目资源管理器</span>
            <div>
              <button title="新建文件" @click="createFile()"><el-icon><DocumentAdd /></el-icon></button>
              <button title="新建文件夹" @click="createDirectory()"><el-icon><FolderAdd /></el-icon></button>
              <button title="保存并刷新项目" :disabled="refreshing" @click="refreshWorkspace"><el-icon :class="{ 'is-loading': refreshing }"><Refresh /></el-icon></button>
            </div>
          </div>
          <div class="project-root"><el-icon><ArrowDown /></el-icon><el-icon><FolderOpened /></el-icon><b>{{ workspace?.project_name }}</b></div>
          <div class="file-list">
            <LabFileTree
              :entries="explorerChildren[''] || []"
              :children="explorerChildren"
              :expanded="expandedDirectories"
              :active-path="activePath"
              :dirty-paths="dirtyFiles"
              @activate="entry => entry.is_directory ? toggleExplorerDirectory(entry) : openExplorerFile(entry.path)"
              @contextmenu="openExplorerContextMenu"
            />
            <div v-if="!visibleExplorerEntries.length" class="empty-files">点击右上角 + 创建第一个文件</div>
          </div>
          <div class="explorer-hint">每题一个 .venv · 右键管理文件 · Ctrl+S 保存</div>
        </template>

        <template v-else>
          <div class="panel-title"><span>项目引导</span><em>{{ completedStages.length }}/{{ stages.length }}</em></div>
          <div class="lesson-intro">
            <span>{{ course.framework }}</span>
            <h3>{{ course.title }}</h3>
            <p>{{ course.description }}</p>
          </div>
          <div class="stage-list">
            <article
              v-for="(stage, index) in stages"
              :key="stage.id"
              :class="['stage-card', { open: currentStage === stage.id, done: completedStages.includes(stage.id) }]"
            >
              <button class="stage-heading" @click="currentStage = currentStage === stage.id ? '' : stage.id">
                <span class="stage-number">{{ completedStages.includes(stage.id) ? '✓' : index + 1 }}</span>
                <span><b>{{ stage.title }}</b><small>{{ stage.checks.join(' · ') }}</small></span>
                <el-icon><ArrowDown /></el-icon>
              </button>
              <div v-if="currentStage === stage.id" class="stage-body">
                <p>{{ stage.instruction }}</p>
                <div v-if="stage.command" class="command-chip">
                  <code>{{ stage.command }}</code>
                  <button @click="sendStageCommand(stage.command)">运行</button>
                </div>
                <button v-if="stage.id === 'implementation'" class="outline-button full" @click="insertStarter">插入本关函数骨架</button>
                <button class="check-button" :disabled="checkingStage === stage.id" @click="checkStage(stage)">
                  <el-icon v-if="checkingStage === stage.id" class="is-loading"><Loading /></el-icon>
                  <el-icon v-else><MagicStick /></el-icon>{{ stage.id === 'implementation' ? `运行 ${stage.test_count || ''} 个测试点` : 'AI 检查本阶段' }}
                </button>
                <div v-if="stageResults[stage.id]" :class="['check-result', { passed: stageResults[stage.id].passed }]">
                  <div v-for="item in stageResults[stage.id].checks" :key="item.label" class="check-result-item">
                    <span>{{ item.passed ? '✓' : '!' }}</span><p><b>{{ item.label }}</b><small>{{ item.detail }}</small></p>
                    <ul v-if="item.cases?.length" class="test-case-list">
                      <li v-for="testCase in item.cases" :key="testCase.label" :class="{ passed: testCase.passed }">
                        <span>{{ testCase.passed ? '✓' : '×' }}</span>
                        <p><b>{{ testCase.label }}</b><small>{{ testCase.detail }}</small></p>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </template>
      </aside>

      <section class="editor-column">
        <div class="editor-tabs">
          <button
            v-for="path in openTabs"
            :key="path"
            :class="{ active: path === activePath }"
            @click="openFile(path)"
          >
            <span :class="['tab-dot', fileKind(path)]"></span>{{ path.split('/').pop() }}
            <i v-if="dirtyFiles.has(path)">●</i>
            <el-icon class="tab-close" @click.stop="closeTab(path)"><Close /></el-icon>
          </button>
          <div class="editor-spacer"></div>
          <button class="save-button" :disabled="!activePath" @click="saveActiveFile"><el-icon><DocumentChecked /></el-icon>保存</button>
        </div>
        <div v-show="activePath" ref="editorRef" class="monaco-host"></div>
        <div v-if="!activePath" class="welcome-editor">
          <div class="welcome-logo">A</div>
          <h2>开始搭建你的 Agent 项目</h2>
          <p>从左侧创建文件，或打开“项目引导”逐步完成环境、依赖与代码。</p>
          <button class="primary-action" @click="leftMode = 'guide'">打开项目引导</button>
        </div>

        <section class="terminal-panel">
          <div class="terminal-tabs">
            <button class="active"><el-icon><Monitor /></el-icon>终端</button>
            <span :class="{ running: terminalRunning }">{{ terminalRunning ? `● 正在执行 ${terminalElapsed}s` : '项目终端 · 实时输出 · 可选中复制' }}</span>
            <button v-if="terminalRunning" class="stop-terminal" title="停止当前命令" @click="stopTerminal">■ 停止</button>
            <button title="清空终端" @click="terminalLines = []"><el-icon><Delete /></el-icon></button>
          </div>
          <div ref="terminalOutputRef" class="terminal-output" @click="handleTerminalOutputClick">
            <div class="terminal-welcome">Agent Lab Terminal · 支持常用命令、管道、重定向与虚拟环境</div>
            <div v-for="(line, index) in terminalLines" :key="index" :class="['terminal-line', line.type]">
              <template v-if="line.type === 'command'"><span v-if="line.activeEnv" class="prompt-env">({{ line.activeEnv.split('/').pop() }})</span><span class="prompt-symbol">➜</span></template><pre>{{ line.text }}</pre>
            </div>
            <div class="terminal-input-row">
              <span v-if="terminalActiveEnv" class="prompt-env">({{ terminalActiveEnv.split('/').pop() }})</span><span class="prompt-symbol">➜</span><span class="prompt-path">~/{{ workspace?.project_name }}{{ terminalCwd ? `/${terminalCwd}` : '' }}</span>
              <input
                ref="terminalInputRef"
                v-model="terminalCommand"
                :disabled="terminalRunning"
                autocomplete="off"
                spellcheck="false"
                @keydown="handleTerminalKeydown"
              />
              <el-icon v-if="terminalRunning" class="is-loading"><Loading /></el-icon>
            </div>
          </div>
        </section>
      </section>

      <aside class="agent-panel">
        <div class="agent-header">
          <div class="agent-avatar"><el-icon><MagicStick /></el-icon></div>
          <div><b>{{ assistantMode === 'agent' ? 'Agent 编程搭档' : 'Chat 编程问答' }}</b><span><i></i>{{ assistantMode === 'agent' ? '正在查看你的项目' : '只回答，不改动项目' }}</span></div>
          <button title="清空对话" @click="resetChat"><el-icon><Delete /></el-icon></button>
        </div>
        <div ref="chatRef" class="chat-list" @click="handleAgentBlockAction">
          <div v-for="(message, index) in chatMessages" :key="index" :class="['chat-message', message.role]">
            <div v-if="message.role === 'assistant'" class="mini-avatar">A</div>
            <div class="message-bubble">
              <div v-if="message.role === 'assistant'" class="assistant-markdown" v-html="renderAssistantMarkdown(message.content)"></div>
              <div v-else>{{ message.content }}</div>
              <small v-if="message.notice">{{ message.notice }}</small>
            </div>
          </div>
          <div v-if="assistantLoading" class="chat-message assistant"><div class="mini-avatar">A</div><div class="message-bubble typing"><i></i><i></i><i></i></div></div>
        </div>
        <div class="quick-prompts">
          <button @click="askQuick('检查我当前的项目结构，告诉我下一步做什么')">检查项目</button>
          <button @click="askQuick('解释当前文件中 LangChain 或 LangGraph 导入的类和函数作用')">解释框架代码</button>
          <button @click="askQuick('根据当前错误帮我定位，但先不要给完整答案')">定位错误</button>
        </div>
        <div class="agent-composer">
          <div class="assistant-mode-switch" role="group" aria-label="编程搭档模式">
            <button :class="{ active: assistantMode === 'chat' }" title="仅问答，不读取整个项目" @click="assistantMode = 'chat'">Chat</button>
            <button :class="{ active: assistantMode === 'agent' }" title="结合当前项目进行分析" @click="assistantMode = 'agent'">Agent</button>
          </div>
          <textarea v-model="assistantQuestion" rows="3" placeholder="问项目、依赖、报错或框架 API…" @keydown.ctrl.enter.prevent="sendAssistant"></textarea>
          <div><span>Ctrl + Enter 发送 · 代码与命令需手动填入</span><button :disabled="assistantLoading || !assistantQuestion.trim()" @click="sendAssistant"><el-icon><Promotion /></el-icon></button></div>
        </div>
      </aside>
    </main>

    <div
      v-if="explorerMenu.visible"
      class="explorer-context-menu"
      :style="{ left: `${explorerMenu.x}px`, top: `${explorerMenu.y}px` }"
      @click.stop
    >
      <button v-if="!explorerMenu.entry?.is_directory" @click="contextOpen"><span>打开</span><kbd>Enter</kbd></button>
      <button v-if="explorerMenu.entry?.is_directory" @click="contextNewFile"><span>新建文件…</span><kbd>Ctrl+N</kbd></button>
      <button v-if="explorerMenu.entry?.is_directory" @click="contextNewDirectory"><span>新建文件夹…</span></button>
      <div class="menu-separator"></div>
      <button @click="contextOpenInTerminal"><span>在集成终端中打开</span></button>
      <button v-if="isPythonEntry(explorerMenu.entry)" @click="contextRunPython"><span>运行 Python 文件</span><kbd>Ctrl+F5</kbd></button>
      <div class="menu-separator"></div>
      <button @click="contextCopy"><span>复制</span><kbd>Ctrl+C</kbd></button>
      <button @click="contextCopyPath(false)"><span>复制路径</span><kbd>Shift+Alt+C</kbd></button>
      <button @click="contextCopyPath(true)"><span>复制相对路径</span></button>
      <button :disabled="explorerMenu.entry?.path === '.venv'" @click="contextDuplicate"><span>创建副本…</span></button>
      <div class="menu-separator"></div>
      <button :disabled="explorerMenu.entry?.path === '.venv'" @click="contextRename"><span>重命名…</span><kbd>F2</kbd></button>
      <button class="danger" :disabled="explorerMenu.entry?.path === '.venv'" @click="contextDelete"><span>删除</span><kbd>Delete</kbd></button>
    </div>

    <el-dialog v-model="defenseDialog" width="760px" class="dark-dialog" :close-on-click-modal="false">
      <template #header><div class="dialog-title"><span>功能验收通过</span><b>继续完成原理答辩</b></div></template>
      <div v-if="capabilityStatus === 'defense_pending'" class="defense-form">
        <p>请结合你刚写的项目回答。重点说明框架接口的作用，不考查基础 Python 语法。</p>
        <label v-for="(question, index) in defenseQuestions" :key="question.id">
          <span>{{ index + 1 }}. {{ question.prompt }}</span>
          <el-input v-model="defenseAnswers[question.id]" type="textarea" :rows="3" placeholder="结合具体函数、文件或调用流程回答" />
        </label>
        <button class="primary-action dialog-submit" :disabled="capabilityBusy" @click="submitDefenseAnswers">提交答辩</button>
      </div>
      <div v-else-if="capabilityStatus === 'repair_pending'" class="repair-form">
        <h3>故障已经写入 solution.py</h3>
        <p>{{ capabilitySession?.mutation_description }}</p>
        <p>请回到编辑器运行并修复，然后在这里说明根因。</p>
        <el-input v-model="repairExplanation" type="textarea" :rows="4" placeholder="至少20字：故障根因是什么，你修改了哪里？" />
        <button class="primary-action dialog-submit" @click="defenseDialog = false">回到编辑器修复</button>
      </div>
      <div v-else class="verified-report">
        <div class="score-ring">{{ capabilitySession?.report?.total_score || 100 }}</div>
        <h2>能力验证完成</h2><p>{{ capabilitySession?.report?.summary || '项目、理解与故障修复证据均已成立。' }}</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as monaco from 'monaco-editor'
import {
  askLabAssistant, checkLabStage, createLabDirectory, deleteLabEntry, duplicateLabEntry,
  getLabWorkspace, listLabEntries, moveLabEntry, readLabFile, saveLabFile, streamLabTerminal,
} from '../api/workspace'
import { bindCodeBlockActions, renderMarkdown } from '../composables/useCodeBlockRenderer'
import LabFileTree from '../components/LabFileTree.vue'
import {
  markCapabilityCodePassed, startCapabilitySession,
  submitCapabilityDefense, submitCapabilityRepair,
} from '../api/capability'

const route = useRoute()
const router = useRouter()
const exerciseId = computed(() => String(route.params.taskId || '1-1'))
const moduleId = computed(() => String(route.params.moduleId || '1'))
const loading = ref(true)
const refreshing = ref(false)
const workspace = ref(null)
const course = computed(() => workspace.value?.course || {})
const stages = computed(() => course.value.stages || [])
const files = ref([])
const directories = ref([])
const completedStages = ref([])
const currentStage = ref('structure')
const stageResults = reactive({})
const checkingStage = ref('')
const leftMode = ref('files')
const layoutMode = ref(['standard', 'project', 'focus', 'pair'].includes(localStorage.getItem('lab_layout')) ? localStorage.getItem('lab_layout') : 'standard')

const editorRef = ref(null)
let editor = null
const models = new Map()
const activePath = ref('')
const openTabs = ref([])
const dirtyFiles = reactive(new Set())

const terminalCommand = ref('')
const terminalLines = ref([])
const terminalRunning = ref(false)
const terminalInputRef = ref(null)
const terminalOutputRef = ref(null)
const terminalHistory = ref([])
const terminalHistoryIndex = ref(-1)
const terminalActiveEnv = ref('')
const terminalCwd = ref('')
const terminalElapsed = ref(0)
let terminalTimer = null
let terminalAbortController = null
const explorerChildren = reactive({})
const expandedDirectories = reactive(new Set())
const explorerMenu = reactive({ visible: false, x: 0, y: 0, entry: null })

const assistantQuestion = ref('')
const assistantLoading = ref(false)
const chatRef = ref(null)
const chatMessages = ref([])
const assistantMode = ref(localStorage.getItem('lab_assistant_mode') === 'chat' ? 'chat' : 'agent')

const capabilitySession = ref(null)
const capabilityBusy = ref(false)
const defenseDialog = ref(false)
const defenseAnswers = reactive({})
const repairExplanation = ref('')
const capabilityStatus = computed(() => capabilitySession.value?.status || 'coding')
const defenseQuestions = computed(() => capabilitySession.value?.defense_questions || [])
const acceptancePassed = computed(() => completedStages.value.includes('acceptance'))
const visibleExplorerEntries = computed(() => {
  const result = []
  const visit = (parent, depth) => {
    for (const entry of explorerChildren[parent] || []) {
      result.push({ ...entry, depth })
      if (entry.is_directory && expandedDirectories.has(entry.path)) visit(entry.path, depth + 1)
    }
  }
  visit('', 0)
  return result
})
const topActionLabel = computed(() => {
  if (capabilityStatus.value === 'verified') return '查看能力报告'
  if (capabilityStatus.value === 'repair_pending') return '提交故障修复'
  if (capabilityStatus.value === 'defense_pending') return '继续原理答辩'
  return acceptancePassed.value ? '进入能力验证' : 'AI 验收项目'
})

function languageFor(path) {
  if (path.endsWith('.py')) return 'python'
  if (path.endsWith('.json')) return 'json'
  if (path.endsWith('.md')) return 'markdown'
  if (path.endsWith('.yml') || path.endsWith('.yaml')) return 'yaml'
  if (path.endsWith('.env') || path.endsWith('.txt') || path.includes('requirements')) return 'plaintext'
  return 'plaintext'
}

function fileKind(path) {
  if (path.endsWith('.py')) return 'python'
  if (path.endsWith('.md')) return 'markdown'
  if (path.includes('.env')) return 'env'
  if (path.endsWith('.json')) return 'json'
  return 'text'
}

function fileLabel(path) {
  const kind = fileKind(path)
  return { python: 'Py', markdown: 'M↓', env: '⚙', json: '{}', text: '≡' }[kind]
}

watch(assistantMode, value => localStorage.setItem('lab_assistant_mode', value))

function setLayout(mode) {
  if (mode === 'project') leftMode.value = 'files'
  layoutMode.value = mode
  localStorage.setItem('lab_layout', mode)
  nextTick(() => editor?.layout())
}

function showLeftPanel(mode) {
  leftMode.value = mode
  if (mode === 'guide' || !['standard', 'project'].includes(layoutMode.value)) setLayout('standard')
}

function showTerminal() {
  if (layoutMode.value === 'focus') setLayout('standard')
  focusTerminal()
}

function createEditor() {
  if (editor || !editorRef.value) return
  editor = monaco.editor.create(editorRef.value, {
    theme: 'vs-dark', automaticLayout: true, fontSize: 15, lineHeight: 24,
    fontFamily: "'JetBrains Mono', 'Cascadia Code', Consolas, monospace",
    minimap: { enabled: true, scale: 0.8 }, padding: { top: 16, bottom: 16 },
    smoothScrolling: true, cursorSmoothCaretAnimation: 'on', wordWrap: 'off',
    renderWhitespace: 'selection', bracketPairColorization: { enabled: true },
    guides: { bracketPairs: true, indentation: true }, scrollBeyondLastLine: false,
  })
  editor.onDidChangeModelContent(() => {
    if (activePath.value) dirtyFiles.add(activePath.value)
  })
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, saveActiveFile)
}

function disposeModels() {
  models.forEach(model => model.dispose())
  models.clear()
}

function syncFiles(payload) {
  files.value = payload.files || []
  directories.value = payload.directories || []
  completedStages.value = payload.completed_stages || []
  terminalActiveEnv.value = payload.active_env || ''
  terminalCwd.value = payload.terminal_cwd || ''
  disposeModels()
  for (const file of files.value) {
    const uri = monaco.Uri.parse(`inmemory://agent-lab/${exerciseId.value}/${file.path}`)
    models.set(file.path, monaco.editor.createModel(file.content, languageFor(file.path), uri))
  }
  dirtyFiles.clear()
}

async function loadExplorerDirectory(path = '', force = false) {
  if (!force && explorerChildren[path]) return
  const payload = await listLabEntries(exerciseId.value, path)
  explorerChildren[path] = payload.entries || []
}

async function resetExplorer() {
  Object.keys(explorerChildren).forEach(key => delete explorerChildren[key])
  expandedDirectories.clear()
  await loadExplorerDirectory('', true)
}

async function toggleExplorerDirectory(entry) {
  if (expandedDirectories.has(entry.path)) {
    expandedDirectories.delete(entry.path)
    return
  }
  try {
    await loadExplorerDirectory(entry.path)
    expandedDirectories.add(entry.path)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '文件夹无法打开')
  }
}

async function openExplorerFile(path) {
  if (!models.has(path)) {
    try {
      const file = await readLabFile(exerciseId.value, path)
      if (file.binary) return ElMessage.info(file.message || '该文件无法作为文本预览')
      files.value.push({ path, content: file.content })
      const uri = monaco.Uri.parse(`inmemory://agent-lab/${exerciseId.value}/${path}`)
      models.set(path, monaco.editor.createModel(file.content, languageFor(path), uri))
    } catch (error) {
      return ElMessage.error(error.response?.data?.detail || '文件读取失败')
    }
  }
  openFile(path)
}

async function loadWorkspace(reset = false) {
  loading.value = true
  try {
    const payload = await getLabWorkspace(exerciseId.value, reset)
    workspace.value = payload
    syncFiles(payload)
    if (payload.removed_virtual_envs?.length) {
      terminalLines.value.push({ type: 'output', text: `每道题只保留一个 .venv，已清理重复环境：${payload.removed_virtual_envs.join('、')}` })
    }
    await resetExplorer()
    const preferred = files.value.find(file => file.path === activePath.value)
      || files.value.find(file => file.path.endsWith('.py')) || files.value[0]
    if (preferred) openFile(preferred.path)
    if (!chatMessages.value.length) resetChat()
    return true
  } catch (error) {
    const detail = error.response?.data?.detail || error.message || '工作区加载失败'
    terminalLines.value.push({ type: 'error', text: `工作区刷新失败：${detail}` })
    return false
  } finally {
    loading.value = false
  }
}

async function refreshWorkspace() {
  if (refreshing.value) return
  refreshing.value = true
  try {
    await saveAll()
    const refreshed = await loadWorkspace(false)
    if (refreshed) ElMessage.success('项目已刷新')
  } finally {
    refreshing.value = false
  }
}

function openFile(path) {
  const model = models.get(path)
  if (!model || !editor) return
  activePath.value = path
  if (!openTabs.value.includes(path)) openTabs.value.push(path)
  editor.setModel(model)
  editor.focus()
}

function closeTab(path) {
  const index = openTabs.value.indexOf(path)
  openTabs.value = openTabs.value.filter(item => item !== path)
  if (path === activePath.value) {
    const next = openTabs.value[Math.max(0, index - 1)] || ''
    activePath.value = ''
    editor?.setModel(null)
    if (next) openFile(next)
  }
}

async function saveActiveFile(silent = false) {
  if (!activePath.value || !models.get(activePath.value)) return
  await saveLabFile(exerciseId.value, activePath.value, models.get(activePath.value).getValue())
  dirtyFiles.delete(activePath.value)
  const item = files.value.find(file => file.path === activePath.value)
  if (item) item.content = models.get(activePath.value).getValue()
  if (!silent) ElMessage.success(`${activePath.value} 已保存`)
}

async function saveAll() {
  for (const path of [...dirtyFiles]) {
    const model = models.get(path)
    if (model) await saveLabFile(exerciseId.value, path, model.getValue())
    dirtyFiles.delete(path)
  }
}

function parentPath(path = '') {
  return path.includes('/') ? path.slice(0, path.lastIndexOf('/')) : ''
}

function joinProjectPath(parent, name) {
  return [parent, name].filter(Boolean).join('/')
}

async function createFile(basePath = '') {
  try {
    const { value } = await ElMessageBox.prompt(basePath ? `在 ${basePath} 中创建文件。` : '文件将创建在项目内，也可以输入 src/tools.py 这样的子路径。', '新建文件', {
      confirmButtonText: '创建', cancelButtonText: '取消', inputPlaceholder: '例如：solution.py',
      inputPattern: /^(?!\/)(?!.*\.\.)(?!.*[<>:"|?*])[\w.\-/]+$/,
      inputErrorMessage: '请输入安全的项目相对路径',
    })
    const path = joinProjectPath(basePath, value)
    if (files.value.some(file => file.path === path)) return ElMessage.warning('该文件已经存在')
    await saveLabFile(exerciseId.value, path, '')
    const file = { path, content: '' }
    files.value.push(file)
    files.value.sort((a, b) => a.path.localeCompare(b.path))
    const uri = monaco.Uri.parse(`inmemory://agent-lab/${exerciseId.value}/${path}`)
    models.set(path, monaco.editor.createModel('', languageFor(path), uri))
    const parent = parentPath(path)
    await loadExplorerDirectory(parent, true)
    if (parent) expandedDirectories.add(parent)
    openFile(path)
  } catch (error) {
    if (error !== 'cancel' && error !== 'close' && error?.message) console.warn(error)
  }
}

async function createDirectory(basePath = '') {
  try {
    const { value } = await ElMessageBox.prompt(basePath ? `在 ${basePath} 中创建文件夹。` : '文件夹将创建在当前项目内，也可以输入 src/services 这样的多级路径。', '新建文件夹', {
      confirmButtonText: '创建', cancelButtonText: '取消', inputPlaceholder: '例如：src/tools',
      inputPattern: /^(?!\/)(?!.*\.\.)(?!.*[<>:"|?*])[\w\-/]+$/,
      inputErrorMessage: '请输入安全的项目相对路径',
    })
    const path = joinProjectPath(basePath, value)
    await createLabDirectory(exerciseId.value, path)
    const parent = parentPath(path)
    await loadExplorerDirectory(parent, true)
    if (parent) expandedDirectories.add(parent)
    ElMessage.success(`文件夹 ${path} 已创建`)
  } catch (error) {
    if (error !== 'cancel' && error !== 'close' && error?.message) console.warn(error)
  }
}

async function refreshAfterEntryMutation(preferredPath = '') {
  activePath.value = ''
  openTabs.value = []
  editor?.setModel(null)
  await loadWorkspace(false)
  if (preferredPath) await openExplorerFile(preferredPath)
}

async function removeEntry(entry) {
  if (!entry?.path) return
  try {
    await ElMessageBox.confirm(`确定删除 ${entry.path}？${entry.is_directory ? '文件夹中的内容也会一并删除。' : ''}此操作不可恢复。`, '删除', { type: 'warning' })
    await deleteLabEntry(exerciseId.value, entry.path)
    await refreshAfterEntryMutation()
  } catch (_) { /* cancelled */ }
}

function closeExplorerMenu() { explorerMenu.visible = false }

function openExplorerContextMenu(event, entry) {
  const width = 260
  const height = entry.is_directory ? 390 : 410
  explorerMenu.entry = entry
  explorerMenu.x = Math.min(event.clientX, window.innerWidth - width - 8)
  explorerMenu.y = Math.min(event.clientY, window.innerHeight - height - 8)
  explorerMenu.visible = true
}

function takeContextEntry() {
  const entry = explorerMenu.entry ? { ...explorerMenu.entry } : null
  closeExplorerMenu()
  return entry
}

function isPythonEntry(entry) { return Boolean(entry && !entry.is_directory && entry.path.toLowerCase().endsWith('.py')) }

async function contextOpen() {
  const entry = takeContextEntry()
  if (entry) await openExplorerFile(entry.path)
}

async function contextNewFile() {
  const entry = takeContextEntry()
  if (entry?.is_directory) await createFile(entry.path)
}

async function contextNewDirectory() {
  const entry = takeContextEntry()
  if (entry?.is_directory) await createDirectory(entry.path)
}

async function copyText(value, message) {
  await navigator.clipboard.writeText(value)
  ElMessage.success(message)
}

async function contextCopy() {
  const entry = takeContextEntry()
  if (!entry) return
  if (entry.is_directory) return copyText(entry.path, '文件夹路径已复制')
  const file = await readLabFile(exerciseId.value, entry.path)
  if (file.binary) return ElMessage.info('二进制文件不能复制为文本')
  await copyText(file.content, '文件内容已复制')
}

async function contextCopyPath(relative) {
  const entry = takeContextEntry()
  if (!entry) return
  const value = relative ? entry.path : `/${workspace.value?.project_name || 'agent-lab'}/${entry.path}`
  await copyText(value, relative ? '相对路径已复制' : '项目路径已复制')
}

function defaultCopyName(entry) {
  const name = entry.name
  if (entry.is_directory || !name.includes('.')) return `${name}-copy`
  const dot = name.lastIndexOf('.')
  return `${name.slice(0, dot)}-copy${name.slice(dot)}`
}

async function contextDuplicate() {
  const entry = takeContextEntry()
  if (!entry || entry.path === '.venv') return
  try {
    const parent = parentPath(entry.path)
    const { value } = await ElMessageBox.prompt('输入副本名称。', '创建副本', {
      confirmButtonText: '复制', cancelButtonText: '取消', inputValue: defaultCopyName(entry),
      inputPattern: /^(?!\.?\.?$)(?!.*[\\/<>:"|?*])[^\\/<>:"|?*]+$/,
      inputErrorMessage: '请输入有效名称',
    })
    const destination = joinProjectPath(parent, value)
    await duplicateLabEntry(exerciseId.value, entry.path, destination)
    await refreshAfterEntryMutation(entry.is_directory ? '' : destination)
  } catch (_) { /* cancelled */ }
}

async function contextRename() {
  const entry = takeContextEntry()
  if (!entry || entry.path === '.venv') return
  try {
    await saveAll()
    const parent = parentPath(entry.path)
    const { value } = await ElMessageBox.prompt('输入新名称。', '重命名', {
      confirmButtonText: '重命名', cancelButtonText: '取消', inputValue: entry.name,
      inputPattern: /^(?!\.?\.?$)(?!.*[\\/<>:"|?*])[^\\/<>:"|?*]+$/,
      inputErrorMessage: '请输入有效名称',
    })
    const destination = joinProjectPath(parent, value)
    if (destination === entry.path) return
    await moveLabEntry(exerciseId.value, entry.path, destination)
    await refreshAfterEntryMutation(entry.is_directory ? '' : destination)
  } catch (_) { /* cancelled */ }
}

async function contextDelete() {
  const entry = takeContextEntry()
  if (entry?.path !== '.venv') await removeEntry(entry)
}

function shellQuote(value) { return `'${String(value).replaceAll("'", "'\\''")}'` }

async function moveTerminalToProjectPath(path) {
  await executeTerminal('cd')
  if (path) await executeTerminal(`cd ${shellQuote(path)}`)
}

async function contextOpenInTerminal() {
  const entry = takeContextEntry()
  if (!entry) return
  showTerminal()
  const directory = entry.is_directory ? entry.path : parentPath(entry.path)
  await moveTerminalToProjectPath(directory)
}

async function contextRunPython() {
  const entry = takeContextEntry()
  if (!isPythonEntry(entry)) return
  showTerminal()
  await moveTerminalToProjectPath('')
  await executeTerminal(`python ${shellQuote(entry.path)}`)
}

async function resetProject() {
  try {
    await ElMessageBox.confirm('这会清空本关工作区并重新创建教学项目，现有文件无法恢复。', '新建项目', { type: 'warning', confirmButtonText: '重新创建' })
    activePath.value = ''
    openTabs.value = []
    terminalLines.value = []
    Object.keys(stageResults).forEach(key => delete stageResults[key])
    await loadWorkspace(true)
  } catch (_) { /* cancelled */ }
}

async function insertStarter() {
  const existing = models.get('solution.py')
  if (existing?.getValue().trim()) {
    try { await ElMessageBox.confirm('solution.py 已有内容，是否用本关函数骨架覆盖？', '插入骨架', { type: 'warning' }) }
    catch (_) { return }
  }
  await saveLabFile(exerciseId.value, 'solution.py', course.value.starter_code || '')
  if (existing) existing.setValue(course.value.starter_code || '')
  else {
    files.value.push({ path: 'solution.py', content: course.value.starter_code || '' })
    const uri = monaco.Uri.parse(`inmemory://agent-lab/${exerciseId.value}/solution.py`)
    models.set('solution.py', monaco.editor.createModel(course.value.starter_code || '', 'python', uri))
  }
  dirtyFiles.delete('solution.py')
  openFile('solution.py')
}

async function checkStage(stage) {
  checkingStage.value = stage.id
  try {
    await saveAll()
    const result = await checkLabStage(exerciseId.value, stage.id)
    stageResults[stage.id] = result
    completedStages.value = result.completed_stages || []
    ElMessage[result.passed ? 'success' : 'warning'](result.summary)
    if (result.passed) {
      const index = stages.value.findIndex(item => item.id === stage.id)
      if (stages.value[index + 1]) currentStage.value = stages.value[index + 1].id
    }
  } finally { checkingStage.value = '' }
}

async function executeTerminal(forcedCommand = '') {
  const command = (forcedCommand || terminalCommand.value).trim()
  if (!command || terminalRunning.value) return
  terminalCommand.value = ''
  if (terminalHistory.value.at(-1) !== command) terminalHistory.value.push(command)
  terminalHistory.value = terminalHistory.value.slice(-80)
  terminalHistoryIndex.value = terminalHistory.value.length
  terminalLines.value.push({ type: 'command', text: command, activeEnv: terminalActiveEnv.value, cwd: terminalCwd.value })
  terminalRunning.value = true
  terminalElapsed.value = 0
  const startedAt = Date.now()
  terminalTimer = window.setInterval(() => { terminalElapsed.value = Math.floor((Date.now() - startedAt) / 1000) }, 1000)
  terminalAbortController = new AbortController()
  scrollTerminal()
  let liveLine = null
  let result = null
  try {
    await saveAll()
    result = await streamLabTerminal(exerciseId.value, command, event => {
      if (event.type === 'output') {
        if (!liveLine) {
          liveLine = { type: 'output', text: '' }
          terminalLines.value.push(liveLine)
        }
        liveLine.text += event.data || ''
        scrollTerminal()
      } else if (event.type === 'clear') {
        terminalLines.value = []
        liveLine = null
      }
    }, terminalAbortController.signal)
    terminalActiveEnv.value = result.active_env || ''
    terminalCwd.value = result.cwd || ''
    if (liveLine) liveLine.type = result.exit_code === 0 ? 'output' : 'error'
    else if (result.output !== '__CLEAR__') terminalLines.value.push({ type: result.exit_code === 0 ? 'status' : 'error', text: result.exit_code === 0 ? `✓ 执行完成（${terminalElapsed.value}s）` : `命令退出，状态码 ${result.exit_code}` })
    if (result.exit_code === 0) {
      const payload = await getLabWorkspace(exerciseId.value, false)
      workspace.value = { ...workspace.value, ...payload }
      await loadExplorerDirectory('', true)
      for (const path of [...expandedDirectories]) await loadExplorerDirectory(path, true)
    }
  } catch (error) {
    const stopped = error.name === 'AbortError'
    terminalLines.value.push({ type: stopped ? 'status' : 'error', text: stopped ? '■ 命令已停止' : (error.response?.data?.detail || error.message) })
  } finally {
    if (terminalTimer) window.clearInterval(terminalTimer)
    terminalTimer = null
    terminalAbortController = null
    terminalRunning.value = false
    scrollTerminal()
    nextTick(focusTerminal)
  }
  return result
}

function stopTerminal() { terminalAbortController?.abort() }

function handleTerminalKeydown(event) {
  if (event.key === 'Enter') {
    event.preventDefault()
    executeTerminal()
    return
  }
  if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
    if (!terminalHistory.value.length) return
    event.preventDefault()
    const delta = event.key === 'ArrowUp' ? -1 : 1
    terminalHistoryIndex.value = Math.max(0, Math.min(terminalHistory.value.length, terminalHistoryIndex.value + delta))
    terminalCommand.value = terminalHistoryIndex.value === terminalHistory.value.length ? '' : terminalHistory.value[terminalHistoryIndex.value]
    nextTick(() => terminalInputRef.value?.setSelectionRange(terminalCommand.value.length, terminalCommand.value.length))
    return
  }
  if (event.key !== 'Tab') return
  event.preventDefault()
  const value = terminalCommand.value
  const commandCandidates = [
    'ls', 'tree', 'pwd', 'cd', 'clear', 'python --version', 'python -m venv .venv',
    'source .venv/bin/activate', 'deactivate', 'pip install', 'pip install -r requirements.txt',
    'python -m py_compile solution.py', 'python solution.py', 'pytest', 'git status',
  ]
  const lastToken = value.split(/\s+/).pop() || ''
  const pathCandidates = [
    ...visibleExplorerEntries.value.map(item => `${item.path}${item.is_directory ? '/' : ''}`),
  ]
  const matches = value.includes(' ')
    ? pathCandidates.filter(item => item.toLowerCase().startsWith(lastToken.toLowerCase()))
    : commandCandidates.filter(item => item.toLowerCase().startsWith(value.toLowerCase()))
  if (!matches.length) return
  if (value.includes(' ')) terminalCommand.value = `${value.slice(0, value.length - lastToken.length)}${matches[0]}`
  else terminalCommand.value = matches[0]
}

function sendStageCommand(command) {
  terminalCommand.value = command
  executeTerminal(command)
}

function setupEnvironment() {
  if (workspace.value?.virtual_env || terminalRunning.value) return
  leftMode.value = 'guide'
  currentStage.value = 'environment'
  executeTerminal('python -m venv .venv')
}

function focusTerminal() { nextTick(() => terminalInputRef.value?.focus()) }
function handleTerminalOutputClick() {
  if (window.getSelection?.().toString()) return
  focusTerminal()
}
function scrollTerminal() { nextTick(() => { if (terminalOutputRef.value) terminalOutputRef.value.scrollTop = terminalOutputRef.value.scrollHeight }) }
function scrollChat() { nextTick(() => { if (chatRef.value) chatRef.value.scrollTop = chatRef.value.scrollHeight }) }

function renderAssistantMarkdown(content) {
  const terminalLanguages = new Set(['bash', 'sh', 'shell', 'zsh', 'cmd', 'bat', 'powershell', 'terminal', 'console'])
  return renderMarkdown(content).replace(
    /(<div class="code-block-wrapper">[\s\S]*?<span class="code-lang-tag">([^<]*)<\/span>[\s\S]*?<div class="code-toolbar-actions">)/g,
    (_match, toolbar, language) => `${toolbar}<button class="code-toolbar-btn" data-action="${terminalLanguages.has(language.toLowerCase()) ? 'fill-terminal' : 'insert-editor'}">${terminalLanguages.has(language.toLowerCase()) ? '填入终端' : '插入编辑器'}</button>`,
  )
}

function handleAgentBlockAction(event) {
  const button = event.target.closest?.('[data-action="insert-editor"], [data-action="fill-terminal"]')
  if (!button) return
  const code = button.closest('.code-block-wrapper')?.querySelector('code')?.textContent || ''
  if (!code.trim()) return
  if (button.dataset.action === 'fill-terminal') {
    const command = code.split(/\r?\n/).map(line => line.trim()).find(line => line && !line.startsWith('#'))?.replace(/^[$>]\s*/, '') || ''
    terminalCommand.value = command
    showTerminal()
    ElMessage.success('命令已填入终端，确认后按 Enter 执行')
    return
  }
  if (!editor || !activePath.value) return ElMessage.warning('请先打开要插入代码的文件')
  const selection = editor.getSelection()
  editor.executeEdits('agent-manual-insert', [{ range: selection, text: code, forceMoveMarkers: true }])
  editor.focus()
  ElMessage.success(`代码已插入 ${activePath.value}，尚未自动保存`)
}

function resetChat() {
  chatMessages.value = [{
    role: 'assistant',
    content: `你好，我是这次 ${course.value.framework || 'Agent'} 项目的编程搭档。我会结合整个项目回答，重点解释框架包、类、函数和工程作用，不重复讲基础 Python 语法。`,
  }]
}

function askQuick(text) { assistantQuestion.value = text; sendAssistant() }

async function sendAssistant() {
  const question = assistantQuestion.value.trim()
  if (!question || assistantLoading.value) return
  chatMessages.value.push({ role: 'user', content: question })
  assistantQuestion.value = ''
  assistantLoading.value = true
  scrollChat()
  try {
    await saveAll()
    const result = await askLabAssistant(exerciseId.value, question, activePath.value, assistantMode.value)
    chatMessages.value.push({ role: 'assistant', content: result.answer, notice: result.notice })
  } catch (error) {
    chatMessages.value.push({ role: 'assistant', content: '项目分析暂时失败，请稍后重试。' })
  } finally { assistantLoading.value = false; scrollChat() }
}

async function handleTopAction() {
  if (capabilityStatus.value === 'verified' || capabilityStatus.value === 'defense_pending') {
    defenseDialog.value = true
    return
  }
  if (capabilityStatus.value === 'repair_pending') return submitRepairCode()
  if (!acceptancePassed.value) {
    leftMode.value = 'guide'
    currentStage.value = 'acceptance'
    const stage = stages.value.find(item => item.id === 'acceptance')
    if (stage) await checkStage(stage)
    return
  }
  await beginCapability()
}

async function beginCapability() {
  const solution = models.get('solution.py')
  if (!solution) return ElMessage.warning('没有找到 solution.py')
  capabilityBusy.value = true
  try {
    await saveAll()
    let session = await startCapabilitySession(exerciseId.value)
    if (session.status === 'coding') session = await markCapabilityCodePassed(session.id, solution.getValue())
    capabilitySession.value = session
    for (const question of session.defense_questions || []) defenseAnswers[question.id] = ''
    defenseDialog.value = true
  } finally { capabilityBusy.value = false }
}

async function submitDefenseAnswers() {
  const unanswered = defenseQuestions.value.filter(item => !String(defenseAnswers[item.id] || '').trim())
  if (unanswered.length) return ElMessage.warning(`还有 ${unanswered.length} 个问题未回答`)
  capabilityBusy.value = true
  try {
    const answers = defenseQuestions.value.map(item => ({ question_id: item.id, answer: defenseAnswers[item.id] }))
    const result = await submitCapabilityDefense(capabilitySession.value.id, answers, 'AI提供了提示')
    capabilitySession.value = result
    if (!result.defense_passed) return ElMessage.warning(`答辩得分 ${result.defense_score}，请补充具体代码依据`)
    await saveLabFile(exerciseId.value, 'solution.py', result.mutation_code)
    models.get('solution.py')?.setValue(result.mutation_code)
    dirtyFiles.delete('solution.py')
    openFile('solution.py')
    ElMessage.success('答辩通过，故障已写入 solution.py，请定位并修复')
  } finally { capabilityBusy.value = false }
}

async function submitRepairCode() {
  if (repairExplanation.value.trim().length < 20) {
    defenseDialog.value = true
    return ElMessage.warning('请先在能力验证窗口用至少20字说明故障根因')
  }
  capabilityBusy.value = true
  try {
    await saveAll()
    const result = await submitCapabilityRepair(capabilitySession.value.id, models.get('solution.py').getValue(), repairExplanation.value)
    if (!result.repair_passed) return ElMessage.warning('修复仍未通过，请结合终端和 Agent 助手继续定位')
    capabilitySession.value = { ...capabilitySession.value, ...result, status: 'verified', report: result.report }
    defenseDialog.value = true
    const completed = JSON.parse(localStorage.getItem('code_completed') || '{}')
    completed[`${moduleId.value}_${exerciseId.value}`] = { verified: true, evidenceScore: result.report.total_score, completedAt: new Date().toISOString() }
    localStorage.setItem('code_completed', JSON.stringify(completed))
  } finally { capabilityBusy.value = false }
}

function goBack() { router.push({ name: 'TaskList', params: { moduleId: moduleId.value } }) }

function handleGlobalKeydown(event) {
  if (!explorerMenu.visible) return
  if (event.key === 'Escape') closeExplorerMenu()
  if (event.key === 'F2') { event.preventDefault(); contextRename() }
  if (event.key === 'Delete') { event.preventDefault(); contextDelete() }
}

onMounted(async () => {
  document.addEventListener('click', closeExplorerMenu)
  window.addEventListener('keydown', handleGlobalKeydown)
  createEditor()
  await loadWorkspace()
  bindCodeBlockActions(chatRef.value)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closeExplorerMenu)
  window.removeEventListener('keydown', handleGlobalKeydown)
  terminalAbortController?.abort()
  if (terminalTimer) window.clearInterval(terminalTimer)
  saveAll().catch(() => {})
  editor?.dispose()
  editor = null
  disposeModels()
})
</script>

<style scoped>
.ide-page { --bg:#080d18; --panel:#0e1524; --panel2:#111a2b; --line:#243044; --muted:#8693a8; --text:#dce5f4; --accent:#6d5dfc; height:100%; min-height:0; color:var(--text); background:var(--bg); overflow:hidden; box-shadow:0 18px 48px rgba(5,10,20,.22); }
button { font:inherit; }
.ide-topbar { height:58px; display:flex; align-items:center; justify-content:space-between; padding:0 14px; background:#0c1321; border-bottom:1px solid var(--line); }
.brand-area,.top-actions,.brand-area>div,.environment-pill,.ghost-action,.primary-action { display:flex; align-items:center; }
.brand-area { gap:10px; min-width:0; }.icon-button { width:34px;height:34px;border:0;border-radius:8px;color:#9aa9bd;background:transparent;cursor:pointer;font-size:18px }.icon-button:hover{background:#1b2639;color:#fff}
.brand-mark,.welcome-logo { display:grid;place-items:center;background:linear-gradient(135deg,#8b75ff,#4c7dff);color:white;font-weight:900;box-shadow:0 0 24px rgba(109,93,252,.35) }.brand-mark{width:31px;height:31px;border-radius:9px}
.project-heading { flex-direction:column;align-items:flex-start!important;min-width:0}.project-heading strong{font-size:14px}.project-heading span{font-size:11px;color:var(--muted);max-width:430px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.top-actions { gap:9px }.layout-switcher{display:flex;align-items:center;gap:2px;padding:3px;border:1px solid #2b3749;border-radius:7px;background:#0a111d}.layout-switcher button{display:grid;width:30px;height:26px;place-items:center;border:0;border-radius:5px;color:#8794a7;background:transparent;cursor:pointer}.layout-switcher button:hover,.layout-switcher button.active{color:#eef3fb;background:#202c40}.layout-glyph{position:relative;display:block;width:16px;height:13px;border:2px solid currentColor}.layout-glyph::before,.layout-glyph::after{position:absolute;top:0;bottom:0;width:2px;background:currentColor;content:""}.layout-glyph.standard::before{left:3px}.layout-glyph.standard::after{right:3px}.layout-glyph.project::before{left:4px}.layout-glyph.project::after{display:none}.layout-glyph.focus::before,.layout-glyph.focus::after{display:none}.layout-glyph.pair::before{left:6px}.layout-glyph.pair::after{display:none}.environment-pill{gap:7px;color:#e8c27d;font-size:12px;padding:7px 10px;background:#1e1b19;border:1px solid #55452e;border-radius:7px;cursor:pointer}.environment-pill:hover:not(:disabled){color:#ffe0a3;border-color:#8d6d38;background:#2a241c}.environment-pill.ready,.environment-pill:disabled.ready{color:#a9b6ca;background:#111c2d;border-color:#26354c;cursor:default}.environment-pill:disabled:not(.ready){cursor:wait}.environment-pill i,.agent-header span i{width:7px;height:7px;background:#f0a948;border-radius:50%}.environment-pill i.online,.agent-header span i{background:#4bd39b;box-shadow:0 0 8px #4bd39b}
.ghost-action,.primary-action,.outline-button{gap:7px;border-radius:7px;padding:8px 12px;cursor:pointer;border:1px solid #34435a}.ghost-action{color:#c3cede;background:#111a29}.primary-action{color:#fff;border-color:#7768ff;background:linear-gradient(135deg,#725fff,#526dff);box-shadow:0 5px 18px rgba(86,91,255,.22)}.primary-action:disabled{opacity:.55;cursor:not-allowed}
.workbench { height:calc(100% - 58px);min-height:0;display:grid;grid-template-columns:46px 272px minmax(470px,1fr) 330px;background:var(--bg) }
.workbench.layout-project{grid-template-columns:46px 272px minmax(0,1fr)}.workbench.layout-project .agent-panel{display:none}.workbench.layout-focus{grid-template-columns:46px minmax(0,1fr)}.workbench.layout-focus .side-panel,.workbench.layout-focus .agent-panel{display:none}.workbench.layout-pair{grid-template-columns:46px minmax(0,1fr) 360px}.workbench.layout-pair .side-panel{display:none}
.activity-bar{display:flex;flex-direction:column;align-items:center;background:#0a101c;border-right:1px solid var(--line);padding-top:7px}.activity-bar button{width:45px;height:45px;border:0;border-left:2px solid transparent;background:transparent;color:#77859b;font-size:21px;cursor:pointer}.activity-bar button:hover,.activity-bar button.active{color:#fff;background:#131d2e}.activity-bar button.active{border-left-color:#7c6cff}
.side-panel{min-width:0;background:var(--panel);border-right:1px solid var(--line);display:flex;flex-direction:column;overflow:hidden}.panel-title{height:43px;padding:0 12px;display:flex;align-items:center;justify-content:space-between;text-transform:uppercase;letter-spacing:.08em;color:#aab6c8;font-size:11px;border-bottom:1px solid var(--line)}.panel-title div{display:flex}.panel-title button,.agent-header>button,.terminal-tabs>button:last-child{border:0;background:transparent;color:#8b99ae;padding:5px;cursor:pointer}.panel-title button:hover{color:#fff}.panel-title em{font-style:normal;color:#7f70ff}
.project-root{height:36px;padding:0 10px;display:flex;align-items:center;gap:5px;border-bottom:1px solid #263247;font-size:12px;color:#d5ddeb;background:#111a29}.project-root>.el-icon:nth-child(2){color:#d5b46d}.file-list{flex:1;overflow:auto;padding:0}.file-badge.python,.tab-dot.python{color:#59a9ff}.file-badge.markdown,.tab-dot.markdown{color:#9aa8ff}.file-badge.env,.tab-dot.env{color:#f1c45a}.file-badge.json,.tab-dot.json{color:#e6a75f}.file-badge.text,.tab-dot.text{color:#a6b0c0}.empty-files,.explorer-hint{padding:18px;color:#68768c;font-size:11px;text-align:center}.explorer-hint{padding:8px;border-top:1px solid var(--line)}
.lesson-intro{padding:16px;border-bottom:1px solid var(--line)}.lesson-intro>span{font-size:10px;color:#a99fff;background:#27224c;padding:4px 7px;border-radius:10px}.lesson-intro h3{font-size:15px;margin:11px 0 7px}.lesson-intro p{font-size:12px;line-height:1.65;color:#8795aa;margin:0;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.stage-list{overflow:auto;padding:8px}.stage-card{margin-bottom:7px;border:1px solid #232f42;border-radius:8px;background:#101827;overflow:hidden}.stage-card.open{border-color:#554ca0}.stage-card.done{border-color:#265443}.stage-heading{width:100%;display:flex;align-items:center;gap:9px;padding:10px;border:0;color:#d2dbe9;background:transparent;text-align:left;cursor:pointer}.stage-heading>span:nth-child(2){flex:1;min-width:0}.stage-heading b,.stage-heading small{display:block}.stage-heading b{font-size:12px}.stage-heading small{margin-top:3px;font-size:10px;color:#75839a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.stage-heading>svg{font-size:11px}.stage-number{width:23px;height:23px;display:grid;place-items:center;border-radius:50%;background:#25304a;color:#a9b4c6;font-size:11px}.stage-card.done .stage-number{background:#174a38;color:#65e0ac}.stage-body{padding:0 11px 12px}.stage-body>p{font-size:11px;color:#9ba8bb;line-height:1.65}.command-chip{display:flex;align-items:center;padding:7px 8px;border:1px solid #26354b;border-radius:6px;background:#080f1b}.command-chip code{flex:1;color:#8fd5b7;font-size:10px;overflow:hidden;text-overflow:ellipsis}.command-chip button{border:0;color:#a99fff;background:transparent;font-size:10px;cursor:pointer}.full{width:100%;justify-content:center;margin-top:8px;color:#bbb5ff;background:transparent}.check-button{width:100%;display:flex;justify-content:center;align-items:center;gap:6px;margin-top:8px;padding:8px;border:0;border-radius:6px;color:#fff;background:#5c52d9;font-size:11px;cursor:pointer}.check-result{margin-top:9px;padding:7px;border-radius:6px;background:#2b1920}.check-result.passed{background:#122d26}.check-result>div{display:flex;gap:7px;padding:4px}.check-result>div>span{color:#ff8797}.check-result.passed>div>span{color:#57d9a1}.check-result p{margin:0}.check-result b,.check-result small{display:block;font-size:10px}.check-result small{color:#8b97aa;margin-top:2px;line-height:1.4}
.editor-column{min-width:0;display:grid;grid-template-rows:38px minmax(280px,1fr) 225px;background:#0b111d}.editor-tabs{display:flex;min-width:0;background:#0c1320;border-bottom:1px solid var(--line);overflow:hidden}.editor-tabs>button:not(.save-button){height:38px;display:flex;align-items:center;gap:6px;padding:0 10px;border:0;border-right:1px solid #202b3d;color:#8794a7;background:#101826;font-size:11px;cursor:pointer;white-space:nowrap}.editor-tabs>button.active{color:#e9eef7;background:#0b111d;border-top:1px solid #7464ff}.tab-dot{width:7px;height:7px;border-radius:50%;background:currentColor}.tab-close{font-size:12px;opacity:0}.editor-tabs button:hover .tab-close{opacity:1}.editor-tabs button i{font-style:normal;color:#887aff}.editor-spacer{flex:1}.save-button{border:0;border-left:1px solid var(--line);background:#0e1726;color:#9aa8bc;padding:0 11px;cursor:pointer;display:flex;gap:5px;align-items:center;font-size:11px}.monaco-host{min-width:0;min-height:0}.welcome-editor{grid-row:2;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#8190a7}.welcome-logo{width:60px;height:60px;border-radius:18px;font-size:29px;opacity:.75}.welcome-editor h2{font-size:18px;color:#c9d3e2;margin:18px 0 6px}.welcome-editor p{font-size:12px;margin:0 0 20px}.terminal-panel{min-height:0;border-top:1px solid var(--line);background:#090f1a}.terminal-tabs{height:35px;display:flex;align-items:center;border-bottom:1px solid #1e293a}.terminal-tabs button{height:35px;border:0;color:#8997aa;background:transparent;font-size:11px;padding:0 12px;cursor:pointer}.terminal-tabs button.active{color:#e4eaf3;border-bottom:1px solid #796bff}.terminal-tabs span{margin-left:auto;color:#526077;font-size:10px}.terminal-tabs span.running{color:#5ed5a4}.terminal-tabs .stop-terminal{height:24px;margin-left:9px;padding:0 8px;border:1px solid #633844;border-radius:5px;color:#ff9aaa;background:#28141b}.terminal-output{height:calc(100% - 36px);overflow:auto;padding:9px 13px;color:#bfcbda;font:12px/1.55 'Cascadia Code',Consolas,monospace;cursor:text;user-select:text}.terminal-output *{user-select:text}.terminal-welcome{color:#687891;margin-bottom:6px}.terminal-line{display:flex;gap:8px}.terminal-line pre{margin:0;white-space:pre-wrap;font:inherit}.terminal-line.command pre{color:#e7ecf4}.terminal-line.error pre{color:#ff7f8f}.terminal-line.output pre{color:#a6b8ca}.terminal-line.status pre{color:#6fd2a8}.prompt-symbol{color:#58d5a2;font-weight:800}.prompt-env{color:#67d5a4;font-weight:700}.terminal-input-row{display:flex;align-items:center;gap:7px}.prompt-path{color:#8075ff}.terminal-input-row input{flex:1;border:0;outline:0;color:#fff;background:transparent;font:inherit;user-select:text}
.agent-panel{min-width:0;min-height:0;background:var(--panel);border-left:1px solid var(--line);display:grid;grid-template-rows:58px minmax(0,1fr) auto 142px}.agent-header{display:flex;align-items:center;gap:9px;padding:0 12px;border-bottom:1px solid var(--line)}.agent-avatar,.mini-avatar{display:grid;place-items:center;border-radius:10px;color:white;background:linear-gradient(135deg,#7a65ff,#4d7cff)}.agent-avatar{width:34px;height:34px}.agent-header>div:nth-child(2){flex:1}.agent-header b,.agent-header span{display:block}.agent-header b{font-size:12px}.agent-header span{margin-top:3px;color:#7f8ea5;font-size:9px}.agent-header span i{display:inline-block;margin-right:5px}.chat-list{min-height:0;overflow-x:hidden;overflow-y:auto;overscroll-behavior:contain;scrollbar-gutter:stable;padding:14px 12px}.chat-message{display:flex;gap:8px;margin-bottom:13px}.chat-message.user{justify-content:flex-end}.mini-avatar{width:24px;height:24px;flex:0 0 24px;font-size:10px}.message-bubble{max-width:88%;min-width:0;padding:9px 10px;border-radius:4px 11px 11px 11px;background:#182236;color:#c5d0df;font-size:11px;line-height:1.65;white-space:pre-wrap;overflow-wrap:anywhere}.chat-message.assistant .message-bubble{white-space:normal}.chat-message.user .message-bubble{background:#4c43a2;color:white;border-radius:11px 4px 11px 11px}.message-bubble small{display:block;margin-top:7px;padding-top:6px;border-top:1px solid rgba(255,255,255,.08);color:#7f8da2;font-size:9px}.assistant-markdown :deep(p){margin:0 0 8px}.assistant-markdown :deep(p:last-child){margin-bottom:0}.assistant-markdown :deep(ul),.assistant-markdown :deep(ol){margin:7px 0;padding-left:20px}.assistant-markdown :deep(h1),.assistant-markdown :deep(h2),.assistant-markdown :deep(h3){margin:12px 0 7px;color:#eef3fb;font-size:13px}.assistant-markdown :deep(code:not(pre code)){padding:2px 5px;border-radius:4px;color:#9fe0c2;background:#0b1321}.assistant-markdown :deep(.code-block-wrapper){margin:9px 0;border:1px solid #2b3850;border-radius:7px;background:#080f1b;overflow:hidden}.assistant-markdown :deep(.code-toolbar){display:flex;align-items:center;justify-content:space-between;gap:4px;padding:5px 7px;border-bottom:1px solid #273349;background:#111a29}.assistant-markdown :deep(.code-lang-tag){color:#8998ae;font-size:9px}.assistant-markdown :deep(.code-toolbar-actions){display:flex;gap:3px}.assistant-markdown :deep(.code-toolbar-btn){width:auto;height:auto;padding:3px 5px;border:0;border-radius:4px;color:#9ba9bd;background:#1b273a;font-size:8px;cursor:pointer}.assistant-markdown :deep(.code-toolbar-btn:hover){color:#fff;background:#34425b}.assistant-markdown :deep(pre){margin:0;padding:9px;overflow:auto;color:#c9d6e7;font:10px/1.55 'Cascadia Code',Consolas,monospace;white-space:pre}.typing{display:flex;gap:4px;padding:12px}.typing i{width:5px;height:5px;border-radius:50%;background:#8f83ff;animation:blink 1s infinite}.typing i:nth-child(2){animation-delay:.16s}.typing i:nth-child(3){animation-delay:.32s}@keyframes blink{50%{opacity:.25;transform:translateY(-2px)}}.quick-prompts{display:flex;flex-wrap:wrap;gap:5px;padding:7px 10px}.quick-prompts button{padding:5px 7px;border:1px solid #2a3850;border-radius:12px;color:#8998ae;background:#101a2a;font-size:9px;cursor:pointer}.quick-prompts button:hover{color:#c7c1ff;border-color:#6156bb}.agent-composer{margin:0 10px 10px;padding:8px;border:1px solid #34425b;border-radius:9px;background:#0a111e}.agent-composer:focus-within{border-color:#6c5fe7}.assistant-mode-switch{display:flex!important;justify-content:flex-start!important;gap:3px;margin:-2px 0 6px}.assistant-mode-switch button{width:auto!important;height:23px!important;padding:0 9px!important;border:1px solid #2c3950!important;border-radius:6px!important;color:#7f8da3!important;background:transparent!important;font-size:9px!important}.assistant-mode-switch button.active{color:#fff!important;border-color:#6658e9!important;background:#332c79!important}.agent-composer textarea{width:100%;resize:none;border:0;outline:0;color:#dce5f2;background:transparent;font:11px/1.5 inherit}.agent-composer>div{display:flex;align-items:center;justify-content:space-between}.agent-composer span{color:#56647a;font-size:9px}.agent-composer button{width:27px;height:27px;border:0;border-radius:7px;color:white;background:#6658e9;cursor:pointer}.agent-composer button:disabled{opacity:.4}
.dialog-title{display:flex;flex-direction:column}.dialog-title span{color:#7b6eff;font-size:11px}.dialog-title b{font-size:18px;margin-top:4px}.defense-form>p,.repair-form p{color:#6c7789;font-size:13px}.defense-form label{display:block;margin:15px 0}.defense-form label>span{display:block;margin-bottom:7px;font-size:13px;font-weight:600}.dialog-submit{margin-top:12px;margin-left:auto}.verified-report{text-align:center;padding:25px}.score-ring{width:95px;height:95px;display:grid;place-items:center;margin:auto;border:7px solid #59d7a3;border-radius:50%;color:#30b981;font-size:28px;font-weight:900}
@media(max-width:1200px){.workbench.layout-standard{grid-template-columns:46px 240px minmax(430px,1fr) 290px}.project-heading span,.environment-pill{display:none}}@media(max-width:980px){.workbench.layout-standard{grid-template-columns:46px 230px minmax(430px,1fr)}.workbench.layout-standard .agent-panel{display:none}.layout-switcher{display:none}}
.test-case-list{grid-column:2;margin:7px 0 1px;padding:5px 0 2px;border-top:1px solid rgba(255,255,255,.08);list-style:none}.test-case-list li{display:flex;gap:7px;padding:4px 0;color:#ff9aa8}.test-case-list li.passed{color:#62d4a5}.test-case-list li>span{width:12px;flex:0 0 12px}.test-case-list p{margin:0;color:#c5cfdd}.test-case-list b,.test-case-list small{display:block;font-size:9px}.test-case-list small{margin-top:2px;color:#7f8da2}.check-result-item{display:grid!important;grid-template-columns:12px minmax(0,1fr);align-items:start}
.explorer-context-menu{position:fixed;z-index:5000;width:250px;padding:6px;border:1px solid #354157;border-radius:8px;background:#171c26;box-shadow:0 14px 36px rgba(0,0,0,.5)}.explorer-context-menu button{width:100%;height:31px;padding:0 10px;display:flex;align-items:center;justify-content:space-between;border:0;border-radius:5px;color:#d1d7e2;background:transparent;font-size:12px;text-align:left;cursor:pointer}.explorer-context-menu button:hover:not(:disabled){color:#fff;background:#293244}.explorer-context-menu button.danger{color:#ff9aa8}.explorer-context-menu button:disabled{color:#5f6878;cursor:not-allowed}.explorer-context-menu kbd{padding:2px 5px;border:1px solid #3a4352;border-radius:4px;color:#929baa;background:#202632;font:10px 'Cascadia Code',Consolas,monospace}.menu-separator{height:1px;margin:5px -6px;background:#343b48}
</style>
