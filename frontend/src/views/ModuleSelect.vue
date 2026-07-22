<template>
  <!-- 第1层：模块选择页面（头歌风格 - 纯文字卡片） -->
  <div class="module-select-page">
    <div class="page-header">
      <h1>Agent 工程编程实验室</h1>
      <p class="header-sub">从一段对话代码开始，逐关搭出可恢复、可审计的完整 Agent。建议按阶段顺序学习。</p>
    </div>

    <div class="module-grid">
      <div
        v-for="mod in MODULES"
        :key="mod.id"
        class="module-card"
        @click="enterModule(mod)"
      >
        <div class="card-heading">
          <h3 class="card-title">{{ mod.name }}</h3>
          <el-tag size="small" effect="plain">{{ mod.level }}</el-tag>
        </div>
        <p class="card-desc">{{ mod.description }}</p>
        <p class="card-project">阶段项目：{{ mod.project }}</p>
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
import { MODULES } from '../config/flagshipExercises'
import { recordStudyVisit } from '../api/learning'

const router = useRouter()

onMounted(() => { recordStudyVisit() })

/**
 * 获取模块完成进度
 * 读取本机已完成的能力验证；登录后的服务端结果会在实验页同步回来。
 */
function getProgress(moduleId) {
  try {
    const completed = JSON.parse(localStorage.getItem('code_completed') || '{}')
    const module = MODULES.find(item => item.id === moduleId)
    return (module?.tasks || []).filter(task => completed[`${moduleId}_${task.id}`]).length
  } catch {
    return 0
  }
}

/** 点击模块 → 进入关卡列表页 */
function enterModule(mod) {
  router.push({ name: 'TaskList', params: { moduleId: mod.id } })
}
</script>

<style scoped>
.module-select-page {
  min-height: 100%;
  padding: 24px 28px;
  max-width: 1180px;
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
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.module-card {
  display: flex;
  min-height: 176px;
  flex-direction: column;
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
.card-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.card-project { margin: -4px 0 14px; color: #303133; font-size: 13px; font-weight: 600; }
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
  margin-top: auto;
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
@media (max-width: 820px) {
  .module-select-page { padding: 20px 16px; }
  .module-grid { grid-template-columns: 1fr; }
}
</style>
