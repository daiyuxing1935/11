<template>
  <div class="analytics-page">
    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="学习概览" name="overview">
        <el-row :gutter="20">
          <el-col :span="6" v-for="s in overviewCards" :key="s.label">
            <el-card shadow="hover"><el-statistic :value="s.value" :title="s.label"><template #prefix><el-icon><component :is="s.icon" /></el-icon></template></el-statistic></el-card>
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
            <el-descriptions-item label="学习天数">{{ weeklyReport.study_days || weeklyReport.total_duration }}天</el-descriptions-item>
            <el-descriptions-item label="正确率">{{ weeklyReport.avg_correct_rate }}%</el-descriptions-item>
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
            <el-descriptions-item label="学习天数">{{ monthlyReport.study_days || monthlyReport.total_duration }}天</el-descriptions-item>
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
import { ref, onMounted, nextTick, watch } from 'vue'
import { getStats, getWeeklyReport, getMonthlyReport, getGrowthData } from '../api/analytics'
import * as echarts from 'echarts'

const activeTab = ref('overview')
const overviewCards = ref([
  { label: '学习天数', value: 0, icon: 'Timer' },
  { label: '做题总数', value: 0, icon: 'EditPen' },
  { label: '平均正确率(%)', value: 0, icon: 'TrendCharts' },
  { label: '测评次数', value: 0, icon: 'DocumentChecked' },
])
const weeklyReport = ref(null)
const monthlyReport = ref(null)
const masteryChart = ref(null)
const weekChart = ref(null)
const growthChartEl = ref(null)

onMounted(async () => {
  try {
    const stats = await getStats()
    overviewCards.value[0].value = stats.study_days || stats.total_study_duration || 0
    overviewCards.value[1].value = stats.total_questions
    overviewCards.value[2].value = stats.avg_correct_rate
    overviewCards.value[3].value = stats.quiz_count

    await nextTick()
    initMasteryChart(stats.knowledge_mastery || {})
    initWeekChart(stats.weekly_stats || [])
  } catch(e) {}

  try { weeklyReport.value = await getWeeklyReport() } catch(e) {}
  try { monthlyReport.value = await getMonthlyReport() } catch(e) {}
})

watch(activeTab, async (tab) => {
  if (tab === 'growth') {
    await nextTick()
    try {
      const data = await getGrowthData()
      initGrowthChart(data.growth_points || [])
    } catch(e) {}
  }
})

function initMasteryChart(mastery) {
  if (!masteryChart.value) return
  const chart = echarts.init(masteryChart.value)
  const names = Object.keys(mastery).slice(0, 8)
  chart.setOption({
    tooltip: {},
    xAxis: { type: 'value', max: 100, name: '掌握度(%)' },
    yAxis: { type: 'category', data: names.map(n => n.length > 8 ? n.slice(0,8)+'..' : n), inverse: true },
    series: [{ type: 'bar', data: names.map(n => Math.round((mastery[n] || 0) * 100)), itemStyle: {
      color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#409EFF' }, { offset: 1, color: '#67C23A' }])
    }, label: { show: true, position: 'right', formatter: '{c}%' } }],
    grid: { left: 100, right: 50, top: 10, bottom: 20 }
  })
}

function initWeekChart(weekStats) {
  if (!weekChart.value) return
  const chart = echarts.init(weekChart.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: weekStats.map(w => w.date?.slice(5)) },
    yAxis: { type: 'value', name: '学习标记', min: 0, max: 1, interval: 1 },
    series: [
      { name: '是否学习', type: 'bar', data: weekStats.map(w => (w.duration > 0 || w.questions > 0) ? 1 : 0), itemStyle: { color: '#409EFF', borderRadius: 4 } },
    ],
    grid: { left: 40, right: 20, top: 20, bottom: 30 }
  })
}

function initGrowthChart(points) {
  if (!growthChartEl.value) return
  const chart = echarts.init(growthChartEl.value)
  chart.setOption({
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
