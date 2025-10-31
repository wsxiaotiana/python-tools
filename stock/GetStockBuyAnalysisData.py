# -*- coding: utf-8 -*-
"""
稳定版（腾讯 gtimg 数据源；前低=结构位/波谷）
- 名称映射：qt.gtimg.cn
- 日K：web.ifzq.gtimg.cn fqkline（前复权/不复权可选）
- 昨收(Close)：基准日收盘（支持 today / yesterday）
- ATR10：SMA(TR,10)；可切换 ATR_METHOD='wilder'
- VOL10(万)：10日均量（万手）；VOL(万)：基准日（万手）
- 前高(P_res)：最近 lookback 天内【含基准日】最高价
- 前低(P_sup)：“结构位”（上一个明确波谷），在基准日前寻找已确认波谷
"""
import re
import pandas as pd
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
import argparse

# ===== 可改参数 =====
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
    "002747.SZ",  # 埃斯顿
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
# 你的股票列表
LOOKBACK_N = 20
USE_QFQ = True               # True=前复权，False=不复权
ATR_N = 10
ATR_METHOD = "sma"           # 'sma' 或 'wilder'
VOL_UNIT_DIVISOR = 1e4       # “万手” = 手 / 1e4
TIMEOUT = 6
BASE_DAY = "today"           # 新增：'today' 或 'yesterday'

# —— 结构位参数（前低/前高判断用）——
PIVOT_K = 3                  # 波谷/波峰左右各K根确认（常用3~5）
STRUCT_LOOKBACK = 120        # 近多少根内查找结构位
EXCLUDE_LATEST = True        # 前低只取“已确认”的上一波谷 -> 排除最后一根K线

# 网络与代理设置
DISABLE_SYSTEM_PROXY = True  # True=忽略系统代理
PROXIES = None               # {"http":"http://127.0.0.1:7890","https":"http://127.0.0.1:7890"}

def make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=4, connect=4, read=4,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "close",
    })
    if DISABLE_SYSTEM_PROXY:
        s.trust_env = False
    if PROXIES:
        s.proxies.update(PROXIES)
    return s

# ===== 代码与市场前缀 =====
def norm_code(code: str) -> str:
    m = re.search(r"(\d{6})", code)
    if not m:
        raise ValueError(f"无效代码: {code}")
    return m.group(1)

def to_symbol(code: str) -> str:
    up = code.upper()
    six = norm_code(up)
    if ".SH" in up or six.startswith(("5","6","9")):
        return f"sh{six}"
    return f"sz{six}"

# ===== 名称映射（腾讯 qt）=====
def get_name_map_tencent(codes_raw: list) -> dict:
    sess = make_session()
    symbols = [to_symbol(c) for c in codes_raw]
    out = {}
    for i in range(0, len(symbols), 60):
        batch = ",".join(symbols[i:i+60])
        url = f"https://qt.gtimg.cn/q={batch}"
        r = sess.get(url, timeout=TIMEOUT)
        r.encoding = "gbk"
        for line in r.text.strip().splitlines():
            if "~" in line:
                try:
                    body = line.split("=",1)[1].strip().strip('";')
                    parts = body.split("~")
                    name = parts[1]
                    code6 = parts[2].zfill(6)
                    out[code6] = name
                except Exception:
                    pass
    return out

