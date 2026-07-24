<template>
  <!-- 第2层：关卡列表页面（头歌风格 - 左侧竖直目录） -->
  <div class="task-list-page">
    <!-- 顶部模块标题 -->
    <div class="top-bar">
      <el-breadcrumb separator=">">
        <el-breadcrumb-item :to="{ name: 'ModuleSelect' }">编程实验室</el-breadcrumb-item>
        <el-breadcrumb-item>{{ currentModule?.name || '加载中...' }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 主体：左侧关卡目录 + 右侧空白区 -->
    <div class="task-body">
      <!-- 左侧：关卡目录列表 -->
      <div class="task-sidebar">
        <div class="sidebar-header">
          <span class="sidebar-title">关卡目录</span>
          <span class="sidebar-count">共 {{ currentModule?.taskCount || 0 }} 关</span>
        </div>
        <div class="sidebar-list">
          <div
            v-for="(task, index) in currentModule?.tasks || []"
            :key="task.id"
            class="task-item"
            :class="{ active: selectedTaskId === task.id, completed: isCompleted(task.id) }"
            @click="selectTask(task)"
          >
            <div class="task-num">{{ index + 1 }}</div>
            <div class="task-text">
              <div class="task-label">关卡 {{ task.id }}</div>
              <div class="task-name">{{ task.title }}</div>
            </div>
            <!-- 分数标识 -->
            <span v-if="getScoreBadge(task.id)" :class="['task-score-badge', getScoreBadge(task.id).cls]">
              {{ getScoreBadge(task.id).text }}
            </span>
            <span v-else-if="isCompleted(task.id)" class="task-dot done">✓</span>
            <span v-else class="task-dot pending">○</span>
          </div>
        </div>
      </div>

      <!-- 右侧：预览/空白区 -->
      <div class="task-main">
        <div v-if="selectedTask" class="task-preview">
          <el-tag size="small" type="primary" effect="plain">{{ currentModule?.level }}阶段</el-tag>
          <h3>关卡 {{ selectedTask.id }}：{{ selectedTask.title }}</h3>
          <p class="project-name">正在构建：{{ currentModule?.project }}</p>
          <p class="task-duration">建议用时 {{ selectedTask.duration }}</p>

          <!-- 分数详情 -->
          <div v-if="getScoreDetail(selectedTask.id)" class="score-detail">
            <div class="score-ring-wrap">
              <div :class="['score-circle', getScoreLevel(getScoreDetail(selectedTask.id).score)]">
                <span class="score-number">{{ getScoreDetail(selectedTask.id).score }}</span>
                <span class="score-label">综合分</span>
              </div>
            </div>
            <div class="score-breakdown">
              <div class="score-row">
                <span>测试点</span>
                <span :class="getScoreDetail(selectedTask.id).test_score >= 60 ? 'pass' : 'fail'">
                  {{ getScoreDetail(selectedTask.id).test_score || 0 }} 分
                </span>
              </div>
              <div class="score-row">
                <span>原理答辩</span>
                <span>{{ getScoreDetail(selectedTask.id).defense_score || 0 }} 分</span>
              </div>
              <div class="score-row">
                <span>故障修复</span>
                <span>{{ getScoreDetail(selectedTask.id).repair_score || 0 }} 分</span>
              </div>
              <div class="score-row" style="margin-top:6px;padding-top:6px;border-top:1px solid #ebeef5">
                <span>{{ getScoreDetail(selectedTask.id).skipped ? '⚠ 已跳过能力验证' : getScoreDetail(selectedTask.id).verified ? '✓ 能力已验证' : '进行中' }}</span>
                <span :class="getScoreDetail(selectedTask.id).skipped ? 'warn' : ''">
                  {{ getScoreDetail(selectedTask.id).skipped ? '仅测试分' : getScoreDetail(selectedTask.id).verified ? '完整评估' : '' }}
                </span>
              </div>
            </div>
          </div>

          <div v-else-if="getCompletion(selectedTask.id)" class="completion-info">
            <el-tag type="success" size="large">已完成</el-tag>
            <p>用时: {{ getCompletion(selectedTask.id).time || '-' }}</p>
            <p>通过: {{ getCompletion(selectedTask.id).passedCount || '?' }}/{{ getCompletion(selectedTask.id).totalCount || '?' }} 用例</p>
            <p class="old-score-hint" style="font-size:11px;color:#909399;margin-top:4px;">（旧版记录，无详细分数。重新完成可获取分数。）</p>
          </div>

          <p class="preview-hint">点击下方按钮进入代码编辑页面</p>
          <el-button type="primary" @click="enterTask(selectedTask)">
            {{ getCompletion(selectedTask.id) || getScoreDetail(selectedTask.id) ? '重做本题' : '开始挑战' }}
          </el-button>
        </div>
        <el-empty v-else description="请从左侧关卡选择" :image-size="80" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { MODULES } from '../config/flagshipExercises'
import { getLabProgressOverview } from '../api/workspace'

const router = useRouter()
const route = useRoute()

const moduleId = computed(() => parseInt(route.params.moduleId))
const currentModule = computed(() => MODULES.find(m => m.id === moduleId.value))
const selectedTaskId = ref(currentModule.value?.tasks?.[0]?.id ?? null)
const selectedTask = ref(currentModule.value?.tasks?.[0] ?? null)
const progressData = ref({})

/**
 * 加载进度数据（含分数）
 */
onMounted(async () => {
  try {
    const data = await getLabProgressOverview()
    progressData.value = data || {}
  } catch (_) {
    progressData.value = {}
  }
})

/**
 * 选择关卡（右侧显示预览，不直接跳转）
 */
function selectTask(task) {
  selectedTaskId.value = task.id
  selectedTask.value = task
}

/**
 * 进入代码编辑页面
 */
function enterTask(task) {
  router.push({
    name: 'CodeLab',
    params: { moduleId: moduleId.value, taskId: task.id }
  })
}

/**
 * 读取关卡完成状态（从 localStorage — 旧版兼容）
 */
function getCompletion(taskId) {
  try {
    const completed = JSON.parse(localStorage.getItem('code_completed') || '{}')
    const key = `${moduleId.value}_${taskId}`
    return completed[key] || null
  } catch {
    return null
  }
}

function isCompleted(taskId) {
  return !!getCompletion(taskId) || !!getScoreDetail(taskId)
}

/**
 * 获取分数详情（从后端 progress 数据）
 */
function getScoreDetail(taskId) {
  const info = progressData.value[taskId]
  if (!info) return null
  if (info.score == null && !info.verified && !info.skipped) {
    // acceptance passed 但无分数 → 不显示分数
    if (!info.acceptance_passed) return null
  }
  if (info.score == null && !info.verified && !info.skipped) return null
  return {
    score: info.score || 0,
    test_score: info.test_score || 0,
    defense_score: info.defense_score || 0,
    repair_score: info.repair_score || 0,
    verified: info.verified || false,
    skipped: info.skipped || false,
    status: info.status || '',
  }
}

/**
 * 获取分数徽标
 */
function getScoreBadge(taskId) {
  const detail = getScoreDetail(taskId)
  if (!detail) {
    // 兼容旧数据
    const comp = getCompletion(taskId)
    if (comp) return { text: '✓', cls: 'old' }
    return null
  }
  if (detail.verified) {
    const level = getScoreLevel(detail.score)
    return { text: `${detail.score}分`, cls: level }
  }
  if (detail.skipped) {
    return { text: `${detail.score}分`, cls: 'skipped' }
  }
  return null
}

function getScoreLevel(score) {
  if (score >= 90) return 'excellent'
  if (score >= 75) return 'good'
  if (score >= 60) return 'pass'
  return 'low'
}
</script>

<style scoped>
.task-list-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: #f5f6f8;
}
.top-bar {
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}
.task-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* ===== 左侧关卡目录 ===== */
.task-sidebar {
  width: 320px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}
