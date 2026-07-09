<template>
  <div class="error-book-page">
    <!-- 第一级：测评会话列表 -->
    <el-card v-if="activeSession === undefined" shadow="hover" v-loading="loading">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div class="page-title"><el-icon><EditPen /></el-icon> 错题本</div>
          <div style="display:flex;align-items:center;gap:8px">
            <el-button
              v-if="selectedSessions.size > 0"
              type="danger"
              @click="handleBatchDeleteSessions"
              :loading="batchDeleting"
            >
              <el-icon><Delete /></el-icon> 批量删除 ({{ selectedSessions.size }})
            </el-button>
            <el-tag type="danger">共 {{ totalErrors }} 道错题 · {{ sessions.length }} 次测评</el-tag>
          </div>
        </div>
      </template>

      <el-empty v-if="sessions.length === 0 && !loading" description="暂无错题，继续保持！">
        <el-button type="primary" @click="$router.push('/diagnosis')">去做测评</el-button>
      </el-empty>

      <!-- 全选工具栏 -->
      <div v-if="sessions.length > 0" class="batch-toolbar">
        <el-checkbox
          v-model="sessionSelectAll"
          :indeterminate="sessionIndeterminate"
          @change="handleSessionSelectAll"
        >
          全选
        </el-checkbox>
        <span class="batch-hint" v-if="selectedSessions.size > 0">已选 {{ selectedSessions.size }} 组</span>
      </div>

      <div
        v-for="s in sessions"
        :key="s.session_id ?? 'orphan'"
        class="session-card"
        :class="{ 'is-selected': selectedSessions.has(deleteKey(s)) }"
      >
        <div class="session-select" @click.stop>
          <el-checkbox
            :model-value="selectedSessions.has(deleteKey(s))"
            @change="(val) => toggleSessionSelect(s, val)"
          />
        </div>
        <div class="session-body" @click="openSession(s)">
          <div class="session-left">
            <div class="session-label">{{ s.label }}</div>
            <div class="session-meta">
              <span v-if="s.quiz_time">{{ s.quiz_time }}</span>
              <span v-if="s.stage && s.stage !== '未知'"> · {{ s.stage }}</span>
              <span v-if="s.total > 0"> · {{ s.score }}/{{ s.total }} 分</span>
            </div>
          </div>
          <div class="session-right">
            <el-tag type="danger" size="large">{{ s.error_count }} 道错题</el-tag>
            <el-button type="danger" size="small" plain @click.stop="handleDeleteSession(s)" :loading="deleting === deleteKey(s)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 第二级：某次测评的错题详情 -->
    <el-card v-else shadow="hover" v-loading="loadingDetail">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div style="display:flex;align-items:center;gap:12px">
            <el-button @click="backToSessions" text><el-icon><ArrowLeft /></el-icon> 返回</el-button>
            <span class="page-title">{{ currentSession?.label }}</span>
            <el-tag type="danger">{{ sessionErrors.total }} 道错题</el-tag>
          </div>
          <el-button type="danger" plain @click="handleDeleteSession(currentSession)" :loading="deleting === deleteKey(currentSession)">
            <el-icon><Delete /></el-icon> 删除本组全部错题
          </el-button>
        </div>
      </template>

      <el-empty v-if="!sessionErrors.items?.length && !loadingDetail" description="该测评没有错题" />

      <div v-for="error in sessionErrors.items" :key="error.id" class="error-card">
        <div class="error-header">
          <div>
            <el-tag :type="getErrorTypeColor(error.error_type)" size="small">{{ error.error_type }}</el-tag>
            <el-tag type="info" size="small" style="margin-left:8px">{{ error.knowledge_tag }}</el-tag>
            <el-tag v-if="getDifficulty(error)" size="small" style="margin-left:8px" effect="plain">{{ getDifficulty(error) }}</el-tag>
            <span style="margin-left:8px;font-size:12px;color:#c0c4cc">{{ error.created_at?.slice(0,16) }}</span>
          </div>
          <el-tag v-if="error.reviewed" type="success" size="small">已复习</el-tag>
          <el-button v-else type="success" size="small" @click="handleReview(error.id)">标记已复习</el-button>
        </div>

        <!-- 原题完整复述 -->
        <div class="error-original-question">
          <div class="section-title">📝 原题</div>
          <div class="question-full">
            <div class="q-type-tag">
              <el-tag size="small" effect="dark" type="primary">{{ getQuestionType(error) }}</el-tag>
            </div>
            <div class="q-text">{{ getQuestionText(error) }}</div>
            <div v-if="getOptions(error).length > 0" class="q-options">
              <div v-for="(opt, oi) in getOptions(error)" :key="oi" class="q-option"
                   :class="{ 'is-correct': isCorrectOption(opt, error.correct_answer), 'is-user-pick': isUserPick(opt, error.user_answer) }">
                <span class="opt-label">{{ String.fromCharCode(65 + oi) }}</span>
                <div class="opt-body">
                  <span class="opt-text">{{ opt }}</span>
                  <span v-if="getOptionReason(error, oi)" class="opt-reason">{{ getOptionReason(error, oi) }}</span>
                </div>
                <div class="opt-tags">
                  <el-tag v-if="isCorrectOption(opt, error.correct_answer)" size="small" type="success" effect="dark">✓ 正确</el-tag>
                  <el-tag v-if="isUserPick(opt, error.user_answer) && !isCorrectOption(opt, error.correct_answer)" size="small" type="danger" effect="dark">✗ 你的选择</el-tag>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 答案对比 -->
        <div class="error-answer-compare">
          <div class="section-title">⚡ 答案对比</div>
          <div class="answer-row">
            <div class="answer-box wrong-box">
              <div class="answer-label">✗ 你的答案</div>
              <div class="answer-text">{{ error.user_answer || '未作答' }}</div>
            </div>
            <div class="answer-arrow">→</div>
            <div class="answer-box correct-box">
              <div class="answer-label">✓ 正确答案</div>
              <div class="answer-text">{{ error.correct_answer }}</div>
            </div>
          </div>
        </div>

        <!-- 错误分析 -->
        <div class="error-why-wrong">
          <div class="section-title">💡 错误分析</div>
          <div class="why-wrong-text">{{ getWhyWrong(error) }}</div>
        </div>

        <!-- 题目解析 -->
        <div v-if="getAnalysisText(error) && getAnalysisText(error) !== '暂无解析'" class="error-analysis">
          <div class="section-title">📖 详细解析</div>
          <div class="analysis-text">{{ getAnalysisText(error) }}</div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="sessionErrors.total_pages > 1" style="text-align:center;margin-top:16px">
        <el-pagination
          v-model:current-page="detailPage"
          :page-size="sessionErrors.page_size || 50"
          :total="sessionErrors.total"
          layout="prev, pager, next, total"
          @current-change="handleDetailPageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useLearningStore } from '../stores/learning'
