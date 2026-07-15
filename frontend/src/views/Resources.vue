<template>
  <div class="resources-page">
    <div class="resources-layout">
      <!-- 左侧：学习资源 -->
      <div class="resources-main">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="全部资源" name="all">
            <div style="margin-bottom:12px">
              <el-select v-model="filterCategory" placeholder="按模块筛选" clearable style="width:280px" @change="fetchAll">
                <el-option v-for="m in moduleList" :key="m.key" :label="m.label" :value="m.key" />
              </el-select>
            </div>
            <div v-for="mod in moduleGroups" :key="mod.key" style="margin-bottom:32px">
              <div style="display:flex;align-items:center;gap:8px;padding:12px 0;margin-bottom:12px;border-bottom:2px solid #409EFF">
                <span style="font-size:22px">{{ mod.icon }}</span>
                <span style="font-size:17px;font-weight:700;color:#1a1a2e">{{ mod.label }}</span>
                <el-tag size="small" type="info">{{ mod.items.length }}个</el-tag>
              </div>
              <el-row :gutter="20">
                <el-col :span="8" v-for="item in mod.items" :key="item.id">
                  <el-card shadow="hover" style="cursor:pointer;margin-bottom:16px" @click="openResource(item)">
                    <div style="display:flex;justify-content:space-between">
                      <el-tag :type="item.difficulty==='Lv1入门'?'success':item.difficulty==='Lv2中等'?'warning':'danger'" size="small">{{ item.difficulty }}</el-tag>
                    </div>
                    <h4 style="margin:8px 0">{{ item.title }}</h4>
                    <p style="color:#909399;font-size:13px">{{ item.summary?.slice(0,60) }}...</p>
                    <span style="font-size:12px;color:#c0c4cc">{{ item.duration }}</span>
                  </el-card>
                </el-col>
              </el-row>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- 右侧：PDF电子书 -->
      <div class="resources-pdf-sidebar">
        <el-card shadow="hover">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <div style="display:flex;align-items:center;gap:8px">
                <span style="font-weight:700;color:#1a1a2e">电子书</span>
                <el-tag size="small" type="info">{{ pdfs.length }}本</el-tag>
              </div>
              <div v-if="selectedPdfs.size > 0" style="display:flex;align-items:center;gap:6px">
                <span style="font-size:12px;color:#F56C6C">已选{{ selectedPdfs.size }}本</span>
                <el-button type="danger" size="small" @click="handleBatchDeletePdfs" :loading="batchDeleting">
                  批量删除
                </el-button>
              </div>
            </div>
          </template>

          <!-- 上传按钮 -->
          <div style="margin-bottom:16px">
            <input
              ref="fileInput"
              type="file"
              accept=".pdf"
              multiple
              style="display:none"
              @change="onFilesSelected"
            />
            <el-button type="primary" style="width:100%" :loading="uploading" @click="$refs.fileInput.click()">
              <el-icon><Upload /></el-icon> 上传PDF（可多选）
            </el-button>
            <div style="font-size:11px;color:#c0c4cc;margin-top:4px">支持PDF，单文件最大200MB，可一次选多个</div>
          </div>
          <!-- 上传状态 -->
          <div v-if="uploadTasks.length > 0" style="margin-bottom:12px">
            <div v-for="t in uploadTasks" :key="t.name" style="font-size:12px;padding:4px 0;color:#909399">
              <span v-if="t.status==='uploading'">{{ t.name }}</span>
              <span v-else-if="t.status==='done'" style="color:#67C23A">{{ t.name }}</span>
              <span v-else-if="t.status==='error'" style="color:#F56C6C">{{ t.name }}: {{ t.err }}</span>
            </div>
          </div>

          <!-- PDF列表 -->
          <div v-if="pdfs.length === 0" style="text-align:center;padding:20px;color:#c0c4cc">
            暂无电子书，上传PDF开始阅读
          </div>
          <div v-for="pdf in pdfs" :key="pdf.id" class="pdf-item" :class="{ 'is-selected': selectedPdfs.has(pdf.id) }">
            <el-checkbox :model-value="selectedPdfs.has(pdf.id)" @change="(v) => togglePdfSelect(pdf.id, v)" style="flex-shrink:0" />
            <div class="pdf-cover" @click="openPdf(pdf)">
              <img v-if="pdf.cover" :src="`/api/resources/pdf/cover/${pdf.id}`" class="cover-img" />
              <span v-else class="pdf-icon">PDF</span>
            </div>
            <div class="pdf-info">
              <div class="pdf-name" :title="pdf.name">{{ pdf.name }}</div>
              <div class="pdf-meta">{{ formatSize(pdf.size) }} · {{ pdf.created_at?.slice(0,10) }}</div>
              <div class="pdf-actions">
                <el-button type="primary" size="small" @click.stop="openPdf(pdf)"><el-icon><View /></el-icon> 打开</el-button>
                <el-button type="success" size="small" @click.stop="downloadPdf(pdf)"><el-icon><Download /></el-icon> 下载</el-button>
                <el-button type="danger" size="small" @click.stop="handleDeletePdf(pdf)"><el-icon><Delete /></el-icon> 删除</el-button>
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </div>
    <!-- 学习资料弹窗 -->
    <div v-if="dialogVisible" @click.self="dialogVisible=false" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:99999;display:flex;align-items:flex-start;justify-content:center;padding-top:3vh">
      <div style="background:#fff;border-radius:8px;width:90%;max-height:90vh;display:flex;flex-direction:column;box-shadow:0 20px 60px rgba(0,0,0,0.3)">
        <div style="display:flex;justify-content:space-between;align-items:center;padding:16px 24px;border-bottom:1px solid #e4e7ed">
          <h2 style="margin:0;font-size:18px">{{ dialogTitle }}</h2>
          <button @click="dialogVisible=false" style="background:none;border:none;font-size:28px;cursor:pointer;color:#909399">&times;</button>
        </div>
        <div style="flex:1;overflow-y:auto;padding:16px 24px;font-size:15px;line-height:1.8;color:#303133">
          <div v-if="dialogLoading" style="text-align:center;padding:40px;color:#409EFF">加载中...</div>
          <div v-else v-html="dialogContent" ref="contentRef"></div>
        </div>
      </div>
    </div>

    <!-- PDF 阅读器弹窗 -->
    <div v-if="pdfViewerVisible" @click.self="pdfViewerVisible=false" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);z-index:99999;display:flex;align-items:flex-start;justify-content:center;padding-top:2vh">
      <div style="background:#fff;border-radius:8px;width:95%;height:94vh;display:flex;flex-direction:column;box-shadow:0 20px 60px rgba(0,0,0,0.3)">
        <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 20px;border-bottom:1px solid #e4e7ed;flex-shrink:0">
          <span style="font-weight:600;font-size:16px">{{ pdfViewerTitle }}</span>
          <div style="display:flex;gap:8px">
            <el-button size="small" @click="downloadPdf(pdfViewerPdf)"><el-icon><Download /></el-icon> 下载</el-button>
            <button @click="pdfViewerVisible=false" style="background:none;border:none;font-size:28px;cursor:pointer;color:#909399;line-height:1">&times;</button>
          </div>
        </div>
        <div style="flex:1;overflow:hidden">
          <iframe :src="pdfViewerUrl" style="width:100%;height:100%;border:none" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { getResourceList, getResourceLearnMaterial, uploadPdf, getPdfList, getPdfUrl, deletePdf, batchDeletePdfs } from '../api/resource'
