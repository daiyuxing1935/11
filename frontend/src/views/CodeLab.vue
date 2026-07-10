<template>
  <div class="code-lab-page">
    <!-- Header -->
    <div class="lab-header">
      <el-page-header @back="goBack" style="margin-bottom:12px">
        <template #content>
          <span>编程实验室 - {{ taskInfo ? taskInfo.title : '加载中...' }}</span>
          <el-tag size="small" style="margin-left:8px" type="success">Day {{ taskDay }}</el-tag>
        </template>
      </el-page-header>
    </div>

    <el-row :gutter="16" class="lab-body">
      <!-- 左侧：任务面板 -->
      <el-col :span="8">
        <el-card shadow="hover" class="task-panel">
          <template #header>
            <span><el-icon><Notebook /></el-icon> 编程任务</span>
            <el-tag v-if="taskInfo" size="small" type="info" style="margin-left:8px">{{ taskInfo.knowledge }}</el-tag>
          </template>

          <el-skeleton v-if="!taskInfo" :rows="8" animated />

          <div v-else>
            <!-- 任务描述 (Markdown) -->
            <div class="task-desc" v-html="renderedDesc" />

            <el-divider />

            <!-- 任务要求 -->
            <div class="task-section">
              <h4>📋 具体要求</h4>
              <ul>
                <li v-for="(req, i) in taskInfo.requirements" :key="i">{{ req }}</li>
              </ul>
            </div>

            <el-divider />

            <!-- 测试用例 -->
            <div class="task-section">
              <h4>🧪 测试用例</h4>
              <div v-for="(tc, i) in taskInfo.test_cases" :key="i" class="test-case-card">
                <div class="tc-header">
                  <el-tag :type="tcResultStyle(tc.name)" size="small" effect="dark">
                    {{ getTestStatus(tc.name) }}
                  </el-tag>
                  <strong style="margin-left:6px">{{ tc.name }}</strong>
                </div>
                <div class="tc-desc">{{ tc.description }}</div>
              </div>
            </div>

            <el-divider />

            <!-- 渐进提示 -->
            <div class="task-section">
              <h4>💡 提示（遇到困难时展开）</h4>
              <el-collapse v-if="taskInfo.hints && taskInfo.hints.length">
                <el-collapse-item v-for="(hint, i) in taskInfo.hints" :key="i" :title="hint[0]">
                  <div class="hint-content">{{ hint[1] }}</div>
                </el-collapse-item>
              </el-collapse>
              <el-empty v-else description="暂无提示" :image-size="40" />
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：代码编辑器 -->
      <el-col :span="16">
        <el-card shadow="hover" class="editor-panel">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span><el-icon><Edit /></el-icon> 代码编辑区 (Python)</span>
              <div style="display:flex;gap:8px">
                <el-button type="primary" @click="runCode" :loading="running">
                  <el-icon><VideoPlay /></el-icon> 运行
                </el-button>
                <el-button type="success" @click="runTests" :loading="testing">
                  <el-icon><Finished /></el-icon> 测试
                </el-button>
                <el-button @click="resetCode">
                  <el-icon><RefreshRight /></el-icon> 重置
                </el-button>
              </div>
            </div>
          </template>

          <div class="editor-wrapper">
            <textarea
              ref="editorRef"
              v-model="code"
              class="code-editor"
              spellcheck="false"
              @keydown="handleKeydown"
              placeholder="# 在这里编写你的 Python 代码..."
            ></textarea>
          </div>

          <!-- 未通过时提示 -->
          <div v-if="result && !result.all_passed" class="answer-prompt">
            <el-alert type="warning" :closable="false" show-icon>
              <template #title>
                测试未全部通过 ({{ result.passed_count || 0 }}/{{ result.total_count || 0 }} 通过)
              </template>
              <div style="margin-top:8px;display:flex;gap:10px;align-items:center">
                <span>需要参考答案吗？</span>
                <el-button type="primary" size="small" @click="showAnswerCode">查看答案</el-button>
                <el-button size="small" @click="runTests">重新测试</el-button>
              </div>
            </el-alert>
          </div>

          <!-- 参考答案 -->
          <div v-if="showAnswer && taskInfo?.answer_code" class="answer-panel">
            <el-card>
              <template #header>
                <div style="display:flex;justify-content:space-between;align-items:center">
                  <span><el-icon><Document /></el-icon> 参考答案</span>
                  <el-button type="success" size="small" @click="applyAnswer">应用答案到编辑器</el-button>
                </div>
              </template>
              <pre class="answer-code"><code>{{ taskInfo.answer_code }}</code></pre>
            </el-card>
          </div>

          <!-- 执行结果 -->
          <div v-if="result" class="result-panel">
            <el-divider />
            <div style="margin-bottom:12px;font-weight:bold">
              <el-icon><DataLine /></el-icon> 执行结果
              <el-tag :type="statusTagType" size="large" effect="dark" style="margin-left:8px">{{ statusText }}</el-tag>
            </div>

            <div v-if="result.test_results?.length" class="test-results" style="margin-top:12px">
              <div v-for="(tr, i) in result.test_results" :key="i"
                   :class="['test-result-item', tr.status === 'passed' ? 'passed' : 'failed']">
                <div class="tr-header">
                  <el-icon :color="tr.status==='passed'?'#67C23A':'#F56C6C'">
                    <CircleCheck v-if="tr.status==='passed'"/><CircleClose v-else/>
                  </el-icon>
                  <strong>{{ tr.name }}</strong><span class="tr-desc"> - {{ tr.description }}</span>
                </div>
                <div class="tr-msg">{{ tr.message }}</div>
              </div>
            </div>
            <div v-if="result.stdout" class="output-block"><h4>输出</h4><pre class="output stdout">{{ result.stdout }}</pre></div>
            <div v-if="result.stderr" class="output-block"><h4>错误</h4><pre class="output stderr">{{ result.stderr }}</pre></div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getCodeTask, executeCode } from '../api/learning'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'

