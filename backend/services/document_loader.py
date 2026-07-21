"""文档加载器 — 支持 PDF/Markdown/JSON 多格式

数据源（按优先级）：
1. PDF 教材（pdf/）→ PyMuPDF 逐页提取
2. Markdown 学习材料（learning_materials/）→ 按 ## 标题分块
3. Q&A 题库（backend/data/dataset/）→ 每条一个块
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """文档分块"""
    text: str                          # 分块文本
    source_type: str                   # "pdf" | "markdown" | "qa_pair" | "resource"
    source_path: str                   # 源文件路径
    title: str = ""                    # 文档标题
    module: str = ""                   # 所属模块
    page: Optional[int] = None         # PDF 页码
    section: str = ""                  # 章节标题
    chunk_index: int = 0               # 块序号
    knowledge_point: str = ""          # 知识点
    difficulty: str = ""               # 难度
    metadata: dict = field(default_factory=dict)

    @property
    def doc_id(self) -> str:
        """唯一标识（用于去重）"""
        content = f"{self.source_path}:{self.page}:{self.chunk_index}:{self.section}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    @property
    def source_label(self) -> str:
        """人类可读的来源标签"""
        if self.source_type == "pdf":
            page_info = f"（第{self.page}页）" if self.page else ""
            return f"📖 {self.title}{page_info}"
        elif self.source_type == "markdown":
            return f"📝 {self.title} — {self.section}"
        elif self.source_type == "qa_pair":
            return f"📋 {self.module} — {self.knowledge_point}"
        return self.source_path


# ============================================================
# PDF 加载器
# ============================================================

def load_pdf_documents(pdf_dir: str) -> List[DocumentChunk]:
    """加载 PDF 教材并分块

    分块策略:
    - 逐页提取文本
    - 单页 > 800 字符 → 按段落二次分割（500-800 字符/块）
    - 保留页号用于来源标注
    """
    import fitz  # PyMuPDF

    chunks = []
    pdf_path = Path(pdf_dir)

    if not pdf_path.exists():
        logger.warning(f"PDF 目录不存在: {pdf_dir}")
        return chunks

    pdf_files = sorted(pdf_path.glob("*.pdf"))
    logger.info(f"发现 {len(pdf_files)} 个 PDF 文件")

    for pdf_file in pdf_files:
        try:
            doc = fitz.open(str(pdf_file))
            title = pdf_file.stem  # 文件名作为标题

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text().strip()
                if not text or len(text) < 20:  # 跳过空页或极短页
                    continue

                # 按段落分块（放宽到 1200 字符，RTX 5060 显存充裕）
                paragraphs = _split_paragraphs(text, max_chars=1200, min_chars=200)
                for ci, para_text in enumerate(paragraphs):
                    # 尝试提取第一个标题作为 section
                    section = _extract_first_heading(para_text) or f"第{page_num+1}页"

                    chunks.append(DocumentChunk(
                        text=para_text,
                        source_type="pdf",
                        source_path=str(pdf_file),
                        title=title,
                        module=_infer_module_from_title(title),
                        page=page_num + 1,
                        section=section,
                        chunk_index=ci,
                    ))

            doc.close()
            logger.info(f"  [{len(chunks)} chunks] {title}")

        except Exception as e:
            logger.error(f"PDF 解析失败: {pdf_file} — {e}")

    return chunks


# ============================================================
# Markdown 加载器
# ============================================================

def load_markdown_documents(
    materials_dir: str,
    index_path: Optional[str] = None
) -> List[DocumentChunk]:
    """加载 Markdown 学习材料

    分块策略:
    - 按 ## 标题作为自然语义边界分块
    - 单个 section > 1000 字符 → 按段落二次分割
    - 通过 index.json 获取模块→主题映射
    """
    chunks = []
    base = Path(materials_dir)

    if not base.exists():
        logger.warning(f"学习材料目录不存在: {materials_dir}")
        return chunks

    # 加载索引
    index = {}
    if index_path and Path(index_path).exists():
        with open(index_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
            for module_name, topics in index_data.get("modules", {}).items():
                for topic_name, rel_path in topics.items():
                    index[rel_path] = {"module": module_name, "topic": topic_name}

    md_files = sorted(base.rglob("*.md"))
    logger.info(f"发现 {len(md_files)} 个 Markdown 文件")

    for md_file in md_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            rel_path = str(md_file.relative_to(base))
            idx_entry = index.get(rel_path, {})
            module = idx_entry.get("module", "")
            topic = idx_entry.get("topic", md_file.stem)

            if not content.strip():
                continue

            # 按 ## 标题分块
            sections = _split_by_headings(content, level=2)
            ci = 0
            for section_title, section_text in sections:
                if not section_text.strip() or len(section_text.strip()) < 30:
                    continue

                # 过长的 section 按段落二次分割（放宽到 1200 字符）
                sub_chunks = _split_paragraphs(section_text, max_chars=1200, min_chars=200)
                for sub_text in sub_chunks:
                    chunks.append(DocumentChunk(
                        text=sub_text,
                        source_type="markdown",
                        source_path=rel_path,
                        title=topic,
                        module=module,
                        section=section_title or topic,
                        chunk_index=ci,
                    ))
                    ci += 1

            if ci > 0:
                logger.debug(f"  [{ci} chunks] {rel_path}")

        except Exception as e:
            logger.error(f"Markdown 解析失败: {md_file} — {e}")

    return chunks


# ============================================================
# Q&A 题库加载器
# ============================================================

def load_qa_documents(dataset_dir: str) -> List[DocumentChunk]:
    """加载 Q&A 题库

    每条题目的 question + answer + analysis 作为一个块
    """
    chunks = []
    dataset_path = Path(dataset_dir)

    if not dataset_path.exists():
        logger.warning(f"题库目录不存在: {dataset_dir}")
        return chunks

    json_files = sorted(dataset_path.glob("*.json"))
    logger.info(f"发现 {len(json_files)} 个题库文件")

    for jf in json_files:
        try:
            with open(jf, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 支持多种格式：直接数组 / {"qa_pairs": [...]} / {"questions": [...]}
            if isinstance(data, list):
                questions = data
            elif isinstance(data, dict):
                questions = data.get("qa_pairs", data.get("questions", []))
            else:
                continue

            for qi, q in enumerate(questions):
                question = q.get("question", "")
                answer = q.get("answer", "")
                analysis = q.get("analysis", "")
                knowledge_point = q.get("knowledge_point", "")

                text_parts = []
                if question:
                    text_parts.append(f"问题: {question}")
                if answer:
                    text_parts.append(f"答案: {answer}")
                if analysis:
                    text_parts.append(f"解析: {analysis}")

                text = "\n".join(text_parts)
                if len(text) < 20:
                    continue

                chunks.append(DocumentChunk(
                    text=text,
                    source_type="qa_pair",
                    source_path=jf.name,
                    title=q.get("knowledge_point", q.get("section", "")),
                    module=q.get("module", ""),
                    section=q.get("section", ""),
                    knowledge_point=knowledge_point,
                    difficulty=q.get("difficulty", ""),
                    chunk_index=qi,
                ))

            logger.info(f"  [{len(questions)} QAs] {jf.name}")

        except Exception as e:
            logger.error(f"题库解析失败: {jf} — {e}")

    return chunks


# ============================================================
# 统一入口
# ============================================================

def load_all_documents(
    pdf_dir: str = "pdf",
    materials_dir: str = "learning_materials",
    dataset_dir: str = "backend/data/dataset",
    index_path: str = "learning_materials/index.json",
) -> List[DocumentChunk]:
    """加载所有数据源的文档块"""
    all_chunks = []

    # PDF 教材
    pdf_chunks = load_pdf_documents(pdf_dir)
    logger.info(f"PDF: {len(pdf_chunks)} chunks")
    all_chunks.extend(pdf_chunks)

    # Markdown 学习材料
    md_chunks = load_markdown_documents(materials_dir, index_path)
    logger.info(f"Markdown: {len(md_chunks)} chunks")
    all_chunks.extend(md_chunks)

    # Q&A 题库
    qa_chunks = load_qa_documents(dataset_dir)
    logger.info(f"QA: {len(qa_chunks)} chunks")
    all_chunks.extend(qa_chunks)

    logger.info(f"总计: {len(all_chunks)} 个文档块")
    return all_chunks


# ============================================================
# 内部分块工具
# ============================================================

def _split_paragraphs(text: str, max_chars: int = 800, min_chars: int = 200) -> List[str]:
    """按段落拆分文本，保持每块在合理大小范围内"""
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    if not paragraphs:
        return [text] if text.strip() else []

    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) > max_chars and len(current) >= min_chars:
            chunks.append(current.strip())
            current = para
        else:
            if current:
                current += "\n" + para
            else:
                current = para

    if current.strip():
        # 最后一块：如果太短就合并到前一块
        if chunks and len(current.strip()) < min_chars:
            chunks[-1] = chunks[-1] + "\n" + current.strip()
        else:
            chunks.append(current.strip())

    return chunks


def _split_by_headings(text: str, level: int = 2) -> List[tuple]:
    """按指定级别的标题拆分文本，返回 [(section_title, section_text), ...]"""
    import re

    prefix = "#" * level
    pattern = rf'^{prefix}\s+(.+)$'

    lines = text.split('\n')
    sections = []
    current_title = ""
    current_text = []

    for line in lines:
        m = re.match(pattern, line.strip())
        if m:
            # 保存上一个 section
            if current_text:
                sections.append((current_title, '\n'.join(current_text)))
            current_title = m.group(1).strip()
            current_text = []
        else:
            if current_text or line.strip():  # 跳过开头空白行
                current_text.append(line)

    # 最后一个 section
    if current_title or any(l.strip() for l in current_text):
        sections.append((current_title, '\n'.join(current_text)))

    return sections if sections else [("", text)]


def _extract_first_heading(text: str, level: int = 2) -> Optional[str]:
    """提取文本中的第一个标题"""
    import re
    prefix = "#" * level
    m = re.search(rf'^{prefix}\s+(.+)$', text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _infer_module_from_title(title: str) -> str:
    """从 PDF 书名推断所属模块"""
    module_keywords = {
        "基础": "模块一：智能体基础通识",
        "原理": "模块一：智能体基础通识",
        "概念": "模块一：智能体基础通识",
        "开发": "模块三：智能体四大核心能力模块",
        "框架": "模块四：开发框架与工程实践",
        "实战": "模块四：开发框架与工程实践",
        "企业": "模块四：开发框架与工程实践",
        "零基础": "模块一：智能体基础通识",
        "扣子": "模块四：开发框架与工程实践",
        "设计模式": "模块四：开发框架与工程实践",
        "全书": "模块一：智能体基础通识",
        "应用": "模块三：智能体四大核心能力模块",
        "多智能体": "模块五：多智能体系统",
        "系统构建": "模块五：多智能体系统",
        "数据挖掘": "数据分析与挖掘",
        "数据分析": "数据分析与挖掘",
        "数据仓库": "数据分析与挖掘",
    }
    for kw, mod in module_keywords.items():
        if kw in title:
            return mod
    return "模块一：智能体基础通识"  # 默认
