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

      <!-- 模式切换 -->
      <el-radio-group v-model="mode" size="default" @change="switchMode" :disabled="loadingGuide">
        <el-radio-button value="free"><el-icon><Edit /></el-icon> 自由模式</el-radio-button>
        <el-radio-button value="step"><el-icon><UserFilled /></el-icon> AI 手把手教学</el-radio-button>
      </el-radio-group>
    </div>

    <!-- ====== 自由模式 ====== -->
    <el-row v-if="mode === 'free'" :gutter="16" class="lab-body">
      <el-col :span="8">
        <el-card shadow="hover" class="task-panel">
          <template #header>
            <span><el-icon><Notebook /></el-icon> 编程任务</span>
          </template>
          <div v-if="taskInfo">
            <el-alert :title="taskInfo.knowledge" type="info" :closable="false" style="margin-bottom:12px" />
            <div class="task-section">
              <h4>任务描述</h4>
              <p>{{ taskInfo.description }}</p>
            </div>
            <el-divider />
            <div class="task-section">
              <h4>任务要求</h4>
              <ul>
                <li v-for="(req, i) in taskInfo.requirements" :key="i">{{ req }}</li>
              </ul>
            </div>
            <el-divider />
            <div class="task-section">
              <h4>测试用例</h4>
              <div v-for="(tc, i) in taskInfo.test_cases" :key="i" class="test-case-card">
                <div class="tc-header">
                  <el-tag :type="tcResultStyle(tc.name)" size="small" effect="dark">{{ getTestStatus(tc.name) }}</el-tag>
                  <strong style="margin-left:6px">{{ tc.name }}</strong>
                </div>
                <div class="tc-desc">{{ tc.description }}</div>
              </div>
            </div>
          </div>
          <el-skeleton v-else :rows="8" animated />
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card shadow="hover" class="editor-panel">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span><el-icon><Edit /></el-icon> 代码编辑区 (Python)</span>
              <div style="display:flex;gap:8px">
                <el-button type="primary" @click="runCode" :loading="running"><el-icon><VideoPlay /></el-icon> 运行</el-button>
                <el-button type="success" @click="runTests" :loading="testing"><el-icon><Finished /></el-icon> 测试</el-button>
                <el-button @click="resetCode"><el-icon><RefreshRight /></el-icon> 重置</el-button>
              </div>
            </div>
          </template>
          <div class="editor-wrapper">
            <textarea ref="editorRef" v-model="code" class="code-editor" spellcheck="false"
              @keydown="handleKeydown" placeholder="# 在这里编写你的 Python 代码..."></textarea>
          </div>

          <div v-if="result && !result.all_passed && !showAnswer" class="answer-prompt">
            <el-alert type="error" :closable="false" show-icon>
              <template #title>编译未全部通过 ({{ result.passed_count || 0 }}/{{ result.total_count || 0 }} 通过)</template>
              <div style="margin-top:8px;display:flex;gap:10px;align-items:center">
                <span>是否查看参考答案？</span>
                <el-button type="primary" size="small" @click="viewAnswer">查看答案</el-button>
                <el-button size="small" @click="retryCompile">重新编译</el-button>
              </div>
            </el-alert>
          </div>

          <div v-if="showAnswer && answerData" class="answer-panel">
            <el-card>
              <template #header>
                <div style="display:flex;justify-content:space-between;align-items:center">
                  <span><el-icon><Document /></el-icon> 参考答案</span>
                  <el-button type="success" size="small" @click="applyAnswer">应用答案</el-button>
                </div>
              </template>
              <div v-for="(exp, i) in answerData.explanations" :key="i" class="explanation-item">
                <div class="exp-line"><span class="exp-line-num">{{ exp.line }}</span><code class="exp-code">{{ exp.code }}</code></div>
                <div class="exp-text"><el-icon color="#409EFF"><InfoFilled /></el-icon> {{ exp.explanation }}</div>
              </div>
            </el-card>
          </div>

          <div v-if="result" class="result-panel">
            <el-divider />
            <div style="margin-bottom:12px;font-weight:bold"><el-icon><DataLine /></el-icon> 执行结果</div>
            <el-tag :type="statusTagType" size="large" effect="dark">{{ statusText }}</el-tag>
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

    <!-- ====== AI 手把手教学模式 ====== -->
    <el-row v-else :gutter="16" class="lab-body">
      <!-- 左侧：步骤列表 + 当前步骤指导 -->
      <el-col :span="8">
        <el-card shadow="hover" class="task-panel">
          <template #header>
            <span><el-icon><Guide /></el-icon> 教学步骤</span>
            <el-tag v-if="stepGuide" type="success" size="small" style="margin-left:8px">
              {{ completedSteps }}/{{ stepGuide.steps.length }} 步
            </el-tag>
          </template>

          <el-skeleton v-if="loadingGuide" :rows="6" animated />
          <el-empty v-else-if="!stepGuide" description="点击「开始教学」生成步骤" />

          <div v-else>
            <!-- 步骤进度条 -->
            <el-steps :active="currentStep" direction="vertical" :space="20" style="margin-bottom:16px">
              <el-step v-for="(s, i) in stepGuide.steps" :key="i"
                :title="s.title"
                :status="i < currentStep ? 'success' : i === currentStep ? 'process' : 'wait'"
                :description="i === currentStep ? '当前步骤' : i < currentStep ? '已完成' : ''"
              />
            </el-steps>

            <!-- 当前步骤详细指导 -->
            <el-divider />
            <div class="step-instruction">
              <h4>{{ stepGuide.steps[currentStep]?.title }}</h4>
              <el-alert type="info" :closable="false" show-icon style="margin-bottom:8px">
                {{ stepGuide.steps[currentStep]?.instruction }}
              </el-alert>

              <!-- 示例代码 -->
              <div v-if="stepGuide.steps[currentStep]?.example_code" class="step-example">
                <div class="example-header">
                  <span class="example-label">📝 照着敲以下代码：</span>
                  <el-button size="small" text @click="copyExampleCode">
                    <el-icon><CopyDocument /></el-icon> 复制
                  </el-button>
                </div>
                <pre class="example-code"><code>{{ stepGuide.steps[currentStep].example_code }}</code></pre>
              </div>

              <div v-if="stepGuide.steps[currentStep]?.hint" class="step-hint">
                <el-icon color="#E6A23C"><InfoFilled /></el-icon>
                {{ stepGuide.steps[currentStep].hint }}
              </div>
              <div class="step-expected">
                <el-tag type="success" effect="plain">{{ stepGuide.steps[currentStep]?.expected }}</el-tag>
              </div>
            </div>

            <!-- AI 反馈 -->
            <div v-if="stepFeedback" class="step-feedback" :class="stepFeedback.passed ? 'fb-pass' : 'fb-fail'">
              <el-divider />
              <p><strong>{{ stepFeedback.passed ? '✓ 通过' : '✗ 未通过' }}</strong></p>
              <p>{{ stepFeedback.feedback }}</p>
              <p v-if="stepFeedback.issue" style="color:#F56C6C;font-size:13px">{{ stepFeedback.issue }}</p>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：代码编辑 -->
      <el-col :span="16">
        <el-card shadow="hover" class="editor-panel">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>
                <el-icon><Edit /></el-icon> 代码编辑 - 第 {{ currentStep + 1 }} 步
              </span>
              <div style="display:flex;gap:8px">
                <el-button v-if="!stepGuide" type="primary" @click="startStepGuide" :loading="loadingGuide">
                  <el-icon><Cpu /></el-icon> AI 生成教学步骤
                </el-button>
                <template v-else>
                  <el-button @click="resetStepCode" :disabled="currentStep === 0 && !stepCode">
                    <el-icon><RefreshRight /></el-icon> 重置
                  </el-button>
                  <el-button type="primary" @click="submitStep" :loading="checkingStep">
                    <el-icon><Finished /></el-icon> 提交当前步骤
                  </el-button>
                  <el-button v-if="currentStep < stepGuide.steps.length - 1 && stepFeedback?.passed"
                    type="success" @click="nextStep">
                    下一步 <el-icon><ArrowRight /></el-icon>
                  </el-button>
                  <el-button v-if="stepFeedback?.passed && currentStep === stepGuide.steps.length - 1"
                    type="success" @click="goBack">
                    <el-icon><CircleCheck /></el-icon> 完成教学
                  </el-button>
                </template>
              </div>
            </div>
          </template>

          <div class="editor-wrapper">
            <textarea
              v-model="stepCode"
              class="code-editor"
              spellcheck="false"
              @keydown="handleStepKeydown"
              :placeholder="stepGuide ? '// 第' + (currentStep+1) + '步: ' + stepGuide.steps[currentStep]?.title + '\n// 在这里编写代码...' : '点击「AI 生成教学步骤」开始'"
            ></textarea>
          </div>

          <!-- 步骤执行结果 -->
          <div v-if="stepResult" class="result-panel">
            <el-divider />
            <div style="font-weight:bold;margin-bottom:8px"><el-icon><DataLine /></el-icon> 运行结果</div>
            <div v-if="stepResult.test_results?.length" class="test-results">
              <div v-for="(tr, i) in stepResult.test_results" :key="i"
                   :class="['test-result-item', tr.status === 'passed' ? 'passed' : 'failed']">
                <div class="tr-header">
                  <el-icon :color="tr.status==='passed'?'#67C23A':'#F56C6C'">
                    <CircleCheck v-if="tr.status==='passed'"/><CircleClose v-else/>
                  </el-icon>
                  <strong>{{ tr.name }}</strong>
                </div>
                <div class="tr-msg">{{ tr.message }}</div>
              </div>
            </div>
            <div v-if="stepResult.stdout" class="output-block"><h4>输出</h4><pre class="output stdout">{{ stepResult.stdout }}</pre></div>
            <div v-if="stepResult.stderr" class="output-block"><h4>错误</h4><pre class="output stderr">{{ stepResult.stderr }}</pre></div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getCodeTask, executeCode, getCodeAnswer, generateCodeStepGuide, checkCodeStep } from '../api/learning'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const taskDay = parseInt(route.params.taskDay) || 1