const router = useRouter()
const route = useRoute()
const taskDay = parseInt(route.params.taskDay) || 1

const taskInfo = ref(null)
const code = ref('')
const starterCode = ref('')
const result = ref(null)
const running = ref(false)
const testing = ref(false)
const editorRef = ref(null)
const showAnswer = ref(false)
const testStatuses = ref({})

const renderedDesc = computed(() => {
  if (!taskInfo.value?.description) return ''
  return marked.parse(taskInfo.value.description)
})

onMounted(async () => {
  try {
    const data = await getCodeTask(taskDay)
    taskInfo.value = data
    starterCode.value = data.starter_code || '# 请在这里编写代码\n'
    code.value = data.starter_code || '# 请在这里编写代码\n'
  } catch(e) {
    ElMessage.error('获取编程任务失败: ' + (e?.message || '请先生成学习路径'))
  }
})

const statusTagType = computed(() => {
  if (!result.value) return 'info'
  if (result.value.all_passed) return 'success'
  return 'danger'
})

const statusText = computed(() => {
  if (!result.value) return ''
  if (result.value.all_passed) return '全部通过！'
  return `未通过 (${result.value.passed_count || 0}/${result.value.total_count || 0})`
})

function getTestStatus(name) {
  const s = testStatuses.value[name]
  if (s === 'passed') return '通过'
  if (s === 'failed') return '失败'
  return '待测'
}

function tcResultStyle(name) {
  const s = testStatuses.value[name]
  if (s === 'passed') return 'success'
  if (s === 'failed') return 'danger'
  return 'info'
}

async function runCode() {
  if (!code.value.trim()) { ElMessage.warning('请先编写代码'); return }
  running.value = true
  result.value = null
  testStatuses.value = {}
  showAnswer.value = false
  try {
    const res = await executeCode({ task_day: taskDay, code: code.value })
    result.value = res
    updateTestStatuses(res)
    ElMessage[res.compile_status === 'success' ? 'success' : 'warning'](
      res.compile_status === 'success' ? '运行成功' : '运行有误，请查看输出'
    )
  } catch(e) { ElMessage.error('执行失败') }
  finally { running.value = false }
}

async function runTests() {
  if (!code.value.trim()) { ElMessage.warning('请先编写代码'); return }
  testing.value = true
  result.value = null
  testStatuses.value = {}
  showAnswer.value = false
  try {
    const res = await executeCode({ task_day: taskDay, code: code.value })
    result.value = res
    updateTestStatuses(res)
    const passed = res.test_results?.filter(t => t.status === 'passed').length || 0
    const total = res.test_results?.length || 0
    ElMessage[res.all_passed ? 'success' : 'warning'](
      res.all_passed ? `全部 ${total} 项测试通过！` : `${passed}/${total} 项测试通过`
    )
  } catch(e) { ElMessage.error('测试失败') }
  finally { testing.value = false }
}

