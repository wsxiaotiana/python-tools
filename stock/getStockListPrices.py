# -*- coding: utf-8 -*-
import re
import requests
from requests.adapters import HTTPAdapter, Retry
from datetime import datetime

# === 在这里填你要查询的股票 ===
CODES = [
    "002028.SZ",  # 思源电气
    "002335.SZ",  # 科华数据
    "002979.SZ",  # 雷赛智能
    "603083.SH",  # 剑桥科技
    "601138.SH",  # 工业富联
    "600183.SH",  # 生益科技
    "002463.SZ",  # 沪电股份
    "002475.SZ",  # 立讯精密
    "002460.SZ",  # 赣锋锂业
    "002074.SZ",  # 国轩高科
    "600580.SH",  # 卧龙电驱
    "601136.SH",  # 首创证券
    "601126.SH",  # 四方股份
    "002050.SZ",  # 三花智控
    "002709.SZ",  # 天赐材料
    "601899.SH",  # 紫金矿业
    "601600.SH",  # 中国铝业
    "000807.SZ",  # 云铝股份
    "002532.SZ",  # 天山铝业
    "002156.SZ",  # 通富微电
    "002407.SZ",  # 多氟多
    "600111.SH",  # 北方稀土

    # 追加的新股票（按你提供的名称顺序，已去重）
    "600021.SH",  # 上海电力
    "600403.SH",  # 大有能源
    "603026.SH",  # 石大胜华
    "603993.SH",  # 洛阳钼业
    "002759.SZ",  # 天际股份
    "600549.SH",  # 厦门钨业
    "002549.SZ",  # 凯美特气
    "002409.SZ",  # 雅克科技
    "603986.SH",  # 兆易创新
    "600895.SH",  # 张江高科
]
# 输出顺序严格按此列表

def norm6(code: str) -> str:
    m = re.search(r"(\d{6})", code)
    if not m:
        raise ValueError(f"无效代码: {code}")
    return m.group(1)

def to_sina_symbol(code: str) -> str:
    c6 = norm6(code)
    return ("sh" if code.upper().endswith(".SH") else "sz") + c6

def fetch_by_akshare(codes6_set):
    """优先用 AkShare 批量抓全市场行情，再本地筛选。"""
    try:
        import akshare as ak
        import pandas as pd
        df = ak.stock_zh_a_spot_em()  # 可能偶发断线
        df["代码"] = df["代码"].astype(str).str.zfill(6)
        sub = df.loc[df["代码"].isin(codes6_set), ["代码", "名称", "最新价"]].set_index("代码")
        out = {}
        for c6, row in sub.iterrows():
            name = str(row["名称"])
            price = row["最新价"]
            if pd.isna(price):
                price_str = ""
            else:
                price_str = str(price)
            out[c6] = (name, price_str)
        return out
    except Exception:
        return None  # 失败则走备用源

def fetch_by_sina(codes: list):
    """备用：新浪行情（GBK 编码）。"""
    sess = requests.Session()
    retry = Retry(
        total=3, connect=3, read=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"])
    )
    sess.mount("http://", HTTPAdapter(max_retries=retry))
    sess.mount("https://", HTTPAdapter(max_retries=retry))

    syms = [to_sina_symbol(c) for c in codes]
    out = {}
    for i in range(0, len(syms), 60):
        batch = syms[i:i+60]
        url = "https://hq.sinajs.cn/list=" + ",".join(batch)
        r = sess.get(
            url,
            headers={
                "Referer": "https://finance.sina.com.cn",
                "User-Agent": "Mozilla/5.0"
            },
            timeout=(5, 10)
        )
        r.encoding = "gbk"
        for line in r.text.strip().splitlines():
            # var hq_str_sh600000="浦发银行,开盘,昨收,现价,最高,最低,...";
            m = re.match(r'var hq_str_(sh|sz)(\d{6})="([^"]*)";', line)
            if not m:
                continue
            c6 = m.group(2)
            payload = m.group(3)
            if not payload:
                out[c6] = ("", "")
                continue
            parts = payload.split(",")
            if len(parts) >= 4:
                name = parts[0].strip()
                price = parts[3].strip()  # 现价
            else:
                name, price = "", ""
            out[c6] = (name, price)
    return out

def main():
    codes6 = [norm6(c) for c in CODES]
    need_set = set(codes6)

    mapping = fetch_by_akshare(need_set)
    if mapping is None:
        mapping = fetch_by_sina(CODES)

    fetch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 第一行：获取时间；第二行：表头；其后每只股票（严格按 CODES 顺序）
    print(f"获取时间：{fetch_time}")
    print("股票名称\t价格")
    for code in CODES:
        c6 = norm6(code)
        if c6 in mapping:
            name, price = mapping[c6]
            name = name or code
            price = "" if price in (None, "None", "nan") else str(price)
        else:
            name, price = code, ""
        print(f"{name}\t{price}")

if __name__ == "__main__":
    main()