import { ElMessage, ElMessageBox } from 'element-plus'
import { recordStudyVisit } from '../api/learning'
import { renderMermaidIn, asciiToMermaid } from '../composables/useMermaid'

const activeTab = ref('all')
const allResources = ref({ items: [] })
const filterCategory = ref('')
const dialogVisible = ref(false)
const dialogTitle = ref('')
const dialogContent = ref('')
const dialogLoading = ref(false)
const contentRef = ref(null)

// PDF 电子书
const pdfs = ref([])
const uploading = ref(false)
const uploadTasks = ref([])
const selectedPdfs = ref(new Set())
const batchDeleting = ref(false)

function togglePdfSelect(id, checked) {
  if (checked) selectedPdfs.value.add(id)
  else selectedPdfs.value.delete(id)
  selectedPdfs.value = new Set(selectedPdfs.value)
}

const moduleList = [
  { key: '模块一：智能体基础通识', label: '模块一：智能体基础通识', icon: '' },
  { key: '模块二：大模型与提示词工程', label: '模块二：大模型与提示词工程', icon: '' },
  { key: '模块三：智能体四大核心能力模块', label: '模块三：智能体四大核心能力模块', icon: '' },
  { key: '模块四：开发框架与工程实践', label: '模块四：开发框架与工程实践', icon: '' },
  { key: '模块五：多智能体系统', label: '模块五：多智能体系统', icon: '' },
  { key: '模块六：评估、安全与前沿拓展', label: '模块六：评估、安全与前沿拓展', icon: '' }
]

