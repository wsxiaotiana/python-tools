#!/usr/bin/env python3
"""
find_obsidian_links.py
在 Obsidian 库中查找链接到指定文件列表的笔记。

实际执行：
python find_obsidian_links.py --vault-path "E:\yxt\obsidian\obsidian-note"
"""
import os
import argparse
from datetime import datetime


def read_duplicate_list(filepath):
    """从文件中读取待查找的文件名列表"""
    if not os.path.exists(filepath):
        print(f"❌ 错误：输入文件 '{filepath}' 不存在。")
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        # 提取文件名，例如从 "image/cat.jpg" 提取 "cat.jpg"
        # 因为 Obsidian 链接通常不包含完整路径
        filenames = {os.path.basename(line.strip()) for line in f if line.strip()}
    return filenames


def find_linking_notes(vault_path, files_to_find):
    """在 vault 中查找链接到目标文件的笔记"""
    linking_notes = set()
    print(f"\n🔍 开始扫描 Obsidian 库: {vault_path}")
    for root, _, files in os.walk(vault_path):
        # 忽略 Obsidian 的内部目录
        if '.obsidian' in root:
            continue

        for file in files:
            if file.endswith('.md'):
                note_path = os.path.join(root, file)
                try:
                    with open(note_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for target_file in files_to_find:
                            # 检查笔记内容是否包含文件名（Obsidian 链接格式 `[[file]]` 或 `![[file]]`）
                            if target_file in content:
                                # 添加笔记名（去掉.md后缀），以便生成可点击链接
                                linking_notes.add(os.path.splitext(file)[0])
                                # 找到一个匹配后就可以检查下一个笔记了
                                break
                except Exception as e:
                    print(f"  - 读取文件 {note_path} 出错: {e}")

    print(f"✅ 扫描完成。发现 {len(linking_notes)} 篇相关笔记。")
    return sorted(list(linking_notes))


def create_report_note(vault_path, output_filename, notes_to_link):
    """在 vault 中创建包含链接的报告笔记"""
    report_path = os.path.join(vault_path, output_filename)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    content = f"# 重复图片关联笔记报告\n\n"
    content += f"- 生成时间: {timestamp}\n"
    content += f"- 涉及笔记数量: {len(notes_to_link)}\n\n"
    content += "---\n\n"

    if not notes_to_link:
        content += "未发现任何笔记链接到指定的重复图片。\n"
    else:
        content += "以下笔记链接到了待删除的重复图片，请检查并手动处理：\n\n"
        for note_name in notes_to_link:
            # 生成 Obsidian 内部链接
            content += f"- [[{note_name}]]\n"

    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n📝 报告已生成！请在 Obsidian 中打开笔记: {output_filename}")
    except IOError as e:
        print(f"❌ 创建报告失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="查找链接到重复文件的 Obsidian 笔记。")
    parser.add_argument("--vault-path", required=True, help="你的 Obsidian 库的根目录路径。")
    parser.add_argument("--input-file", default="duplicates_to_delete.txt",
                        help="由 OSS 脚本生成的、包含待删除文件名的列表文件。 (默认: duplicates_to_delete.txt)")
    parser.add_argument("--output-note", default="重复图片关联笔记报告.md",
                        help="在 Obsidian 库中生成的报告笔记的文件名。 (默认: 重复图片关联笔记报告.md)")
    args = parser.parse_args()

    files_to_find = read_duplicate_list(args.input_file)
    if files_to_find is None:
        return

    linking_notes = find_linking_notes(args.vault_path, files_to_find)
    create_report_note(args.vault_path, args.output_note, linking_notes)


if __name__ == "__main__":
    main()