<template>
  <div class="analytics-page">
    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="学习概览" name="overview">
        <el-row :gutter="20">
          <el-col :span="6" v-for="s in overviewCards" :key="s.label">
            <el-card shadow="hover">
              <el-statistic :value="s.value" :title="s.label" :precision="s.precision ?? 0">
                <template #prefix><el-icon><component :is="s.icon" /></el-icon></template>
              </el-statistic>
            </el-card>
          </el-col>
        </el-row>
        <el-row :gutter="20" style="margin-top:20px">
          <el-col :span="12"><el-card shadow="hover"><template #header>知识点掌握度</template><div ref="masteryChart" style="height:350px"></div></el-card></el-col>
          <el-col :span="12"><el-card shadow="hover"><template #header>本周学习趋势</template><div ref="weekChart" style="height:350px"></div></el-card></el-col>
        </el-row>
      </el-tab-pane>
      <el-tab-pane label="周报告" name="weekly">
        <el-card v-if="weeklyReport" shadow="hover">
          <template #header>周报告 {{ weeklyReport.period }}</template>
          <el-descriptions :column="4" border>
            <el-descriptions-item label="学习天数">{{ weeklyReport.study_days }}天</el-descriptions-item>
            <el-descriptions-item label="做题总数">{{ weeklyReport.total_questions || 0 }}题</el-descriptions-item>
            <el-descriptions-item label="平均正确率">{{ weeklyReport.avg_correct_rate }}%</el-descriptions-item>
            <el-descriptions-item label="趋势">
              <el-tag :type="weeklyReport.trend === '上升' ? 'success' : 'warning'">{{ weeklyReport.trend }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
          <div style="margin-top:16px">
            <h4>学习建议</h4>
            <ul><li v-for="s in weeklyReport.suggestions" :key="s">{{ s }}</li></ul>
          </div>
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="月报告" name="monthly">
        <el-card v-if="monthlyReport" shadow="hover">
          <template #header>月报告 {{ monthlyReport.period }}</template>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="学习天数">{{ monthlyReport.study_days || 0 }}天</el-descriptions-item>
            <el-descriptions-item label="做题总数">{{ monthlyReport.total_questions }}题</el-descriptions-item>
            <el-descriptions-item label="平均正确率">{{ monthlyReport.avg_correct_rate }}%</el-descriptions-item>
            <el-descriptions-item label="测评次数">{{ monthlyReport.quiz_count }}次</el-descriptions-item>
            <el-descriptions-item label="测评均分">{{ monthlyReport.quiz_avg_score }}%</el-descriptions-item>
            <el-descriptions-item label="相比上月">
              <el-tag :type="monthlyReport.growth_direction === 'up' ? 'success' : 'warning'">
                {{ monthlyReport.growth > 0 ? '+' : '' }}{{ monthlyReport.growth }}%
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="能力成长" name="growth">
        <el-card shadow="hover">
          <template #header>能力成长轨迹</template>
          <div ref="growthChartEl" style="height:400px"></div>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useStatStore } from '../stores/statStore'
import * as echarts from 'echarts'
import { recordStudyVisit } from '../api/learning'

const statStore = useStatStore()
const activeTab = ref('overview')

// 概览卡片（computed 从 Pinia 获取）
const overviewCards = computed(() => [
  { label: '学习天数', value: statStore.studyDays, icon: 'Timer', precision: 0 },
  { label: '做题总数', value: statStore.totalQuestions, icon: 'EditPen', precision: 0 },
  { label: '平均正确率(%)', value: statStore.avgCorrectRate, icon: 'TrendCharts', precision: 1 },
  { label: '测评次数', value: statStore.quizCount, icon: 'DocumentChecked', precision: 0 },
])

// 报告（computed 从 Pinia 获取）
const weeklyReport = computed(() => statStore.weeklyReport)
const monthlyReport = computed(() => statStore.monthlyReport)

const masteryChart = ref(null)
const weekChart = ref(null)
const growthChartEl = ref(null)

let masteryChartInst = null
let weekChartInst = null
let growthChartInst = null