const moduleGroups = computed(() => {
  return moduleList.map(m => ({ ...m, items: (allResources.value.items||[]).filter(i => i.category === m.key) })).filter(m => m.items.length > 0)
})

onMounted(() => { recordStudyVisit(); fetchAll(); fetchPdfs() })
async function fetchAll() {
  try { allResources.value = await getResourceList({ page: 1, page_size: 100, category: filterCategory.value||undefined }) } catch(e) {}
}

// PDF 电子书相关
async function fetchPdfs() {
  try { pdfs.value = await getPdfList() } catch(e) {}
}
async function onFilesSelected(e) {
  const files = e.target.files
  if (!files || files.length === 0) return
  uploading.value = true
  uploadTasks.value = []
  let doneCount = 0; let failCount = 0
  for (const file of files) {
    if (!file.name.toLowerCase().endsWith('.pdf')) continue
    const task = { name: file.name, status: 'uploading', err: '' }
    uploadTasks.value.push(task)
    try {
      await uploadPdf(file)
      task.status = 'done'
      doneCount++
    } catch(err) {
      task.status = 'error'
      task.err = err?.response?.data?.detail || err?.message || '未知错误'
      failCount++
    }
  }
  uploading.value = false
  if (doneCount > 0 && failCount === 0) ElMessage.success(`成功上传 ${doneCount} 个文件`)
  else if (doneCount > 0 && failCount > 0) ElMessage.warning(`${doneCount} 个成功, ${failCount} 个失败`)
  else if (failCount > 0) ElMessage.error(`${failCount} 个上传失败`)
  await fetchPdfs()
  // 重置 input 以便再次选择相同文件
  e.target.value = ''
  setTimeout(() => { uploadTasks.value = [] }, 3000)
}
// PDF 阅读器
const pdfViewerVisible = ref(false)
const pdfViewerUrl = ref('')
const pdfViewerTitle = ref('')
const pdfViewerPdf = ref(null)

function openPdf(pdf) {
  const token = localStorage.getItem('token')
  pdfViewerPdf.value = pdf
  pdfViewerTitle.value = pdf.name
  pdfViewerUrl.value = getPdfUrl(pdf.id) + '?token=' + encodeURIComponent(token)
  pdfViewerVisible.value = true
}

