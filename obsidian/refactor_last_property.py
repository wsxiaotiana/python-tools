import os
import re
import frontmatter


def refactor_last_property_and_content(vault_path):
    """
    遍历 Obsidian 库，执行以下操作：
    1. 在元数据中，将 'modified_time' 重命名为 'last'。
    2. 删除所有没有对应 'modified_time' 的旧 'last' 属性。
    3. 在笔记正文中，将所有出现的 'modified_time' 文本替换为 'last'。
    """
    print(f"开始重构 'last' 属性并替换文本: {vault_path}\n")
    updated_files_count = 0
    scanned_files_count = 0

    # 使用正则表达式进行全词匹配，确保不会替换掉类似 "unmodified_time" 的词
    pattern = re.compile(r'\bmodified_time\b')

    for root, dirs, files in os.walk(vault_path):
        if '.trash' in dirs:
            dirs.remove('.trash')

        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                scanned_files_count += 1

                try:
                    post = frontmatter.load(file_path)
                    made_changes_frontmatter = False
                    made_changes_content = False

                    # --- 1. 处理元数据 ---
                    # 如果 modified_time 存在，用它的值覆盖/创建 last，并删除 modified_time
                    if 'modified_time' in post.metadata:
                        post.metadata['last'] = post.metadata.pop('modified_time')
                        made_changes_frontmatter = True
                    # 否则，如果一个旧的 last 存在，删除它
                    elif 'last' in post.metadata:
                        del post.metadata['last']
                        made_changes_frontmatter = True

                    # --- 2. 处理正文内容 ---
                    original_content = post.content
                    new_content = pattern.sub('last', original_content)

                    if new_content != original_content:
                        post.content = new_content
                        made_changes_content = True

                    # --- 3. 仅在有变化时保存文件 ---
                    if made_changes_frontmatter or made_changes_content:
                        # 准备一个清晰的日志，说明修改了哪些部分
                        change_log = []
                        if made_changes_frontmatter: change_log.append("元数据")
                        if made_changes_content: change_log.append("正文内容")

                        with open(file_path, 'wb') as f:
                            frontmatter.dump(post, f)

                        print(f"✅  已更新: {file_path} (修改部分: {', '.join(change_log)})")
                        updated_files_count += 1

                except Exception as e:
                    print(f"❌  处理文件时出错: {file_path} | 错误: {e}")

    print("\n----------------------------------------")
    print("✨ 操作完成！")
    print(f"总共扫描了 {scanned_files_count} 个 Markdown 文件。")
    print(f"总共更新了 {updated_files_count} 个文件。")
    print("----------------------------------------")


# --- 配置您的Obsidian库路径 ---
# ⚠️ 请将下面的路径替换为您自己库的绝对路径。
VAULT_DIRECTORY = "E:\yxt\obsidian\obsidian-note"

# --- 运行脚本 ---
if __name__ == '__main__':
    if VAULT_DIRECTORY == "请在这里输入您的Obsidian库的绝对路径":
        print("❌ 错误：请先在脚本中设置您的 'VAULT_DIRECTORY' 变量！")
    else:
        # 安装依赖库
        try:
            import frontmatter
        except ImportError:
            print("正在安装必需的库: python-frontmatter")
            import subprocess
            import sys

            subprocess.check_call([sys.executable, "-m", "pip", "install", "python-frontmatter"])

        refactor_last_property_and_content(VAULT_DIRECTORY)