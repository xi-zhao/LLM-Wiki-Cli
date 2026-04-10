#!/usr/bin/env python3

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
BASE = Path(os.environ.get('FOKB_BASE', str(APP_ROOT))).expanduser().resolve()
TOPICS_DIR = BASE / 'topics'
SORTED_DIR = BASE / 'sorted'
MOC_NAME = 'topics-moc.md'

TOPIC_META = {
    'ai-coding-and-autoresearch.md': {
        'title': 'AI 编程与自动研究',
        'definition': '围绕大模型在代码生成、性能优化、自动研究与工程迭代中的应用，尤其是高难度技术任务中的能力边界。',
        'questions': [
            '新一代模型是否已经能承担接近高级工程师级别的技术探索任务',
            '自动研究 + 强模型 + 长时间迭代，能否改变量级复杂工程效率',
            '哪些任务适合交给模型，哪些仍需强人工把关',
        ],
    },
    'ai-research-writing.md': {
        'title': 'AI 科研写作与研究辅助',
        'definition': '围绕 AI 在论文写作、科研表达、研究辅助、学术工作流中的应用，包括 prompt、skills、coauthoring、翻译润色与科研流程增强。',
        'questions': [
            'AI 如何真正进入科研生产流程，而不只是聊天助手',
            'prompt、skill、agent 在科研工作中的分工是什么',
            '哪些科研能力会被增强，哪些能力仍然稀缺',
        ],
    },
    'tob-ai-productization.md': {
        'title': 'ToB AI 产品化',
        'definition': '围绕企业级 AI 从项目制交付走向产品化的判断框架、工程门槛、数据治理难点与行业适配问题。',
        'questions': [
            '哪些 ToB AI 需求适合产品化，哪些更像持续定制化项目',
            '数据治理、行业术语、业务规则沉淀的成本如何摊薄',
            '产品化路径中，行业 know-how 与通用 AI 能力的边界在哪里',
        ],
    },
    'wechat-agent-routing.md': {
        'title': '微信 Agent 路由',
        'definition': '围绕微信场景中的 AI Agent 入口绑定、路由规则、多用户隔离与多智能体配置。',
        'questions': [
            '一个微信入口如何绑定到指定 agent',
            '多个用户如何在同一套 OpenClaw 中隔离',
            '多账号、多 agent、多工作区之间如何取舍',
        ],
    },
    'quantum-computing-industry.md': {
        'title': '量子计算产业与投融资',
        'definition': '围绕量子计算产业的政策、融资、技术进展、产业化落地与资本热度变化。',
        'questions': [
            '量子计算赛道是否进入新一轮融资升温',
            '超导路线的商业化进展处于什么阶段',
            '政策信号与资本热度之间如何互相强化',
        ],
    },
    'ai-voice-and-edge-models.md': {
        'title': 'AI 语音与端侧小模型',
        'definition': '跟踪 AI 语音生成、音色克隆、多语种 TTS 以及其与端侧 AI、小模型、开源生态之间的关联。',
        'questions': [
            'AI 语音何时真正从演示效果走向专业生产可用',
            '开源语音模型与闭源商用产品之间的能力差距还有多大',
            '语音能力在端侧设备、出海场景和内容工业中的落地速度如何',
        ],
    },
}


def read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8') if path.exists() else ''


def infer_title(parsed_text: str, fallback: str) -> str:
    m = re.search(r'^# 标题：(.+)$', parsed_text, re.M)
    return m.group(1).strip() if m else fallback


