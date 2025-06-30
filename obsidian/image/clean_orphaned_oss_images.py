#!/usr/bin/env python3
"""
clean_orphaned_oss_images.py (v2 - 已修正解码方法)
扫描 Obsidian 库，找出其中链接的阿里云 OSS 图片，
然后对比 OSS Bucket 中的文件列表，删除未被引用的“孤立”图片。

在powershell命令行预设api key
$env:OSS_AK =""
$env:OSS_SK  =""

第一次先不加 --delete执行查看oss中已经没用的图片列表，第二次添加 --delete 执行删除。
python clean_orphaned_oss_images.py `
  --vault-path "E:\yxt\obsidian\obsidian-note" `
  --endpoint "oss-cn-beijing.aliyuncs.com" `
  --bucket "ember-grove" `
  --prefix "image/" `
  --delete
"""
import os
import re
import sys
import argparse
import oss2
import urllib.parse  # <-- 1. 导入正确的库


def extract_oss_links_from_vault(vault_path, bucket_name, endpoint):
    """
    遍历 Obsidian 库，提取所有阿里云 OSS 图片链接的对象密钥 (Object Key)。
    """
    url_pattern = re.compile(f"https://{re.escape(bucket_name)}\.{re.escape(endpoint)}/([^)\"']+)")

    used_keys = set()
    print(f"🔍 开始扫描 Obsidian 库: {vault_path}")

    if not os.path.isdir(vault_path):
        print(f"❌ 错误：提供的库路径 '{vault_path}' 不是一个有效的目录。")
        sys.exit(1)

    for root, _, files in os.walk(vault_path):
        if '.obsidian' in root:
            continue

        for file in files:
            if file.endswith('.md'):
                note_path = os.path.join(root, file)
                try:
                    with open(note_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        found_urls = url_pattern.findall(content)
                        for key in found_urls:
                            # <-- 2. 使用 urllib.parse.unquote 进行正确的 URL 解码
                            used_keys.add(urllib.parse.unquote(key))
                except Exception as e:
                    # 这个异常捕获现在主要用于处理文件读取等问题
                    print(f"  - 处理文件 {note_path} 时出错: {e}", file=sys.stderr)

    print(f"✅ 扫描完成。在 Obsidian 笔记中总共发现 {len(used_keys)} 个唯一的 OSS 图片引用。")
    return used_keys


def list_all_objects_in_oss(bucket, prefix=None):
    """
    列出 OSS Bucket 中指定前缀下的所有对象密钥。
    """
    print(f"\n☁️ 开始连接并获取 OSS Bucket '{bucket.bucket_name}' 中的文件列表...")
    if prefix:
        print(f"   (仅扫描前缀: '{prefix}')")

    remote_keys = set()
    for obj in oss2.ObjectIteratorV2(bucket, prefix=prefix):
        remote_keys.add(obj.key)

    print(f"✅ 获取完成。在 OSS 中总共发现 {len(remote_keys)} 个文件。")
    return remote_keys


def main():
    parser = argparse.ArgumentParser(description="清理 Obsidian 未引用的阿里云 OSS 图片。")
    parser.add_argument("--vault-path", required=True, help="你的 Obsidian 库的根目录路径。")
    parser.add_argument("--endpoint", required=True, help="OSS 的 Endpoint，例如：oss-cn-beijing.aliyuncs.com")
    parser.add_argument("--bucket", required=True, help="你的 OSS Bucket 名称。")
    parser.add_argument("--prefix", default="", help="要扫描的 OSS 目录前缀，例如 'images/'。留空则扫描整个 Bucket。")
    parser.add_argument("--ak", default=os.getenv("OSS_AK"), help="AccessKeyId (或使用环境变量 OSS_AK)")
    parser.add_argument("--sk", default=os.getenv("OSS_SK"), help="AccessKeySecret (或使用环境变量 OSS_SK)")
    parser.add_argument("--delete", action="store_true", help="执行删除操作。若不提供此参数，则仅进行预览。")
    args = parser.parse_args()

    if not args.ak or not args.sk:
        print("❌ 错误：AccessKey 未提供。请通过 --ak/--sk 参数或设置 OSS_AK/OSS_SK 环境变量来提供。")
        sys.exit(1)

    used_keys = extract_oss_links_from_vault(args.vault_path, args.bucket, args.endpoint)

    try:
        auth = oss2.Auth(args.ak, args.sk)
        bucket = oss2.Bucket(auth, f"https://{args.endpoint}", args.bucket)
        remote_keys = list_all_objects_in_oss(bucket, prefix=args.prefix)
    except Exception as e:
        print(f"\n❌ 连接到 OSS 或列出文件时出错: {e}", file=sys.stderr)
        sys.exit(1)

    orphaned_keys = remote_keys - used_keys

    if not orphaned_keys:
        print("\n🎉 恭喜！未在 OSS 中发现任何未被引用的孤立文件。")
        return

    print(f"\n🗑️ 发现 {len(orphaned_keys)} 个孤立文件（存在于 OSS 但未在 Obsidian 中被引用）：")
    for key in sorted(list(orphaned_keys)):
        print(f"  - {key}")

    if not args.delete:
        print("\n💡 当前为预览模式。要真正删除这些文件，请在运行时加入 `--delete` 参数。")
        return

    confirm = input(
        "\n⚠️ 你确定要永久删除上面列出的所有文件吗？此操作不可恢复！(请输入 'yes' 进行确认): ").strip().lower()
    if confirm != 'yes':
        print("操作已取消。")
        return

    print("\n▶️ 正在执行批量删除...")
    keys_to_delete = list(orphaned_keys)
    deleted_count = 0
    for i in range(0, len(keys_to_delete), 1000):
        chunk = keys_to_delete[i:i + 1000]
        result = bucket.batch_delete_objects(chunk)
        deleted_count += len(result.deleted_keys)
        print(f"  - 已成功删除 {len(result.deleted_keys)} 个文件。")

    print(f"\n✅ 删除完成！总共移除了 {deleted_count} 个孤立文件。")


if __name__ == "__main__":
    main()