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
            <span v-if="isCompleted(task.id)" class="task-dot done">✓</span>
            <span v-else class="task-dot pending">○</span>
          </div>
        </div>
      </div>

      <!-- 右侧：预览/空白区 -->
      <div class="task-main">
        <div v-if="selectedTask" class="task-preview">
          <h3>关卡 {{ selectedTask.id }}：{{ selectedTask.title }}</h3>
          <div v-if="getCompletion(selectedTask.id)" class="completion-info">
            <el-tag type="success" size="large">已完成</el-tag>
            <p>用时: {{ getCompletion(selectedTask.id).time }}</p>
            <p>通过: {{ getCompletion(selectedTask.id).passedCount }}/{{ getCompletion(selectedTask.id).totalCount }} 用例</p>
          </div>
          <p class="preview-hint">点击下方按钮进入代码编辑页面</p>
          <el-button type="primary" @click="enterTask(selectedTask)">
            {{ getCompletion(selectedTask.id) ? '重做本题' : '开始挑战' }}
          </el-button>
        </div>
        <el-empty v-else description="请从左侧选择关卡" :image-size="80" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { MODULES, MOCK_PROGRESS } from '../config/flagshipExercises'

const router = useRouter()
const route = useRoute()

const moduleId = computed(() => parseInt(route.params.moduleId))
const currentModule = computed(() => MODULES.find(m => m.id === moduleId.value))
const selectedTaskId = ref(null)
const selectedTask = ref(null)

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
 * 读取关卡完成状态（从 localStorage）
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
  return !!getCompletion(taskId)
}
</script>

<style scoped>
.task-list-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 100px);
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
</style>
