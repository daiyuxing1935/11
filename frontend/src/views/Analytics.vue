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

const masteryChart = ref(null)
const weekChart = ref(null)

let masteryChartInst = null
let weekChartInst = null

// ===== 页面挂载 =====
onMounted(async () => {
  recordStudyVisit()
  // 注册 watcher（数据后续变化时自动重绘）
  watch(() => statStore.moduleMastery, () => { nextTick(() => initMasteryChart()) }, { deep: true })
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

/** 切换选项卡时重新渲染图表 */
watch(activeTab, async (tab) => {
  if (tab === 'overview') {
    await nextTick()
    initMasteryChart()
    initWeekChart()
  }
})

function initMasteryChart() {
  if (!masteryChart.value) { console.log('[Analytics] 柱图 DOM 未就绪'); return }
  if (!masteryChartInst) {
    masteryChartInst = echarts.init(masteryChart.value)
    window.addEventListener('resize', () => masteryChartInst?.resize())
  }
  const mastery = statStore.moduleMastery
  const names = statStore.moduleNames || Object.keys(mastery)
  console.log('[Analytics] initMasteryChart 模块数:', names.length)
  if (names.length === 0) { console.log('[Analytics] mastery 为空，跳过柱图渲染'); return }
  masteryChartInst.setOption({
    tooltip: {},
    xAxis: { type: 'value', max: 100, name: '掌握度(%)' },
    yAxis: { type: 'category', data: names, inverse: true },
    series: [{ type: 'bar', data: names.map(n => mastery[n] || 0), itemStyle: {
      color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#409EFF' }, { offset: 1, color: '#67C23A' }])
    }, label: { show: true, position: 'right', formatter: '{c}%' } }],
    grid: { left: 200, right: 50, top: 10, bottom: 20 }
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

</script>

<style scoped>
h4 { margin-bottom: 8px; }
li { padding: 4px 0; font-size: 14px; color: #606266; }
</style>
