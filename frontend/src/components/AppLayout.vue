<template>
  <el-container class="app-layout">
    <el-aside :width="sidebarWidth" class="sidebar" :class="{ 'is-collapsed': isCollapse, 'is-mobile-open': mobileOpen }">
      <div class="brand" @click="router.push('/dashboard')">
        <div class="brand-mark" aria-hidden="true">
          <span class="orbit-dot"></span>
          <span class="brand-core">π</span>
        </div>
        <div v-show="!isCollapse || mobileOpen" class="brand-copy">
          <strong>智学引擎</strong>
          <span>AI LEARNING ATLAS</span>
        </div>
      </div>

      <div v-show="!isCollapse || mobileOpen" class="nav-caption">学习空间</div>
      <el-menu :default-active="activeMenu" :collapse="isCollapse && !mobileOpen" router>
        <el-menu-item v-for="item in menuItems" :key="item.route" :index="item.route" @click="mobileOpen = false">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-footer" :class="{ compact: isCollapse && !mobileOpen }">
        <div class="stage-orbit"><span></span></div>
        <div v-show="!isCollapse || mobileOpen" class="stage-copy">
          <small>当前学习阶段</small>
          <strong>{{ userStore.learningStage }}</strong>
        </div>
      </div>
    </el-aside>

    <div v-if="mobileOpen" class="sidebar-scrim" @click="mobileOpen = false"></div>

    <el-container class="content-shell">
      <el-header class="top-header">
        <div class="header-left">
          <el-button class="menu-trigger desktop-trigger" text aria-label="收起侧栏" @click="isCollapse = !isCollapse">
            <el-icon :size="20"><Fold v-if="!isCollapse"/><Expand v-else/></el-icon>
          </el-button>
          <el-button class="menu-trigger mobile-trigger" text aria-label="打开导航" @click="mobileOpen = true">
            <el-icon :size="20"><Menu /></el-icon>
          </el-button>
          <div class="route-heading">
            <span class="route-eyebrow">你的学习坐标</span>
            <h1>{{ route.meta.title || '学习控制台' }}</h1>
          </div>
        </div>
        <div class="header-right">
          <div class="focus-chip"><span class="focus-pulse"></span> 今日学习中</div>
          <el-dropdown @command="handleCommand">
            <button class="user-pill">
              <span class="avatar">{{ userInitial }}</span>
              <span class="user-copy">
                <strong>{{ userStore.user?.nickname || '同学' }}</strong>
                <small>Lv. {{ userStore.learningStage }}</small>
              </span>
              <el-icon><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile"><el-icon><User /></el-icon>个人中心</el-dropdown-item>
                <el-dropdown-item command="logout" divided><el-icon><SwitchButton /></el-icon>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
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
const mobileOpen = ref(false)
const activeMenu = computed(() => route.path)
const sidebarWidth = computed(() => isCollapse.value ? '84px' : '252px')
const userInitial = computed(() => (userStore.user?.nickname || '学').trim().slice(0, 1).toUpperCase())

const menuItems = [
  { route: '/dashboard', label: '学习控制台', icon: 'DataAnalysis' },
  { route: '/diagnosis', label: '学情自测', icon: 'DocumentChecked' },
  { route: '/qa', label: '智能答疑', icon: 'ChatDotRound' },
  { route: '/learning-path', label: '学习路径', icon: 'Guide' },
  { route: '/error-book', label: '错题本', icon: 'EditPen' },
  { route: '/analytics', label: '学情复盘', icon: 'TrendCharts' },
  { route: '/resources', label: '学习资源', icon: 'Collection' },
  { route: '/code-lab', label: '编程实验室', icon: 'Monitor' },
  { route: '/profile', label: '个人中心', icon: 'User' },
]

function handleCommand(cmd) {
  if (cmd === 'logout') {
    userStore.logout()
    router.push('/login')
  } else if (cmd === 'profile') router.push('/profile')
}
</script>

