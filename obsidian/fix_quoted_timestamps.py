import os
import datetime
import frontmatter

# --- 配置：支持的日期/时间格式列表 ---
# 我们使用之前版本中已经很强大的格式列表
SUPPORTED_FORMATS = [
    '%Y-%m-%dT%H:%M:%S%z',
    '%Y-%m-%d',
    '%Y/%m/%dT%H:%M:%S',
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%dT%H:%M',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%dT%I:%M %p',
    '%Y-%m-%d %I:%M %p',
]


def parse_flexible_date(date_string):
    """
    使用预定义格式列表，将字符串解析为 datetime 对象。
    在解析前会清理非标准的时区描述文本。
    """
    if isinstance(date_string, str) and ' (' in date_string:
        date_string = date_string.split(' (')[0]

    for fmt in SUPPORTED_FORMATS:
        try:
            return datetime.datetime.strptime(str(date_string), fmt)
        except (ValueError, TypeError):
            continue
    return None


def fix_quoted_timestamps(vault_path):
    """
    遍历Obsidian库，将 'modified_time' 属性中带引号的字符串值
    转换为不带引号的 datetime 对象。
    """
    print(f"开始扫描并修正带引号的时间戳: {vault_path}\n")
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
                    attributes_to_check = ['created_time', 'modified_time']  # <--- 定义要检查的属性列表

                    # 循环检查列表中的每个属性
                    for attr in attributes_to_check:
                        value = post.metadata.get(attr)

                        # 只处理那些值是字符串的情况
                        if value and isinstance(value, str):
                            # 跳过 Templater 动态命令
                            if '<%' in value:
                                continue

                            # 尝试将字符串解析为 datetime 对象
                            parsed_datetime = parse_flexible_date(value)

                            if parsed_datetime:
                                # 使用 datetime 对象替换原来的字符串
                                post.metadata[attr] = parsed_datetime
                                made_changes = True
                                corrected_attributes.append(attr)
                            else:
                                print(f"🟡  警告: 无法解析 '{attr}' 的值 '{value}' 在文件: {file_path}")

                    # 仅在实际修正了格式后才保存文件
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
        fix_quoted_timestamps(VAULT_DIRECTORY)