// ===== 页面挂载 =====
onMounted(async () => {
  recordStudyVisit()
  // 注册 watcher（数据后续变化时自动重绘）
  watch(() => statStore.knowledgeMastery, () => { nextTick(() => initMasteryChart()) }, { deep: true })
  watch(() => statStore.weeklyStats, () => { nextTick(() => initWeekChart()) }, { deep: true })
  // Pinia 为空时补拉一次
  if (!statStore.hasMasteryData) {
    await statStore.refreshAll()
  }
  // 无论是否拉取，都立即渲染一次（Pinia 可能已有 Dashboard 加载的数据）
  await nextTick()
  initMasteryChart()
  initWeekChart()
})

/** 切换选项卡时加载对应数据 */
watch(activeTab, async (tab) => {
  if (tab === 'overview') {
    await nextTick()
    initMasteryChart()
    initWeekChart()
  } else if (tab === 'weekly') {
    await statStore.loadWeeklyReport()
  } else if (tab === 'monthly') {
    await statStore.loadMonthlyReport()
  } else if (tab === 'growth') {
    await statStore.loadGrowthData()
    await nextTick()
    initGrowthChart()
  }
})

function initMasteryChart() {
  if (!masteryChart.value) { console.log('[Analytics] 柱图 DOM 未就绪'); return }
  if (!masteryChartInst) {
    masteryChartInst = echarts.init(masteryChart.value)
    window.addEventListener('resize', () => masteryChartInst?.resize())
  }
  const mastery = statStore.knowledgeMastery
  const names = Object.keys(mastery).slice(0, 8)
  console.log('[Analytics] initMasteryChart 渲染时 mastery 标签数:', Object.keys(mastery).length, '前3:', names.slice(0, 3).map(k => `${k}=${mastery[k]}`))
  if (names.length === 0) { console.log('[Analytics] mastery 为空，跳过柱图渲染'); return }
  masteryChartInst.setOption({
    tooltip: {},
    xAxis: { type: 'value', max: 100, name: '掌握度(%)' },
    yAxis: { type: 'category', data: names.map(n => n.length > 8 ? n.slice(0,8)+'..' : n), inverse: true },
    series: [{ type: 'bar', data: names.map(n => Math.round((mastery[n] || 0) * 100)), itemStyle: {
      color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#409EFF' }, { offset: 1, color: '#67C23A' }])
    }, label: { show: true, position: 'right', formatter: '{c}%' } }],
    grid: { left: 100, right: 50, top: 10, bottom: 20 }
  })
}

function initWeekChart() {
  if (!weekChart.value) return
  if (!weekChartInst) {
    weekChartInst = echarts.init(weekChart.value)
    window.addEventListener('resize', () => weekChartInst?.resize())
  }
  const data = statStore.weeklyStats
  if (data.length === 0) return
  weekChartInst.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: data.map(w => w.date?.slice(5)) },
    yAxis: [
      { type: 'value', name: '做题数' },
      { type: 'value', name: '正确率(%)', min: 0, max: 100 }
    ],
    series: [
      { name: '做题数量', type: 'bar', data: data.map(w => w.questions || 0), itemStyle: { color: '#409EFF', borderRadius: 4 } },
      { name: '正确率(%)', type: 'line', yAxisIndex: 1, data: data.map(w => w.correct_rate || 0), smooth: true, itemStyle: { color: '#67C23A' } }
    ],
    grid: { left: 60, right: 70, top: 30, bottom: 30 }
  })
}

function initGrowthChart() {
  if (!growthChartEl.value) return
  if (!growthChartInst) {
    growthChartInst = echarts.init(growthChartEl.value)
    window.addEventListener('resize', () => growthChartInst?.resize())
  }
  const points = statStore.growthData?.growth_points || []
  if (points.length === 0) return
  growthChartInst.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: points.map(p => p.date) },
    yAxis: { type: 'value', name: '正确率(%)', max: 100 },
    series: [{
      name: '正确率', type: 'line', data: points.map(p => p.rate),
      smooth: true, areaStyle: { opacity: 0.3 }, itemStyle: { color: '#67C23A' },
      markLine: { data: [{ type: 'average', name: '平均' }] }
    }],
    grid: { left: 50, right: 30, top: 20, bottom: 30 }
  })
}
</script>

<style scoped>
h4 { margin-bottom: 8px; }
li { padding: 4px 0; font-size: 14px; color: #606266; }
</style>
