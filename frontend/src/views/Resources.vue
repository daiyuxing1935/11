<template>
  <div class="resources-page">
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
            <el-col :span="6" v-for="item in mod.items" :key="item.id">
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getResourceList, getResourceLearnMaterial } from '../api/resource'

const activeTab = ref('all')
const allResources = ref({ items: [] })
const filterCategory = ref('')
const dialogVisible = ref(false)
const dialogTitle = ref('')
const dialogContent = ref('')
const dialogLoading = ref(false)
const contentRef = ref(null)

const moduleList = [
  { key: '模块一：智能体基础通识', label: '模块一：智能体基础通识', icon: '🤖' },
  { key: '模块二：大模型与提示词工程', label: '模块二：大模型与提示词工程', icon: '🧠' },
  { key: '模块三：智能体四大核心能力模块', label: '模块三：智能体四大核心能力模块', icon: '⚙️' },
  { key: '模块四：开发框架与工程实践', label: '模块四：开发框架与工程实践', icon: '🔧' },
  { key: '模块五：多智能体系统', label: '模块五：多智能体系统', icon: '🤝' },
  { key: '模块六：评估、安全与前沿拓展', label: '模块六：评估、安全与前沿拓展', icon: '🛡️' }
]

const moduleGroups = computed(() => {
  return moduleList.map(m => ({ ...m, items: (allResources.value.items||[]).filter(i => i.category === m.key) })).filter(m => m.items.length > 0)
})

onMounted(() => { fetchAll() })
async function fetchAll() {
  try { allResources.value = await getResourceList({ page: 1, page_size: 100, category: filterCategory.value||undefined }) } catch(e) {}
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
            '<span style="font-size:18px">🖼️</span><span style="font-weight:600;color:#2c6fce;font-size:13px">配图</span>' +
            '<button class="gen-btn" data-pid="' + i + '" style="margin-left:auto;padding:5px 14px;background:#409EFF;color:#fff;border:none;border-radius:6px;font-size:12px;cursor:pointer">✨ 生成</button>' +
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
              '<span style="font-size:18px">🖼️</span><span style="font-weight:600;color:#2c6fce;font-size:13px">配图</span>' +
              '<button class="gen-btn" data-pid="' + j + '" style="margin-left:auto;padding:5px 14px;background:#409EFF;color:#fff;border:none;border-radius:6px;font-size:12px;cursor:pointer">✨ 生成</button>' +
            '</div>' +
            '<div style="padding:14px 18px">' +
              '<div class="img-result" data-pid="' + j + '" style="display:none;margin-bottom:12px;text-align:center"></div>' +
              '<p style="margin:0 0 10px;font-size:13px;color:#444;line-height:1.7">' + f2 + '</p>' +
            '</div></div>'
        }
        html += '<details style="margin-top:24px"><summary style="cursor:pointer;font-size:14px;color:#409EFF;font-weight:600">📋 更多配图 (+' + (counter - maxShow) + '条)</summary>' + hidden + '</details>'
      }
      dialogContent.value = html

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
              btn.textContent = '✅'
              btn.style.background = '#67C23A'
            }
          }
        }
      }
    }
  } catch(e) {}
}

async function genImage(btn, pid) {
  var prompt = window._prompts[pid]
  if (!prompt) return
  var card = btn.closest('.prompt-card')
  var resultDiv = card.querySelector('.img-result')
  btn.disabled = true
  btn.textContent = '⏳...'
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
      btn.textContent = '🔄'
      btn.style.background = '#67C23A'
    } else {
      btn.textContent = '❌'
      btn.style.background = '#F56C6C'
      resultDiv.style.display = 'block'
      resultDiv.innerHTML = '<div style="text-align:center;padding:20px;color:#F56C6C">' + (data.message || '失败') + '</div>'
    }
  } catch(e) {
    btn.textContent = '❌'
    btn.style.background = '#F56C6C'
  }
  btn.disabled = false
}
</script>
