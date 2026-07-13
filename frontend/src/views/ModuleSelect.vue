<template>
  <!-- 第1层：模块选择页面（头歌风格 - 纯文字卡片） -->
  <div class="module-select-page">
    <div class="page-header">
      <h1>AI 编程实验室</h1>
      <p class="header-sub">选择一个学习模块，开始你的 AI 智能体编程之旅</p>
    </div>

    <div class="module-grid">
      <div
        v-for="mod in MODULES"
        :key="mod.id"
        class="module-card"
        @click="enterModule(mod)"
      >
        <h3 class="card-title">{{ mod.name }}</h3>
        <p class="card-desc">{{ mod.description }}</p>
        <div class="card-footer">
          <span class="card-count">共 {{ mod.taskCount }} 个关卡</span>
          <span class="card-progress" :class="{ done: getProgress(mod.id) >= mod.taskCount, active: getProgress(mod.id) > 0 && getProgress(mod.id) < mod.taskCount }">
            {{ getProgress(mod.id) >= mod.taskCount ? '已完成' : getProgress(mod.id) > 0 ? '进行中 ' + getProgress(mod.id) + '/' + mod.taskCount : '未开始' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { MODULES, MOCK_PROGRESS } from '../config/exercises'
import { recordStudyVisit } from '../api/learning'

const router = useRouter()

onMounted(() => { recordStudyVisit() })

/**
 * 获取模块完成进度
 * TODO: 对接后端 GET /api/progress/module/{moduleId}
 */
function getProgress(moduleId) {
  return MOCK_PROGRESS[moduleId] || 0
}

/** 点击模块 → 进入关卡列表页 */
function enterModule(mod) {
  router.push({ name: 'TaskList', params: { moduleId: mod.id } })
}
</script>

<style scoped>
.module-select-page {
  padding: 32px;
  max-width: 960px;
  margin: 0 auto;
}
.page-header {
  margin-bottom: 28px;
}
.page-header h1 {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 6px;
}
.header-sub {
  font-size: 14px;
  color: #909399;
  margin: 0;
}
.module-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.module-card {
  background: #fff;
  border-radius: 6px;
  padding: 20px 24px;
  cursor: pointer;
  border: 1px solid #e4e7ed;
  border-left: 4px solid #409EFF;
  transition: all .2s;
}
.module-card:hover {
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.10);
  border-left-color: #3370cc;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 6px;
}
.card-desc {
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
  margin: 0 0 14px;
}
.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-count {
  font-size: 13px;
  color: #409EFF;
  font-weight: 500;
}
.card-progress {
  font-size: 12px;
  color: #c0c4cc;
}
.card-progress.active {
  color: #e6a23c;
}
.card-progress.done {
  color: #67C23A;
}
</style>