// 模式
const mode = ref('free')

// 自由模式状态
const taskInfo = ref(null)
const code = ref('')
const starterCode = ref('')
const result = ref(null)
const running = ref(false)
const testing = ref(false)
const editorRef = ref(null)
const showAnswer = ref(false)
const answerData = ref(null)
const answerLoading = ref(false)
const testStatuses = ref({})

// 手把手教学模式状态
const stepGuide = ref(null)
const currentStep = ref(0)
const stepCode = ref('')
const stepFeedback = ref(null)
const stepResult = ref(null)
const loadingGuide = ref(false)
const checkingStep = ref(false)

const completedSteps = computed(() => {
  if (!stepFeedback.value?.passed) return currentStep.value
  return currentStep.value + 1
})

onMounted(async () => {
  try {
    const data = await getCodeTask(taskDay)
    taskInfo.value = data
    starterCode.value = data.starter_code || ''
    code.value = data.starter_code || ''
    stepCode.value = data.starter_code || ''
  } catch(e) {
    ElMessage.error('获取编程任务失败: ' + (e?.message || '请先生成学习路径'))
  }
})

const statusTagType = computed(() => {
  if (!result.value) return 'info'
  if (result.value.compile_status === 'success') return 'success'
  if (result.value.compile_status === 'timeout') return 'warning'
  return 'danger'
})

