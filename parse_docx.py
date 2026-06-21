"""
批量解析 docx 题库 → 结构化 JSON
"""
import os
import re
import json
import docx

BASE = r"C:\Users\星河\Desktop\新建文件夹 (2)\answer_tool"
CUSTOM_DIR = os.path.join(BASE, "data", "custom", "C++上机考试")
OUTPUT = os.path.join(BASE, "data", "custom_parsed.json")

all_entries = []

for fname in sorted(os.listdir(CUSTOM_DIR)):
    if not fname.endswith('.docx'):
        continue

    fpath = os.path.join(CUSTOM_DIR, fname)
    doc = docx.Document(fpath)

    # 提取所有非空段落文本
    lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    # 判断题目类型
    if '选择' in fname or fname.startswith('xzt') or fname.startswith('C选择'):
        qtype = '选择题'
    elif '判断' in fname:
        qtype = '判断题'
    elif '填空' in fname:
        qtype = '程序填空'
    elif '改错' in fname:
        qtype = '程序改错'
    elif '设计' in fname:
        qtype = '程序设计'
    else:
        qtype = '未知'

    i = 0
    while i < len(lines):
        line = lines[i]

        # 匹配题号开头: N） 或 N）
        m = re.match(r'^(\d+)\s*[）)]\s*(.+)', line)
        if not m:
            # 可能题目跨行，跳过
            i += 1
            continue

        q_num = m.group(1)
        q_text = m.group(2)

        # 收集选项（如果有的话）
        options = []
        i += 1
        while i < len(lines) and re.match(r'^[A-H][、.,)]', lines[i]):
            options.append(lines[i])
            i += 1

        # 收集答案
        answer = ""
        chapter = ""
        knowledge = ""

        while i < len(lines):
            line2 = lines[i]
            if re.match(r'^\d+\s*[）)]', line2):  # 下一题开始了
                break
            if re.match(r'^答案[：:]', line2):
                answer = re.sub(r'^答案[：:]\s*', '', line2)
            elif re.match(r'^章节[：:]', line2):
                chapter = re.sub(r'^章节[：:]\s*', '', line2)
            elif re.match(r'^知识点[：:]', line2):
                knowledge = re.sub(r'^知识点[：:]\s*', '', line2)
            else:
                # 可能是题目的补充内容（代码段等），追加到题目
                q_text += '\n' + line2
            i += 1

        # 构建完整题目
        full_q = q_num + '）. ' + q_text
        if options:
            full_q += '\n' + '\n'.join(options)

        entry = {
            'question': full_q[:500],  # 限制长度
            'answer': answer,
            'type': qtype,
            'chapter': chapter,
            'knowledge': knowledge,
            'source': fname.replace('.docx', ''),
        }
        all_entries.append(entry)

    print(f"  {fname}: 解析出 {len([e for e in all_entries if e['source'] == fname.replace('.docx', '')])} 道题")

# 保存
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(all_entries, f, ensure_ascii=False, indent=2)

print(f"\n总共解析 {len(all_entries)} 道题目")
print(f"输出: {OUTPUT}")

# 统计
from collections import Counter
types = Counter(e['type'] for e in all_entries)
print(f"\n题目类型分布:")
for t, c in types.items():
    print(f"  {t}: {c} 题")
