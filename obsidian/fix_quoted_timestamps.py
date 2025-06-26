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


def fix_date_format_in_vault(vault_path):
    """
    遍历 Obsidian 库，查找指定属性，并将其值统一格式化为
    'YYYY-MM-DD HH:MM:SS' 格式的字符串。
    此版本能处理值为字符串或已为 date/datetime 对象的情况。
    """
    print(f"开始扫描并修正日期格式: {vault_path}\n")
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
                    with open(file_path, 'r', encoding='utf-8') as f:
                        post = frontmatter.load(f)

                    made_changes = False
                    corrected_attributes = []
                    attributes_to_check = ['created_time', 'last']

                    for attr in attributes_to_check:
                        original_value = post.metadata.get(attr)

                        if not original_value:
                            continue

                        # 跳过 Templater 动态命令
                        if isinstance(original_value, str) and '<%' in original_value:
                            continue

                        parsed_datetime = None
                        # 【核心修正】扩展逻辑以处理多种类型
                        # 情况1: 值是一个字符串，需要解析
                        if isinstance(original_value, str):
                            parsed_datetime = parse_flexible_date(original_value)
                        # 情况2: 值已是 date 或 datetime 对象 (由 frontmatter 自动解析)
                        elif isinstance(original_value, (datetime.datetime, datetime.date)):
                            parsed_datetime = original_value

                        # 如果成功获取了 datetime 对象，则进行格式化和检查
                        if parsed_datetime:
                            target_format_string = parsed_datetime.strftime('%Y-%m-%d %H:%M:%S')

                            # 检查是否需要更新：
                            # 1. 如果原始值不是字符串 (说明是date/datetime对象，需要转成字符串)
                            # 2. 或者原始值是字符串，但格式不正确
                            is_already_correct_string = isinstance(original_value,
                                                                   str) and original_value == target_format_string

                            if not is_already_correct_string:
                                post.metadata[attr] = target_format_string
                                made_changes = True
                                corrected_attributes.append(attr)

                        # 仅当原始值是字符串且无法解析时才警告
                        elif isinstance(original_value, str):
                            print(f"🟡  警告: 无法解析 '{attr}' 的值 '{original_value}' 在文件: {file_path}")

                    if made_changes:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(frontmatter.dumps(post))

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
VAULT_DIRECTORY = "E:\\yxt\\obsidian\\obsidian-note"  # Windows路径建议使用双反斜杠或原始字符串

# --- 运行脚本 ---
if __name__ == '__main__':
    if VAULT_DIRECTORY == "请在这里输入您的Obsidian库的绝对路径":
        print("❌ 错误：请先在脚本中设置您的 'VAULT_DIRECTORY' 变量！")
    else:
        fix_date_format_in_vault(VAULT_DIRECTORY)
