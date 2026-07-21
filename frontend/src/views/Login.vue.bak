<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <el-icon :size="48" color="#409EFF"><Cpu /></el-icon>
        <h1>AI智能体学科学习平台</h1>
        <p>个性化 · 伴随式 · 智能化</p>
      </div>
      <el-tabs v-model="activeTab" class="login-tabs">
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" :rules="loginRules" ref="loginFormRef">
            <el-form-item prop="username"><el-input v-model="loginForm.username" placeholder="用户名" prefix-icon="User" size="large" /></el-form-item>
            <el-form-item prop="password"><el-input v-model="loginForm.password" type="password" placeholder="密码" prefix-icon="Lock" size="large" show-password /></el-form-item>
            <el-form-item><el-button type="primary" size="large" @click="handleLogin" :loading="loading" style="width:100%">登 录</el-button></el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="注册" name="register">
          <el-form :model="regForm" :rules="regRules" ref="regFormRef">
            <el-form-item prop="username"><el-input v-model="regForm.username" placeholder="用户名" size="large" /></el-form-item>
            <el-form-item prop="password"><el-input v-model="regForm.password" type="password" placeholder="密码(至少6位)" size="large" show-password /></el-form-item>
            <el-form-item prop="nickname"><el-input v-model="regForm.nickname" placeholder="昵称" size="large" /></el-form-item>
            <el-form-item prop="learning_stage">
              <el-select v-model="regForm.learning_stage" placeholder="选择学习阶段" size="large" style="width:100%">
                <el-option label="入门 - 零基础开始" value="入门" />
                <el-option label="进阶 - 有一定基础" value="进阶" />
                <el-option label="高阶 - 冲刺深度学习" value="高阶" />
              </el-select>
            </el-form-item>
            <el-form-item prop="learning_goal">
              <el-select v-model="regForm.learning_goal" placeholder="学习目标" size="large" style="width:100%">
                <el-option label="课程预习与复习" value="课程预习" />
                <el-option label="期末备考冲刺" value="期末备考" />
                <el-option label="智能体开发实操" value="开发实操" />
                <el-option label="竞赛项目落地" value="竞赛项目" />
                <el-option label="深度学习研究" value="深度学习" />
              </el-select>
            </el-form-item>
            <el-form-item><el-button type="primary" size="large" @click="handleRegister" :loading="loading" style="width:100%">注 册</el-button></el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
      <div class="demo-hint">首次使用请先注册账号</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const activeTab = ref('login')
const loading = ref(false)

const loginForm = reactive({ username: '', password: '' })
const loginRules = { username: [{ required: true, message: '请输入用户名' }], password: [{ required: true, message: '请输入密码' }] }
const regForm = reactive({ username: '', password: '', nickname: '', learning_stage: '入门', learning_goal: '课程预习' })
const regRules = {
  username: [{ required: true, message: '请输入用户名', min: 3 }],
  password: [{ required: true, message: '请输入密码', min: 6 }],
  nickname: [{ required: true, message: '请输入昵称' }],
  learning_stage: [{ required: true, message: '请选择学习阶段' }],
  learning_goal: [{ required: true, message: '请选择学习目标' }]
}
const loginFormRef = ref(null)
const regFormRef = ref(null)

async function handleLogin() {
  const valid = await loginFormRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await userStore.login(loginForm.username, loginForm.password)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch(e) { ElMessage.error(e.response?.data?.detail || '登录失败') }
  finally { loading.value = false }
}

async function handleRegister() {
  const valid = await regFormRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await userStore.register(regForm)
    ElMessage.success('注册成功')
    router.push('/dashboard')
  } catch(e) { ElMessage.error(e.response?.data?.detail || '注册失败') }
  finally { loading.value = false }
}
</script>

<style scoped>
.login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.login-card { width: 460px; background: #fff; border-radius: 16px; padding: 40px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
.login-header { text-align: center; margin-bottom: 24px; }
.login-header h1 { font-size: 24px; margin: 12px 0 4px; color: #303133; }
.login-header p { color: #909399; font-size: 14px; }
.login-tabs { margin-top: 8px; }
.demo-hint { text-align: center; color: #c0c4cc; font-size: 12px; margin-top: 16px; }
</style>