import { reviewError, deleteSessionErrors, deleteOrphanErrors } from '../api/learning'
import { ElMessage, ElMessageBox } from 'element-plus'

const store = useLearningStore()
const loading = ref(false)
const loadingDetail = ref(false)
const activeSession = ref(undefined)
const detailPage = ref(1)
const deleting = ref(null)

// 会话批量选择
const selectedSessions = ref(new Set())
const batchDeleting = ref(false)
const sessionSelectAll = ref(false)
const sessionIndeterminate = computed(() =>
  selectedSessions.value.size > 0 && selectedSessions.value.size < (sessions.value.length || 0)
)

function deleteKey(s) {
  return s?.session_id ?? '__orphan__'
}

onMounted(async () => {
  await loadSessions()
})

const sessions = computed(() => store.errorSessions)
const sessionErrors = computed(() => store.sessionErrors)
const currentSession = computed(() => store.errorSessions.find(s => s.session_id === activeSession.value))

const totalErrors = computed(() => store.errorSessions.reduce((sum, s) => sum + s.error_count, 0))

async function loadSessions() {
  loading.value = true
  try {
    await store.fetchErrorSessions()
  } catch(e) {
    console.error('加载错题分组失败:', e)
  } finally {
    loading.value = false
  }
}

async function openSession(session) {
  activeSession.value = session.session_id
  detailPage.value = 1
  await loadSessionErrors()
}

