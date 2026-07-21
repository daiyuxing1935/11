<template>
  <div class="profile-page">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="hover" style="text-align:center">
          <el-avatar :size="80"><el-icon :size="40"><UserFilled /></el-icon></el-avatar>
          <h2 style="margin:12px 0 4px">{{ userStore.user?.nickname || '未设置' }}</h2>
          <el-tag>{{ userStore.user?.learning_stage || '入门' }} 学习者</el-tag>
          <p style="color:#909399;margin-top:8px">{{ userStore.user?.learning_goal || '未设置学习目标' }}</p>
          <el-divider />
          <el-descriptions :column="1" size="small">
            <el-descriptions-item label="用户名">{{ userStore.user?.username }}</el-descriptions-item>
            <el-descriptions-item label="年级">{{ userStore.user?.grade || '未设置' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header><div class="page-title"><el-icon><Setting /></el-icon> 个人信息设置</div></template>
          <el-form :model="form" label-width="100px" style="max-width:500px">
            <el-form-item label="昵称"><el-input v-model="form.nickname" /></el-form-item>
            <el-form-item label="年级/专业"><el-input v-model="form.grade" placeholder="如：大一/计算机科学" /></el-form-item>
            <el-form-item label="学习阶段">
              <el-radio-group v-model="form.learning_stage">
                <el-radio label="入门">入门</el-radio>
                <el-radio label="进阶">进阶</el-radio>
                <el-radio label="高阶">高阶</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="学习目标">
              <el-select v-model="form.learning_goal" style="width:100%">
                <el-option label="课程预习与复习" value="课程预习" />
                <el-option label="期末备考冲刺" value="期末备考" />
                <el-option label="智能体开发实操" value="开发实操" />
                <el-option label="竞赛项目落地" value="竞赛项目" />
                <el-option label="深度学习研究" value="深度学习" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSave" :loading="saving">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="hover" style="margin-top:20px">
          <template #header><div class="page-title"><el-icon><Cpu /></el-icon> AI大模型配置</div></template>
          <p style="color:#909399;font-size:13px;margin-bottom:16px">配置您自己的大模型API，支持OpenAI及兼容接口（如DeepSeek、Azure、本地模型等）</p>
          <el-form v-if="!llmEditing" label-width="120px" style="max-width:500px">
            <el-form-item label="配置状态">
              <el-tag :type="llmConfig.is_configured ? 'success' : 'info'">
                {{ llmConfig.is_configured ? '已自定义配置' : '使用系统默认（未配置）' }}
              </el-tag>
            </el-form-item>
            <el-form-item v-if="llmConfig.is_configured" label="服务商">
              <el-tag size="small">{{ llmConfig.provider === 'deepseek' ? 'DeepSeek' : llmConfig.provider === 'openai' ? 'OpenAI' : llmConfig.provider || '自定义' }}</el-tag>
            </el-form-item>
            <el-form-item v-if="llmConfig.is_configured" label="模型名称">
              <span>{{ llmConfig.model_name }}</span>
            </el-form-item>
            <el-form-item v-if="llmConfig.is_configured" label="API地址">
              <span style="font-size:12px;color:#909399">{{ llmConfig.base_url }}</span>
            </el-form-item>
            <el-form-item v-if="llmConfig.is_configured" label="API Key">
              <span style="font-size:12px;color:#909399">{{ llmConfig.api_key || '未设置' }}</span>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="llmEditing = true">修改配置</el-button>
              <el-button v-if="llmConfig.is_configured" type="danger" plain @click="handleResetLLM">重置为默认</el-button>
            </el-form-item>
          </el-form>
          <el-form v-else label-width="120px" style="max-width:500px">
            <el-form-item label="服务商">
              <el-select v-model="llmForm.provider" @change="onProviderChange" style="width:200px">
                <el-option label="OpenAI" value="openai" />
                <el-option label="DeepSeek" value="deepseek" />
                <el-option label="自定义" value="custom" />
              </el-select>
              <el-button v-if="llmForm.provider !== 'deepseek'" size="small" type="success" plain @click="quickSetupDeepSeek" style="margin-left:8px">⚡ 一键配置DeepSeek</el-button>
            </el-form-item>
            <el-form-item label="API Key">
              <el-input v-model="llmForm.api_key" type="password" show-password placeholder="sk-..." />
              <div style="font-size:12px;color:#909399">支持OpenAI、DeepSeek等兼容接口的API Key</div>
            </el-form-item>
            <el-form-item label="接口地址">
              <el-input v-model="llmForm.base_url" placeholder="https://api.openai.com" />
            </el-form-item>
            <el-form-item label="模型名称">
              <el-input v-model="llmForm.model_name" placeholder="gpt-4o" />
              <div style="font-size:12px;margin-top:4px">
                <span style="color:#909399">点击快速选择：</span>
                <el-tag v-for="m in currentModelSuggestions" :key="m" size="small" :type="llmForm.model_name === m ? 'primary' : 'info'" @click="llmForm.model_name = m" style="cursor:pointer;margin:2px">{{ m }}</el-tag>
              </div>
            </el-form-item>
            <el-form-item label="图片生成 Key">
              <el-input v-model="llmForm.image_api_key" type="password" show-password placeholder="r8_..." />
              <div style="font-size:12px;color:#909399">Replicate API Key，用于AI配图生成。<a href="https://replicate.com/account/api-tokens" target="_blank" style="color:#409EFF">免费注册获取 →</a></div>
            </el-form-item>
            <el-form-item label="温度参数">
              <el-slider v-model="llmForm.temperature" :min="0" :max="2" :step="0.1" show-stops style="width:200px" />
              <span style="margin-left:12px;color:#909399;font-size:12px">{{ llmForm.temperature }} (越高越随机)</span>
            </el-form-item>
            <el-form-item label="最大Token数">
              <el-input-number v-model="llmForm.max_tokens" :min="256" :max="32768" :step="256" size="small" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSaveLLM" :loading="llmSaving">保存配置</el-button>
              <el-button @click="llmEditing = false">取消</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="hover" style="margin-top:20px">
          <template #header><div class="page-title"><el-icon><Tools /></el-icon> 自定义学习设置</div></template>
          <el-form label-width="140px" style="max-width:500px">
            <el-form-item label="答疑讲解深度">
              <el-radio-group v-model="settings.explanationLevel">
                <el-radio label="beginner">入门通俗</el-radio>
                <el-radio label="standard">标准分步</el-radio>
                <el-radio label="advanced">拔高拓展</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="每日学习提醒">
              <el-switch v-model="settings.reminder" active-text="开启" inactive-text="关闭" />
            </el-form-item>
            <el-form-item label="学习节奏">
              <el-slider v-model="settings.pace" :min="1" :max="5" :step="1" show-stops style="width:200px" />
              <span style="margin-left:12px;color:#909399">{{ ['轻松','适中','标准','紧凑','冲刺'][settings.pace-1] }}</span>
            </el-form-item>
            <el-form-item><el-button @click="saveSettings">保存偏好</el-button></el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useUserStore } from '../stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getLLMConfig, saveLLMConfig, resetLLMConfig } from '../api/llm'

const userStore = useUserStore()
const saving = ref(false)
const llmEditing = ref(false)
const llmSaving = ref(false)
const form = reactive({
  nickname: userStore.user?.nickname || '',
  grade: userStore.user?.grade || '',
  learning_stage: userStore.user?.learning_stage || '入门',
  learning_goal: userStore.user?.learning_goal || '',
})
const settings = reactive({
  explanationLevel: localStorage.getItem('qa_level') || 'standard',
  reminder: localStorage.getItem('reminder') !== 'false',
  pace: parseInt(localStorage.getItem('pace') || '3')
})
const llmConfig = ref({
  provider: 'openai',
  api_key: '',
  base_url: 'https://api.openai.com',
  model_name: 'gpt-4o',
  temperature: 0.7,
  max_tokens: 4096,
  is_configured: false
})
const llmForm = reactive({
  provider: 'openai',
  api_key: '',
  image_api_key: '',
  base_url: 'https://api.openai.com',
  model_name: 'gpt-4o',
  temperature: 0.7,
  max_tokens: 4096
})
const modelSuggestions = {
  openai: ['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo', 'o1-mini', 'o1-preview'],
  deepseek: ['deepseek-chat', 'deepseek-reasoner', 'deepseek-v4-pro'],
  custom: ['gpt-4o', 'deepseek-chat', 'deepseek-reasoner', 'deepseek-v4-pro', 'qwen-turbo', 'glm-4']
}
const currentModelSuggestions = computed(() => modelSuggestions[llmForm.provider] || modelSuggestions.custom)

function onProviderChange(provider) {
  const presets = {
    openai: { base_url: 'https://api.openai.com', model_name: 'gpt-4o' },
    deepseek: { base_url: 'https://api.deepseek.com', model_name: 'deepseek-chat' },
    custom: { base_url: '', model_name: '' }
  }
  const preset = presets[provider]
  if (preset) {
    llmForm.base_url = preset.base_url
    llmForm.model_name = preset.model_name
  }
}

function quickSetupDeepSeek() {
  llmForm.provider = 'deepseek'
  llmForm.base_url = 'https://api.deepseek.com'
  llmForm.model_name = 'deepseek-chat'
  ElMessage.success('已切换到DeepSeek配置，请输入您的API Key后保存')
}

onMounted(async () => {
  try {
    const data = await getLLMConfig()
    llmConfig.value = data
    if (data.is_configured) {
      llmForm.api_key = ''
      llmForm.image_api_key = ''
      llmForm.provider = data.provider || 'openai'
      llmForm.base_url = data.base_url
      llmForm.model_name = data.model_name
      llmForm.temperature = data.temperature
      llmForm.max_tokens = data.max_tokens
    }
  } catch(e) {}
})

async function handleSave() {
  saving.value = true
  try {
    await userStore.updateUser(form)
    ElMessage.success('保存成功')
  } catch(e) { ElMessage.error('保存失败') }
  finally { saving.value = false }
}

function saveSettings() {
  localStorage.setItem('qa_level', settings.explanationLevel)
  localStorage.setItem('reminder', settings.reminder.toString())
  localStorage.setItem('pace', settings.pace.toString())
  ElMessage.success('偏好设置已保存')
}

async function handleSaveLLM() {
  llmSaving.value = true
  try {
    await saveLLMConfig(llmForm)
    ElMessage.success('大模型配置已保存')
    llmEditing.value = false
    const data = await getLLMConfig()
    llmConfig.value = data
  } catch(e) { ElMessage.error('保存失败: ' + (e.message || '未知错误')) }
  finally { llmSaving.value = false }
}

async function handleResetLLM() {
  try {
    await ElMessageBox.confirm('确认重置为系统默认配置？', '提示', { confirmButtonText: '确认', cancelButtonText: '取消', type: 'warning' })
    await resetLLMConfig()
    llmConfig.value = { provider: 'openai', api_key: '', image_api_key: '', base_url: 'https://api.openai.com', model_name: 'gpt-4o', temperature: 0.7, max_tokens: 4096, is_configured: false }
    llmForm.provider = 'openai'
    llmForm.api_key = ''
    llmForm.image_api_key = ''
    llmForm.base_url = 'https://api.openai.com'
    llmForm.model_name = 'gpt-4o'
    llmForm.temperature = 0.7
    llmForm.max_tokens = 4096
    llmEditing.value = false
    ElMessage.success('已重置为系统默认配置')
  } catch(e) {
    if (e !== 'cancel') ElMessage.error('重置失败')
  }
}
</script>

<style scoped>
.page-title { display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: bold; }
</style>
