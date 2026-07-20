/**
 * 共享的 markdown 渲染器 — 为代码块添加"复制"按钮
 * 用于 LearningPath.vue / Resources.vue 等不需要"运行"按钮的页面
 */
import { marked } from 'marked'
import { copyToClipboard } from '../utils/clipboard'
import { ElMessage } from 'element-plus'

function escapeHtml(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

const renderer = new marked.Renderer()

renderer.code = function (code, infostring) {
  const lang = infostring || 'plaintext'
  return `<div class="code-block-wrapper">
    <div class="code-toolbar">
      <span class="code-lang-tag">${lang}</span>
      <div class="code-toolbar-actions">
        <button class="code-toolbar-btn copy-btn" data-action="copy" title="复制代码">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          复制
        </button>
      </div>
    </div>
    <pre><code class="language-${lang}">${escapeHtml(code)}</code></pre>
  </div>`
}

/**
 * 渲染 Markdown 并绑定代码块复制事件
 * @param {string} text - Markdown 文本
 * @returns {string} HTML 字符串
 */
export function renderMarkdown(text) {
  if (!text) return ''
  return marked(text, { breaks: true, renderer })
}

/**
 * 为容器内的代码块工具栏按钮绑定事件（委托绑定）
 * 在 v-html 渲染后调用
 * @param {HTMLElement} container - 包含渲染后 HTML 的容器元素
 */
export function bindCodeBlockActions(container) {
  if (!container || container.dataset.codeCopyBound === 'true') return

  // Use event delegation because resource pagination replaces its rendered
  // HTML. A single listener keeps copy buttons on every new page working.
  container.dataset.codeCopyBound = 'true'
  container.addEventListener('click', async (event) => {
    const target = event.target
    if (!(target instanceof Element)) return
    const btn = target.closest('.code-block-wrapper .copy-btn')
    if (!btn || !container.contains(btn)) return

    const wrapper = btn.closest('.code-block-wrapper')
    const code = wrapper?.querySelector('code')?.textContent || ''
    const ok = await copyToClipboard(code)
    ElMessage[ok ? 'success' : 'warning'](
      ok ? '代码已复制到剪贴板' : '复制失败，请手动复制'
    )
  })
}

export default renderMarkdown
