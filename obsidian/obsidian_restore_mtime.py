import os
import datetime
import frontmatter

# --- 配置 ---
# 当元数据中只有日期时，使用这个默认时间来创建完整的时间戳。
# "12:00:00" 是一个中性且安全的选择。
DEFAULT_TIME = datetime.time(12, 0, 0)


def restore_file_timestamps(vault_path):
    """
    根据笔记元数据中的 'last_modified' 或 'created_time' 属性，
    批量恢复文件的物理修改时间戳 (mtime)。

    恢复逻辑:
    1.  优先使用元数据中的 'last' 属性，如果不存在则使用 'created_time'。
    2.  根据值的类型（datetime对象、date对象或字符串）进行相应处理。
    3.  如果是字符串，会尝试多种常见格式进行解析。
    4.  使用生成的时间戳来更新文件的访问时间 (atime) 和修改时间 (mtime)。

    参数:
    vault_path (str): 您的Obsidian库的绝对路径。
    """
    print(f"开始扫描您的Obsidian库: {vault_path}\n")
    restored_files_count = 0
    skipped_files_count = 0
    error_files_count = 0

    for root, dirs, files in os.walk(vault_path):
        # 跳过 .trash 文件夹
        if '.trash' in dirs:
            dirs.remove('.trash')

        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)

                try:
                    post = frontmatter.load(file_path)
                    metadata_value = None
                    final_datetime = None

                    # 优先从 'last' 属性获取，然后从 'created_time' 获取
                    # 注意：根据您的描述，属性键是 'last' 和 'created_time'
                    metadata_value = post.metadata.get('last') or post.metadata.get('created_time')

                    if metadata_value:
                        # --- 修改后的核心逻辑 ---
                        if isinstance(metadata_value, datetime.datetime):
                            # 1. 如果元数据是完整的 datetime 对象，直接使用
                            final_datetime = metadata_value
                        elif isinstance(metadata_value, datetime.date):
                            # 2. 如果元数据只是 date 对象，附加默认时间
                            final_datetime = datetime.datetime.combine(metadata_value, DEFAULT_TIME)
                        elif isinstance(metadata_value, str):
                            # 3. 如果是字符串，尝试按多种格式解析
                            try:
                                # **第一优先级：** 尝试您提供的格式 'YYYY-MM-DD HH:MM:SS'
                                final_datetime = datetime.datetime.strptime(metadata_value, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                # 第二优先级：尝试 ISO 格式 (例如 'YYYY-MM-DDTHH:MM:SS')
                                try:
                                    final_datetime = datetime.datetime.fromisoformat(metadata_value)
                                except ValueError:
                                    # 第三优先级：尝试只解析日期 'YYYY-MM-DD'
                                    try:
                                        target_date = datetime.datetime.strptime(metadata_value, '%Y-%m-%d').date()
                                        final_datetime = datetime.datetime.combine(target_date, DEFAULT_TIME)
                                    except ValueError:
                                        # 如果所有格式都失败，则跳过
                                        print(f"🟡  跳过 (日期格式无法识别): {file_path} | 值为: '{metadata_value}'")
                                        skipped_files_count += 1
                                        continue
                        else:
                            # 如果是其他无法处理的类型，则跳过
                            print(f"🟡  跳过 (元数据类型不支持): {file_path} | 类型为: {type(metadata_value)}")
                            skipped_files_count += 1
                            continue
                        # --- 逻辑修改结束 ---

                        # 使用 os.utime 来更新文件的访问和修改时间
                        # 在Windows上，修改时间(st_mtime)和访问时间(st_atime)都可以通过这种方式设置
                        target_timestamp = final_datetime.timestamp()
                        os.utime(file_path, (target_timestamp, target_timestamp))

                        print(f"✅  已恢复时间戳: {file_path} -> {final_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                        restored_files_count += 1
                    else:
                        print(f"🟡  跳过 (缺少 'last' 或 'created_time' 属性): {file_path}")
                        skipped_files_count += 1

                except Exception as e:
                    print(f"❌  处理文件时出错: {file_path} | 错误: {e}")
                    error_files_count += 1

    print("\n----------------------------------------")
    print("✨ 操作完成！")
    print(f"总共恢复了 {restored_files_count} 个文件的时间戳。")
    print(f"总共跳过了 {skipped_files_count} 个文件。")
    if error_files_count > 0:
        print(f"处理了 {error_files_count} 个错误。")
    print("----------------------------------------")


# --- 配置您的Obsidian库路径 ---
# ⚠️ 请将下面的路径替换为您自己库的绝对路径。
# Windows示例: "C:\\Users\\YourUser\\Documents\\ObsidianVault"
# macOS/Linux示例: "/Users/YourUser/Documents/ObsidianVault"

VAULT_DIRECTORY = "E:\\yxt\\obsidian\\obsidian-note" # 注意：在Python中，建议使用双反斜杠'\\'或正斜杠'/'作为路径分隔符

# --- 运行脚本 ---
if __name__ == '__main__':
    if VAULT_DIRECTORY == "请在这里输入您的Obsidian库的绝对路径":
        print("❌ 错误：请先在脚本中设置您的 'VAULT_DIRECTORY' 变量！")
    else:
        restore_file_timestamps(VAULT_DIRECTORY)