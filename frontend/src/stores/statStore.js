/**
 * statStore.js — 全局统计数据仓库（唯一数据源）
 *
 * 架构规则：
 * - 页面只读 state，不调 api
 * - refreshStatData() 一次性拉取 概览 + 掌握度 + 动态，全部完成后统一赋值
 * - 掌握度来自后端 get_user_knowledge_profile()，前端不写死任何数值
 */

import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import {
  fetchStats,              // GET /api/analytics/stats
  fetchKnowledgeMastery,   // GET /api/diagnosis/profile
  fetchWeeklyReport,
  fetchMonthlyReport,
  fetchGrowthData,
  fetchRecentActivity,
  submitQuizResult,
  refreshStats as refreshApi,
} from '../api/statistics'

export const useStatStore = defineStore('statistics', () => {
  // ===== 概览卡片 =====
  const studyDays = ref(0)
  const totalQuestions = ref(0)
  const avgCorrectRate = ref(0)
  const quizCount = ref(0)
  const quizAvgScore = ref(0)
  const errorCount = ref(0)

  // ===== 图表 =====
  const weeklyStats = ref([])
  const knowledgeMastery = ref({})

  // ===== 动态 =====
  const recentActivity = ref([])

  // ===== 报告 =====
  const weeklyReport = ref(null)
  const monthlyReport = ref(null)
  const growthData = ref(null)

  // ===== 状态 =====
  const loading = ref(false)

  // ===== 计算 =====
  const hasMasteryData = computed(() => Object.keys(knowledgeMastery.value).length > 0)

  // ===== 调试：监听 knowledgeMastery 每次变化 =====
  watch(knowledgeMastery, (newVal, oldVal) => {
    console.log('[statStore watch] mastery 变化: 旧', Object.keys(oldVal || {}).length, '→ 新', Object.keys(newVal || {}).length)
  })

  // ================================================================
  //  内部加载函数
  // ================================================================

  async function loadOverview() {
    const stats = await fetchStats()
    studyDays.value       = stats.study_days || 0
    totalQuestions.value  = stats.total_questions || 0
    avgCorrectRate.value  = stats.avg_correct_rate || 0
    quizCount.value       = stats.quiz_count || 0
    quizAvgScore.value    = stats.quiz_avg_score || 0
    errorCount.value      = stats.error_count || 0
    weeklyStats.value     = stats.weekly_stats || []
  }

  async function loadKnowledgeMastery() {
    const data = await fetchKnowledgeMastery()
    console.log('[statStore] 后端原始 mastery:', JSON.stringify(data).slice(0, 200))
    knowledgeMastery.value = data
    console.log('[statStore] Pinia mastery 已存入, 标签数:', Object.keys(knowledgeMastery.value).length)
  }

  async function loadRecentActivity() {
    recentActivity.value = await fetchRecentActivity()
  }

  async function loadWeeklyReport() {
    loading.value = true
    try { weeklyReport.value = await fetchWeeklyReport() } catch (e) { console.error(e) }
    finally { loading.value = false }
  }

  async function loadMonthlyReport() {
    loading.value = true
    try { monthlyReport.value = await fetchMonthlyReport() } catch (e) { console.error(e) }
    finally { loading.value = false }
  }

  async function loadGrowthData() {
    loading.value = true
    try { growthData.value = await fetchGrowthData() } catch (e) { console.error(e) }
    finally { loading.value = false }
  }

  // ================================================================
  //  对外公共方法
  // ================================================================

  /**
   * 【核心】做题提交后调用
   * 依次请求：① 概览统计  ② 知识点掌握度  ③ 学习动态
   * 全部完成后再赋值 Pinia state，缺一不可
   */
  async function refreshStatData(result) {
    // 通知后端（mock 记录动态）
    await submitQuizResult(result)

    // 并行拉取三份数据，全部完成后再赋值
    const [statsResult, masteryResult, activityResult] = await Promise.all([
      fetchStats(),
      fetchKnowledgeMastery(),
      fetchRecentActivity(),
    ])

    // ===== 统一赋值（确保三个接口全部成功才更新 state） =====
    const s = statsResult
    studyDays.value       = s.study_days || 0
    totalQuestions.value  = s.total_questions || 0
    avgCorrectRate.value  = s.avg_correct_rate || 0
    quizCount.value       = s.quiz_count || 0
    quizAvgScore.value    = s.quiz_avg_score || 0
    errorCount.value      = s.error_count || 0
    weeklyStats.value     = s.weekly_stats || []

    console.log('[statStore.refreshStatData] 后端原始 mastery:', JSON.stringify(masteryResult).slice(0, 200))
    knowledgeMastery.value = masteryResult
    console.log('[statStore.refreshStatData] Pinia mastery 已存入, 标签数:', Object.keys(knowledgeMastery.value).length)

    recentActivity.value  = activityResult
  }

  /** 全量刷新（Dashboard 进入时调用，不产生假动态） */
  async function refreshAll() {
    try {
      await refreshApi()
      const [statsResult, masteryResult, activityResult] = await Promise.all([
        fetchStats(),
        fetchKnowledgeMastery(),
        fetchRecentActivity(),
      ])
      const s = statsResult
      studyDays.value       = s.study_days || 0
      totalQuestions.value  = s.total_questions || 0
      avgCorrectRate.value  = s.avg_correct_rate || 0
      quizCount.value       = s.quiz_count || 0
      quizAvgScore.value    = s.quiz_avg_score || 0
      errorCount.value      = s.error_count || 0
      weeklyStats.value     = s.weekly_stats || []

      console.log('[statStore.refreshAll] 后端原始 mastery:', JSON.stringify(masteryResult).slice(0, 200))
      knowledgeMastery.value = masteryResult
      console.log('[statStore.refreshAll] Pinia mastery 已存入, 标签数:', Object.keys(knowledgeMastery.value).length)

      recentActivity.value = activityResult

      // 报告（异步，失败不影响主要数据）
      loadWeeklyReport().catch(() => {})
      loadMonthlyReport().catch(() => {})
      loadGrowthData().catch(() => {})
    } catch (e) {
      console.error('[statStore.refreshAll] 失败:', e)
    }
  }

  return {
    studyDays, totalQuestions, avgCorrectRate, quizCount, quizAvgScore, errorCount,
    weeklyStats, knowledgeMastery, recentActivity,
    weeklyReport, monthlyReport, growthData, loading,
    hasMasteryData,
    refreshStatData, refreshAll,
  }
})