function downloadPdf(pdf) {
  const token = localStorage.getItem('token')
  const url = getPdfUrl(pdf.id) + '?token=' + encodeURIComponent(token) + '&download=1'
  const a = document.createElement('a')
  a.href = url
  a.download = pdf.name
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
async function handleDeletePdf(pdf) {
  try {
    await ElMessageBox.confirm(`确定删除「${pdf.name}」？`, '删除电子书', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
  } catch { return }
  try {
    await deletePdf(pdf.id)
    ElMessage.success('已删除')
    await fetchPdfs()
  } catch(e) {
    ElMessage.error('删除失败')
  }
}

async function handleBatchDeletePdfs() {
  if (selectedPdfs.value.size === 0) return
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedPdfs.value.size} 本电子书？此操作不可恢复。`,
      '批量删除', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }
  batchDeleting.value = true
  try {
    const result = await batchDeletePdfs([...selectedPdfs.value])
    ElMessage.success(`已删除 ${result.deleted} 本电子书`)
    selectedPdfs.value = new Set()
    await fetchPdfs()
  } catch(e) {
    ElMessage.error('批量删除失败')
  } finally {
    batchDeleting.value = false
  }
}
function formatSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

window._prompts = {}

async function openResource(resource) {
  dialogVisible.value = true
  dialogTitle.value = resource.title
  dialogContent.value = ''
  dialogLoading.value = true
  try {
    if (!window.marked) {
      await new Promise((resolve) => {
        const s = document.createElement('script')
        s.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js'
        s.onload = resolve
        document.head.appendChild(s)
      })
    }
    const res = await getResourceLearnMaterial(resource.id)
    if (res && res.content) {
      dialogTitle.value = res.resource_title || resource.title
      var raw = res.content
      // ===== ASCII‑Art → Mermaid 自动转换 =====
      raw = raw.replace(/```\s*\n?([\s\S]*?)```/g, function(m, content) {
        // 检测盒绘图字符
        var boxCount = (content.match(/[┌─│└├┐┘┴┬┤┼]/g) || []).length
        if (boxCount >= 8) {
          var mermaidCode = asciiToMermaid(content)
          if (mermaidCode) {
            // asciiToMermaid 已经包含了 ``` 包裹
            return mermaidCode
          }
          // 无法识别 → 隐藏，不显示乱码 ASCII
          return '\n\n> *此结构图暂未适配 Mermaid，如需显示请联系管理员转换。*\n\n'
        }
        return m
      })
      // ===== 提取 Image-Prompt 为卡片 =====
      window._prompts = {}
      var counter = 0
      // 提取 Image-Prompt 为卡片
      raw = raw.replace(/(?:\*\*)?Image-Prompt\(([^)]+)\):(?:\*\*)?\s*([\s\S]*?)(?=\n\n(?:#|\*\*Image-Prompt|Image-Prompt)|\n(?:#|\*\*Image-Prompt|Image-Prompt)|$)/g, function(m, label, body) {
        var clean = body.trim().replace(/^```\s*/,'').replace(/\s*```$/,'').trim()
        if (clean && clean.length > 10) {
          var id = counter++
          window._prompts[id] = clean
          return '%%PROMPT_' + id + '%%'
        }
        return ''
      })
      var html = window.marked.parse(raw)
      // ===== Mermaid 代码块直接转为 <div class="mermaid"> =====
      html = html.replace(/<pre><code class="language-mermaid">([\s\S]*?)<\/code><\/pre>/g, function(m, code) {
        // marked.js 会把 < > & 转义，需要解码
        var decoded = code.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/&quot;/g, '"')
        return '<div class="mermaid">' + decoded + '</div>'
      })
      // 按 h2 分页
      var parts = html.split(/(?=<h2)/i)
      if (parts.length > 1) {
        var pages = parts
        var cid = 'pages_' + Date.now()
        window._pageData = { pages: pages, cid: cid, current: 0 }
        var nav = '<div id="' + cid + '_nav" style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;margin-bottom:16px;border-bottom:1px solid #e4e7ed"></div>'
        var body = '<div id="' + cid + '_body"></div>'
        html = nav + body
      }
      var maxShow = 3
      // 前4张替换为卡片（保留在原文位置），其余删除
      for (var i = 0; i < counter; i++) {
        var text = window._prompts[i]
        var first = text.split('.')[0] + '.'
        if (first.length > 120) first = first.substring(0, 120) + '...'
        var card = '<div class="prompt-card" data-pid="' + i + '" style="margin:24px 0;border-radius:10px;overflow:hidden;background:#fff;border:1px solid #d4e6ff;box-shadow:0 1px 8px rgba(64,158,255,0.06)">' +
          '<div style="display:flex;align-items:center;gap:8px;padding:10px 18px;background:linear-gradient(135deg,#eef6ff,#e3f0ff)">' +
            '<span style="font-size:18px">️</span><span style="font-weight:600;color:#2c6fce;font-size:13px">配图</span>' +
            '<button class="gen-btn" data-pid="' + i + '" style="margin-left:auto;padding:5px 14px;background:#409EFF;color:#fff;border:none;border-radius:6px;font-size:12px;cursor:pointer"> 生成</button>' +
          '</div>' +
          '<div style="padding:14px 18px">' +
            '<div class="img-result" data-pid="' + i + '" style="display:none;margin-bottom:12px;text-align:center"></div>' +
            '<p style="margin:0 0 10px;font-size:13px;color:#444;line-height:1.7">' + first + '</p>' +
            '<details><summary style="cursor:pointer;font-size:12px;color:#409EFF">完整提示词</summary>' +
              '<pre style="margin:10px 0 0;padding:12px;background:#f8fafc;border-radius:6px;font-size:12px;color:#555;line-height:1.7;white-space:pre-wrap;word-break:break-word;max-height:300px;overflow-y:auto">' + text.replace(/</g,'&lt;').replace(/&/g,'&amp;') + '</pre>' +
            '</details>' +
          '</div></div>'
        if (i < maxShow) {
          // 前4张：替换占位符保留在原文位置
          html = html.split('%%PROMPT_' + i + '%%').join(card)
          html = html.split('<p>%%PROMPT_' + i + '%%</p>').join(card)
        } else {
          // 其余的删除占位符，后面折叠放
          html = html.split('%%PROMPT_' + i + '%%').join('')
          html = html.split('<p>%%PROMPT_' + i + '%%</p>').join('')
        }
      }
      // 多余的折叠在末尾
      if (counter > maxShow) {
        var hidden = ''
        for (var j = maxShow; j < counter; j++) {
          var t2 = window._prompts[j]
          var f2 = t2.split('.')[0] + '.'
          if (f2.length > 120) f2 = f2.substring(0, 120) + '...'
          hidden += '<div class="prompt-card" data-pid="' + j + '" style="margin:16px 0;border-radius:10px;overflow:hidden;background:#fff;border:1px solid #d4e6ff;box-shadow:0 1px 8px rgba(64,158,255,0.06)">' +
            '<div style="display:flex;align-items:center;gap:8px;padding:10px 18px;background:linear-gradient(135deg,#eef6ff,#e3f0ff)">' +
              '<span style="font-size:18px">️</span><span style="font-weight:600;color:#2c6fce;font-size:13px">配图</span>' +
              '<button class="gen-btn" data-pid="' + j + '" style="margin-left:auto;padding:5px 14px;background:#409EFF;color:#fff;border:none;border-radius:6px;font-size:12px;cursor:pointer"> 生成</button>' +
            '</div>' +
            '<div style="padding:14px 18px">' +
              '<div class="img-result" data-pid="' + j + '" style="display:none;margin-bottom:12px;text-align:center"></div>' +
              '<p style="margin:0 0 10px;font-size:13px;color:#444;line-height:1.7">' + f2 + '</p>' +
            '</div></div>'
        }
        html += '<details style="margin-top:24px"><summary style="cursor:pointer;font-size:14px;color:#409EFF;font-weight:600"> 更多配图 (+' + (counter - maxShow) + '条)</summary>' + hidden + '</details>'
      }
      dialogContent.value = html
      // 分页渲染
      setTimeout(function() {
        var pd = window._pageData
        if (pd && pd.pages.length > 1) {
          window._showPage = function(idx) {
            var d = window._pageData
            if (!d) return
            if (idx < 0) idx = 0
            if (idx >= d.pages.length) idx = d.pages.length - 1
            d.current = idx
            var ne = document.getElementById(d.cid + '_nav')
            var be = document.getElementById(d.cid + '_body')
            if (ne) ne.innerHTML = '<button onclick="window._showPage(' + (idx-1) + ')" style="padding:6px 16px;background:#f0f2f5;border:1px solid #d9d9d9;border-radius:6px;cursor:pointer;font-size:13px" ' + (idx===0?'disabled':'') + '>◀ 上一页</button>' +
              '<span style="font-size:13px;color:#909399">' + (idx+1) + ' / ' + d.pages.length + '</span>' +
              '<button onclick="window._showPage(' + (idx+1) + ')" style="padding:6px 16px;background:#409EFF;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px" ' + (idx===d.pages.length-1?'disabled':'') + '>下一页 ▶</button>'
            if (be) be.innerHTML = d.pages[idx] || ''
            // 渲染当前页的 Mermaid 图表
            if (be) setTimeout(function() { renderMermaidIn(be) }, 50)
          }
          window._showPage(0)
        }
      }, 100)

      // 绑定按钮
      setTimeout(function() {
        var btns = document.querySelectorAll('.gen-btn[data-pid]')
        btns.forEach(function(btn) {
          btn.addEventListener('click', function() {
            genImage(btn, parseInt(this.getAttribute('data-pid')))
          })
        })
        // 自动生成前2张（缓存秒出，未缓存后台生成）
        if (btns.length > 0) genImage(btns[0], 0)
        if (btns.length > 1) setTimeout(function(){ genImage(btns[1], 1) }, 500)
        if (btns.length > 2) setTimeout(function(){ genImage(btns[2], 2) }, 1000)
      }, 200)
    }
  } catch(e) {}
  dialogLoading.value = false
  // ===== 渲染 Mermaid 图表（dialogLoading=false 后 DOM 才挂载）=====
  nextTick(function() { renderMermaidIn(contentRef.value) })
}

