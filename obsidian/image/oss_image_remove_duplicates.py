#!/usr/bin/env python3
"""
oss_dedupe_etag.py (v3 - 带删除日志功能)
默认保留最新文件，并可记录待删除文件列表。

在powershell命令行预设api key
$env:OSS_AK =""
$env:OSS_SK  =""

第一步先不带 --delete,查询重复图片文件列表
python oss_image_remove_duplicates.py --endpoint oss-cn-beijing.aliyuncs.com --bucket ember-grove --prefix image/

第二步带 --delete执行删除，和 --log-deletions duplicates_to_delete.txt 并且导出相关笔记列表

python oss_image_remove_duplicates.py --endpoint oss-cn-beijing.aliyuncs.com --bucket ember-grove --prefix image/ --delete --log-deletions duplicates_to_delete.txt
"""
import oss2, argparse, collections, os, sys, time
from datetime import datetime, timezone


# (前面的辅助函数 fmt_ts, build_bucket 等保持不变，这里省略)
def fmt_ts(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def build_bucket(ep, ak, sk, bucket_name):
    auth = oss2.Auth(ak, sk)
    return oss2.Bucket(auth, f"https://{ep}", bucket_name)


def gather_objects(bucket, prefix=None):
    print("▶ 正在遍历对象列表 ...")
    it = oss2.ObjectIteratorV2(bucket, prefix=prefix)
    objs = []
    for obj in it:
        objs.append(obj)
    print(f"  总计 {len(objs)} 个对象")
    return objs


def group_by_md5(objs, skip_multipart=True):
    groups = collections.defaultdict(list)
    for obj in objs:
        etag = obj.etag.strip('"')
        if "-" in etag and skip_multipart:
            continue
        groups[etag].append(obj)
    return {md5: lst for md5, lst in groups.items() if len(lst) > 1}


def decide_keep(list_obj, rule="latest"):
    if rule == "oldest":
        return sorted(list_obj, key=lambda o: o.last_modified)[0]
    elif rule == "latest":
        return sorted(list_obj, key=lambda o: o.last_modified)[-1]
    else:
        return list_obj[0]


def main():
    parser = argparse.ArgumentParser(description="通过 ETag/MD5 对 OSS 文件进行去重")
    parser.add_argument("--endpoint", required=True, help="Bucket endpoint")
    parser.add_argument("--bucket", required=True, help="Bucket name")
    parser.add_argument("--ak", default=os.getenv("OSS_AK"), help="AccessKeyId (环境变量 OSS_AK)")
    parser.add_argument("--sk", default=os.getenv("OSS_SK"), help="AccessKeySecret (环境变量 OSS_SK)")
    parser.add_argument("--prefix", help="仅扫描指定前缀（目录）下的文件")
    parser.add_argument("--rule", choices=["oldest", "latest", "first"], default="latest",
                        help="在重复文件中，保留哪一个的规则 (默认: latest)")
    parser.add_argument("--delete", action="store_true", help="确认后删除重复文件")

    # --- 新增参数 ---
    parser.add_argument("--log-deletions", help="将待删除的文件名记录到指定文件")
    # ----------------

    args = parser.parse_args()

    if not args.ak or not args.sk:
        print("❌ AccessKey 未提供，可通过 --ak/--sk 或环境变量 OSS_AK/OSS_SK 设置")
        sys.exit(1)

    bucket = build_bucket(args.endpoint, args.ak, args.sk, args.bucket)
    objs = gather_objects(bucket, prefix=args.prefix)
    dup_groups = group_by_md5(objs)

    if not dup_groups:
        print("✅ 未发现重复文件")
        return

    # 收集待删除的文件列表
    files_to_delete = []
    print(f"\n⚠ 发现 {len(dup_groups)} 组重复文件：")
    for md5, lst in dup_groups.items():
        keep = decide_keep(lst, args.rule)
        print(f"\nMD5={md5} （保留 → {keep.key} @ {fmt_ts(keep.last_modified)}）")
        for obj in lst:
            if obj.key == keep.key:
                flag = "KEEP"
            else:
                flag = "DEL "
                files_to_delete.append(obj.key)  # 收集待删除的文件名
            print(f" {flag}  {obj.key:<60}  {fmt_ts(obj.last_modified)}")

    if not args.delete:
        print("\n💡 默认仅预览。若确认无误，重新运行时加入 --delete 即可执行删除。")
        return

    confirm = input("\n⚠ 确认删除上面标记为 DEL 的对象？(yes/no) ").strip().lower()
    if confirm != "yes":
        print("操作已取消。")
        return

    # 如果用户指定了日志文件，则在删除前写入
    if args.log_deletions:
        try:
            with open(args.log_deletions, 'w', encoding='utf-8') as f:
                for filename in files_to_delete:
                    f.write(filename + '\n')
            print(f"\n📝 待删除文件列表已保存至: {args.log_deletions}")
        except IOError as e:
            print(f"❌ 无法写入日志文件 {args.log_deletions}: {e}")

    # 真正删除
    print("\n▶ 正在删除 ...")
    deleted_count = 0
    result = bucket.batch_delete_objects(files_to_delete)
    deleted_count = len(result.deleted_keys)

    print(f"✅ 删除完成，共移除 {deleted_count} 个重复文件")


if __name__ == "__main__":
    main()