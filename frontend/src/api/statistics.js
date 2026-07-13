/**
 * statistics.js — 统计数据 API 层（唯一网络请求入口）
 *
 * 架构约定：
 * - 所有网络请求只在此文件发起，页面和 Store 不直接调后端
 * - 后续对接真实后端只改此文件的接口地址
 * - 前端不写死任何数值，全部来自后端返回
 */

// ============ 概览统计（真实后端） ============

/** GET /api/analytics/stats → analytics_service.get_user_stats() */
export async function fetchStats() {
  const res = await fetch('/api/analytics/stats', {
    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
  })
  const data = await res.json()
  return data.data || data
}

// ============ 知识点掌握度（真实后端） ============

/** GET /api/diagnosis/profile → diagnosis_service.get_user_knowledge_profile() */
export async function fetchKnowledgeMastery() {
  const res = await fetch('/api/diagnosis/profile', {
    headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
  })
  const data = await res.json()
  const profile = data.data || data
  return profile.mastery || {}
}

// ============ 以下为暂未对接后端的 mock（保留用于动态列表/报告，后续切换） ============

function delay(ms = 300) { return new Promise(r => setTimeout(r, ms)) }

const MOCK_WEEKLY = { period: '2026-07-07 ~ 2026-07-13', study_days: 5, total_questions: 86, avg_correct_rate: 72.5, new_errors: 12, trend: '上升', suggestions: ['保持每天45分钟专注学习', '重点复习错题本中的薄弱知识点', '尝试高阶难度题目挑战自己'] }
const MOCK_MONTHLY = { period: '2026-07-01 ~ 2026-07-13', study_days: 10, total_questions: 180, avg_correct_rate: 70.2, quiz_count: 12, quiz_avg_score: 68.3, growth: 5.5, growth_direction: 'up' }
const MOCK_GROWTH = { growth_points: [
  { date: '2026-07-01', score: 5, total: 10, rate: 50.0 }, { date: '2026-07-03', score: 6, total: 10, rate: 60.0 },
  { date: '2026-07-05', score: 7, total: 10, rate: 70.0 }, { date: '2026-07-07', score: 6, total: 10, rate: 60.0 },
  { date: '2026-07-09', score: 8, total: 10, rate: 80.0 }, { date: '2026-07-11', score: 7, total: 10, rate: 70.0 },
  { date: '2026-07-13', score: 9, total: 10, rate: 90.0 },
], trend: 'up' }

let MOCK_ACTIVITY = [
  { type: 'exam', content: '完成了测评练习：AI智能体定义', createTime: '2026-07-13 14:20:00' },
  { type: 'chat', content: '进行了AI答疑：Chain of Thought 原理', createTime: '2026-07-13 10:15:00' },
  { type: 'wrong', content: '复习了错题：Transformer架构', createTime: '2026-07-12 16:45:00' },
]

export async function fetchWeeklyReport() { await delay(350); return { ...MOCK_WEEKLY } }
export async function fetchMonthlyReport() { await delay(400); return { ...MOCK_MONTHLY } }
export async function fetchGrowthData() { await delay(350); return { ...MOCK_GROWTH } }
export async function fetchRecentActivity() { await delay(250); return MOCK_ACTIVITY.map(item => ({ ...item })) }

/** 提交测评后模拟后端追加动态（TODO: 切后端 POST /api/analytics/submit-result） */
export async function submitQuizResult(result) {
  await delay(200)
  const { knowledge = '综合' } = result || {}
  MOCK_ACTIVITY.unshift({ type: 'exam', content: `完成了测评练习：${knowledge}`, createTime: new Date().toISOString().replace('T', ' ').slice(0, 19) })
  if (MOCK_ACTIVITY.length > 20) MOCK_ACTIVITY.length = 20
  return { success: true }
}

export async function refreshStats() { await delay(200); return { success: true } }