<style scoped>
.app-layout { min-height: 100vh; }
.sidebar {
  position: relative;
  z-index: 30;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid rgba(255,255,255,.08);
  background:
    radial-gradient(circle at 20% 5%, rgba(86,183,220,.18), transparent 25%),
    linear-gradient(165deg, #151f3c 0%, #10182f 62%, #171b35 100%);
  box-shadow: 12px 0 36px rgba(17, 25, 50, .08);
  transition: width .3s cubic-bezier(.2,.8,.2,1);
}
.brand { display: flex; align-items: center; gap: 12px; height: 88px; padding: 0 21px; color: #fff; cursor: pointer; }
.brand-mark { position: relative; display: grid; width: 42px; height: 42px; flex: 0 0 42px; place-items: center; border: 1px solid rgba(255,255,255,.28); border-radius: 50%; }
.brand-mark::before { position: absolute; width: 50px; height: 25px; border: 1px solid rgba(86,183,220,.6); border-radius: 50%; content: ""; transform: rotate(-28deg); }
.brand-core { font-family: Georgia, serif; font-size: 20px; color: #fff; }
.orbit-dot { position: absolute; right: -5px; top: 4px; width: 7px; height: 7px; border-radius: 50%; background: #ff8c73; box-shadow: 0 0 0 4px rgba(255,129,102,.13); }
.brand-copy { min-width: 0; line-height: 1.05; white-space: nowrap; }
.brand-copy strong { display: block; font-size: 17px; letter-spacing: .08em; }
.brand-copy span { display: block; margin-top: 7px; color: rgba(255,255,255,.42); font-size: 9px; letter-spacing: .18em; }
.nav-caption { padding: 12px 26px 8px; color: rgba(255,255,255,.36); font-size: 10px; font-weight: 700; letter-spacing: .18em; }
.el-menu { flex: 1; border: 0; background: transparent; padding: 4px 12px; }
.el-menu--collapse { width: 84px; padding-inline: 12px; }
.el-menu-item { height: 48px; margin: 4px 0; border-radius: 12px; color: rgba(237,241,255,.64); }
.el-menu-item:hover { color: #fff; background: rgba(255,255,255,.07); }
.el-menu-item.is-active { color: #fff; background: linear-gradient(100deg, rgba(70,87,216,.9), rgba(86,183,220,.6)); box-shadow: 0 9px 24px rgba(28,43,118,.32); }
.el-menu-item.is-active::after { position: absolute; right: 10px; width: 5px; height: 5px; border-radius: 50%; background: #ff9a83; content: ""; }
.el-menu-item .el-icon { font-size: 19px; }
.sidebar-footer { display: flex; align-items: center; gap: 12px; margin: 16px; padding: 14px; border: 1px solid rgba(255,255,255,.09); border-radius: 15px; background: rgba(255,255,255,.055); }
.sidebar-footer.compact { justify-content: center; margin-inline: 12px; padding-inline: 8px; }
.stage-orbit { display: grid; width: 34px; height: 34px; flex: 0 0 34px; place-items: center; border: 1px dashed rgba(86,183,220,.6); border-radius: 50%; }
.stage-orbit span { width: 9px; height: 9px; border-radius: 50%; background: #56b7dc; box-shadow: 0 0 0 5px rgba(86,183,220,.12); }
.stage-copy small { display: block; color: rgba(255,255,255,.42); font-size: 10px; }
.stage-copy strong { display: block; margin-top: 4px; color: #fff; font-size: 13px; }
.content-shell { min-width: 0; }
.top-header { display: flex; align-items: center; justify-content: space-between; height: 88px; padding: 0 30px; border-bottom: 1px solid rgba(220,226,238,.85); background: rgba(255,255,255,.82); backdrop-filter: blur(16px); }
.header-left, .header-right { display: flex; align-items: center; gap: 18px; }
.menu-trigger { width: 40px; padding: 0 !important; color: var(--ink-600); border: 1px solid var(--line); background: #fff; }
.mobile-trigger { display: none; }
.route-heading { line-height: 1.1; }
.route-eyebrow { display: block; margin-bottom: 6px; color: var(--ink-400); font-size: 10px; font-weight: 700; letter-spacing: .18em; }
.route-heading h1 { color: var(--ink-950); font-size: 20px; font-weight: 760; letter-spacing: -.02em; }
.focus-chip { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border: 1px solid #dfeee9; border-radius: 999px; color: #318b70; background: #f4fbf8; font-size: 12px; font-weight: 650; }
.focus-pulse { width: 7px; height: 7px; border-radius: 50%; background: var(--mint); box-shadow: 0 0 0 4px rgba(57,185,145,.13); }
.user-pill { display: flex; align-items: center; gap: 10px; padding: 6px 9px 6px 7px; border: 1px solid var(--line); border-radius: 14px; color: var(--ink-800); background: #fff; cursor: pointer; box-shadow: 0 4px 14px rgba(30,45,84,.05); }
.avatar { display: grid; width: 36px; height: 36px; place-items: center; border-radius: 11px; color: #fff; background: linear-gradient(145deg, var(--primary), var(--sky)); font-size: 14px; font-weight: 800; }
.user-copy { min-width: 72px; text-align: left; line-height: 1.15; }
.user-copy strong, .user-copy small { display: block; }
.user-copy strong { max-width: 110px; overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.user-copy small { margin-top: 4px; color: var(--ink-400); font-size: 10px; }
.main-content { overflow-x: hidden; padding: 28px 30px 44px; background: transparent; }
.sidebar-scrim { display: none; }

@media (max-width: 900px) {
  .sidebar { position: fixed; inset: 0 auto 0 0; width: 268px !important; transform: translateX(-105%); transition: transform .28s ease; }
  .sidebar.is-mobile-open { transform: translateX(0); }
  .sidebar-scrim { position: fixed; z-index: 20; inset: 0; display: block; background: rgba(12,18,39,.46); backdrop-filter: blur(3px); }
  .desktop-trigger { display: none; }
  .mobile-trigger { display: inline-flex; }
  .top-header { height: 76px; padding: 0 18px; }
  .route-eyebrow, .focus-chip, .user-copy { display: none; }
  .route-heading h1 { font-size: 18px; }
  .main-content { padding: 20px 16px 34px; }
}
</style>
