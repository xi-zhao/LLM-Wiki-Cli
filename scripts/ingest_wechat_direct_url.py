#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

APP_ROOT = Path(__file__).resolve().parent.parent
BASE = Path(os.environ.get('FOKB_BASE', str(APP_ROOT))).expanduser().resolve()
SCRIPTS_DIR = APP_ROOT / 'scripts'
FETCH_SCRIPT = SCRIPTS_DIR / 'fetch_wechat_article.py'
NORMALIZE_SCRIPT = SCRIPTS_DIR / 'normalize_wechat_materials.py'
SUMMARY_SCRIPT = SCRIPTS_DIR / 'build_wechat_assets_summary.py'
RAW_DIR = BASE / 'articles' / 'raw'
PARSED_DIR = BASE / 'articles' / 'parsed'
BRIEF_DIR = BASE / 'articles' / 'briefs'
SOURCES_DIR = BASE / 'sources'
SOURCES_INDEX = SOURCES_DIR / 'index.md'
OBSIDIAN_SOURCES_INDEX = SOURCES_DIR / 'sources-index.md'
DEFAULT_MATERIALS_DIR = BASE / 'materials' / 'wechat'
BACKUP_ROOT = BASE / 'archive' / 'ingest-backups'

ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')
WHITESPACE_RE = re.compile(r'\s+')
ARTICLE_ID_RE = re.compile(r'/s/([^/?#]+)')
HEADING_NUMBER_RE = re.compile(r'^\d+(?:\.\d+)*$')
ASSET_LINE_RE = re.compile(r'-\s+([0-9]{3}\.[A-Za-z0-9]+)\b')
DATE_LINE_RE = re.compile(
    r'^\d{4}年\d{1,2}月\d{1,2}日(?: \d{1,2}:\d{2})?(?: [A-Za-z\u4e00-\u9fff·]{1,12})?$'
)
TABLEISH_LINE_RE = re.compile(r'^(?:第 ?[1234567890]+ 层|加载时机|内容|Token 消耗示例|层级|场景复杂度|典型结构|示例|维度|核心定位|解决问题|载体形态|状态管理|适用场景)$')
ENUM_ITEM_RE = re.compile(r'^\d+[、.]\s*')


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or 'unknown failure'
        raise RuntimeError(detail)
    return proc.stdout


def detect_folder(stdout: str) -> Path:
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        candidate = Path(line).expanduser()
        if candidate.is_dir():
            return candidate.resolve()
    raise RuntimeError('fetch script did not report a material folder')