def extract_bullet_section(text: str, heading: str) -> list[str]:
    m = re.search(rf'^## {re.escape(heading)}\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith('- '):
            out.append(line[2:].strip())
    return out


def extract_numbered_section(text: str, heading: str) -> list[str]:
    m = re.search(rf'^## {re.escape(heading)}\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        line = line.strip()
        mm = re.match(r'^\d+\.\s+(.*)$', line)
        if mm:
            out.append(mm.group(1).strip())
    return out


def append_unique_bullet(section: str, value: str) -> str:
    bullets = [line.strip()[2:].strip() for line in section.splitlines() if line.strip().startswith('- ')]
    if value in bullets:
        return section
    if section and not section.endswith('\n'):
        section += '\n'
    section += f'- {value}\n'
    return section


def build_topic_frontmatter(topic_slug: str) -> str:
    return '\n'.join([
        '---',
        'type: topic',
        f'topic: {topic_slug}',
        'tags:',
        '  - topic',
        '  - obsidian',
        f'  - topic/{topic_slug}',
        '---',
        '',
    ])


def build_note_relations(topic_slug: str, title: str) -> str:
    return '\n'.join([
        f'- Topic Note: [[{topic_slug}|{title}]]',
        f'- Digest Note: [[{topic_slug}-digest]]',
        '- MOC: [[topics-moc]]',
    ]) + '\n'


def ensure_topic_frontmatter(text: str, topic_slug: str) -> str:
    if text.lstrip().startswith('---\n'):
        return text
    return build_topic_frontmatter(topic_slug) + text.lstrip()


def build_obsidian_article_link(parsed_path: Path, parsed_title: str) -> str:
    return f'[[{parsed_path.stem}|{parsed_title}]]'


def list_topic_files() -> list[Path]:
    if not TOPICS_DIR.exists():
        return []
    return sorted(
        [path for path in TOPICS_DIR.glob('*.md') if path.name not in {'_template.md', MOC_NAME}],
        key=lambda p: p.name,
    )


def extract_topic_title(topic_text: str, fallback: str) -> str:
    m = re.search(r'^# Topic: (.+)$', topic_text, re.M)
    return m.group(1).strip() if m else fallback


def build_topics_moc() -> str:
    lines = [
        '---',
        'type: moc',
        'scope: topics',
        'tags:',
        '  - moc',
        '  - obsidian',
        '  - topics',
        '---',
        '',
        '# Topics MOC',
        '',
        '## 用途',
        '- 这是 topic / digest / source note 的导航页。',
        '- 适合在 Obsidian 里作为图谱和双链的总入口。',
        '',
        '## Topic Notes',
    ]
    topic_files = list_topic_files()
    if topic_files:
        for path in topic_files:
            text = read_text(path)
            title = extract_topic_title(text, path.stem)
            lines.append(f'- [[{path.stem}|{title}]]')
    else:
        lines.append('- 待补 topic')
    lines.extend(['', '## Digests'])
    if topic_files:
        for path in topic_files:
            digest_path = SORTED_DIR / f'{path.stem}-digest.md'
            if digest_path.exists():
                lines.append(f'- [[{path.stem}-digest]]')
    else:
        lines.append('- 待补 digest')
    lines.extend(['', '## Workflow'])
    lines.append('- Topic Note -> Digest -> Related Source Notes')
    lines.append('- 用 `[[wikilink]]` 连接 topic、digest、article notes。')
    return '\n'.join(lines) + '\n'


def write_topics_moc() -> Path:
    path = TOPICS_DIR / MOC_NAME
    path.write_text(build_topics_moc(), encoding='utf-8')
    return path


def ensure_topic_file(topic_file: str) -> Path:
    path = TOPICS_DIR / topic_file
    if path.exists():
        return path
    meta = TOPIC_META.get(topic_file, None)
    title = meta['title'] if meta else topic_file.replace('.md', '')
    definition = meta['definition'] if meta else '待补主题定义'
    questions = meta['questions'] if meta else ['待补问题 1', '待补问题 2', '待补问题 3']
    topic_slug = path.stem
    content = '\n'.join([
        build_topic_frontmatter(topic_slug).rstrip(),
        f'# Topic: {title}',
        '',
        '## 笔记关系',
        build_note_relations(topic_slug, title).rstrip(),
        '',
        '## 主题定义',
        f'- {definition}',
        '',
        '## 当前核心问题',
        *[f'- {q}' for q in questions],
        '',
        '## 稳定结论',
        '- 待补稳定结论',
        '',
        '## 新增观察',
        '',
        '## 代表性案例 / 证据',
        '- 待补代表性案例',
        '',
        '## 可输出方向',
        '- 可写文章：待补',
        '- 可做 PPT：待补',
        '- 可做分享：待补',
        '',
        '## 关联文章',
        '- 待补关联文章',
        '',
        '## 关联笔记（Obsidian）',
        '- 待补关联笔记',
        '',
        '## 待跟进',
        '- 待补跟进项',
        '',
    ])
    path.write_text(content, encoding='utf-8')
    write_topics_moc()
    return path


def update_section_block(text: str, heading: str, new_body: str) -> str:
    pattern = re.compile(rf'(^## {re.escape(heading)}\n)(.*?)(?=^## |\Z)', re.M | re.S)
    if pattern.search(text):
        return pattern.sub(lambda m: m.group(1) + new_body.rstrip() + '\n\n', text, count=1)
    suffix = '' if text.endswith('\n') else '\n'
    return text + suffix + f'## {heading}\n' + new_body.rstrip() + '\n\n'


def insert_section_after_title(text: str, heading: str, body: str) -> str:
    if f'## {heading}\n' in text:
        return text
    match = re.search(r'(^# Topic: .+$\n)', text, re.M)
    if not match:
        return update_section_block(text, heading, body)
    insertion = f'\n## {heading}\n{body.rstrip()}\n'
    return text[:match.end()] + insertion + text[match.end():]


def maintain_topic(topic_file: str, parsed_file: str) -> dict:
    topic_path = ensure_topic_file(topic_file)
    parsed_path = Path(parsed_file)
    topic_text = read_text(topic_path)
    parsed_text = read_text(parsed_path)
    parsed_title = infer_title(parsed_text, parsed_path.stem)
    month = datetime.now().strftime('%Y-%m')
    actions = []

    topic_slug = topic_path.stem
    topic_title = TOPIC_META.get(topic_file, {}).get('title', topic_slug)
    topic_text = ensure_topic_frontmatter(topic_text, topic_slug)
    relations_section = build_note_relations(topic_slug, topic_title)
    topic_text = insert_section_after_title(topic_text, '笔记关系', relations_section)
    topic_text = update_section_block(topic_text, '笔记关系', relations_section)

    core_points = extract_numbered_section(parsed_text, '核心结论')
    facts = extract_bullet_section(parsed_text, '关键事实 / 证据')
    relation_link = f'[{parsed_title}](../articles/parsed/{parsed_path.name})'
    obsidian_link = build_obsidian_article_link(parsed_path, parsed_title)
    evidence_ref = parsed_path.name

    obs_match = re.search(r'^## 新增观察\n(.*?)(?=^## |\Z)', topic_text, re.M | re.S)
    obs_body = obs_match.group(1) if obs_match else ''
    month_heading = f'### {month}'
    observation_line = f'- 新增文章《{parsed_title}》已纳入该主题，可作为后续综述与判断的支撑材料。'
    if observation_line not in obs_body:
        actions.append('append_observation')
    if month_heading in obs_body:
        block_pattern = re.compile(rf'({re.escape(month_heading)}\n)(.*?)(?=^### |\Z)', re.M | re.S)
        def repl(m):
            block = m.group(2)
            if observation_line in block:
                return m.group(0)
            return m.group(1) + block + ('' if block.endswith('\n') or not block else '\n') + observation_line + '\n'
        obs_body = block_pattern.sub(repl, obs_body, count=1)
    else:
        if obs_body and not obs_body.endswith('\n'):
            obs_body += '\n'
        obs_body += f'{month_heading}\n{observation_line}\n'
    topic_text = update_section_block(topic_text, '新增观察', obs_body)

    evidence_body = re.search(r'^## 代表性案例 / 证据\n(.*?)(?=^## |\Z)', topic_text, re.M | re.S)
    evidence_section = evidence_body.group(1) if evidence_body else ''
    evidence_section = evidence_section.replace('- 待补代表性案例\n', '')
    before_evidence = evidence_section
    evidence_section = append_unique_bullet(evidence_section, evidence_ref)
    for fact in facts[:2]:
        evidence_section = append_unique_bullet(evidence_section, fact)
    if evidence_section != before_evidence:
        actions.append('append_evidence')
    topic_text = update_section_block(topic_text, '代表性案例 / 证据', evidence_section)

    related_body = re.search(r'^## 关联文章\n(.*?)(?=^## |\Z)', topic_text, re.M | re.S)
    related_section = related_body.group(1) if related_body else ''
    related_section = related_section.replace('- 待补关联文章\n', '')
    before_related = related_section
    related_section = append_unique_bullet(related_section, relation_link)
    if related_section != before_related:
        actions.append('append_related_article')
    topic_text = update_section_block(topic_text, '关联文章', related_section)

    obsidian_body = re.search(r'^## 关联笔记（Obsidian）\n(.*?)(?=^## |\Z)', topic_text, re.M | re.S)
    obsidian_section = obsidian_body.group(1) if obsidian_body else ''
    obsidian_section = obsidian_section.replace('- 待补关联笔记\n', '')
    before_obsidian = obsidian_section
    obsidian_section = append_unique_bullet(obsidian_section, obsidian_link)
    if obsidian_section != before_obsidian:
        actions.append('append_obsidian_link')
    topic_text = update_section_block(topic_text, '关联笔记（Obsidian）', obsidian_section)

    stable_body = re.search(r'^## 稳定结论\n(.*?)(?=^## |\Z)', topic_text, re.M | re.S)
    stable_section = stable_body.group(1) if stable_body else ''
    if '待补稳定结论' in stable_section and core_points:
        stable_section = ''.join(f'- {point}\n' for point in core_points[:2])
        topic_text = update_section_block(topic_text, '稳定结论', stable_section)
        actions.append('promote_stable_conclusion')

    topic_path.write_text(topic_text, encoding='utf-8')
    moc_path = write_topics_moc()
    return {
        'topic': topic_file,
        'topic_path': str(topic_path),
        'moc_path': str(moc_path),
        'status': 'updated' if actions else 'no_change',
        'actions': actions or ['no_change'],
    }


def main():
    parser = argparse.ArgumentParser(description='Maintain topic files after ingest')
    parser.add_argument('--topic', required=True, help='Topic file name, e.g. ai-coding-and-autoresearch.md')
    parser.add_argument('--parsed', required=True, help='Parsed article path')
    args = parser.parse_args()
    print(json.dumps(maintain_topic(args.topic, args.parsed), ensure_ascii=False))


if __name__ == '__main__':
    main()
