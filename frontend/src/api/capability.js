import request from './request'

export const startCapabilitySession = (exerciseId, forceNew = false) =>
  request.post('/capability/sessions', { exercise_id: exerciseId, force_new: forceNew })

export const recordCapabilityEvents = (sessionId, events) =>
  request.post(`/capability/sessions/${sessionId}/events`, { events })

export const markCapabilityCodePassed = (sessionId, code) =>
  request.post(`/capability/sessions/${sessionId}/code-passed`, { code }, { timeout: 180000 })

export const submitCapabilityDefense = (sessionId, answers, aiUsage) =>
  request.post(`/capability/sessions/${sessionId}/defense`, {
    answers,
    ai_usage: aiUsage,
  })

export const submitCapabilityRepair = (sessionId, code, explanation) =>
  request.post(`/capability/sessions/${sessionId}/repair`, { code, explanation }, { timeout: 180000 })

/** 跳过能力验证，仅以测试分数完成关卡 */
export const skipCapability = (sessionId) =>
  request.post(`/capability/sessions/${sessionId}/skip`)

/** 获取能力验证回顾数据（用户回答 vs 标准答案） */
export const getSessionReview = (sessionId) =>
  request.get(`/capability/sessions/${sessionId}/review`)

/** 获取所有已完成关卡的分数概览 */
export const getCapabilityScores = () =>
  request.get('/capability/scores')