async function loadCached() {
  try {
    var resp = await fetch('/api/images/list', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
    })
    var data = await resp.json()
    if (data.code === 200 && data.data) {
      for (var i = 0; i < data.data.length; i++) {
        var item = data.data[i]
        for (var pid in window._prompts) {
          var encoded = new TextEncoder().encode(window._prompts[pid])
          var hashBuffer = await crypto.subtle.digest('SHA-256', encoded)
          var hash = Array.from(new Uint8Array(hashBuffer)).map(b => b.toString(16).padStart(2, '0')).join('')
          if (hash === item.prompt_hash) {
            var div = document.querySelector('.img-result[data-pid="' + pid + '"]')
            var btn = document.querySelector('.gen-btn[data-pid="' + pid + '"]')
            if (div && btn) {
              div.innerHTML = '<div style="text-align:center;padding:12px;background:#fafbfc;border-radius:6px;overflow:hidden;max-height:800px"><img src="' + item.url + '" style="max-width:100%;height:auto;display:block" onerror="this.parentElement.innerHTML=\'加载失败\'" /></div>'
              div.style.display = 'block'
              btn.textContent = ''
              btn.style.background = '#67C23A'
            }
          }
        }
      }
    }
  } catch(e) {}
}

async function onPageClick(e) {
  var btn = e.target.closest('[data-page]')
  if (btn) {
    var idx = parseInt(btn.getAttribute('data-page'))
    if (window._showPage) window._showPage(idx)
  }
}

