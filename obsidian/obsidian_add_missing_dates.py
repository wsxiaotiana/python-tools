import os
import datetime
import frontmatter
import copy  # <--- 1. 导入 copy 模块


def add_missing_date_attributes(vault_path):
    """
    遍历Obsidian库，为缺少或值为空的 'created'/'last' 属性补充日期。
    - 'created' 和 'last' 的值都来自文件的创建日期。
    - 日期格式为 YYYY-MM-DD (无引号)。
    - 跳过 .trash 文件夹。
    - 仅在实际补充了属性时才修改文件。
    - 通过复制对象来避免 YAML 锚点/别名问题。

    参数:
    vault_path (str): 您的Obsidian库的绝对路径。
    """
    print(f"开始扫描您的Obsidian库: {vault_path}\n")
    updated_files_count = 0
    scanned_files_count = 0

    for root, dirs, files in os.walk(vault_path):
        if '.trash' in dirs:
            dirs.remove('.trash')

        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                scanned_files_count += 1

                try:
                    post = frontmatter.load(file_path)
                    added_attributes = []

                    needs_created = not post.metadata.get('created')
                    needs_last = not post.metadata.get('last')

                    if needs_created or needs_last:
                        file_stat = os.stat(file_path)
                        try:
                            creation_timestamp = file_stat.st_birthtime
                        except AttributeError:
                            creation_timestamp = file_stat.st_ctime

                        creation_date_obj = datetime.datetime.fromtimestamp(creation_timestamp).date()

                        if needs_created:
                            post.metadata['created'] = creation_date_obj
                            added_attributes.append('created')

                        if needs_last:
                            # 【核心修复点】赋值一个对象的拷贝，而不是原始引用
                            post.metadata['last'] = copy.copy(creation_date_obj)
                            added_attributes.append('last')

                        if added_attributes:
                            with open(file_path, 'wb') as f:
                                frontmatter.dump(post, f)

                            print(f"✅  已更新: {file_path} (补充属性: {', '.join(added_attributes)})")
                            updated_files_count += 1

                except Exception as e:
                    print(f"❌  处理文件时出错: {file_path} | 错误: {e}")

    print("\n----------------------------------------")
    print("✨ 操作完成！")
    print(f"总共扫描了 {scanned_files_count} 个 Markdown 文件。")
    print(f"总共更新了 {updated_files_count} 个文件。")
    print("----------------------------------------")


# --- 配置您的Obsidian库路径 ---
VAULT_DIRECTORY = "E:\yxt\obsidian\obsidian-note"

# --- 运行脚本 ---
if __name__ == '__main__':
    if VAULT_DIRECTORY == "请在这里输入您的Obsidian库的绝对路径":
        print("❌ 错误：请先在脚本中设置您的 'VAULT_DIRECTORY' 变量！")
    else:
        add_missing_date_attributes(VAULT_DIRECTORY)