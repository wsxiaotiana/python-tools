import os
import datetime
import frontmatter

# --- 配置：支持的日期/时间格式列表 ---
# 脚本将按顺序尝试这些格式。
# %z 用于处理时区信息 (e.g., +08:00)
SUPPORTED_FORMATS = [
    '%Y-%m-%dT%H:%M:%S%z',
    '%Y-%m-%d',
    '%Y/%m/%dT%H:%M:%S',      # 【新增】支持斜杠分隔的日期格式
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%dT%H:%M',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%dT%I:%M %p',
    '%Y-%m-%d %I:%M %p',
]


def parse_flexible_date(date_string):
    """
    使用一个预定义的格式列表，尝试将字符串解析为 datetime 对象。
    """
    for fmt in SUPPORTED_FORMATS:
        try:
            return datetime.datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    return None


def fix_date_format_in_vault(vault_path):
    """
    遍历Obsidian库，检查并修正 'created' 和 'last' 属性的格式。
    """
    print(f"开始扫描并修正您的Obsidian库中的日期格式: {vault_path}\n")
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
                    made_changes = False
                    corrected_attributes = []
                    attributes_to_check = ['created_time', 'last']

                    for attr in attributes_to_check:
                        if post.metadata.get(attr) and not isinstance(post.metadata.get(attr), datetime.date):
                            current_value = post.metadata.get(attr)
                            new_date_obj = None

                            if isinstance(current_value, datetime.datetime):
                                # 如果值本身就是一个datetime对象，直接提取日期部分
                                new_date_obj = current_value.date()

                            elif isinstance(current_value, str):
                                # 如果是字符串，调用我们的解析函数
                                parsed_datetime = parse_flexible_date(current_value)
                                if parsed_datetime:
                                    # 提取解析出的datetime对象的日期部分
                                    new_date_obj = parsed_datetime.date()
                                else:
                                    print(f"🟡  警告: 无法解析的日期字符串 '{current_value}' 在文件: {file_path}")

                            if new_date_obj:
                                # 无论源格式如何，最终都只存入纯粹的date对象
                                post.metadata[attr] = new_date_obj
                                made_changes = True
                                corrected_attributes.append(attr)

                    if made_changes:
                        with open(file_path, 'wb') as f:
                            frontmatter.dump(post, f)

                        print(f"✅  已修正格式: {file_path} (字段: {', '.join(corrected_attributes)})")
                        updated_files_count += 1

                except Exception as e:
                    print(f"❌  处理文件时出错: {file_path} | 错误: {e}")

    print("\n----------------------------------------")
    print("✨ 操作完成！")
    print(f"总共扫描了 {scanned_files_count} 个 Markdown 文件。")
    print(f"总共修正了 {updated_files_count} 个文件。")
    print("----------------------------------------")


# --- 配置您的Obsidian库路径 ---
VAULT_DIRECTORY = "E:\yxt\obsidian\obsidian-note"

# --- 运行脚本 ---
if __name__ == '__main__':
    if VAULT_DIRECTORY == "请在这里输入您的Obsidian库的绝对路径":
        print("❌ 错误：请先在脚本中设置您的 'VAULT_DIRECTORY' 变量！")
    else:
        fix_date_format_in_vault(VAULT_DIRECTORY)