const statusText = computed(() => {
  if (!result.value) return ''
  if (result.value.compile_status === 'success') return '编译成功'
  if (result.value.compile_status === 'timeout') return '执行超时'
  return '编译失败'
})

function getTestStatus(name) {
  const s = testStatuses.value[name]
  if (s === 'passed') return 'success'
  if (s === 'failed') return 'danger'
  if (s === 'warning') return 'warning'
  return 'info'
}

function tcResultStyle(name) {
  const s = testStatuses.value[name]
  if (s === 'passed') return 'success'
  if (s === 'failed') return 'danger'
  if (s === 'warning') return 'warning'
  return 'info'
}

async function runCode() {
  if (!code.value.trim()) {
    ElMessage.warning('请先编写代码')
    return
  }
  running.value = true
  result.value = null
  testStatuses.value = {}
  showAnswer.value = false
  answerData.value = null
  try {
    const res = await executeCode({ task_day: taskDay, code: code.value })
    result.value = res
    updateTestStatuses(res)
    if (res.compile_status === 'success') {
      ElMessage.success('代码运行成功')
    } else {
      ElMessage.warning('代码运行有误，请查看输出')
    }
  } catch(e) {
    ElMessage.error('执行失败: ' + (e?.message || ''))
  } finally {
    running.value = false
  }
}

async function runTests() {
  if (!code.value.trim()) {
    ElMessage.warning('请先编写代码')
    return
  }
  testing.value = true
  result.value = null
  testStatuses.value = {}
  showAnswer.value = false
  answerData.value = null
  try {
    const res = await executeCode({ task_day: taskDay, code: code.value })
    result.value = res
    updateTestStatuses(res)
    const passed = res.test_results?.filter(t => t.status === 'passed').length || 0
    const total = res.test_results?.length || 0
    if (res.all_passed) {
      ElMessage.success(`全部 ${total} 项测试通过！`)
    } else {
      ElMessage.warning(`${passed}/${total} 项测试通过`)
    }
  } catch(e) {
    ElMessage.error('测试失败: ' + (e?.message || ''))
  } finally {
    testing.value = false
  }
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
  answerData.value = null
  ElMessage.info('代码已重置')
}

