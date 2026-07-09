import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, register as registerApi, getProfile, updateProfile } from '../api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isLoggedIn = computed(() => !!token.value)
  const learningStage = computed(() => user.value?.learning_stage || '入门')

  async function login(username, password) {
    const data = await loginApi({ username, password })
    token.value = data.access_token
    user.value = data.user
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))
    return data
  }

  async function register(form) {
    const data = await registerApi(form)
    token.value = data.access_token
    user.value = data.user
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))
    return data
  }

  async function fetchProfile() {
    const data = await getProfile()
    user.value = data
    localStorage.setItem('user', JSON.stringify(data))
  }

  async function updateUser(form) {
    await updateProfile(form)
    await fetchProfile()
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return { token, user, isLoggedIn, learningStage, login, register, fetchProfile, updateUser, logout }
}, { persist: true })
