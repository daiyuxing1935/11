<template>
  <div class="resources-page">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="个性化推荐" name="recommend">
        <el-row :gutter="20">
          <el-col :span="8" v-for="item in recommendations" :key="item.resource.id">
            <el-card shadow="hover" class="resource-card" @click="openResource(item.resource)">
              <template #header>
                <div style="display:flex;justify-content:space-between;align-items:center">
                  <el-tag :type="getDiffType(item.resource.difficulty)" size="small">{{ item.resource.difficulty }}</el-tag>
                  <div>
                    <el-button text size="small" @click.stop="openResource(item.resource)" type="primary">
                      <el-icon><Reading /></el-icon> 学习
                    </el-button>
                    <el-button text @click.stop="toggleCollect(item.resource.id)" :type="isCollected(item.resource.id) ? 'warning' : ''">
                      <el-icon><StarFilled v-if="isCollected(item.resource.id)" /><Star v-else /></el-icon>
                    </el-button>
                  </div>
                </div>
              </template>
              <h4>{{ item.resource.title }}</h4>
              <p class="res-summary">{{ item.resource.summary }}</p>
              <div class="res-meta">
                <el-tag v-for="t in item.resource.tags?.slice(0,3)" :key="t" size="small" type="info" style="margin:2px;cursor:pointer" @click.stop="clickKnowledgeTag(t)">{{ t }}</el-tag>
              </div>
              <div class="res-footer">
                <span><el-icon><Timer /></el-icon> {{ item.resource.duration }}</span>
                <el-tag type="warning" size="small">{{ item.reason }}</el-tag>
              </div>
            </el-card>
          </el-col>
        </el-row>
        <el-empty v-if="!recommendations.length" description="完成测评后可获取个性化推荐" />
      </el-tab-pane>
      <el-tab-pane label="全部资源" name="all">
        <div class="filter-bar">
          <el-select v-model="filterCategory" placeholder="分类筛选" clearable style="width:200px" @change="onFilterChange">
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>
          <el-select v-model="filterDifficulty" placeholder="难度筛选" clearable style="width:150px;margin-left:12px" @change="onFilterChange">
            <el-option label="Lv1入门" value="Lv1入门" /><el-option label="Lv2中等" value="Lv2中等" /><el-option label="Lv3高阶" value="Lv3高阶" />
          </el-select>
        </div>
        <el-row :gutter="20" style="margin-top:16px">
          <el-col :span="6" v-for="item in allResources.items" :key="item.id">
            <el-card shadow="hover" class="resource-card-small" @click="openResource(item)">
              <div style="display:flex;justify-content:space-between;align-items:flex-start">
                <el-tag :type="getDiffType(item.difficulty)" size="small">{{ item.difficulty }}</el-tag>
                <el-button text size="small" type="primary" @click.stop="openResource(item)">
                  <el-icon><Reading /></el-icon>
                </el-button>
              </div>
              <h4 style="margin:8px 0">{{ item.title }}</h4>
              <p class="res-summary">{{ item.summary?.slice(0,60) }}...</p>
              <span style="font-size:12px;color:#c0c4cc">{{ item.duration }} · {{ item.category }}</span>
            </el-card>
          </el-col>
        </el-row>
        <el-pagination v-if="allResources.total > allResources.page_size" :total="allResources.total" :page-size="allResources.page_size" :current-page="currentPage" @current-change="fetchAll" layout="prev, pager, next" style="margin-top:20px;text-align:center" />
      </el-tab-pane>
    </el-tabs>

    <!-- 学习资料弹窗（点击资源卡片或知识点标签） -->
    <el-dialog v-model="learnDialogVisible" :title="learnDialogTitle" width="90%" top="3vh" :close-on-click-modal="false" destroy-on-close>
      <div v-if="learnDialogLoading" style="text-align:center;padding:40px">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <p style="margin-top:12px;color:#909399">正在加载学习资料...</p>
      </div>
      <div v-else class="learn-material-content" v-html="learnDialogContent"></div>
      <template #footer>
        <el-button type="primary" @click="learnDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getRecommendations, getResourceList, collectResource, getCollectedResources, getKnowledgeMaterial, getResourceLearnMaterial } from '../api/resource'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'

const activeTab = ref('recommend')
const recommendations = ref([])
const allResources = ref({ items: [], total: 0 })
const collected = ref([])
const categories = ref([])
const filterCategory = ref('')
const filterDifficulty = ref('')
const currentPage = ref(1)

// 学习资料弹窗
const learnDialogVisible = ref(false)
const learnDialogTitle = ref('')
const learnDialogContent = ref('')
const learnDialogLoading = ref(false)

onMounted(async () => {
  try { recommendations.value = await getRecommendations() } catch(e) {}
  try {
    allResources.value = await getResourceList({ page: 1 })
    categories.value = allResources.value.categories || []
  } catch(e) {}
  try { collected.value = await getCollectedResources() } catch(e) {}
})

