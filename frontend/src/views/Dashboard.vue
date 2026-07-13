<template>
  <div class="dashboard">
    <!-- 欢迎横幅 -->
    <div class="welcome-banner">
      <div class="welcome-content">
        <div class="welcome-left">
          <h1 class="welcome-title">{{ greeting }}，{{ userStore.user?.nickname || '同学' }} 👋</h1>
          <p class="welcome-subtitle">{{ welcomeQuote }}</p>
          <div class="welcome-meta">
            <el-tag type="info" effect="plain" size="large">{{ userStore.learningStage || '入门' }}学员</el-tag>
            <span class="welcome-date">{{ todayDate }}</span>
          </div>
        </div>
        <div class="welcome-right">
          <div class="welcome-stats-row">
            <div class="welcome-mini-stat">
              <div class="wms-value">{{ statsCards[0].value }}</div>
              <div class="wms-label">学习天数</div>
            </div>
            <div class="welcome-mini-stat">
              <div class="wms-value">{{ statsCards[2].value }}</div>
              <div class="wms-label">正确率</div>
            </div>
            <div class="welcome-mini-stat">
              <div class="wms-value">{{ statsCards[1].value }}</div>
              <div class="wms-label">做题总数</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 快捷功能入口 -->
    <div class="quick-actions">
      <div class="qa-card" v-for="act in quickActions" :key="act.label" @click="router.push(act.route)">
        <div class="qa-icon" :style="{ background: act.bg }">
          <el-icon :size="28"><component :is="act.icon" /></el-icon>
        </div>
        <div class="qa-label">{{ act.label }}</div>
        <div class="qa-desc">{{ act.desc }}</div>
      </div>
    </div>

    <!-- 学习统计卡片 -->
    <el-row :gutter="20">
      <el-col :span="6" v-for="stat in statsCards" :key="stat.label">
        <el-card shadow="hover" class="stat-card" @click="router.push(stat.route)">
          <div class="stat-inner">
            <div class="stat-icon-wrap" :style="{ background: stat.bg }">
              <el-icon :size="24" :style="{ color: stat.color }"><component :is="stat.icon" /></el-icon>
            </div>
            <div class="stat-body">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
            <div class="stat-trend" v-if="stat.trend">
              <el-icon :color="stat.trend > 0 ? '#67C23A' : '#F56C6C'">
                <component :is="stat.trend > 0 ? 'CaretTop' : 'CaretBottom'" />
              </el-icon>
              <span>{{ Math.abs(stat.trend) }}%</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表 -->
    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="14">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title"><el-icon><TrendCharts /></el-icon> 学习成长趋势</span>
              <el-tag size="small" type="info">近7天</el-tag>
            </div>
          </template>
          <div ref="growthChart" style="height:300px"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title"><el-icon><PieChart /></el-icon> 知识点掌握度</span>
            </div>
          </template>
          <div v-show="statStore.hasMasteryData" ref="radarChart" style="height:300px"></div>
          <el-empty v-if="!statStore.hasMasteryData" description="完成测评后即可查看知识掌握度" :image-size="80" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 今日任务 + 学习动态 -->
    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="12">
        <el-card shadow="hover" class="task-card">
          <template #header>
            <div class="card-header">
              <span class="card-title"><el-icon><Sunny /></el-icon> 今日学习任务</span>
              <el-tag v-if="dailyTasks?.tasks?.length" size="small" :type="dailyTasks?.completed ? 'success' : 'warning'">
                {{ dailyTasks?.completed ? '已完成' : '进行中' }}
              </el-tag>
            </div>
          </template>
          <div v-if="dailyTasks?.tasks?.length">
            <div v-for="(task, idx) in dailyTasks.tasks" :key="idx" class="task-row">
              <div class="task-check">
                <el-icon :size="18" :color="task.done ? '#67C23A' : '#DCDFE6'">
                  <component :is="task.done ? 'CircleCheckFilled' : 'CircleCheck'" />
                </el-icon>
              </div>
              <div class="task-info">
                <div class="task-topic" :class="{ done: task.done }">{{ task.topic }}</div>
                <div class="task-action">{{ task.action }}</div>
              </div>
            </div>
            <div v-if="dailyTasks.study_tips" class="tips-bar">
              <el-icon><InfoFilled /></el-icon> {{ dailyTasks.study_tips }}
            </div>
            <div class="task-footer">
              <el-button type="primary" :disabled="dailyTasks?.completed" @click="markTaskDone">
                {{ dailyTasks?.completed ? '✓ 今日任务已完成' : '完成今日所有任务' }}
              </el-button>
            </div>
          </div>
          <el-empty v-else description="暂无今日任务">
            <el-button type="primary" @click="router.push('/learning-path')">去生成学习路径</el-button>
          </el-empty>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover" class="activity-card">
          <template #header>
            <div class="card-header">
              <span class="card-title"><el-icon><Clock /></el-icon> 最近学习动态</span>
            </div>
          </template>
          <el-timeline v-if="statStore.recentActivity.length">
            <el-timeline-item
              v-for="(item, idx) in statStore.recentActivity.slice(0, 6)"
              :key="idx"
              :timestamp="relativeTime(item.createTime)"
              :color="activityColor(item.type)"
              :icon="activityIcon(item.type)"
            >
              <div class="activity-item">
                <span class="activity-desc">{{ item.content }}</span>
              </div>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无学习记录，快去学习吧！" :image-size="80" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { useStatStore } from '../stores/statStore'
