<template>
  <el-container class="app-layout">
    <el-aside :width="isCollapse ? '64px' : '220px'" class="sidebar">
      <div class="logo" @click="$router.push('/dashboard')">
        <el-icon :size="28"><Cpu /></el-icon>
        <span v-if="!isCollapse" class="logo-text">AI智能体学习平台</span>
      </div>
      <el-menu :default-active="activeMenu" :collapse="isCollapse" router background-color="#001529" text-color="#fff9" active-text-color="#409EFF">
        <el-menu-item index="/dashboard"><el-icon><DataAnalysis /></el-icon><span>学习控制台</span></el-menu-item>
        <el-menu-item index="/diagnosis"><el-icon><DocumentChecked /></el-icon><span>学情自测</span></el-menu-item>
        <el-menu-item index="/qa"><el-icon><ChatDotRound /></el-icon><span>智能答疑</span></el-menu-item>
        <el-menu-item index="/learning-path"><el-icon><Guide /></el-icon><span>学习路径</span></el-menu-item>
        <el-menu-item index="/error-book"><el-icon><EditPen /></el-icon><span>错题本</span></el-menu-item>
        <el-menu-item index="/analytics"><el-icon><TrendCharts /></el-icon><span>学情复盘</span></el-menu-item>
        <el-menu-item index="/resources"><el-icon><Collection /></el-icon><span>学习资源</span></el-menu-item>
        <el-menu-item index="/code-lab"><el-icon><Monitor /></el-icon><span>写代码</span></el-menu-item>
        <el-menu-item index="/profile"><el-icon><User /></el-icon><span>个人中心</span></el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="top-header">
        <div class="header-left">
          <el-button @click="isCollapse = !isCollapse" text><el-icon :size="20"><Fold v-if="!isCollapse"/><Expand v-else/></el-icon></el-button>
          <el-breadcrumb separator="/"><el-breadcrumb-item>AI智能体学科</el-breadcrumb-item><el-breadcrumb-item>{{ $route.meta.title }}</el-breadcrumb-item></el-breadcrumb>
        </div>
        <div class="header-right">
          <el-tag type="warning" size="small">Lv.{{ userStore.learningStage }}</el-tag>
          <el-dropdown @command="handleCommand">
            <span class="user-info"><el-icon><UserFilled /></el-icon> {{ userStore.user?.nickname || '用户' }}<el-icon><ArrowDown /></el-icon></span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const isCollapse = ref(false)
const activeMenu = computed(() => route.path)

function handleCommand(cmd) {
  if (cmd === 'logout') {
    userStore.logout()
    router.push('/login')
  } else if (cmd === 'profile') {
    router.push('/profile')
  }
}
</script>

<style scoped>
.app-layout { height: 100vh; }
.sidebar { background: #001529; overflow: hidden; transition: width 0.3s; }
.logo { display: flex; align-items: center; gap: 8px; padding: 16px; color: #fff; cursor: pointer; height: 60px; }
.logo-text { font-size: 15px; font-weight: bold; white-space: nowrap; }
.top-header { display: flex; align-items: center; justify-content: space-between; background: #fff; border-bottom: 1px solid #e8e8e8; padding: 0 20px; height: 60px; }
.header-left { display: flex; align-items: center; gap: 12px; }
.header-right { display: flex; align-items: center; gap: 16px; }
.user-info { cursor: pointer; display: flex; align-items: center; gap: 6px; }
.main-content { background: #f0f2f5; padding: 20px; overflow-y: auto; }
.el-menu { border-right: none; }
.el-menu-item.is-active { background-color: #1890ff !important; color: #fff !important; }
</style>