async function genImage(btn, pid) {
  var prompt = window._prompts[pid]
  if (!prompt) return
  var card = btn.closest('.prompt-card')
  var resultDiv = card.querySelector('.img-result')
  btn.disabled = true
  btn.textContent = '...'
  btn.style.background = '#909399'
  try {
    var resp = await fetch('/api/images/generate?prompt=' + encodeURIComponent(prompt), {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
    })
    var data = await resp.json()
    if (data.code === 200 && data.data && data.data.svg) {
      var svg = data.data.svg
      if (svg.indexOf('viewBox') === -1) svg = svg.replace('<svg', '<svg viewBox="0 0 800 500"')
      svg = svg.replace('<svg', '<svg width="100%" style="max-width:100%;height:auto;display:block"')
      resultDiv.innerHTML = '<div style="text-align:center;padding:12px;background:#fafbfc;border-radius:6px;overflow:hidden;max-height:800px">' + svg + '</div>'
      resultDiv.style.display = 'block'
      btn.textContent = ''
      btn.style.background = '#67C23A'
    } else {
      btn.textContent = ''
      btn.style.background = '#F56C6C'
      resultDiv.style.display = 'block'
      resultDiv.innerHTML = '<div style="text-align:center;padding:20px;color:#F56C6C">' + (data.message || '失败') + '</div>'
    }
  } catch(e) {
    btn.textContent = ''
    btn.style.background = '#F56C6C'
  }
  btn.disabled = false
}
</script>

<style scoped>
.resources-layout {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}
.resources-main {
  flex: 1;
  min-width: 0;
}
.resources-pdf-sidebar {
  width: 300px;
  flex-shrink: 0;
  position: sticky;
  top: 20px;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
}
.pdf-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 8px;
  border-bottom: 1px solid #f0f0f0;
  transition: background .2s;
}
.pdf-item:hover {
  background: #f5f7fa;
}
.pdf-item.is-selected {
  background: #fef0f0;
}
.pdf-cover {
  width: 48px;
  height: 64px;
  flex-shrink: 0;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid #e4e7ed;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fafafa;
}
.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.pdf-icon {
  font-size: 24px;
}
.pdf-info {
  flex: 1;
  min-width: 0;
}
.pdf-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pdf-meta {
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 2px;
}
.pdf-actions {
  display: flex;
  gap: 4px;
  margin-top: 6px;
}
.pdf-actions .el-button {
  font-size: 12px;
  padding: 2px 8px;
  height: 26px;
}
</style>