function handleKeydown(e) {
  // Tab key support
  if (e.key === 'Tab') {
    e.preventDefault()
    const ta = editorRef.value
    if (!ta) return
    const start = ta.selectionStart
    const end = ta.selectionEnd
    code.value = code.value.substring(0, start) + '    ' + code.value.substring(end)
    // Set cursor position after tab
    setTimeout(() => {
      ta.selectionStart = ta.selectionEnd = start + 4
    }, 0)
  }
}

async function viewAnswer() {
  answerLoading.value = true
  showAnswer.value = true
  try {
    const data = await getCodeAnswer(taskDay)
    answerData.value = data
  } catch(e) {
    ElMessage.error('获取答案失败: ' + (e?.message || ''))
    showAnswer.value = false
  } finally {
    answerLoading.value = false
  }
}

function retryCompile() {
  showAnswer.value = false
  answerData.value = null
  // Re-run the tests
  runTests()
}

function applyAnswer() {
  if (answerData.value?.answer_code) {
    code.value = answerData.value.answer_code
    ElMessage.success('答案已应用到编辑器，可点击编译测试验证')
  }
}

// ===== 手把手教学模式 =====

async function switchMode(val) {
  if (val === 'step' && !stepGuide.value) {
    await startStepGuide()
  }
}

async function startStepGuide() {
  loadingGuide.value = true
  stepFeedback.value = null
  stepResult.value = null
  try {
    const data = await generateCodeStepGuide({ task_day: taskDay })
    if (data.steps?.length) {
      stepGuide.value = data
      currentStep.value = 0
      stepCode.value = starterCode.value
      ElMessage.success(`AI 已将任务分解为 ${data.steps.length} 个步骤`)
    } else {
      ElMessage.error(data.error || '生成步骤失败')
    }
  } catch(e) {
    ElMessage.error('生成教学步骤失败: ' + (e?.message || '请确认已配置 AI API Key'))
  } finally {
    loadingGuide.value = false
  }
}

async function submitStep() {
  if (!stepCode.value.trim()) {
    ElMessage.warning('请先编写代码')
    return
  }
  checkingStep.value = true
  stepFeedback.value = null
  stepResult.value = null
  try {
    const curStep = stepGuide.value?.steps[currentStep.value]
    const data = await checkCodeStep({
      task_day: taskDay,
      step_index: currentStep.value,
      code: stepCode.value,
      step_title: curStep?.title || '',
      step_instruction: curStep?.instruction || ''
    })
    stepFeedback.value = data

    // 显示执行结果
    if (data.exec_result) {
      stepResult.value = data.exec_result
    }

    if (data.passed) {
      ElMessage.success('当前步骤通过！')
    } else {
      ElMessage.warning('代码还有问题，看看 AI 的建议')
    }
  } catch(e) {
    ElMessage.error('检查失败: ' + (e?.message || '请重试'))
  } finally {
    checkingStep.value = false
  }
}

function nextStep() {
  if (currentStep.value < (stepGuide.value?.steps.length || 0) - 1) {
    currentStep.value++
    stepFeedback.value = null
    stepResult.value = null
    ElMessage.info(`进入第 ${currentStep.value + 1} 步`)
  }
}

function resetStepCode() {
  stepCode.value = starterCode.value
  stepFeedback.value = null
  stepResult.value = null
}

function copyExampleCode() {
  const code = stepGuide.value?.steps[currentStep.value]?.example_code
  if (code) {
    navigator.clipboard.writeText(code).then(() => {
      ElMessage.success('示例代码已复制到剪贴板')
    }).catch(() => {
      ElMessage.info('请手动复制代码')
    })
  }
}

function handleStepKeydown(e) {
  if (e.key === 'Tab') {
    e.preventDefault()
    const ta = e.target
    if (!ta) return
    const start = ta.selectionStart
    const end = ta.selectionEnd
    stepCode.value = stepCode.value.substring(0, start) + '    ' + stepCode.value.substring(end)
    setTimeout(() => { ta.selectionStart = ta.selectionEnd = start + 4 }, 0)
  }
}

// ===== 通用 =====

function goBack() {
  router.push('/learning-path')
}
</script>

