#!/usr/bin/env python3
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
TOPICS = BASE / 'topics'
OUT = BASE / 'sorted'


def extract_section(text: str, heading: str):
    pattern = re.compile(rf'^## {re.escape(heading)}\n(.*?)(?=^## |\Z)', re.M | re.S)
    m = pattern.search(text)
    return m.group(1).strip() if m else ''


def bullets(section: str):
    out = []
    for line in section.splitlines():
        line = line.strip()
        if line.startswith('- '):
            out.append(line[2:].strip())
    return out


def title_from_topic(text: str, fallback: str):
    m = re.search(r'^# Topic: (.+)$', text, re.M)
    return m.group(1).strip() if m else fallback


def main():
    if len(sys.argv) < 2:
        print('usage: generate_topic_digest.py <topic-file-name>')
        sys.exit(1)
    topic_name = sys.argv[1]
    topic_path = TOPICS / topic_name
    if not topic_path.exists():
        print(f'missing topic file: {topic_path}', file=sys.stderr)
        sys.exit(2)

    text = topic_path.read_text(encoding='utf-8')
    title = title_from_topic(text, topic_name)
    definition = bullets(extract_section(text, '主题定义'))
    core_questions = bullets(extract_section(text, '当前核心问题'))
    stable = bullets(extract_section(text, '稳定结论'))
    observations = extract_section(text, '新增观察')
    evidence = bullets(extract_section(text, '代表性案例 / 证据'))
    outputs = bullets(extract_section(text, '可输出方向'))
    followups = bullets(extract_section(text, '待跟进'))

    one_liner = stable[0] if stable else (definition[0] if definition else f'{title} 正在持续积累，值得做阶段性综述。')

    lines = []
    lines.append(f'# 主题综述：{title}')
    lines.append('')
    lines.append('## 一句话判断')
    lines.append(f'- {one_liner}')
    lines.append('')
    lines.append('## 为什么现在值得关注')
    worth = []
    if stable:
        worth.append('该主题已经沉淀出相对稳定的阶段性判断。')
    if evidence:
        worth.append('已有代表性文章/案例/数据可直接支撑输出。')
    if followups:
        worth.append('后续仍有持续跟踪空间，不是一次性话题。')
    for item in (worth or ['该主题已具备从资料堆转成输出草稿的基础。']):
        lines.append(f'- {item}')
    lines.append('')
    lines.append('## 当前核心结论')
    for item in (stable[:5] or ['待补结论']):
        lines.append(f'1. {item}' if item == (stable[:5] or ['待补结论'])[0] else f'{len([l for l in lines if re.match(r"^\d+\. ", l)])+1}. {item}')
    # fix numbering
    numbered = []
    idx = 1
    for item in (stable[:5] or ['待补结论']):
        numbered.append(f'{idx}. {item}')
        idx += 1
    lines = lines[:-len((stable[:5] or ['待补结论']))]
    lines.extend(numbered)
    lines.append('')
    lines.append('## 支撑证据')
    if evidence:
        for item in evidence:
            lines.append(f'- {item}')
    else:
        lines.append('- 待补代表性证据')
    lines.append('')
    lines.append('## 当前核心问题')
    for item in (core_questions[:5] or ['待补核心问题']):
        lines.append(f'- {item}')
    lines.append('')
    lines.append('## 最近新增观察')
    if observations:
        for line in observations.splitlines()[:12]:
            lines.append(line if line.strip() else '')
    else:
        lines.append('- 待补新增观察')
    lines.append('')
    lines.append('## 适合写成什么')
    if outputs:
        for item in outputs:
            lines.append(f'- {item}')
    else:
        lines.append('- 可写文章：待补')
        lines.append('- 可做 PPT：待补')
    lines.append('')
    lines.append('## 还需要继续跟踪什么')
    for item in (followups[:5] or ['待补后续跟踪点']):
        lines.append(f'- {item}')
    lines.append('')
    lines.append(f'## 来源主题文件')
    lines.append(f'- `{topic_path}`')

    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / f'{topic_path.stem}-digest.md'
    out_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(out_path)

if __name__ == '__main__':
    main()
