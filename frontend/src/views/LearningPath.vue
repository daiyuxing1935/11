<template>
  <div class="learning-path-page">
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <div class="page-title"><el-icon><Guide /></el-icon> 个性化学习路径</div>
              <div style="display:flex;gap:8px">
                <el-popconfirm
                  v-if="pathData?.phases"
                  title="确定要删除当前学习路径吗？删除后无法恢复。"
                  confirm-button-text="确认删除"
                  cancel-button-text="取消"
                  @confirm="deletePath"
                >
                  <template #reference>
                    <el-button type="danger" plain>删除路径</el-button>
                  </template>
                </el-popconfirm>
                <el-button type="primary" @click="openGenerateDialog">生成/更新路径</el-button>
              </div>
            </div>
          </template>

          <!-- 周选择按钮 -->
          <div v-if="weeks.length > 0" class="week-tabs">
            <el-button
              v-for="w in weeks"
              :key="w.num"
              :type="activeWeek === w.num ? 'primary' : ''"
              :plain="activeWeek !== w.num"
              size="large"
              @click="activeWeek = w.num"
            >
              第{{ w.num }}周
              <el-tag :type="activeWeek === w.num ? 'warning' : 'info'" size="small" style="margin-left:6px" effect="dark">
                {{ w.done }}/{{ w.total }}
              </el-tag>
            </el-button>
          </div>

          <el-empty v-if="!pathData?.phases" description="尚未生成学习路径，请点击右上角按钮生成">
            <el-button type="primary" @click="openGenerateDialog">AI生成个性化学习路径</el-button>
          </el-empty>

          <!-- 当前周的任务 -->
          <div v-if="currentWeekTasks.length > 0" class="week-content">
            <div
              v-for="(task, ti) in currentWeekTasks"
              :key="ti"
              class="task-card"
              :class="{
                'task-done': getTaskStatus(task).allDone,
                'task-partial': getTaskStatus(task).done > 0 && !getTaskStatus(task).allDone,
                'task-pending': getTaskStatus(task).done === 0,
                'task-remedial': task.remedial
              }"
            >
              <!-- 复习任务标记 -->
              <div v-if="task.remedial" class="remedial-badge">
                <el-tag type="danger" size="small" effect="dark">🔥 针对性复习</el-tag>
                <span v-if="task.source_day" class="remedial-source">第{{ task.source_day }}天正确率仅{{ task.correct_rate }}%</span>
              </div>

              <div class="task-header">
                <div class="task-day">第{{ task.day }}天</div>
                <el-tag v-if="getTaskStatus(task).allDone" type="success" size="small" effect="dark">✅ 已完成</el-tag>
                <el-tag v-else-if="getTaskStatus(task).done > 0" type="warning" size="small" effect="dark">⏳ {{ getTaskStatus(task).done }}/2</el-tag>
              </div>

              <div class="task-topic">{{ task.topic }}</div>
              <div class="task-meta">
                <el-tag size="small" type="primary" effect="plain">{{ task.phaseName }}</el-tag>
              </div>
              <div class="task-detail">知识点: {{ task.knowledge }}</div>
              <div class="task-detail">行动: {{ task.action }}</div>
              <div class="task-detail">资源: {{ task.resource }}</div>
              <div class="task-detail">验收: {{ task.check }}</div>

              <div class="task-actions">
                <el-button type="warning" size="small" :loading="learnLoading[task.day]" @click="goToLearning(task)"
                  :class="{ 'btn-done': getTaskStatus(task).learn }">
                  <el-icon v-if="!getTaskStatus(task).learn"><Reading /></el-icon>
                  <el-icon v-else><CircleCheck /></el-icon>
                  {{ getTaskStatus(task).learn ? '已学习' : '去学习' }}
                </el-button>
                <el-button type="primary" size="small" :loading="quizLoading[task.day]" @click="goToTaskQuiz(task)"
                  :class="{ 'btn-done': getTaskStatus(task).quiz }">
                  <el-icon v-if="!getTaskStatus(task).quiz"><EditPen /></el-icon>
                  <el-icon v-else><CircleCheck /></el-icon>
                  {{ getTaskStatus(task).quiz ? '已做题' : '去做题' }}
                </el-button>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>学习概览</template>
          <div v-if="pathData">
            <el-statistic title="预计总天数" :value="pathData.estimated_total_days || 0" />
            <el-divider />
            <div class="weekly-goals">
              <h4>每周目标</h4>
              <div v-for="(goal, i) in pathData.weekly_goals" :key="i" class="goal-item">
                <el-icon color="#67C23A"><CircleCheck /></el-icon> {{ goal }}
              </div>
            </div>
            <el-divider />
            <div class="milestones">
              <h4>关键里程碑</h4>
              <el-tag v-for="m in pathData.key_milestones" :key="m" type="warning" style="margin:4px;display:block">{{ m }}</el-tag>
            </div>
            <el-divider />
            <el-alert :title="pathData.tips" type="info" :closable="false" />
            <!-- 诊断掌握等级 -->
            <el-divider v-if="pathData.diagnostic_level" />
            <el-alert v-if="pathData.diagnostic_level" :title="'诊断测评等级: ' + pathData.diagnostic_level" type="success" :closable="false" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 生成/更新路径 Dialog — 模块选择模式 -->
    <el-dialog v-model="showDialog" title="选择学习模块" width="560px" :close-on-click-modal="false">
      <el-alert type="info" :closable="false" style="margin-bottom:20px"
        title="勾选要学习的模块，系统将从对应模块知识中自动构建学习路径。" />

      <el-checkbox-group v-model="genForm.selectedModules" class="module-checkbox-group">
        <el-checkbox
          v-for="m in availableModules"
          :key="m"
          :label="m"
          border
          size="large"
          class="module-checkbox"
        >
          <div class="module-label">{{ m }}</div>
          <div class="module-desc">{{ getModuleDesc(m) }}</div>
        </el-checkbox>
      </el-checkbox-group>

      <div v-if="genForm.selectedModules.length > 0" style="margin-top:16px;color:#409EFF;font-size:13px">
        已选 {{ genForm.selectedModules.length }} 个模块，预计生成约 {{ genForm.selectedModules.length * 8 }}~{{ genForm.selectedModules.length * 15 }} 天的学习任务
      </div>

      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button
          type="primary"
          @click="generateModulePath"
          :loading="loading"
          :disabled="genForm.selectedModules.length === 0"
        >
          生成学习路径
        </el-button>
      </template>
    </el-dialog>

    <!-- 学习资料弹窗 -->
    <el-dialog v-model="learnDialogVisible" :title="learnDialogTitle" width="90%" top="3vh" :close-on-click-modal="false" destroy-on-close
      @closed="onLearnDialogClosed">
      <div v-if="learnDialogLoading" style="text-align:center;padding:40px">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <p style="margin-top:12px;color:#909399">加载学习资料中...</p>
      </div>
      <div v-else class="learn-material-content" v-html="learnDialogContent"></div>
      <template #footer>
        <el-button type="primary" @click="learnDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useLearningStore } from '../stores/learning'
