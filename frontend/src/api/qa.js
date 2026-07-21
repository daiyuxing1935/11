import request from './request'

export const askQuestion = (data) => request.post('/qa/ask', data)
export const getQAHistory = (page = 1) => request.get('/qa/history', { params: { page } })
export const deleteQAHistory = (id) => request.delete(`/qa/history/${id}`)
export const clearQAHistory = () => request.delete('/qa/history')
export const submitFeedback = (data) => request.post('/qa/feedback', data)

/** 运行QA中的Python代码片段 */
export const runCode = (data) => request.post('/qa/code-run', data)

/** 上传文件并提取文本内容 */
export async function uploadFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  const token = localStorage.getItem('token')
  const res = await fetch('/api/qa/upload', {
    method: 'POST',
    headers: { 'Authorization': token ? `Bearer ${token}` : '' },
    body: formData
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '上传失败' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  const data = await res.json()
  return data.data
}

/**
 * 保存流式问答记录
 * @param {Object} data — { question, answer, question_type, explanation_level }
 */
export const saveQA = (data) => request.post('/qa/save', data)

/**
 * 流式提问 — 使用SSE实时接收AI回答
 * @param {Object} data — { question, question_type, explanation_level, context, deep_thinking, enable_search }
 * @param {Function} onChunk — 每收到一个文本块时调用 (chunkText: string)
 * @param {Function} onDone — 流结束时调用 (fullAnswer: string)
 * @param {Function} onRagSources — 收到RAG知识库来源时调用 (sources: Array)
 * @param {Function} onRagUnavailable — RAG不可用时调用 (message: string)
 * @param {Function} onError — 出错时调用 (error: Error)
 * @returns {Function} abort — 调用以取消请求
 */
export function askQuestionStream(data, { onChunk, onDone, onError, onSearchResults, onRagSources, onRagUnavailable }) {
  const token = localStorage.getItem('token')
  const controller = new AbortController()

  fetch('/api/qa/ask/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    },
    body: JSON.stringify(data),
    signal: controller.signal
  }).then(async response => {
    if (!response.ok) {
      // 非200响应，读取错误信息
      const errData = await response.json().catch(() => ({ detail: '请求失败' }))
      onError(new Error(errData.detail || `HTTP ${response.status}`))
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let fullAnswer = ''
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      // 最后一个可能不完整，保留到下次处理
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim()
          if (data === '[DONE]') continue
          try {
            const parsed = JSON.parse(data)
            if (parsed.rag_sources && onRagSources) {
              onRagSources(parsed.rag_sources)
            }
            if (parsed.rag_unavailable && onRagUnavailable) {
              onRagUnavailable(parsed.message || '知识库暂不可用')
            }
            if (parsed.search_results && onSearchResults) {
              onSearchResults(parsed.search_results, parsed.search_query || '')
            }
            if (parsed.content) {
              fullAnswer += parsed.content
              onChunk(parsed.content, fullAnswer)
            }
            if (parsed.error) {
              onError(new Error(parsed.error))
              return
            }
          } catch (e) {
            // 非JSON行，忽略
          }
        }
      }
    }
    onDone(fullAnswer)
  }).catch(err => {
    if (err.name === 'AbortError') return
    onError(err)
  })

  return () => controller.abort()
}