async function fetchAll(page = 1) {
  currentPage.value = page
  allResources.value = await getResourceList({
    page,
    category: filterCategory.value || undefined,
    difficulty: filterDifficulty.value || undefined
  })
}

function onFilterChange() {
  fetchAll(1)
}

function getDiffType(d) { return d === 'Lv1入门' ? 'success' : d === 'Lv2中等' ? 'warning' : 'danger' }

function isCollected(id) { return collected.value.some(c => c.id === id) }

function openResource(resource) {
  learnDialogVisible.value = true
  learnDialogTitle.value = resource.title
  learnDialogContent.value = ''
  learnDialogLoading.value = true
  getResourceLearnMaterial(resource.id).then(res => {
    if (res && res.content) {
      learnDialogTitle.value = res.resource_title || resource.title
      learnDialogContent.value = marked.parse(res.content)
    } else {
      learnDialogContent.value = '<p style="color:#909399">暂无学习资料，请稍后重试</p>'
    }
  }).catch(e => {
    learnDialogContent.value = '<p style="color:#f56c6c">获取学习资料失败，请检查网络后重试</p>'
  }).finally(() => {
    learnDialogLoading.value = false
  })
}

async function toggleCollect(id) {
  try {
    await collectResource(id)
    collected.value = await getCollectedResources()
  } catch(e) {}
}

/** 点击知识点标签 - 联网搜索+AI整理学习资料 */
async function clickKnowledgeTag(tag) {
  learnDialogVisible.value = true
  learnDialogTitle.value = tag
  learnDialogContent.value = ''
  learnDialogLoading.value = true
  try {
    const res = await getKnowledgeMaterial(tag)
    if (res && res.content) {
      learnDialogTitle.value = res.matched_tag || tag
      learnDialogContent.value = marked.parse(res.content)
    } else {
      learnDialogContent.value = '<p style="color:#909399">暂无相关资料，请稍后重试</p>'
    }
  } catch(e) {
    learnDialogContent.value = '<p style="color:#f56c6c">获取学习资料失败，请检查AI配置后重试</p>'
  } finally {
    learnDialogLoading.value = false
  }
}
</script>

<style scoped>
.resource-card { height: 100%; cursor: pointer; }
.resource-card:hover { transform: translateY(-4px); transition: 0.3s; }
.resource-card h4 { margin: 8px 0; font-size: 14px; }
.res-summary { color: #909399; font-size: 13px; line-height: 1.5; }
.res-meta { margin: 8px 0; }
.res-footer { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #c0c4cc; margin-top: 8px; }
.resource-card-small { cursor: pointer; margin-bottom: 16px; }
.resource-card-small:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.filter-bar { margin-bottom: 8px; }

/* 学习资料 Markdown 渲染样式 */
.learn-material-content {
  max-height: 78vh;
  overflow-y: auto;
  padding: 8px 4px;
  font-size: 15px;
  line-height: 1.8;
  color: #303133;
}
.learn-material-content :deep(h1) { font-size: 22px; font-weight: 700; margin: 8px 0 16px; padding-bottom: 8px; border-bottom: 2px solid #409EFF; color: #1a1a2e; }
.learn-material-content :deep(h2) { font-size: 18px; font-weight: 600; margin: 24px 0 12px; color: #303133; border-left: 4px solid #409EFF; padding-left: 12px; }
.learn-material-content :deep(h3) { font-size: 16px; font-weight: 600; margin: 18px 0 10px; color: #409EFF; }
.learn-material-content :deep(p) { margin: 10px 0; }
.learn-material-content :deep(strong) { color: #1a1a2e; }
.learn-material-content :deep(code) { background: #f0f2f5; padding: 2px 6px; border-radius: 4px; font-size: 13px; color: #e83e8c; font-family: 'Courier New', monospace; }
.learn-material-content :deep(pre) { background: #1a1a2e; color: #f8f8f2; padding: 16px; border-radius: 8px; overflow-x: auto; margin: 12px 0; }
.learn-material-content :deep(pre code) { background: none; color: #f8f8f2; padding: 0; font-size: 13px; }
.learn-material-content :deep(ul), .learn-material-content :deep(ol) { padding-left: 24px; margin: 8px 0; }
.learn-material-content :deep(li) { margin: 4px 0; }
.learn-material-content :deep(table) { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 14px; }
.learn-material-content :deep(th) { background: #f5f7fa; padding: 10px 12px; text-align: left; font-weight: 600; border: 1px solid #e4e7ed; }
.learn-material-content :deep(td) { padding: 8px 12px; border: 1px solid #e4e7ed; }
.learn-material-content :deep(blockquote) { border-left: 4px solid #e4e7ed; padding: 8px 16px; margin: 12px 0; background: #fafafa; color: #606266; }
.learn-material-content :deep(hr) { border: none; border-top: 1px solid #e4e7ed; margin: 20px 0; }
</style>