import { useDiagnosisStore } from '../stores/diagnosis'
import { generateTaskQuiz, getLearningResource, recordStudyVisit } from '../api/learning'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'

const router = useRouter()
const store = useLearningStore()
const diagnosisStore = useDiagnosisStore()
const pathData = ref(null)
const progressData = ref({})
const showDialog = ref(false)
const loading = ref(false)
const genForm = reactive({ selectedModules: [] })
const doneTasks = ref([])
const activeWeek = ref(1)
const quizLoading = reactive({})
const learnLoading = reactive({})
// 学习资料弹窗
const learnDialogVisible = ref(false)
const learnDialogTitle = ref('')
const learnDialogContent = ref('')
const learnDialogLoading = ref(false)
const currentLearnTask = ref(null)

// 六大模块
const availableModules = [
  '智能体基础通识',
  '大模型与提示词工程',
  '智能体四大核心能力模块',
  '开发框架与工程实践',
  '多智能体系统',
  '评估安全与前沿拓展',
]

const moduleDescs = {
  '智能体基础通识': 'AI智能体定义、分类、核心特征、架构设计、运行闭环',
  '大模型与提示词工程': 'Transformer架构、LoRA微调、提示词技术、思维链',
  '智能体四大核心能力模块': '感知、记忆、规划、行动模块 + 算法逻辑',
  '开发框架与工程实践': 'LangChain、LlamaIndex、CrewAI、RAG技术',
  '多智能体系统': '多Agent协作、架构模式、通信机制、博弈论',
  '评估安全与前沿拓展': 'Agent评估基准、安全治理、MCP协议、具身智能',
}

function getModuleDesc(name) {
  return moduleDescs[name] || ''
}

onMounted(async () => {
  recordStudyVisit()
  await loadPath()
})

async function loadPath() {
  try {
    const path = await store.fetchPath()
    if (path && path.path_data?.phases && path.path_data.phases.length > 0) {
      pathData.value = path.path_data
      progressData.value = path.progress || {}
      doneTasks.value = path.progress?.completed_tasks || []
    } else {
      // 路径记录存在但内容为空（如LLM生成失败导致的空数据），视为无路径
      pathData.value = null
      progressData.value = {}
      doneTasks.value = []
      // 如果后台有残留空路径记录，自动清除
      if (path && path.id && !path.path_data?.phases) {
        try { await store.removePath() } catch {}
      }
    }
  } catch(e) {
    pathData.value = null
  }
}