function updateTestStatuses(res) {
  if (res.test_results) {
    for (const tr of res.test_results) {
      testStatuses.value[tr.name] = tr.status
    }
  }
}

function resetCode() {
  code.value = starterCode.value
  result.value = null
  testStatuses.value = {}
  showAnswer.value = false
  ElMessage.info('代码已重置')
}

function showAnswerCode() {
  showAnswer.value = true
}

function applyAnswer() {
  if (taskInfo.value?.answer_code) {
    code.value = taskInfo.value.answer_code
    ElMessage.success('答案已应用到编辑器，可点击测试验证')
    showAnswer.value = false
  }
}

function handleKeydown(e) {
  if (e.key === 'Tab') {
    e.preventDefault()
    const ta = editorRef.value
    if (!ta) return
    const start = ta.selectionStart
    const end = ta.selectionEnd
    code.value = code.value.substring(0, start) + '    ' + code.value.substring(end)
    setTimeout(() => { ta.selectionStart = ta.selectionEnd = start + 4 }, 0)
  }
}

function goBack() {
  router.push('/learning-path')
}
</script>

<style scoped>
.code-lab-page { max-width: 1400px; margin: 0 auto; }
.lab-header { margin-bottom: 12px; }
.lab-body { margin: 0 !important; }
.task-panel { height: calc(100vh - 140px); overflow-y: auto; }

.task-desc { font-size: 14px; color: #303133; line-height: 1.8; }
.task-desc :deep(h2) { font-size: 17px; margin: 8px 0 6px; color: #1a1a2e; }
.task-desc :deep(h4) { font-size: 14px; margin: 6px 0 4px; color: #409EFF; }
.task-desc :deep(ul) { padding-left: 18px; margin: 4px 0; }
.task-desc :deep(li) { margin: 3px 0; font-size: 13px; }
.task-desc :deep(strong) { color: #1a1a2e; }

.task-section h4 { font-size: 14px; margin-bottom: 8px; color: #303133; }
.task-section li { font-size: 13px; color: #606266; line-height: 1.7; }

.test-case-card { padding: 10px 12px; margin-bottom: 8px; background: #fafafa; border-radius: 6px; border: 1px solid #f0f0f0; }
.tc-header { display: flex; align-items: center; margin-bottom: 4px; }
.tc-desc { font-size: 12px; color: #909399; margin-left: 26px; }

.hint-content { font-size: 13px; color: #606266; line-height: 1.6; white-space: pre-wrap; }

.editor-panel { height: calc(100vh - 140px); display: flex; flex-direction: column; }
.editor-wrapper { flex: 1; min-height: 350px; }
.code-editor {
  width: 100%; height: 100%; min-height: 350px;
  border: 1px solid #e0e0e0; border-radius: 6px; padding: 14px 16px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  font-size: 14px; line-height: 1.6; resize: none; outline: none;
  background: #1e1e1e; color: #d4d4d4; tab-size: 4;
}
.code-editor:focus { border-color: #409EFF; }
.code-editor::placeholder { color: #6a6a6a; }

.result-panel { margin-top: 8px; }
.result-panel h4 { font-size: 13px; margin-bottom: 8px; color: #303133; }

.test-result-item { padding: 10px 12px; margin-bottom: 6px; border-radius: 6px; border-left: 4px solid #e0e0e0; }
.test-result-item.passed { border-left-color: #67C23A; background: #f0faf4; }
.test-result-item.failed { border-left-color: #F56C6C; background: #fef0f0; }
.tr-header { display: flex; align-items: center; gap: 4px; font-size: 13px; }
.tr-desc { color: #909399; font-size: 12px; }
.tr-msg { margin-top: 4px; margin-left: 20px; font-size: 12px; color: #606266; }

.output-block { margin-top: 12px; }
.output { padding: 12px; border-radius: 6px; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.5; white-space: pre-wrap; word-break: break-all; max-height: 200px; overflow-y: auto; }
.output.stdout { background: #f5f7fa; color: #303133; border: 1px solid #e8e8e8; }
.output.stderr { background: #fef0f0; color: #F56C6C; border: 1px solid #fde2e2; }

.answer-prompt { margin-top: 12px; }
.answer-panel { margin-top: 12px; max-height: 400px; overflow-y: auto; }
.answer-code { padding: 14px 16px; background: #1e1e1e; color: #d4d4d4; font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 13px; line-height: 1.6; border-radius: 6px; white-space: pre; overflow-x: auto; }
</style>