def load_json(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def read_text(path: Path) -> str:
    if not path.exists():
        return ''
    return path.read_text(encoding='utf-8')


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip()
    return f'{parsed.scheme}://{parsed.netloc}{parsed.path}'


def article_id_from_url(url: str) -> str:
    match = ARTICLE_ID_RE.search(url)
    if match:
        return match.group(1)
    path = urlparse(url).path.rstrip('/').split('/')
    if path and path[-1]:
        return path[-1]
    return 'unknown'


def collapse(text: str) -> str:
    return WHITESPACE_RE.sub(' ', text).strip()


def short(text: str, limit: int = 120) -> str:
    compact = collapse(text)
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + '…'


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def simplify_line(text: str) -> str:
    return collapse(text).strip(' -:：;；')


def normalize_date_text(text: str) -> str:
    text = collapse(text)
    text = text.replace('-', '年', 1).replace('-', '月', 1)
    if '年' in text and '月' in text and '日' not in text:
        parts = text.split()
        date_part = parts[0]
        if '年' in date_part and '月' in date_part:
            text = f'{date_part}日' + (f' {parts[1]}' if len(parts) > 1 else '')
    return text


def looks_like_publish_line(line: str, publish_time: str) -> bool:
    if DATE_LINE_RE.match(line):
        return True
    if not publish_time:
        return False
    publish_norm = normalize_date_text(publish_time)
    return line == publish_norm


def is_noise_line(line: str, source_account: str, publish_time: str) -> bool:
    if not line:
        return True
    if '微信公众平台' in line and len(line) <= 12:
        return True
    if line.startswith('https://mp.weixin.qq.com/'):
        return True
    if HEADING_NUMBER_RE.match(line):
        return True
    if looks_like_publish_line(line, publish_time):
        return True
    if TABLEISH_LINE_RE.match(line):
        return True
    if line in {'---', '```', '以下，enjoy:'}:
        return True
    if source_account and line.startswith('原创 ') and source_account in line:
        return True
    return False


def parse_body_lines(raw_text: str, title: str, source_account: str, publish_time: str) -> list[str]:
    cleaned = ANSI_RE.sub('', raw_text).replace('\r', '\n')
    lines = [collapse(line) for line in cleaned.splitlines()]
    kept = []
    skipped_title = False
    for line in lines:
        if is_noise_line(line, source_account, publish_time):
            continue
        if title and line == title and not skipped_title:
            skipped_title = True
            continue
        kept.append(line)
    return kept


def compress_clausey_line(text: str, limit: int = 120) -> str:
    compact = simplify_line(text)
    if len(compact) <= limit:
        return compact
    if re.search(r'[A-Za-z]', compact) and not re.search(r'[\u4e00-\u9fff]', compact):
        return short(compact, limit)
    major_parts = [part.strip() for part in re.split(r'[。！？；;]', compact) if part.strip()]
    if not major_parts:
        return short(compact, limit)
    chosen = []
    for part in major_parts:
        if len(collapse('。'.join(chosen + [part]))) > limit:
            break
        chosen.append(part)
    if chosen:
        merged = '。'.join(chosen)
        if len(merged) <= limit:
            return merged
    minor_parts = [part.strip() for part in re.split(r'[、，,]', compact) if part.strip()]
    chosen = []
    for part in minor_parts:
        candidate = '，'.join(chosen + [part])
        if len(candidate) > limit - 4:
            break
        chosen.append(part)
    if chosen:
        merged = '，'.join(chosen)
        return merged + ('等问题。' if not merged.endswith(('。', '！', '？')) else '')
    return short(compact, limit)


def find_anchor_content(lines: list[str], anchor: str) -> str:
    for idx, line in enumerate(lines):
        if anchor not in line:
            continue
        before, _, after = line.partition(anchor)
        del before
        after = after.lstrip('：: ')
        if after:
            return after
        for nxt in lines[idx + 1: idx + 4]:
            if not is_noise_line(nxt, '', '') and not nxt.startswith('项目地址：'):
                return nxt
    return ''


def find_matching_line(lines: list[str], markers: tuple[str, ...]) -> str:
    for line in lines:
        if any(marker in line for marker in markers):
            return line
    return ''


def pick_summary(lines: list[str]) -> str:
    candidate = find_anchor_content(lines, '这篇试图说清楚')
    if candidate:
        return compress_clausey_line(candidate, 110)
    candidate = find_anchor_content(lines, '一句话定义')
    if candidate:
        return compress_clausey_line(candidate, 110)
    for line in lines:
        compact = collapse(line)
        if any(marker in compact for marker in ('综合对比如下', '配置维度初步推荐', '从大模型配置、向量数据库选择、Embedder首选项、分块策略等四方面')):
            return compress_clausey_line(compact, 110)
    for line in lines:
        if '一句话讲清楚' in line:
            line = re.sub(r'^.*一句话讲清楚[^：:]*[：:👉🏻 ]*', '', line).strip(' -')
            if len(line) >= 16:
                return compress_clausey_line(line, 110)
    for line in lines:
        if len(line) >= 24 and 'http' not in line and not HEADING_NUMBER_RE.match(line):
            return compress_clausey_line(line, 110)
    return '待补摘要'


def pick_enumerated_points(lines: list[str], anchor: str) -> list[str]:
    for idx, line in enumerate(lines):
        if anchor not in line:
            continue
        points = []
        for nxt in lines[idx + 1: idx + 6]:
            if ENUM_ITEM_RE.match(nxt):
                points.append(ENUM_ITEM_RE.sub('', nxt).strip())
            elif points:
                break
        if points:
            return points[:3]
    return []


def normalize_point(line: str) -> str:
    line = simplify_line(line)
    line = re.sub(r'^(?:一句话定义|说人话就是|核心观点|总结下来|关键点|为什么重要|核心优势|适用场景|主要结论)[:：]\s*', '', line)
    line = line.split('核心我总结下来就三件事', 1)[0].rstrip('，:： ')
    return compress_clausey_line(line, 110)


def pick_core_points(lines: list[str], summary: str) -> list[str]:
    preferred = []
    summary_norm = collapse(summary)
    definition = find_anchor_content(lines, '一句话定义')
    if definition:
        preferred.append(normalize_point(definition))
    loading = find_matching_line(lines, ('解决方案是三层按需加载', '三层按需加载'))
    if loading:
        preferred.append(normalize_point(loading))
    value = find_matching_line(lines, ('真正价值在于', '给 Agent 写的操作手册', '可以组合使用'))
    if value:
        preferred.append(normalize_point(value))

    enumerated = pick_enumerated_points(lines, '核心我总结下来就三件事')
    preferred.extend(normalize_point(item) for item in enumerated[:3])

    for line in lines:
        compact = collapse(line)
        if compact.startswith('核心优势：') or compact.startswith('自主开发的明显优势是') or compact.startswith('但问题也很明显'):
            preferred.append(normalize_point(compact))

    fallback = []
    keywords = (
        '真正价值在于', '解决方案是', '本质上就是', '区别于', '核心理念',
        '关键点', '脚本代码不进入上下文', 'description 的质量直接决定',
        'Skill vs MCP', '说人话就是', '产品化潜力'
    )
    for line in lines:
        compact = collapse(line)
        if len(compact) < 18 or compact == summary_norm:
            continue
        if compact.startswith('项目地址') or compact.startswith('使用场景') or looks_like_publish_line(compact, ''):
            continue
        if HEADING_NUMBER_RE.match(compact) or compact in {'什么是 Agent Skills？', 'Skill vs MCP vs 多 Agent'}:
            continue
        if any(keyword in compact for keyword in keywords):
            preferred.append(normalize_point(compact))
        else:
            fallback.append(normalize_point(compact))
    choices = dedupe_keep_order(preferred + fallback)
    return choices[:3]


def pick_facts(lines: list[str], meta: dict, image_count: int) -> list[str]:
    facts = []
    source_account = meta.get('source_account') or '待补'
    publish_time = meta.get('create_time') or '待补'
    if source_account:
        facts.append(f'来源账号：{source_account}')
    if publish_time:
        facts.append(f'发布时间：{publish_time}')
    facts.append(f'素材包图片数量：{image_count}')

    keywords = ('项目地址', '安装', '命令', '模板', 'Skill', 'skill', 'Prompt', 'prompt', 'Agent', 'agent', 'RAG', 'GitHub', '参考实现', 'Python 脚本')
    for line in lines:
        compact = collapse(line)
        if len(compact) < 10:
            continue
        if looks_like_publish_line(compact, ''):
            continue
        if compact.endswith('？') or compact.endswith('?'):
            continue
        if compact.endswith('使用效果'):
            continue
        if len(compact) > 100 and not compact.startswith('项目地址：'):
            continue
        if any(keyword in compact for keyword in keywords) or (re.search(r'\d', compact) and len(compact) <= 80):
            facts.append(compress_clausey_line(compact, 100))
        if len(dedupe_keep_order(facts)) >= 5:
            break
    return dedupe_keep_order(facts)[:5]


def is_heading_text(line: str) -> bool:
    if not line or len(line) > 30:
        return False
    if re.search(r'[#`%]|https?://|→|<-|->', line):
        return False
    if line.endswith('？'):
        return True
    keywords = ('什么', '为什么', '如何', '机制', '价值', '实现', '原理', '总结', '场景', '介绍', '方式', '加载', '案例', 'MCP', 'Agent')
    return any(keyword in line for keyword in keywords)


def pick_structure(lines: list[str]) -> list[str]:
    headings = []
    for idx, line in enumerate(lines):
        if HEADING_NUMBER_RE.match(line) and idx + 1 < len(lines):
            nxt = lines[idx + 1]
            if is_heading_text(nxt) and not ENUM_ITEM_RE.match(nxt):
                headings.append(nxt)
    headings = dedupe_keep_order(headings)
    if headings:
        return headings[:3]
    for line in lines:
        if ENUM_ITEM_RE.match(line):
            continue
        if is_heading_text(line):
            headings.append(line)
    headings = dedupe_keep_order(headings)
    if headings:
        return headings[:3]
    return ['开场与背景', '核心机制', '落地价值']


def detect_type(title: str, body: str) -> str:
    haystack = f'{title}\n{body}'.lower()
    if any(keyword in haystack for keyword in ('教程', '步骤', '安装', '使用', 'how to', '实战')):
        return '教程'
    if any(keyword in haystack for keyword in ('融资', '发布', '宣布', '获', 'q1')):
        return '新闻'
    if any(keyword in haystack for keyword in ('案例', '拆解')):
        return '案例'
    if any(keyword in haystack for keyword in ('研究', '论文', '科研')):
        return '研究'
    return '观点'


def detect_tags(title: str, body: str) -> list[str]:
    haystack = f'{title}\n{body}'
    lower = haystack.lower()
    tags = ['微信公众号']
    rules = [
        ('AI Agent', ('agent',)),
        ('Skills', ('skill', 'skills')),
        ('Prompt', ('prompt',)),
        ('RAG', ('rag', '入库')),
        ('知识库', ('知识库',)),
        ('数据治理', ('数据治理',)),
        ('OpenClaw', ('openclaw',)),
        ('科研写作', ('科研写作', '论文写作', '投稿', '顶会', 'latex', '文献综述', '期刊')),
        ('ToB AI', ('tob', '2b', '企业', '产品化')),
        ('AI 编程', ('cursor', 'opencode', 'claude code', '编程')),
        ('微信', ('微信',)),
    ]
    for tag, needles in rules:
        if any((needle in lower) if needle.isascii() else (needle in haystack) for needle in needles):
            tags.append(tag)
    return dedupe_keep_order(tags)[:6]


def detect_topics(title: str, body: str) -> list[str]:
    haystack = f'{title}\n{body}'
    lower = haystack.lower()
    topics = []

    if any(keyword in lower for keyword in ('科研写作', '论文写作', '投稿', '顶会', 'latex', '文献综述', '期刊', '研究工作流', '知识库')):
        topics.append('ai-research-writing.md')

    if (
        any(keyword in haystack for keyword in ('产品化', '企业级', '投标书', '客户', '交付', '报价 AI', '数据治理'))
        or 'tob' in lower
        or '2b' in lower
    ):
        topics.append('tob-ai-productization.md')

    if any(keyword in lower for keyword in ('cursor', 'opencode', 'claude code', 'skill', 'skills', 'agent', 'prompt', 'mcp', 'coding', 'codex', 'autoresearch', 'harness')) or any(keyword in haystack for keyword in ('知识管理员', '代码生成器')):
        topics.append('ai-coding-and-autoresearch.md')

    if any(keyword in lower for keyword in ('bindings', 'accountid', 'clawbot', 'openclaw-weixin', 'openclaw channels login')) or any(keyword in haystack for keyword in ('微信 Clawbot', '多用户', '路由', '路由隔离', '专属的智能体和工作区')):
        topics.append('wechat-agent-routing.md')

    if any(keyword in haystack for keyword in ('量子计算', '量子科技', '超导量子', '量子计算机', '量子通信', 'QKD', 'RSA-2048')) or 'quantum' in lower:
        topics.append('quantum-computing-industry.md')

    if any(keyword in haystack for keyword in ('语音模型', '音色克隆', '方言', '多语种', 'VoxCPM', '端侧 AI', '小模型', 'TTS')):
        topics.append('ai-voice-and-edge-models.md')

    return dedupe_keep_order(topics)[:3]


def completeness_for(folder: Path, body: str, broken_assets: int) -> str:
    required = ['meta.json', 'page.html', 'content.html', 'text.txt', 'images.json', 'assets.md']
    if all((folder / name).exists() for name in required) and len(body) >= 2000 and broken_assets == 0:
        return 'complete'
    return 'partial'


def confidence_for(completeness: str) -> str:
    return 'high' if completeness == 'complete' else 'medium'


def reuse_level_for(tags: list[str]) -> str:
    if any(tag in tags for tag in ('Skills', 'Prompt', 'RAG', 'OpenClaw', 'AI Agent')):
        return 'high'
    return 'medium'


def parse_assets(folder: Path) -> list[str]:
    assets = []
    for line in read_text(folder / 'assets.md').splitlines():
        match = ASSET_LINE_RE.search(line)
        if match:
            assets.append(match.group(1))
    return dedupe_keep_order(assets)[:5]


def find_existing_material_folder(normalized_url: str) -> Path | None:
    if not DEFAULT_MATERIALS_DIR.exists():
        return None
    for folder in sorted(DEFAULT_MATERIALS_DIR.iterdir()):
        if not folder.is_dir():
            continue
        meta = load_json(folder / 'meta.json')
        for key in ('url', 'link'):
            value = str(meta.get(key, '')).strip()
            if value and normalize_url(value) == normalized_url:
                return folder.resolve()
    return None


def find_existing_by_url(directory: Path, normalized_url: str) -> Path | None:
    if not directory.exists():
        return None
    for path in sorted(directory.glob('*.md')):
        if path.name.startswith('_'):
            continue
        if normalized_url and normalized_url in read_text(path):
            return path
    return None


def choose_target(existing: Path | None, canonical: Path, article_id: str) -> tuple[Path, bool]:
    if existing is None:
        return canonical, False
    if existing == canonical:
        return canonical, False
    if canonical.exists():
        return existing, False
    stem = existing.stem
    if article_id in stem or 'wechat_article' in stem:
        existing.rename(canonical)
        return canonical, True
    return existing, False


def backup_existing(path: Path, stamp: str) -> str | None:
    if not path.exists():
        return None
    relative_parent = path.parent.relative_to(BASE)
    target_dir = BACKUP_ROOT / stamp / relative_parent
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / path.name
    shutil.copy2(path, target)
    return str(target)


def ensure_dirs():
    for directory in (RAW_DIR, PARSED_DIR, BRIEF_DIR, SOURCES_DIR, BACKUP_ROOT):
        directory.mkdir(parents=True, exist_ok=True)


def write_note(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + '\n', encoding='utf-8')


def write_raw(path: Path, title: str, source_account: str, url: str, publish_time: str, capture_date: str, completeness: str, body_lines: list[str]):
    lines = [
        f'# {title}',
        '',
        '## 元信息',
        '- 来源平台：微信公众号',
        f'- 来源账号：{source_account or "待补"}',
        f'- 原文链接：{url}',
        f'- 发布时间：{publish_time or "待补"}',
        f'- 采集时间：{capture_date}',
        f'- 完整度：{completeness}',
        '',
        '## 正文摘录（自动抓取）',
        *body_lines,
        '',
        '## 备注',
        '- 原文已通过本地直链抓取工具完成归档。',
        '- 如需进一步沉淀主题卡或时间线，可在此基础上继续整理。',
    ]
    write_note(path, '\n'.join(lines))


def write_parsed(
    path: Path,
    title: str,
    source_account: str,
    url: str,
    publish_time: str,
    capture_date: str,
    tags: list[str],
    article_type: str,
    completeness: str,
    summary: str,
    core_points: list[str],
    facts: list[str],
    structure: list[str],
    folder: Path,
    assets: list[str],
    topics: list[str],
    quotes: list[str],
):
    material_root = f'file-organizer/materials/wechat/{folder.name}'
    recommendation_lines = assets or ['待补素材推荐']
    topic_wikilinks = [f'[[{Path(topic).stem}]]' for topic in topics] if topics else ['[[topics-moc]]']
    note_lines = [
        '---',
        'type: article',
        'source_type: wechat',
        f'title: "{title}"',
        f'file_name: "{path.name}"',
        'tags:',
        '  - article',
        '  - obsidian',
        '  - source/wechat',
        *[f'  - topic/{Path(topic).stem}' for topic in topics],
        '---',
        '',
        f'# 标题：{title}',
        '',
        '## 笔记关系',
        '- Source Index: [[sources-index]]',
        '- Topics MOC: [[topics-moc]]',
        *[f'- Topic Note: {link}' for link in topic_wikilinks],
        '',
        '## 元信息',
        '- 来源平台：微信公众号',
        f'- 来源账号：{source_account or "待补"}',
        '- 作者：待补',
        f'- 原文链接：{url}',
        f'- 发布时间：{publish_time or "待补"}',
        f'- 采集时间：{capture_date}',
        f'- 文件名：{path.name}',
        f'- 标签：{", ".join(tags)}',
        f'- 类型：{article_type}',
        f'- 完整度：{completeness}',
        '',
        '## 一句话摘要',
        f'- {summary}',
        '',
        '## 核心结论',
        *[f'{idx}. {point}' for idx, point in enumerate(core_points, start=1)],
        '',
        '## 关键事实 / 证据',
        *[f'- {fact}' for fact in facts],
        '',
        '## 原文结构',
        *[f'### {idx}. {heading}' for idx, heading in enumerate(structure, start=1)],
        '',
        '## 可复用素材',
        '### 可写文章的观点',
        *[f'- {point}' for point in core_points[:2]],
        '- 这篇文章适合被改写成“方法论 + 落地案例”型内容。',
        '',
        '### 可做 PPT 的标题 / 金句',
        f'- {title}',
        '- 把高频工作流沉淀成可复用能力',
        '- 从单次提示词到长期可维护的执行规范',
        '',
        '### 可引用案例 / 数据',
        *[f'- {fact}' for fact in facts[:3]],
        '',
        '## 本地素材',
        f'- 素材目录：`{material_root}/`',
        f'- 页面HTML：`{material_root}/page.html`',
        f'- 正文HTML：`{material_root}/content.html`',
        f'- 纯文本：`{material_root}/text.txt`',
        f'- 图片清单：`{material_root}/images.json`',
        f'- 素材摘要：`{material_root}/assets.md`',
        '',
        '## 推荐引用素材',
        *[f'- `{asset}`' for asset in recommendation_lines],
        '',
        '## 风险 / 不确定性 / 待验证',
        '- 当前文章卡基于本地抓取结果与规则抽取生成，重要细节建议回看原文核对。',
        '- 当前自动归档只完成到 brief 和 source index；topic/timeline 仍需后续维护。',
        '',
        '## 原文摘录',
        *[f'> {quote}' for quote in quotes],
        '',
        '## 关联主题',
        *([f'- {topic}' for topic in topics] if topics else ['- 待补主题']),
        '',
        '## 关联笔记（Obsidian）',
        *([f'- [[{Path(topic).stem}]]' for topic in topics] if topics else ['- [[topics-moc]]']),
        '',
        '## 我的备注',
        '- 这份文章卡由直链归档管道自动生成，适合作为后续人工精修的起点。',
        '- CLI 的结构化结果给 agent 消费，这份 Markdown 文章卡主要给 Obsidian 查看与组织。',
    ]
    write_note(path, '\n'.join(note_lines))


def write_brief(path: Path, title: str, summary: str, core_points: list[str], tags: list[str], topics: list[str]):
    importance = next((point for point in core_points if point != summary), core_points[0] if core_points else '这篇内容值得后续继续跟进。')
    topic_wikilinks = [f'[[{Path(topic).stem}]]' for topic in topics] if topics else ['[[topics-moc]]']
    lines = [
        '---',
        'type: brief',
        'source_type: wechat',
        f'title: "{title}"',
        f'file_name: "{path.name}"',
        'tags:',
        '  - brief',
        '  - obsidian',
        '  - source/wechat',
        *[f'  - topic/{Path(topic).stem}' for topic in topics],
        '---',
        '',
        f'# Brief｜{title}',
        '',
        '## 笔记关系',
        f'- Article Note: [[{path.stem}]]',
        '- Source Index: [[sources-index]]',
        '- Topics MOC: [[topics-moc]]',
        *[f'- Topic Note: {link}' for link in topic_wikilinks],
        '',
        '## 这篇讲了什么',
        summary,
        '',
        '## 为什么重要',
        importance,
        '',
        '## 可复用点',
        *[f'- {point}' for point in core_points[:3]],
        '',
        '## 关联笔记（Obsidian）',
        *([f'- [[{Path(topic).stem}]]' for topic in topics] if topics else ['- [[topics-moc]]']),
        '',
        '## 应持续跟踪',
        f'- 与 {", ".join(tags[:3])} 相关的后续案例或标准演进',
        '- 这套方法在更多真实项目里的复用效果',
        '',
        '## 我的备注',
        '- 这份 brief 由归档流程自动生成，主要给 Obsidian 快速浏览。',
    ]
    write_note(path, '\n'.join(lines))


def parse_source_rows(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        if not line.startswith('|'):
            continue
        if line.startswith('| 标题 ') or line.startswith('|------'):
            continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) != 12:
            continue
        rows.append({
            'title': cells[0],
            'source_account': cells[1],
            'date': cells[2],
            'url': cells[3],
            'tags': cells[4],
            'topics': cells[5],
            'type': cells[6],
            'completeness': cells[7],
            'confidence': cells[8],
            'reuse_level': cells[9],
            'followup_needed': cells[10],
            'status': cells[11],
        })
    return rows


def infer_note_title(path: Path) -> str:
    text = read_text(path)
    for line in text.splitlines():
        if line.startswith('# 标题：'):
            return line.replace('# 标题：', '', 1).strip()
    return path.stem


def build_obsidian_sources_index(rows: list[dict]) -> str:
    lines = [
        '---',
        'type: source-index',
        'scope: sources',
        'tags:',
        '  - sources',
        '  - obsidian',
        '  - moc',
        '---',
        '',
        '# Sources Index',
        '',
        '## 用途',
        '- 这是 article/source notes 的导航页。',
        '- CLI 的结构化结果给 agent，本页主要给 Obsidian 查看与组织。',
        '',
        '## 最新来源',
    ]
    parsed_notes = sorted([p for p in PARSED_DIR.glob('*.md') if p.is_file() and not p.name.startswith('_')], key=lambda p: p.name, reverse=True)
    if parsed_notes:
        for path in parsed_notes[:20]:
            lines.append(f'- [[{path.stem}|{infer_note_title(path)}]]')
    else:
        lines.append('- 待补 source note')
    lines.extend(['', '## 相关主题'])
    topic_refs = []
    for row in rows:
        topics = [item.strip() for item in row.get('topics', '').split(',') if item.strip() and item.strip() != '-']
        for topic in topics:
            stem = Path(topic).stem
            if stem not in topic_refs:
                topic_refs.append(stem)
    if topic_refs:
        for stem in sorted(topic_refs):
            lines.append(f'- [[{stem}]]')
    else:
        lines.append('- [[topics-moc]]')
    return '\n'.join(lines) + '\n'


def update_source_index(entry: dict):
    existing_text = read_text(SOURCES_INDEX)
    rows = parse_source_rows(existing_text)
    normalized_url = normalize_url(entry['url'])
    replaced = False
    for idx, row in enumerate(rows):
        if normalize_url(row['url']) == normalized_url:
            rows[idx] = entry
            replaced = True
            break
    if not replaced:
        rows.append(entry)

    rows.sort(key=lambda row: (row['date'], row['title']), reverse=True)
    stats = {'raw': 0, 'parsed': 0, 'briefed': 0, 'integrated': 0}
    for row in rows:
        status = row['status']
        if status in stats:
            stats[status] += 1

    lines = [
        '# 文章来源索引',
        '',
        '| 标题 | 来源账号 | 日期 | URL | 标签 | 相关主题 | 类型 | 完整性 | 置信度 | 复用级别 | 跟进需求 | 状态 |',
        '|------|----------|------|-----|------|----------|------|--------|--------|----------|----------|------|',
    ]
    for row in rows:
        lines.append(
            f"| {row['title']} | {row['source_account']} | {row['date']} | {row['url']} | "
            f"{row['tags']} | {row['topics']} | {row['type']} | {row['completeness']} | "
            f"{row['confidence']} | {row['reuse_level']} | {row['followup_needed']} | {row['status']} |"
        )
    lines.extend([
        '',
        '## 统计',
        '',
        f'- 总条目: {len(rows)}',
        f'- raw: {stats["raw"]}',
        f'- parsed: {stats["parsed"]}',
        f'- briefed: {stats["briefed"]}',
        f'- integrated: {stats["integrated"]}',
    ])
    write_note(SOURCES_INDEX, '\n'.join(lines))
    write_note(OBSIDIAN_SOURCES_INDEX, build_obsidian_sources_index(rows))


def archive_materials(url: str, folder: Path) -> dict:
    ensure_dirs()
    meta = load_json(folder / 'meta.json')
    images = load_json(folder / 'images.json')
    raw_text = read_text(folder / 'text.txt')
    broken_assets = 0
    if isinstance(images, list):
        broken_assets = sum(1 for item in images if isinstance(item, dict) and item.get('error'))

    normalized_url = normalize_url(url)
    article_id = article_id_from_url(normalized_url)
    capture_date = datetime.now().strftime('%Y-%m-%d')
    publish_time = str(meta.get('create_time', '')).strip()
    publish_date = publish_time[:10] if len(publish_time) >= 10 else capture_date
    title = str(meta.get('title') or folder.name).strip()
    source_account = str(meta.get('source_account') or '待补').strip()
    body_lines = parse_body_lines(raw_text, title, source_account, publish_time)
    body = '\n'.join(body_lines)
    completeness = completeness_for(folder, body, broken_assets)
    article_type = detect_type(title, body)
    tags = detect_tags(title, body)
    topics = detect_topics(title, body)
    summary = pick_summary(body_lines)
    core_points = pick_core_points(body_lines, summary)
    while len(core_points) < 3:
        core_points.append('待补核心结论')
    facts = pick_facts(body_lines, meta, int(meta.get('image_count', 0)))
    structure = pick_structure(body_lines)
    assets = parse_assets(folder)
    quotes = [short(line, 140) for line in body_lines if len(line) >= 24][:2]
    if len(quotes) < 2:
        quotes.append(summary)

    canonical_name = f'{publish_date}_wechat_article_{article_id}.md'
    raw_existing = find_existing_by_url(RAW_DIR, normalized_url)
    parsed_existing = find_existing_by_url(PARSED_DIR, normalized_url)
    brief_existing = find_existing_by_url(BRIEF_DIR, normalized_url)
    raw_path, raw_renamed = choose_target(raw_existing, RAW_DIR / canonical_name, article_id)
    parsed_path, parsed_renamed = choose_target(parsed_existing, PARSED_DIR / canonical_name, article_id)
    brief_path, brief_renamed = choose_target(brief_existing, BRIEF_DIR / canonical_name, article_id)
    backup_stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_files = []
    for candidate in (raw_path, parsed_path, brief_path):
        backup = backup_existing(candidate, backup_stamp)
        if backup:
            backup_files.append(backup)

    write_raw(raw_path, title, source_account, normalized_url, publish_time, capture_date, completeness, body_lines)
    write_parsed(
        parsed_path,
        title,
        source_account,
        normalized_url,
        publish_time,
        capture_date,
        tags,
        article_type,
        completeness,
        summary,
        core_points,
        facts,
        structure,
        folder,
        assets,
        topics,
        quotes,
    )
    write_brief(brief_path, title, summary, core_points, tags, topics)

    status = 'briefed'
    followup_needed = 'yes' if status != 'integrated' else 'no'
    source_entry = {
        'title': title,
        'source_account': source_account,
        'date': publish_date,
        'url': normalized_url,
        'tags': ', '.join(tags),
        'topics': ', '.join(topics) if topics else '-',
        'type': article_type,
        'completeness': completeness,
        'confidence': confidence_for(completeness),
        'reuse_level': reuse_level_for(tags),
        'followup_needed': followup_needed,
        'status': status,
    }
    update_source_index(source_entry)

    files = {
        'raw': str(raw_path),
        'parsed': str(parsed_path),
        'brief': str(brief_path),
        'source_index': str(SOURCES_INDEX),
    }
    renamed = [str(path) for path, did_rename in (
        (raw_path, raw_renamed),
        (parsed_path, parsed_renamed),
        (brief_path, brief_renamed),
    ) if did_rename]
    return {
        'title': title,
        'folder': str(folder),
        'image_count': int(meta.get('image_count', 0)),
        'broken_assets': broken_assets,
        'completeness': completeness,
        'status': status,
        'topics': topics,
        'files': files,
        'renamed_existing_files': renamed,
        'backup_files': backup_files,
        'followup_needed': followup_needed,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('url')
    ap.add_argument('--base-dir', default=str(DEFAULT_MATERIALS_DIR))
    args = ap.parse_args()

    normalized_url = normalize_url(args.url)
    retrieval_mode = 'refetched'
    try:
        fetch_output = run([sys.executable, str(FETCH_SCRIPT), args.url, '--base-dir', args.base_dir])
        folder = detect_folder(fetch_output)
    except RuntimeError:
        folder = find_existing_material_folder(normalized_url)
        if folder is None:
            raise
        retrieval_mode = 'reused_existing_materials'
    run([sys.executable, str(NORMALIZE_SCRIPT), str(folder)])
    run([sys.executable, str(SUMMARY_SCRIPT), str(folder)])
    summary = archive_materials(args.url, folder)

    print(str(folder))
    print(json.dumps({
        'status': 'ok',
        'url': normalized_url,
        'retrieval_mode': retrieval_mode,
        **summary,
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