# ===== 历史日K（腾讯 fqkline）=====
def fetch_hist_tencent(code_raw: str, use_qfq: bool=True, limit: int=1200) -> pd.DataFrame:
    """
    返回列：date, open, close, high, low, volume（volume单位：手）
    """
    sess = make_session()
    symbol = to_symbol(code_raw)
    adj = "qfq" if use_qfq else ""
    params = {"param": f"{symbol},day,,,{limit},{adj}"}
    bases = ["http://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
             "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"]
    last_err = None
    for base in bases:
        try:
            j = sess.get(base, params=params, timeout=TIMEOUT).json()
            data = j.get("data", {})
            node = data.get(symbol, {}) if data else {}
            arr = node.get("qfqday" if use_qfq else "day") or node.get("day")
            if not arr:
                raise RuntimeError(f"无K线数据: {code_raw} @ {base}")
            rows = []
            for it in arr:
                parts = it.split(",") if isinstance(it, str) else it
                date, op, cl, hi, lo, vol = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
                rows.append([date, op, cl, hi, lo, vol])
            df = pd.DataFrame(rows, columns=["date","open","close","high","low","volume"])
            for c in ["open","close","high","low","volume"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            df = df.dropna(subset=["close","high","low","volume"]).reset_index(drop=True)
            return df
        except Exception as e:
            last_err = e
            continue
    raise last_err if last_err else RuntimeError(f"腾讯K线拉取失败: {code_raw}")

# ===== ATR =====
def calc_tr(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr

def atr_series(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 10, method: str = "sma") -> pd.Series:
    tr = calc_tr(high, low, close)
    if method == "wilder":
        init = tr.rolling(n, min_periods=n).mean()
        ema = tr.ewm(alpha=1/n, adjust=False).mean()
        atr = init.copy()
        atr.iloc[n-1:] = ema.iloc[n-1:]
        return atr
    return tr.rolling(n, min_periods=n).mean()

# ===== 选择基准索引 =====
def choose_base_index(hist: pd.DataFrame, base_day: str) -> int:
    """
    返回用于计算的基准索引：
    - 'today'：最后一根K线
    - 'yesterday'：倒数第二根（若不足两根则回退到最后一根）
    """
    n = len(hist)
    if n == 0:
        raise RuntimeError("历史数据为空")
    if base_day == "yesterday" and n >= 2:
        return n - 2
    return n - 1

# ===== 结构位：波谷（前低）=====
def find_pivot_low(df: pd.DataFrame, k: int = 3, max_lookback: int = 120, exclude_last: bool = True):
    """
    返回： (前低价, 前低日期, 索引)
    定义：low[i] 严格小于 左右各 k 根的 low（避免平台/持平）
    搜索区间：最近 max_lookback 根，默认排除最后一根（只取已确认波谷）
    若未找到，回退为该区间的最小值
    """
    lows = df["low"].values
    n = len(lows)
    end = n - 1 if exclude_last else n   # 排除最后一根
    start = max(0, end - max_lookback - k - 1)

    pivot_idx = None
    for i in range(end - k - 1, start + k - 1, -1):
        left_min = np.min(lows[i - k:i])
        right_min = np.min(lows[i + 1:i + 1 + k])
        if np.isfinite(lows[i]) and lows[i] < left_min and lows[i] < right_min:
            pivot_idx = i
            break

    if pivot_idx is None:
        window = lows[start:end]
        if len(window) == 0:
            pivot_idx = n - 2 if n >= 2 else 0
        else:
            rel = int(np.nanargmin(window))
            pivot_idx = start + rel

    price = float(df.iloc[pivot_idx]["low"])
    date_ = str(df.iloc[pivot_idx]["date"])
    return price, date_, pivot_idx

# ===== 聚合 =====
def last_metrics(code_raw: str, name_map: dict, lookback: int=20, base_day: str="today") -> dict:
    hist = fetch_hist_tencent(code_raw, use_qfq=USE_QFQ)

    # ——裁剪到“基准日”——
    base_idx = choose_base_index(hist, base_day)
    hist_upto = hist.iloc[:base_idx+1].copy()
    base_date = str(hist_upto.iloc[-1]["date"])

    close = hist_upto["close"]; high = hist_upto["high"]; low = hist_upto["low"]; vol = hist_upto["volume"]

    # 均线（基准日最新值）
    ma5  = close.rolling(5).mean().iloc[-1]
    ma10 = close.rolling(10).mean().iloc[-1]
    ma20 = close.rolling(20).mean().iloc[-1]
    ma60 = close.rolling(60).mean().iloc[-1]

    # 前高（含基准日，取最近 LOOKBACK_N 的最高）
    p_res = high.iloc[-lookback:].max()

    # 前低（结构位：在基准日前寻找“已确认波谷”）
    p_sup_val, p_sup_date, _ = find_pivot_low(
        hist_upto, k=PIVOT_K, max_lookback=STRUCT_LOOKBACK, exclude_last=EXCLUDE_LATEST
    )

    # 昨收（基准日收盘）
    y_close = float(close.iloc[-1])

    # ATR10（基准日）
    atr_n = float(atr_series(high, low, close, n=ATR_N, method=ATR_METHOD).iloc[-1])

    # VOL10(万手) 与 基准日 VOL(万手)
    vol10 = vol.rolling(10).mean().iloc[-1] / VOL_UNIT_DIVISOR
    vol_last = float(vol.iloc[-1]) / VOL_UNIT_DIVISOR

    code6 = norm_code(code_raw)
    return {
        "代码": code6,
        "名称": name_map.get(code6, ""),
        "前高(P_res)": round(p_res, 3),
        "前低(P_sup)": round(p_sup_val, 3),   # 结构位（波谷）
        "MA5": round(ma5, 3),
        "MA10": round(ma10, 3),
        "MA20": round(ma20, 3),
        "MA60": round(ma60, 3),
        "昨收(Close)": round(y_close, 3),
        "ATR10": round(atr_n, 3),
        "VOL10(万)": round(vol10, 3),
        "VOL(万)": round(vol_last, 3),
        # 如需调试可加： "基准日期": base_date, "结构位日期": p_sup_date
    }

def parse_args():
    p = argparse.ArgumentParser(description="生成股票指标Excel（支持基准天数：today/yesterday）")
    p.add_argument("--base-day", choices=["today","yesterday"], default=BASE_DAY, help="基准天数（默认：today）")
    return p.parse_args()

def main():
    args = parse_args()
    base_day = args.base_day

    codes_raw = CODES[:]
    name_map = get_name_map_tencent(codes_raw)

    # ——保持与 CODES 完全一致的导出顺序——
    order_map = {norm_code(c): i for i, c in enumerate(codes_raw)}

    rows = []
    for code in codes_raw:
        rows.append(last_metrics(code, name_map, LOOKBACK_N, base_day=base_day))

    out = pd.DataFrame(rows, columns=[
        "代码","名称","前高(P_res)","前低(P_sup)",
        "MA5","MA10","MA20","MA60",
        "昨收(Close)","ATR10","VOL10(万)","VOL(万)"
    ])

    # 关键：按原 CODES 顺序排序，避免被其他排序打乱
    out["__order__"] = out["代码"].map(order_map)
    out.sort_values("__order__", inplace=True)
    out.drop(columns="__order__", inplace=True)

    # 确保“代码”文本格式且保留前导零
    out["代码"] = out["代码"].astype(str).str.zfill(6)

    suffix = "" if base_day == "today" else f"-{base_day}"
    fn = f"stock_metrics_{datetime.now().strftime('%Y%m%d')}{suffix}.xlsx"
    out.to_excel(fn, index=False)

    print(f"基准天数: {base_day} | 文件: {fn}")
    print(out)

if __name__ == "__main__":
    main()
