import request from './request'

export const getLLMConfig = () => request.get('/llm-config')
export const saveLLMConfig = (data) => request.put('/llm-config', data)
export const resetLLMConfig = () => request.delete('/llm-config')