async function openGenerateDialog() {
  // 重新加载最新路径数据，避免使用过期缓存
  await loadPath()
  genForm.selectedModules = pathData.value?.modules_selected ? [...pathData.value.modules_selected] : []
  showDialog.value = true
}

function closeDialog() {
  showDialog.value = false
}

async function generateModulePath() {
  if (genForm.selectedModules.length === 0) {
    ElMessage.warning('请至少选择一个学习模块')
    return
  }
  // 防御：深拷贝选中模块，防止意外修改
  const selected = [...genForm.selectedModules]
  loading.value = true
  try {
    await store.createPath('', '', '标准', null, selected)
    await loadPath()
    activeWeek.value = 1
    closeDialog()
    ElMessage.success(`学习路径已生成！共 ${selected.length} 个模块，${pathData.value?.estimated_total_days || 0} 天学习任务`)
  } catch(e) {
    const msg = e?.response?.data?.detail || e?.message || '生成失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

async function deletePath() {
  try {
    await store.removePath()
    pathData.value = null
    progressData.value = {}
    doneTasks.value = []
    ElMessage.success('学习路径已删除')
  } catch(e) {
    ElMessage.error('删除失败，请重试')
  }
}

// 收集所有任务
const allTasks = computed(() => {
  const tasks = []
  if (!pathData.value?.phases) return tasks
  for (const phase of pathData.value.phases) {
    for (const task of (phase.tasks || [])) {
      tasks.push({
        ...task,
        phaseName: phase.name || '',
        week: Math.ceil((task.day || 1) / 7)
      })
    }
  }
  return tasks
})

const weeks = computed(() => {
  const map = {}
  for (const t of allTasks.value) {
    const w = t.week || 1
    if (!map[w]) map[w] = { num: w, total: 0, done: 0 }
    map[w].total++
    if (isTaskDone(t)) map[w].done++
  }
  return Object.values(map).sort((a, b) => a.num - b.num)
})

const currentWeekTasks = computed(() => {
  return allTasks.value.filter(t => (t.week || 1) === activeWeek.value)
})

function getTaskStatus(task) {
  const key = `${task.day}-${task.topic}`
  const ct = progressData.value?.completed_tasks || {}
  // 兼容旧格式（数组）
  if (Array.isArray(ct)) {
    const done = ct.includes(key)
    return { learn: done, quiz: done, code: false, done: done ? 2 : 0, allDone: done }
  }
  const status = ct[key] || { learn: false, quiz: false, code: false }
  const learn = status.learn || false
  const quiz = status.quiz || false
  const done = (learn ? 1 : 0) + (quiz ? 1 : 0)
  return { learn, quiz, code: false, done, allDone: done === 2 }
}

function isTaskDone(task) {
  return getTaskStatus(task).allDone
}

async function toggleTask(task) {
  const key = `${task.day}-${task.topic}`
  const currentStatus = getTaskStatus(task)
  const newCompleted = !currentStatus.allDone
  try {
    await store.updateProgress(key, newCompleted)
    await loadPath()
  } catch(e) {
    ElMessage.error('操作失败')
  }
}

async function goToTaskQuiz(task) {
  // 必须先完成"去学习"
  if (!getTaskStatus(task).learn) {
    ElMessage.warning('请先完成"去学习"再做题')
    return
  }
  quizLoading[task.day] = true
  try {
    const result = await generateTaskQuiz({ task_day: task.day, count: 10 })
    diagnosisStore.currentQuiz = result
    diagnosisStore.currentReport = null
    router.push(`/task-quiz/${result.session_id}`)
  } catch(e) {
    const msg = e?.response?.data?.detail || e?.response?.data?.message || e?.message || '生成练习失败，请重试'
    ElMessage.error(msg)
  } finally {
    quizLoading[task.day] = false
  }
}

async function goToLearning(task) {
  const knowledge = task.knowledge || task.topic || ''
  learnLoading[task.day] = true
  try {
    const res = await getLearningResource(knowledge)
    if (res && res.content) {
      learnDialogTitle.value = res.matched_tag || knowledge
      learnDialogContent.value = marked.parse(res.content)
      currentLearnTask.value = task
      learnDialogVisible.value = true
      // 立刻标记"去学习"完成（对话框打开即视为已学习）
      const key = `${task.day}-${task.topic}`
      try {
        await store.updateProgress(key, true, 'learn')
        await loadPath()
      } catch(err) {
        console.error('标记学习进度失败:', err)
      }
    } else {
      ElMessage.warning('该知识点的学习资料暂未准备好')
    }
  } catch(e) {
    ElMessage.error('获取学习资料失败')
  } finally {
    learnLoading[task.day] = false
  }
}

// 对话框关闭时刷新数据，确保进度显示正确
async function onLearnDialogClosed() {
  currentLearnTask.value = null
  // 刷新学习路径数据
  await loadPath()
}

</script>

<style scoped>
.page-title { display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: bold; }
.week-tabs { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
.week-content { margin-top: 8px; }
.task-card {
  padding: 20px; margin-bottom: 16px;
  background: #fff; border-radius: 12px;
  border: 2px solid #e4e7ed;
  transition: all .3s;
}
.task-card.task-done {
  border-color: #b3e19d; background: #f6ffed;
}
.task-card.task-done .task-topic {
  text-decoration: line-through; color: #909399;
}
.task-card.task-partial {
  border-color: #f5dab1; background: #fffbe6;
}
.task-card.task-remedial {
  border-color: #fab6b6; background: #fff2f0;
}
.task-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;
}
.task-day { font-size: 13px; font-weight: 600; color: #409EFF; }
.task-topic { font-size: 16px; font-weight: 600; color: #303133; margin-bottom: 8px; }
.task-meta { margin: 6px 0; }
.task-detail { font-size: 13px; color: #606266; margin: 4px 0; }

/* 复习任务标记 */
.remedial-badge {
  display: flex; align-items: center; gap: 8px; margin-bottom: 12px;
  padding: 8px 12px; background: #fef0f0; border-radius: 6px;
}
.remedial-source { font-size: 12px; color: #e6a23c; }

/* 操作按钮 */
.task-actions {
  display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; margin-top: 12px;
}
.btn-done {
  opacity: 0.6;
}
.weekly-goals h4, .milestones h4 { margin-bottom: 8px; font-size: 14px; }
.goal-item { font-size: 13px; padding: 4px 0; display: flex; align-items: center; gap: 6px; }

/* 模块选择 */
.module-checkbox-group { display: flex; flex-direction: column; gap: 8px; }
.module-checkbox { width: 100%; margin-right: 0 !important; padding: 14px 16px; border-radius: 8px; }
.module-label { font-size: 15px; font-weight: 600; color: #303133; margin-bottom: 4px; }
.module-desc { font-size: 12px; color: #909399; }

/* 学习资料 Markdown 渲染样式 */
.learn-material-content {
  max-height: 78vh;
  overflow-y: auto;
  padding: 8px 4px;
  font-size: 15px;
  line-height: 1.8;
  color: #303133;
}
.learn-material-content :deep(h1) { font-size: 22px; font-weight: 700; margin: 8px 0 16px; padding-bottom: 8px; border-bottom: 2px solid #409EFF; color: #1a1a2e; }
.learn-material-content :deep(h2) { font-size: 18px; font-weight: 600; margin: 24px 0 12px; color: #303133; border-left: 4px solid #409EFF; padding-left: 12px; }
.learn-material-content :deep(h3) { font-size: 16px; font-weight: 600; margin: 18px 0 10px; color: #409EFF; }
.learn-material-content :deep(p) { margin: 10px 0; }
.learn-material-content :deep(strong) { color: #1a1a2e; }
.learn-material-content :deep(code) { background: #f0f2f5; padding: 2px 6px; border-radius: 4px; font-size: 13px; color: #e83e8c; font-family: 'Courier New', monospace; }
.learn-material-content :deep(pre) { background: #1a1a2e; color: #f8f8f2; padding: 16px; border-radius: 8px; overflow-x: auto; margin: 12px 0; }
.learn-material-content :deep(pre code) { background: none; color: #f8f8f2; padding: 0; font-size: 13px; }
.learn-material-content :deep(ul), .learn-material-content :deep(ol) { padding-left: 24px; margin: 8px 0; }
.learn-material-content :deep(li) { margin: 4px 0; }
.learn-material-content :deep(table) { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 14px; }
.learn-material-content :deep(th) { background: #f5f7fa; padding: 10px 12px; text-align: left; font-weight: 600; border: 1px solid #e4e7ed; }
.learn-material-content :deep(td) { padding: 8px 12px; border: 1px solid #e4e7ed; }
.learn-material-content :deep(blockquote) { border-left: 4px solid #e4e7ed; padding: 8px 16px; margin: 12px 0; background: #fafafa; color: #606266; }
.learn-material-content :deep(hr) { border: none; border-top: 1px solid #e4e7ed; margin: 20px 0; }
</style>