import { getDailyTasks, recordStudyVisit } from '../api/learning'
import { useLearningStore } from '../stores/learning'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { relativeTime } from '../composables/useTime'

const router = useRouter()
const userStore = useUserStore()
const statStore = useStatStore()
const learningStore = useLearningStore()

const dailyTasks = ref({})
const growthChart = ref(null)
const radarChart = ref(null)
let growthChartInst = null
let radarChartInst = null

/** 动态类型 → 图标 / 颜色映射 */
const activityIconMap = { exam: 'EditPen', chat: 'ChatDotRound', wrong: 'View' }
const activityColorMap = { exam: '#409EFF', chat: '#67C23A', wrong: '#E6A23C' }

// 问候语
const todayDate = computed(() => {
  const now = new Date()
  return `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 ${['日','一','二','三','四','五','六'][now.getDay()]}`
})

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 9) return '早上好'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const welcomeQuotes = [
  '每天进步一点点，AI的世界等你探索 🚀',
  '坚持是最好的学习方法，今天也要加油 💪',
  '知识改变命运，AI创造未来 🌟',
  '学习如逆水行舟，不进则退 📚',
  '今天的努力是明天的基石 ⛏️',
]
const welcomeQuote = ref(welcomeQuotes[Math.floor(Math.random() * welcomeQuotes.length)])

// 快捷功能
const quickActions = [
  { label: '学情自测', desc: '测试当前水平', icon: 'EditPen', bg: 'linear-gradient(135deg, #667eea, #764ba2)', route: '/diagnosis' },
  { label: '学习路径', desc: 'AI定制学习计划', icon: 'Guide', bg: 'linear-gradient(135deg, #f093fb, #f5576c)', route: '/learning-path' },
  { label: '智能答疑', desc: '随时随地解惑', icon: 'ChatDotRound', bg: 'linear-gradient(135deg, #4facfe, #00f2fe)', route: '/qa' },
  { label: '学习资源', desc: '精选教程文章', icon: 'Collection', bg: 'linear-gradient(135deg, #43e97b, #38f9d7)', route: '/resources' },
  { label: '错题本', desc: '查漏补缺', icon: 'Notebook', bg: 'linear-gradient(135deg, #fa709a, #fee140)', route: '/error-book' },
  { label: '学情复盘', desc: '数据驱动成长', icon: 'DataAnalysis', bg: 'linear-gradient(135deg, #a18cd1, #fbc2eb)', route: '/analytics' },
]