<style scoped>
.code-lab-page {
  max-width: 1400px;
  margin: 0 auto;
}
.lab-header {
  margin-bottom: 12px;
}
.lab-body {
  margin: 0 !important;
}
.task-panel {
  height: calc(100vh - 140px);
  overflow-y: auto;
}
.task-section h4 {
  font-size: 14px;
  margin-bottom: 8px;
  color: #303133;
}
.task-section p,
.task-section li {
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
}
.test-case-card {
  padding: 10px 12px;
  margin-bottom: 8px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #f0f0f0;
}
.tc-header {
  display: flex;
  align-items: center;
  margin-bottom: 4px;
}
.tc-desc {
  font-size: 12px;
  color: #909399;
  margin-left: 26px;
}
.editor-panel {
  height: calc(100vh - 140px);
  display: flex;
  flex-direction: column;
}
.editor-wrapper {
  flex: 1;
  min-height: 350px;
}
.code-editor {
  width: 100%;
  height: 100%;
  min-height: 350px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 14px 16px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', 'Monaco', monospace;
  font-size: 14px;
  line-height: 1.6;
  resize: none;
  outline: none;
  background: #1e1e1e;
  color: #d4d4d4;
  tab-size: 4;
}
.code-editor:focus {
  border-color: #409EFF;
}
.code-editor::placeholder {
  color: #6a6a6a;
}
.result-panel {
  margin-top: 8px;
}
.result-panel h4 {
  font-size: 13px;
  margin-bottom: 8px;
  color: #303133;
}
.test-result-item {
  padding: 10px 12px;
  margin-bottom: 6px;
  border-radius: 6px;
  border-left: 4px solid #e0e0e0;
}
.test-result-item.passed {
  border-left-color: #67C23A;
  background: #f0faf4;
}
.test-result-item.failed {
  border-left-color: #F56C6C;
  background: #fef0f0;
}
.test-result-item.warning {
  border-left-color: #E6A23C;
  background: #fef9f0;
}
.tr-header {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
}
.tr-desc {
  color: #909399;
  font-size: 12px;
}
.tr-msg {
  margin-top: 4px;
  margin-left: 20px;
  font-size: 12px;
  color: #606266;
}
.tr-compare {
  margin: 6px 0 0 20px;
  font-size: 12px;
}
.tr-expected {
  color: #67C23A;
  margin-bottom: 2px;
}
.tr-expected code {
  background: #f0faf4;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Consolas', monospace;
}
.tr-actual {
  color: #F56C6C;
}
.tr-actual code {
  background: #fef0f0;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Consolas', monospace;
}
.output-block {
  margin-top: 12px;
}
.output {
  padding: 12px;
  border-radius: 6px;
  font-family: 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
}
.output.stdout {
  background: #f5f7fa;
  color: #303133;
  border: 1px solid #e8e8e8;
}
.output.stderr {
  background: #fef0f0;
  color: #F56C6C;
  border: 1px solid #fde2e2;
}
.answer-prompt {
  margin-top: 12px;
}
.answer-panel {
  margin-top: 12px;
  max-height: 500px;
  overflow-y: auto;
}
.explanation-item {
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}
.explanation-item:last-child {
  border-bottom: none;
}
.exp-line {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 4px;
}
.exp-line-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 22px;
  font-size: 11px;
  color: #909399;
  background: #f0f0f0;
  border-radius: 4px;
  flex-shrink: 0;
}
.exp-code {
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
  color: #303133;
  white-space: pre-wrap;
  word-break: break-all;
}
.exp-text {
  margin-left: 32px;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

/* 手把手教学模式 */
.lab-header {
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 8px;
}
.step-instruction h4 {
  font-size: 15px;
  color: #303133;
  margin-bottom: 8px;
}
.step-hint {
  padding: 8px 12px;
  background: #fef9f0;
  border-radius: 6px;
  font-size: 13px;
  color: #E6A23C;
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-bottom: 8px;
}
.step-expected {
  margin-top: 4px;
}
.step-feedback {
  margin-top: 8px;
  padding: 12px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
}
.step-feedback.fb-pass {
  background: #f0f9eb;
  border: 1px solid #b3e19d;
}
.step-feedback.fb-fail {
  background: #fef0f0;
  border: 1px solid #fab6b6;
}

.step-example {
  margin-bottom: 12px;
  background: #1e1e1e;
  border-radius: 8px;
  overflow: hidden;
}
.example-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  background: #2d2d2d;
  border-bottom: 1px solid #404040;
}
.example-label {
  font-size: 13px;
  color: #e0e0e0;
  font-weight: 500;
}
.example-code {
  margin: 0;
  padding: 14px 16px;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.7;
  color: #d4d4d4;
  white-space: pre;
  overflow-x: auto;
  max-height: 250px;
  overflow-y: auto;
}
</style>