.sidebar-title {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a2e;
}
.sidebar-count {
  font-size: 12px;
  color: #909399;
}
.sidebar-list {
  flex: 1;
  overflow-y: auto;
}

/* 关卡条目 */
.task-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f5f5f5;
  transition: background .15s;
}
.task-item:hover {
  background: #f5f7fa;
}
.task-item.active {
  background: #e6f0ff;
  border-left: 3px solid #409EFF;
}
.task-item.completed .task-num {
  background: #67C23A;
}
.task-num {
  width: 28px;
  height: 28px;
  border-radius: 4px;
  background: #c0c4cc;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.task-item.active .task-num {
  background: #409EFF;
}
.task-text {
  flex: 1;
  min-width: 0;
}
.task-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 2px;
}
.task-name {
  font-size: 13px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.task-dot {
  font-size: 16px;
  flex-shrink: 0;
}
.task-dot.done {
  color: #67C23A;
}
.task-dot.pending {
  color: #c0c4cc;
}

/* 分数徽标 */
.task-score-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 10px;
  flex-shrink: 0;
  white-space: nowrap;
}
.task-score-badge.excellent {
  background: #e6f7e6;
  color: #2e8b57;
  border: 1px solid #a3d9a3;
}
.task-score-badge.good {
  background: #e6f4ff;
  color: #2979c1;
  border: 1px solid #93c5fd;
}
.task-score-badge.pass {
  background: #fff8e6;
  color: #b8860b;
  border: 1px solid #f0d78c;
}
.task-score-badge.low {
  background: #fff0f0;
  color: #c0392b;
  border: 1px solid #f5a6a6;
}
.task-score-badge.skipped {
  background: #f5f5f5;
  color: #888;
  border: 1px solid #d0d0d0;
}
.task-score-badge.old {
  font-size: 12px;
  color: #67C23A;
  padding: 0;
  background: none;
  border: none;
}