async function loadSessionErrors() {
  loadingDetail.value = true
  try {
    await store.fetchSessionErrors(activeSession.value, detailPage.value)
  } catch(e) {
    console.error('加载错题详情失败:', e)
  } finally {
    loadingDetail.value = false
  }
}

async function backToSessions() {
  activeSession.value = undefined
  detailPage.value = 1
  await loadSessions()
}

async function handleDeleteSession(session) {
  const sid = session.session_id
  const key = deleteKey(session)
  try {
    await ElMessageBox.confirm(
      `确认删除「${session.label}」的全部 ${session.error_count} 道错题？此操作不可恢复。`,
      '删除错题组',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }

  deleting.value = key
  try {
    await store.removeSession(sid)
    ElMessage.success(`已删除 ${session.error_count} 道错题`)
    if (activeSession.value !== undefined) {
      activeSession.value = undefined
      detailPage.value = 1
    }
    selectedSessions.value = new Set()
    sessionSelectAll.value = false
    await loadSessions()
  } catch(e) {
    ElMessage.error('删除失败')
  } finally {
    deleting.value = null
  }
}

// ===== 批量删除会话 =====

function toggleSessionSelect(session, checked) {
  const key = deleteKey(session)
  if (checked) {
    selectedSessions.value.add(key)
  } else {
    selectedSessions.value.delete(key)
  }
  selectedSessions.value = new Set(selectedSessions.value)
  updateSessionSelectAll()
}

function handleSessionSelectAll(checked) {
  if (checked) {
    selectedSessions.value = new Set(sessions.value.map(s => deleteKey(s)))
  } else {
    selectedSessions.value = new Set()
  }
}

function updateSessionSelectAll() {
  const total = sessions.value.length || 0
  const sel = selectedSessions.value.size
  sessionSelectAll.value = total > 0 && sel === total
}

async function handleBatchDeleteSessions() {
  if (selectedSessions.value.size === 0) return

  const toDelete = sessions.value.filter(s => selectedSessions.value.has(deleteKey(s)))
  const totalErrors = toDelete.reduce((sum, s) => sum + s.error_count, 0)

  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedSessions.value.size} 组错题集（共 ${totalErrors} 道错题）？此操作不可恢复。`,
      '批量删除',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }

  batchDeleting.value = true
  let deleted = 0
  try {
    for (const s of toDelete) {
      if (s.session_id != null) {
        await deleteSessionErrors(s.session_id)
      } else {
        await deleteOrphanErrors()
      }
      deleted++
    }
    ElMessage.success(`已删除 ${deleted} 组错题集（共 ${totalErrors} 道错题）`)
    selectedSessions.value = new Set()
    sessionSelectAll.value = false
    await loadSessions()
  } catch(e) {
    ElMessage.error(`已删除 ${deleted} 组，部分删除失败`)
  } finally {
    batchDeleting.value = false
  }
}

async function handleDetailPageChange(page) {
  detailPage.value = page
  await loadSessionErrors()
}

async function handleReview(id) {
  try {
    await reviewError(id)
    ElMessage.success('已标记为已复习')
    await loadSessionErrors()
  } catch(e) { ElMessage.error('操作失败') }
}

function getQuestionData(error) {
  if (error.question_data && typeof error.question_data === 'object') return error.question_data
  if (typeof error.question_data === 'string') {
    try { return JSON.parse(error.question_data) } catch { return {} }
  }
  return {}
}

function getQuestionText(error) {
  const qd = getQuestionData(error)
  return qd.question || '题目内容缺失'
}

function getQuestionType(error) {
  const qd = getQuestionData(error)
  return qd.question_type || '简答'
}

function getDifficulty(error) {
  const qd = getQuestionData(error)
  return qd.difficulty || ''
}

function getOptions(error) {
  const qd = getQuestionData(error)
  return qd.options || []
}

function isCorrectOption(opt, correctAnswer) {
  if (!correctAnswer) return false
  return opt === correctAnswer || correctAnswer.includes(opt)
}

function isUserPick(opt, userAnswer) {
  if (!userAnswer) return false
  return opt === userAnswer || userAnswer.includes(opt)
}

function getOptionReason(error, optionIndex) {
  // 优先使用后端生成的逐选项解析
  const qd = getQuestionData(error)
  const optionAnalysis = qd.option_analysis || {}
  const letter = String.fromCharCode(65 + optionIndex)
  if (optionAnalysis[letter]) return optionAnalysis[letter]

  // 兜底：基础判断
  const options = getOptions(error)
  const opt = options[optionIndex]
  if (!opt) return ''
  const correctAnswer = (error.correct_answer || '').trim()
  const knowledgeTag = error.knowledge_tag || '该知识点'
  if (isCorrectOption(opt, correctAnswer)) {
    return `[正确选项] 该选项准确描述了「${knowledgeTag}」的核心概念，是本题的正确答案。`
  }
  return `[错误选项] 该选项不符合题意，可能混淆了「${knowledgeTag}」中的相似概念。请查看下方错误分析中的逐选项讲解。`
}

function getAnalysisText(error) {
  const qd = getQuestionData(error)
  return qd.analysis || '暂无解析'
}

function getWhyWrong(error) {
  const userAnswer = (error.user_answer || '').trim()
  const correctAnswer = (error.correct_answer || '').trim()
  const errorType = error.error_type || ''
  const questionType = getQuestionType(error)
  const knowledgeTag = error.knowledge_tag || '该知识点'
  const questionText = getQuestionText(error)

  // 未作答
  if (!userAnswer) {
    return [
      '▸ 未作答',
      '',
      '可能原因：',
      `  • 对「${knowledgeTag}」的基础概念不了解，无从下手`,
      '  • 答题时间不够，来不及写',
      '  • 没看懂题目在问什么',
      '',
      '建议：',
      `  1. 先搞懂「${knowledgeTag}」的核心定义`,
      '  2. 下次遇到不熟悉的题，先写你知道的部分',
      '  3. 控制每题答题时间，不要卡在一题上',
    ].join('\n')
  }

  const overlap = _calcOverlap(userAnswer, correctAnswer)

  // 选择/判断题
  if (questionType === '单选' || questionType === '判断') {
    return _analyzeChoiceError(error, userAnswer, correctAnswer, overlap, knowledgeTag)
  }

  // 填空题
  if (questionType === '填空') {
    return _analyzeFillBlankError(userAnswer, correctAnswer, overlap, knowledgeTag)
  }

  // 简答题（默认）
  return _analyzeShortAnswerError(userAnswer, correctAnswer, overlap, knowledgeTag)
}

function _analyzeChoiceError(error, userAnswer, correctAnswer, overlap, knowledgeTag) {
  const out = []
  const options = getOptions(error)
  const labels = ['A', 'B', 'C', 'D', 'E', 'F']

  out.push('▸ 选项分析')
  out.push('')

  // 逐选项讲解
  if (options.length > 0) {
    for (let i = 0; i < options.length; i++) {
      const opt = options[i]
      const label = labels[i] || String(i)
      const isCorrect = isCorrectOption(opt, correctAnswer)
      const isUser = isUserPick(opt, userAnswer)

      out.push(`${label}. ${opt}`)
      if (isCorrect) {
        out.push(`   ✅ 正确选项。这是「${knowledgeTag}」知识点的准确描述。`)
      } else if (isUser) {
        out.push(`   ❌ 你的选择。该选项不正确，你可能混淆了「${knowledgeTag}」中的相关概念。`)
      } else {
        out.push(`   — 错误选项，与正确答案不符。`)
      }
      out.push('')
    }
  }

  // 总评
  out.push('▸ 诊断')
  out.push('')
  if (overlap < 0.1) {
    out.push(`你选的答案与正确答案基本无关，说明对「${knowledgeTag}」的核心概念理解有误。`)
  } else if (overlap < 0.4) {
    out.push(`你的选择沾边但不准确，对「${knowledgeTag}」有浅层认知但关键细节没掌握。`)
  } else {
    out.push(`大方向对的，但在关键细节上出现了偏差。`)
  }

  out.push('')
  out.push('建议：')
  out.push(`  1. 把每个选项当作一道判断题来做，逐个排除`)
  out.push(`  2. 重点关注「${knowledgeTag}」中容易混淆的相似概念的区别`)
  out.push('  3. 做2-3道同类选择题，直到能准确说出每个选项为什么对/错')

  return out.join('\n')
}

function _analyzeFillBlankError(userAnswer, correctAnswer, overlap, knowledgeTag) {
  const out = []

  if (overlap < 0.1) {
    out.push('▸ 完全未掌握')
    out.push('')
    out.push(`你对「${correctAnswer}」这个关键概念没有印象，可能是还没学到或遗忘了。`)
    out.push('')
    out.push('建议：')
    out.push(`  1. 搜索「${correctAnswer}」，阅读定义和相关内容`)
    out.push('  2. 制作记忆卡片，正面写概念名，背面写定义和示例')
    out.push('  3. 用「' + correctAnswer + '」造个句子加深印象')
  } else if (overlap < 0.5) {
    out.push('▸ 记忆模糊')
    out.push('')
    out.push(`你记得有这个知识点但表述不准确，「${userAnswer}」和「${correctAnswer}」有差距。`)
    out.push('')
    out.push('建议：')
    out.push(`  1. 整理「${knowledgeTag}」的术语表，每天过一遍`)
    out.push('  2. 用默写代替浏览——盖住答案自己写，然后对照纠错')
  } else {
    out.push('▸ 接近正确')
    out.push('')
    out.push('大方向对，但表述不够精准，差一点就对了。填空对精确性要求很高。')
    out.push('')
    out.push('建议：')
    out.push('  1. 对比差异点——往往就是关键得分点')
    out.push('  2. 养成精准表达的习惯，差一个字可能就是错的')
  }

  return out.join('\n')
}

function _analyzeShortAnswerError(userAnswer, correctAnswer, overlap, knowledgeTag) {
  const out = []

  if (overlap < 0.1) {
    out.push('▸ 方向完全错误')
    out.push('')
    out.push(`你的回答与参考答案几乎没有共同关键词，可能：`)
    out.push(`  • 把「${knowledgeTag}」和其他概念搞混了`)
    out.push('  • 没审清题，答偏了方向')
    out.push('')
    out.push('行动：')
    out.push(`  1. 重新阅读「${knowledgeTag}」章节，搞清楚核心定义`)
    out.push('  2. 合上书写下3个要点，再和答案对比')
  } else if (overlap < 0.4) {
    out.push('▸ 部分相关，偏差较大')
    out.push('')
    out.push('你的回答涉及了相关知识，但整体方向有偏差，理解不够系统。')
    out.push('')
    out.push('行动：')
    out.push(`  1. 对比你和答案的关键词差异，找出认知盲区`)
    out.push(`  2. 梳理「${knowledgeTag}」的知识结构，理清各要素之间的关系`)
  } else {
    out.push('▸ 接近正确，细节不足')
    out.push('')
    out.push('大方向对了，但关键细节不够精准，或遗漏了部分要点。')
    out.push('')
    out.push('行动：')
    out.push('  1. 逐句对比你和参考答案的差异点')
    out.push('  2. 把遗漏和错误的部分标注出来，重点复习')
    out.push('  3. 一周后重新作答，检验掌握程度')
  }

  return out.join('\n')
}

/** 计算两段文本的词汇重叠度 (0~1) */
function _calcOverlap(text1, text2) {
  if (!text1 || !text2) return 0
  const words1 = new Set(text1.toLowerCase().replace(/[，,。.、\s]+/g, ' ').split(' ').filter(w => w.length >= 2))
  const words2 = new Set(text2.toLowerCase().replace(/[，,。.、\s]+/g, ' ').split(' ').filter(w => w.length >= 2))
  if (words2.size === 0) return 0
  const common = [...words2].filter(w => words1.has(w)).length
  return common / words2.size
}

function getErrorTypeColor(type) {
  const map = {
    '概念认知偏差': 'warning',
    '代码语法失误': 'danger',
    '知识点遗漏': 'info',
    '审题理解偏差': ''
  }
  return map[type] || ''
}
</script>

<style scoped>
.page-title { display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: bold; }

/* 会话选择工具栏 */
.batch-toolbar { display: flex; align-items: center; gap: 12px; padding: 10px 14px; margin-bottom: 12px; background: #f5f7fa; border-radius: 8px; }
.batch-hint { font-size: 13px; color: #F56C6C; font-weight: 500; }

/* 会话卡片 */
.session-card {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 20px; margin-bottom: 8px;
  background: #fafafa; border-radius: 10px; border: 1px solid #f0f0f0;
  transition: all .2s;
}
.session-card.is-selected { background: #fef0f0; border-color: #fab6b6; }
.session-select { flex-shrink: 0; }
.session-body { flex: 1; display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
.session-body:hover .session-left { color: #409EFF; }
.session-left { flex: 1; }
.session-label { font-size: 15px; font-weight: 500; color: #303133; margin-bottom: 4px; }
.session-meta { font-size: 12px; color: #909399; }
.session-right { display: flex; align-items: center; gap: 12px; }

/* 错题详情卡片 */
.error-card { padding: 20px; margin-bottom: 16px; background: #fafafa; border-radius: 12px; border: 1px solid #f0f0f0; }
.error-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.section-title { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 8px; }

/* 原题区域 */
.error-original-question { margin-bottom: 16px; background: #fff; padding: 14px; border-radius: 8px; border: 1px solid #e4e7ed; }
.q-type-tag { margin-bottom: 8px; }
.q-text { font-size: 15px; color: #1a1a2e; line-height: 1.7; font-weight: 500; }
.q-options { margin-top: 10px; }
.q-option { display: flex; align-items: flex-start; gap: 8px; padding: 10px 12px; margin: 6px 0; border-radius: 6px; background: #f5f7fa; border: 1px solid #e4e7ed; }
.q-option.is-correct { background: #f0f9eb; border-color: #b3e19d; }
.q-option.is-user-pick { background: #fef0f0; border-color: #fab6b6; }
.opt-label { font-weight: 700; font-size: 14px; color: #409EFF; min-width: 20px; padding-top: 1px; }
.opt-body { flex: 1; min-width: 0; }
.opt-text { font-size: 14px; line-height: 1.6; }
.opt-reason { display: block; margin-top: 4px; font-size: 12px; color: #909399; line-height: 1.5; }
.opt-tags { flex-shrink: 0; display: flex; gap: 4px; }

/* 答案对比 */
.error-answer-compare { margin-bottom: 16px; }
.answer-row { display: flex; align-items: center; gap: 12px; }
.answer-box { flex: 1; padding: 12px; border-radius: 8px; min-height: 50px; }
.wrong-box { background: #fef0f0; border: 1px solid #fab6b6; }
.correct-box { background: #f0f9eb; border: 1px solid #b3e19d; }
.answer-label { font-size: 12px; font-weight: 600; margin-bottom: 4px; }
.wrong-box .answer-label { color: #F56C6C; }
.correct-box .answer-label { color: #67C23A; }
.answer-text { font-size: 14px; color: #303133; line-height: 1.6; white-space: pre-wrap; }
.answer-arrow { font-size: 20px; color: #c0c4cc; font-weight: bold; }

/* 错误分析 */
.error-why-wrong { margin-bottom: 16px; background: #fff7e6; padding: 12px 14px; border-radius: 8px; border-left: 4px solid #e6a23c; }
.why-wrong-text { font-size: 14px; color: #303133; line-height: 1.7; }

/* 详细解析 */
.error-analysis { background: #f0f5ff; padding: 12px 14px; border-radius: 8px; border-left: 4px solid #409EFF; }
.analysis-text { font-size: 14px; color: #303133; line-height: 1.7; white-space: pre-wrap; }
</style>
