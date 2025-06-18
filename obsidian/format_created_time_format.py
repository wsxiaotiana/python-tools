import os
import re


def correct_date_format_in_file(file_path):
    """
    读取一个Obsidian笔记文件，检查并修正YAML frontmatter中
    'created_time'和'last'属性的日期格式。

    Args:
        file_path (str): Markdown文件的完整路径。

    Returns:
        bool: 如果文件被修改则返回True，否则返回False。
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 使用正则表达式查找YAML frontmatter
        frontmatter_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)

        if not frontmatter_match:
            return False

        original_frontmatter = frontmatter_match.group(0)
        modified_frontmatter = original_frontmatter
        was_modified = False

        properties_to_check = ["created_time", "last"]

        for prop in properties_to_check:
            # 正则表达式，用于查找类似 'created_time: "2025-06-09T10:08:39"' 的行
            # 这个表达式可以处理属性名后有无空格，以及值有无被引号包围的情况
            prop_regex = re.compile(
                r"^(%s\s*:\s*[\"']?)(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})([\"']?)$" % prop,
                re.MULTILINE
            )

            # 在frontmatter内部进行搜索和替换
            modified_frontmatter, num_replacements = prop_regex.subn(
                lambda m: f"{m.group(1)}{m.group(2).replace('T', ' ')}{m.group(3)}",
                modified_frontmatter
            )

            if num_replacements > 0:
                was_modified = True

        if was_modified:
            # 用修改后的frontmatter替换原始内容中的旧frontmatter
            new_content = content.replace(original_frontmatter, modified_frontmatter)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True

    except Exception as e:
        print(f"处理文件“{file_path}”时出错: {e}")
        return False

    return False


def batch_process_obsidian_notes(vault_path):
    """
    递归查找仓库中的所有Markdown文件并修正其中的日期格式。

    Args:
        vault_path (str): Obsidian仓库目录的路径。
    """
    if not os.path.isdir(vault_path):
        print(f"错误：提供的路径“{vault_path}”不是一个有效的目录。")
        return

    modified_files_count = 0
    total_files_processed = 0

    print("开始批量处理笔记...")

    for root, _, files in os.walk(vault_path):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                total_files_processed += 1
                if correct_date_format_in_file(file_path):
                    print(f"已修改文件: {file_path}")
                    modified_files_count += 1

    print("\n处理完成！")
    print(f"总共处理了 {total_files_processed} 个Markdown文件。")
    print(f"成功修改了 {modified_files_count} 个文件。")


if __name__ == "__main__":
    # --- 请在这里修改你的路径 ---
    # 使用时，请将下面的 "你的Obsidian仓库路径" 替换为你的实际仓库路径
    # 例如: vault_directory = "D:/Documents/MyObsidianVault"
    vault_directory = "D:\\my documents\\obsidian\\obsidian-note"
    # --------------------------

    if vault_directory == "你的Obsidian仓库路径" or not vault_directory:
        print("请先在脚本中设置你的Obsidian仓库路径。")
        print("请编辑此脚本文件，将 '你的Obsidian仓库路径' 替换为你的笔记库的实际文件夹路径。")
    else:
        batch_process_obsidian_notes(vault_directory)