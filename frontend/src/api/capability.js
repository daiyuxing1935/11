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