// 统计卡片（computed 从 Pinia 获取，数值自动更新）
const statsCards = computed(() => [
  { label: '学习天数', value: statStore.studyDays, icon: 'Timer', bg: '#ecf5ff', color: '#409EFF', route: '/analytics', trend: null },
  { label: '做题总数', value: statStore.totalQuestions, icon: 'EditPen', bg: '#f0f9eb', color: '#67C23A', route: '/error-book', trend: null },
  { label: '平均正确率', value: Number(statStore.avgCorrectRate).toFixed(1) + '%', icon: 'TrendCharts', bg: '#fdf6ec', color: '#E6A23C', route: '/analytics', trend: null },
  { label: '测评次数', value: statStore.quizCount, icon: 'DocumentChecked', bg: '#fef0f0', color: '#F56C6C', route: '/diagnosis', trend: null },
])

// 活动图标/颜色（基于后端 type 字段动态匹配）
function activityIcon(type) { return activityIconMap[type] || 'More' }
function activityColor(type) { return activityColorMap[type] || '#909399' }

// ===== 页面挂载 =====
onMounted(async () => {
  recordStudyVisit()
  // 【Dashboard 专属】每次进入强制拉取后端最新数据
  await statStore.refreshAll()
  await nextTick()
  initGrowthChart()
  initRadarChart()

  // 监听 Pinia → 图表自动更新
  watch(() => statStore.weeklyStats, () => { nextTick(() => initGrowthChart()) }, { deep: true })
  watch(() => statStore.knowledgeMastery, () => { nextTick(() => initRadarChart()) }, { deep: true })

  // 今日任务
  try { dailyTasks.value = enrichTasks(await getDailyTasks()) || {} } catch (e) {}
})

/**
 * 初始化学习成长趋势图（近7天）
 * 数据来源于 Pinia statStore.weeklyStats
 */
function initGrowthChart() {
  if (!growthChart.value) return
  if (!growthChartInst) {
    growthChartInst = echarts.init(growthChart.value)
    // 窗口缩放时图表自适应
    window.addEventListener('resize', () => growthChartInst?.resize())
  }
  const data = statStore.weeklyStats
  const dates = data.length > 0
    ? data.map(w => (w.date || '').slice(5))
    : Array.from({ length: 7 }, (_, i) => {
        const d = new Date(); d.setDate(d.getDate() - (6 - i)); return `${d.getMonth() + 1}/${d.getDate()}`
      })

  growthChartInst.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['做题数量', '正确率(%)'], bottom: 0 },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: [
      { type: 'value', name: '题数', minInterval: 1 },
      { type: 'value', name: '%', max: 100 }
    ],
    series: [
      {
        name: '做题数量', type: 'bar',
        // 优先展示做题总数量（比套数更直观）
        data: data.map(w => w.questions || 0),
        itemStyle: { color: '#409EFF', borderRadius: [4, 4, 0, 0] },
        barWidth: 20
      },
      {
        name: '正确率(%)', type: 'line', yAxisIndex: 1,
        data: data.map(w => Math.round(w.correct_rate || 0)),
        itemStyle: { color: '#67C23A' },
        smooth: true, symbol: 'circle', symbolSize: 8,
        lineStyle: { width: 3 }
      }
    ],
    grid: { left: 60, right: 70, top: 30, bottom: 40 }
  })
}

/**
 * 初始化知识点掌握度雷达图
 * 数据来源于 Pinia statStore.knowledgeMastery
 */
function initRadarChart() {
  if (!radarChart.value) return
  if (!radarChartInst) {
    radarChartInst = echarts.init(radarChart.value)
    window.addEventListener('resize', () => radarChartInst?.resize())
  }
  const mastery = statStore.knowledgeMastery
  const keys = Object.keys(mastery || {})
  if (keys.length === 0) return  // 数据未加载，等 watch 触发

  const names = keys.slice(0, 6)
  const values = names.map(n => Math.round((mastery[n] || 0) * 100))

  radarChartInst.setOption({
    tooltip: { trigger: 'item' },
    radar: {
      indicator: names.map(n => ({ name: n.length > 8 ? n.slice(0, 8) + '..' : n, max: 100 })),
      center: ['50%', '55%'], radius: '65%',
      axisName: { color: '#606266', fontSize: 12 }
    },
    series: [{
      name: '掌握度', type: 'radar',
      data: [{ value: values, name: '当前掌握度' }],
      areaStyle: { color: 'rgba(64, 158, 255, 0.25)' },
      lineStyle: { color: '#409EFF', width: 2 },
      itemStyle: { color: '#409EFF' },
      symbol: 'circle', symbolSize: 6
    }]
  })
}

