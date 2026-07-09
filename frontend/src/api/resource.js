import request from './request'

export const getRecommendations = () => request.get('/resources/recommend')
export const getResourceList = (params) => request.get('/resources/list', { params })
export const collectResource = (id) => request.post(`/resources/collect/${id}`)
export const getCollectedResources = () => request.get('/resources/collected')

/** 根据知识点获取AI整理的学习资料（联网搜索+AI组织） */
export const getKnowledgeMaterial = (knowledge) =>
  request.get('/resources/material', { params: { knowledge } })

/** 根据资源ID获取学习资料（优先本地，兜底联网） */
export const getResourceLearnMaterial = (resourceId) =>
  request.get(`/resources/learn/${resourceId}`)
