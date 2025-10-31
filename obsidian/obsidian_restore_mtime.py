import os
import datetime
import frontmatter
import io

# --- 配置 ---
DEFAULT_TIME = datetime.time(12, 0, 0)


def restore_file_timestamps(vault_path):
    """
    根据笔记元数据中的 'last' 或 'created_time' 属性，
    批量恢复文件的物理修改时间戳 (mtime)。

    【版本 3.0 - 兼容性修正版】
    - 修正了 `frontmatter.parse()` 返回值为元组 (tuple) 导致的 `AttributeError`。
    - 移除了对特定 `YAMLParseError` 的捕获，以兼容不同版本的 `python-frontmatter` 库。

    参数:
    vault_path (str): 您的Obsidian库的绝对路径。
    """
    print(f"开始扫描您的Obsidian库: {vault_path}\n")
    restored_files_count = 0
    skipped_files_count = 0
    error_files_count = 0

    for root, dirs, files in os.walk(vault_path):
        if '.trash' in dirs:
            dirs.remove('.trash')

        for file in files:
            if not file.endswith(".md"):
                continue

            file_path = os.path.join(root, file)

            try:
                with io.open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()

                # --- 核心修改 1：将返回的元组解包 ---
                # `frontmatter.parse` 返回一个元组 (metadata, content)
                # 我们将元数据部分赋值给 `metadata` 变量
                metadata, _ = frontmatter.parse(file_content)
                # --- 修改结束 ---

                final_datetime = None

                # 现在直接从解包后的 metadata 字典中获取值
                metadata_value = metadata.get('last') or metadata.get('created_time')

                if not metadata_value:
                    # 这条打印信息现在是准确的，因为文件已被读取但未被修改
                    # print(f"🟡  跳过 (缺少 'last' 或 'created_time'): {file_path}")
                    skipped_files_count += 1
                    continue

                if isinstance(metadata_value, datetime.datetime):
                    final_datetime = metadata_value
                elif isinstance(metadata_value, datetime.date):
                    final_datetime = datetime.datetime.combine(metadata_value, DEFAULT_TIME)
                elif isinstance(metadata_value, str):
                    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
                        try:
                            parsed_dt = datetime.datetime.strptime(metadata_value, fmt)
                            if fmt == '%Y-%m-%d':
                                final_datetime = datetime.datetime.combine(parsed_dt.date(), DEFAULT_TIME)
                            else:
                                final_datetime = parsed_dt
                            break
                        except ValueError:
                            continue

                if final_datetime:
                    target_timestamp = final_datetime.timestamp()
                    os.utime(file_path, (target_timestamp, target_timestamp))
                    print(f"✅  已恢复: {file_path} -> {final_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                    restored_files_count += 1
                else:
                    # 为了避免过多无关输出，可以选择注释掉这条
                    # print(f"🟡  跳过 (值无法处理): {file_path} | 值: '{metadata_value}' (类型: {type(metadata_value).__name__})")
                    skipped_files_count += 1

            # --- 核心修改 2：移除对特定 ParseError 的捕获 ---
            # 通用的 Exception 会捕获所有错误，包括可能的解析错误
            except Exception as e:
                print(f"❌  处理文件时发生错误: {file_path} | 错误: {e}")
                error_files_count += 1

    print("\n----------------------------------------")
    print("✨ 操作完成！")
    print(f"总共恢复了 {restored_files_count} 个文件的时间戳。")
    print(f"总共跳过了 {skipped_files_count} 个文件（无目标属性或值无法处理）。")
    if error_files_count > 0:
        print(f"处理过程中遇到了 {error_files_count} 个错误。")
    print("----------------------------------------")


# --- 配置您的Obsidian库路径 ---
VAULT_DIRECTORY = "E:\yxt\obsidian\obsidian-note"

# --- 运行脚本 ---
if __name__ == '__main__':
    if "请在这里输入" in VAULT_DIRECTORY:
        print("❌ 错误：请先在脚本中设置您的 'VAULT_DIRECTORY' 变量！")
    else:
        restore_file_timestamps(VAULT_DIRECTORY)