function enrichTasks(data) {
  if (!data) return data
  const completed = data.completed
  if (data.tasks) {
    data.tasks = data.tasks.map(t => ({ ...t, done: completed }))
  }
  return data
}

async function markTaskDone() {
  try {
    const isCompleted = dailyTasks.value?.completed
    await learningStore.finishTask('', isCompleted ? 0 : 1)
    dailyTasks.value = enrichTasks(await getDailyTasks()) || {}
    ElMessage.success(isCompleted ? '任务已重新打开' : '今日任务全部完成！继续保持！🎉')
  } catch (e) {
    ElMessage.error('更新失败，请重试')
  }
}
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
}

/* ======== Welcome Banner ======== */
.welcome-banner {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%);
  border-radius: 16px;
  padding: 32px 36px;
  margin-bottom: 24px;
  position: relative;
  overflow: hidden;
}
.welcome-banner::before {
  content: '';
  position: absolute;
  right: -60px;
  top: -60px;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(64,158,255,0.15) 0%, transparent 70%);
  border-radius: 50%;
}
.welcome-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  z-index: 1;
}
.welcome-title {
  color: #fff;
  font-size: 26px;
  font-weight: 700;
  margin: 0 0 8px 0;
}
.welcome-subtitle {
  color: rgba(255,255,255,0.7);
  font-size: 14px;
  margin: 0 0 14px 0;
}
.welcome-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}
.welcome-date {
  color: rgba(255,255,255,0.6);
  font-size: 13px;
}
.welcome-right {
  display: flex;
  gap: 32px;
}
.welcome-stats-row {
  display: flex;
  gap: 32px;
}
.welcome-mini-stat {
  text-align: center;
}
.wms-value {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
}
.wms-label {
  font-size: 12px;
  color: rgba(255,255,255,0.55);
  margin-top: 4px;
}

/* ======== Quick Actions ======== */
.quick-actions {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.qa-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.25s;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.qa-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 25px rgba(0,0,0,0.12);
}
.qa-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 10px;
  color: #fff;
}
.qa-label {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}
.qa-desc {
  font-size: 12px;
  color: #909399;
}

/* ======== Stat Cards ======== */
.stat-card {
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 12px;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.1);
}
.stat-inner {
  display: flex;
  align-items: center;
  gap: 14px;
}
.stat-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-body {
  flex: 1;
}
.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}
.stat-label {
  font-size: 13px;
  color: #909399;
}
.stat-trend {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 13px;
  color: #909399;
}

/* ======== Chart Cards ======== */
.chart-card, .task-card, .activity-card {
  border-radius: 12px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
  color: #303133;
}

/* ======== Today's Tasks ======== */
.task-row {
  display: flex;
  gap: 12px;
  padding: 14px 0;
  border-bottom: 1px solid #f5f5f5;
}
.task-row:last-child { border-bottom: none; }
.task-check {
  padding-top: 2px;
}
.task-topic {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}
.task-topic.done {
  color: #909399;
  text-decoration: line-through;
}
.task-action {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.tips-bar {
  margin-top: 14px;
  padding: 10px 14px;
  background: #ecf5ff;
  border-radius: 8px;
  color: #409EFF;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.task-footer {
  margin-top: 16px;
  text-align: center;
}

/* ======== Activity ======== */
.activity-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.activity-desc {
  font-size: 13px;
  color: #606266;
}

/* ======== Responsive ======== */
@media (max-width: 1200px) {
  .quick-actions { grid-template-columns: repeat(3, 1fr); }
  .welcome-stats-row { display: none; }
}
@media (max-width: 768px) {
  .welcome-banner { padding: 20px; }
  .welcome-title { font-size: 20px; }
  .quick-actions { grid-template-columns: repeat(2, 1fr); }
}
</style>