/* ===== 右侧预览区 ===== */
.task-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}
.task-preview {
  text-align: center;
  max-width: 420px;
}
.task-preview h3 {
  font-size: 18px;
  color: #1a1a2e;
  margin: 0 0 8px;
}
.preview-hint {
  font-size: 14px;
  color: #909399;
  margin: 0 0 20px;
}
.project-name { color: #303133; font-size: 14px; font-weight: 600; margin: 10px 0 4px; }
.task-duration { color: #909399; font-size: 13px; margin: 0 0 14px; }
.completion-info {
  background: #f0f9eb;
  border: 1px solid #c2e7b0;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
}
.completion-info p {
  font-size: 13px;
  color: #606266;
  margin: 4px 0;
}
.old-score-hint {
  font-size: 11px;
  color: #909399;
  margin-top: 4px;
}

/* 分数详情面板 */
.score-detail {
  background: #fafbff;
  border: 1px solid #e0e4f0;
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 16px;
}
.score-ring-wrap {
  display: flex;
  justify-content: center;
  margin-bottom: 12px;
}
.score-circle {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 4px solid #c0c4cc;
}
.score-circle.excellent { border-color: #2e8b57; background: #f0faf4; }
.score-circle.good { border-color: #2979c1; background: #f0f6ff; }
.score-circle.pass { border-color: #e6a817; background: #fffdf5; }
.score-circle.low { border-color: #c0392b; background: #fff5f5; }
.score-number {
  font-size: 22px;
  font-weight: 800;
  color: #1a1a2e;
  line-height: 1;
}
.score-label {
  font-size: 10px;
  color: #909399;
  margin-top: 2px;
}
.score-breakdown {
  text-align: left;
  font-size: 12px;
}
.score-row {
  display: flex;
  justify-content: space-between;
  padding: 3px 0;
  color: #606266;
}
.score-row span:last-child {
  font-weight: 600;
}
.score-row .pass { color: #2e8b57; }
.score-row .fail { color: #c0392b; }
.score-row .warn { color: #e6a817; }
</style>
