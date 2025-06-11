import os
import datetime
import frontmatter

# --- 配置：支持的日期/时间格式列表 ---
# 用于解析元数据中 'created' 和 'last' 的值
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
    使用预定义格式列表，尝试将字符串解析为 datetime 对象。
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


def add_datetime_attributes(vault_path):
    """
    为笔记添加 'created_time' 和 'modified_time' 属性。

    - 优先使用 'created'/'last' 的日期，结合文件系统的物理时间。
    - 输出为国际标准格式: YYYY-MM-DDTHH:MM:SS
    """
    print(f"开始扫描并添加完整时间戳属性: {vault_path}\n")
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
                    added_attributes = []

                    # 获取一次文件状态，提高效率
                    file_stat = os.stat(file_path)

                    # --- 1. 处理 created_time ---
                    if 'created_time' not in post.metadata:
                        source_date_val = post.metadata.get('created')
                        if source_date_val:
                            # 确定日期部分
                            if isinstance(source_date_val, datetime.datetime):
                                date_part = source_date_val.date()
                            elif isinstance(source_date_val, datetime.date):
                                date_part = source_date_val
                            else:  # 尝试作为字符串解析
                                parsed_dt = parse_flexible_date(source_date_val)
                                date_part = parsed_dt.date() if parsed_dt else None

                            if date_part:
                                # 确定时间部分 (来自文件系统)
                                try:
                                    creation_timestamp = file_stat.st_birthtime
                                except AttributeError:
                                    creation_timestamp = file_stat.st_ctime
                                time_part = datetime.datetime.fromtimestamp(creation_timestamp).time()

                                # 组合并赋值
                                full_datetime = datetime.datetime.combine(date_part, time_part)
                                post.metadata['created_time'] = full_datetime.isoformat(timespec='seconds')
                                made_changes = True
                                added_attributes.append('created_time')

                    # --- 2. 处理 modified_time (类似逻辑) ---
                    if 'modified_time' not in post.metadata:
                        source_date_val = post.metadata.get('last')
                        if source_date_val:
                            # 确定日期部分
                            if isinstance(source_date_val, datetime.datetime):
                                date_part = source_date_val.date()
                            elif isinstance(source_date_val, datetime.date):
                                date_part = source_date_val
                            else:
                                parsed_dt = parse_flexible_date(source_date_val)
                                date_part = parsed_dt.date() if parsed_dt else None

                            if date_part:
                                # 确定时间部分 (来自文件系统)
                                modification_timestamp = file_stat.st_mtime
                                time_part = datetime.datetime.fromtimestamp(modification_timestamp).time()

                                # 组合并赋值
                                full_datetime = datetime.datetime.combine(date_part, time_part)
                                post.metadata['modified_time'] = full_datetime.isoformat(timespec='seconds')
                                made_changes = True
                                added_attributes.append('modified_time')

                    # --- 3. 统一保存 ---
                    if made_changes:
                        with open(file_path, 'wb') as f:
                            frontmatter.dump(post, f)

                        print(f"✅  已更新: {file_path} (添加属性: {', '.join(added_attributes)})")
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
        add_datetime_attributes(VAULT_DIRECTORY)