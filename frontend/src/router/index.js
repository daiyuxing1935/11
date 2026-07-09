import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { noAuth: true } },
  {
    path: '/',
    component: () => import('../components/AppLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '学习控制台' } },
      { path: 'diagnosis', name: 'Diagnosis', component: () => import('../views/Diagnosis.vue'), meta: { title: '学情自测' } },
      { path: 'diagnosis/report/:id', name: 'DiagnosisReport', component: () => import('../views/DiagnosisReport.vue'), meta: { title: '诊断报告' } },
      { path: 'qa', name: 'QA', component: () => import('../views/QA.vue'), meta: { title: '智能答疑' } },
      { path: 'learning-path', name: 'LearningPath', component: () => import('../views/LearningPath.vue'), meta: { title: '学习路径' } },
      { path: 'task-quiz/:sessionId', name: 'TaskQuiz', component: () => import('../views/TaskQuiz.vue'), meta: { title: '专项练习' } },
      { path: 'code-lab/:taskDay', name: 'CodeLab', component: () => import('../views/CodeLab.vue'), meta: { title: '编程实验室' } },
      { path: 'code-runner', name: 'CodeRunner', component: () => import('../views/CodeRunner.vue'), meta: { title: '代码运行器' } },
      { path: 'error-book', name: 'ErrorBook', component: () => import('../views/ErrorBook.vue'), meta: { title: '错题本' } },
      { path: 'analytics', name: 'Analytics', component: () => import('../views/Analytics.vue'), meta: { title: '学情复盘' } },
      { path: 'resources', name: 'Resources', component: () => import('../views/Resources.vue'), meta: { title: '学习资源' } },
      { path: 'profile', name: 'Profile', component: () => import('../views/Profile.vue'), meta: { title: '个人中心' } },
    ]
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  if (!to.meta.noAuth && !userStore.token) {
    next('/login')
  } else if (to.path === '/login' && userStore.token) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
