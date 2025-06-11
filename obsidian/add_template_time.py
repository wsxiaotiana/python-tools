import os
import frontmatter

# --- 配置 ---
# 您的模板文件夹的名称。请根据您的实际情况修改。
# 常见的名称有 "templates", "Templates", "模板" 等。
TEMPLATE_FOLDER_NAME = "templates"

# 要添加的Templater命令
CREATED_TIME_SYNTAX = '<% tp.file.creation_date("YYYY-MM-DDTHH:mm:ss") %>'
MODIFIED_TIME_SYNTAX = '<% tp.file.last_modified_date("YYYY-MM-DDTHH:mm:ss") %>'  # 使用正确的命令


def add_templater_syntax_to_templates(vault_path):
    """
    为指定模板文件夹下的所有文件添加 created_time 和 modified_time 的
    Templater 动态命令。

    参数:
    vault_path (str): 您的Obsidian库的绝对路径。
    """
    template_path = os.path.join(vault_path, TEMPLATE_FOLDER_NAME)

    if not os.path.exists(template_path):
        print(f"❌ 错误：找不到模板文件夹！路径: {template_path}")
        print(f"   请检查脚本中的 'TEMPLATE_FOLDER_NAME' 变量是否与您库中的文件夹名称一致。")
        return

    print(f"开始扫描您的模板文件夹: {template_path}\n")
    updated_files_count = 0
    scanned_files_count = 0

    # os.listdir只会遍历当前文件夹，不会进入子文件夹
    for filename in os.listdir(template_path):
        file_path = os.path.join(template_path, filename)

        # 确保我们只处理文件，而不是子文件夹
        if os.path.isfile(file_path):
            scanned_files_count += 1
            try:
                post = frontmatter.load(file_path)
                made_changes = False
                added_attributes = []

                # 1. 检查并添加 created_time
                if 'created_time' not in post.metadata:
                    post.metadata['created_time'] = CREATED_TIME_SYNTAX
                    made_changes = True
                    added_attributes.append('created_time')

                # 2. 检查并添加 modified_time
                if 'modified_time' not in post.metadata:
                    post.metadata['modified_time'] = MODIFIED_TIME_SYNTAX
                    made_changes = True
                    added_attributes.append('modified_time')

                # 3. 如果有任何修改，则保存文件
                if made_changes:
                    with open(file_path, 'wb') as f:
                        frontmatter.dump(post, f)

                    print(f"✅  已更新模板: {filename} (添加属性: {', '.join(added_attributes)})")
                    updated_files_count += 1

            except Exception as e:
                print(f"❌  处理文件时出错: {file_path} | 错误: {e}")

    print("\n----------------------------------------")
    print("✨ 操作完成！")
    print(f"总共扫描了 {scanned_files_count} 个文件。")
    print(f"总共更新了 {updated_files_count} 个模板文件。")
    print("----------------------------------------")


# --- 配置您的Obsidian库路径 ---
# ⚠️ 请将下面的路径替换为您自己库的绝对路径。
VAULT_DIRECTORY = "E:\yxt\obsidian\obsidian-note"

# --- 运行脚本 ---
if __name__ == '__main__':
    if VAULT_DIRECTORY == "请在这里输入您的Obsidian库的绝对路径":
        print("❌ 错误：请先在脚本中设置您的 'VAULT_DIRECTORY' 变量！")
    else:
        add_templater_syntax_to_templates(VAULT_DIRECTORY)