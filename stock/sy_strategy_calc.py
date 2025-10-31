# -*- coding: utf-8 -*-
"""
多股票策略计算（通过脚本内置数组控制股票列表；不使用命令行）
- 用 CODES 指定要计算的股票代码列表（输出顺序与 CODES 完全一致）
- 每只股票内部按“日期”升序排列（无法解析时按原始顺序）
- 公式/口径与单股版保持一致，便于对表校核

依赖：pip install pandas numpy openpyxl xlsxwriter
"""

import os, math
from typing import Optional
import numpy as np
import pandas as pd

# ======================
# 顶部配置（仅改这里）
# ======================
CODES = [
    "002028.SZ",  # 思源电气
    "002335.SZ",  # 科华数据
    "002979.SZ",  # 雷赛智能
]

INPUT_FILE   = "data.xlsx"   # 可填 .xlsx 或 .csv；若留空(None)则使用内置示例
SHEET_NAME   = "Sheet1"         # 仅对 .xlsx 有效
OUTPUT_FILE  = "multi_calc.xlsx"
TOTAL_MINUTES = 240             # A股交易分钟数（用于盘中量能校正）
CFG = dict(
    ft_floor=0.0,
    vol_mult_break=1.5,
    vol_mult_dip=0.8,
    vol_mult_ma20=1.0,
    breakout_eps=0.001,   # 突破买1 = 前高*(1+0.1%)
    add_atr_break2=0.3,   # 突破买2 = 买1 + 0.3×ATR
    sl_atr_break=0.8,     # 突破SL = 前高 - 0.8×ATR
    dip_b1_atr=0.3,       # 低吸买1 = 前低 + 0.3×ATR
    dip_b2_atr=0.8,       # 低吸买2 = 前低 + 0.8×ATR
    dip_sl_atr=0.6,       # 低吸SL = 前低 - 0.6×ATR
    ma20_b_atr=0.2,       # 回踩买入 = MA20 - 0.2×ATR
    ma20_sl_atr=1.0,      # 回踩SL = MA20 - 1.0×ATR
    chand_k1=2.5,
    chand_k2=3.0,
    atr_min_pct=0.015,    # 1.5%
    atr_max_pct=0.06,     # 6.0%
    signal_threshold=70,
)

# 列名常量
C = {
    "date": "日期",
    "dow": "周几",
    "code": "代码",
    "name": "名称",
    "ok_buy": "是否适合买入",
    "signal": "策略信号",
    "pres": "前高(P_res)",
    "psup": "前低(P_sup)",
    "ma5": "MA5",
    "ma10": "MA10",
    "ma20": "MA20",
    "ma60": "MA60",
    "cost": "成本价",
    "max_entry": "入场以来最高价",
    "close": "昨收(Close)",
    "pnow": "实时报价(P_now)",
    "peval": "评估价(P_eval)",
    "atr": "ATR14",
    "vol10": "VOL10",
    "vol": "当日量(Vol)",
    "m_elapsed": "M_elapsed(分钟)",
    "ft": "f_t(盘中进度)",
    "rs10": "RS10",
    "vol10_15": "VOL10×1.5",
    "vol10_20": "VOL10×2.0",
    "lr": "量比(当日/10日)",
    "lr_adj": "量比_校正(盘中)",
    "atr_pct": "ATR%",
    "ma20_prev": "MA20_1(昨)",
    "ma20_up": "MA20 向上?",
    "s_ma": "S_ma",
    "rs10_ge0": "RS10≥0?",
    "dist_res": "距前高%",
    "dist_sup": "距前低%",
    "dist_ma20": "距MA20%",
    "hit_break": "突破条件达成?",
    "in_dip_band": "在低吸带?",
    "in_ma20_band": "MA20回踩带?",
    "hit_break_vol": "突破量能达成?",
    "hit_dip_vol": "低吸量能不萎缩?",
    "hit_ma20_vol": "回踩量能健康?",
    "chand_25": "保护线2.5(跌破止盈)",
    "chand_30": "保护线3.0(跌破止盈)",
    "bu_break1": "突破买1",
    "bu_break2": "突破买2",
    "sl_break": "突破SL",
    "R_break1": "R_突破1",
    "R1_break1": "R1_突破1",
    "R2_break1": "R2_突破1",
    "R3_break1": "R3_突破1",
    "R_break2": "R_突破2",
    "R1_break2": "R1_突破2",
    "R2_break2": "R2_突破2",
    "R3_break2": "R3_突破2",
    "bu_dip1": "低吸买1",
    "bu_dip2": "低吸买2",
    "sl_dip": "低吸SL",
    "R_dip1": "R_低吸1",
    "R1_dip1": "R1_低吸1",
    "R2_dip1": "R2_低吸1",
    "R3_dip1": "R3_低吸1",
    "R_dip2": "R_低吸2",
    "R1_dip2": "R1_低吸2",
    "R2_dip2": "R2_低吸2",
    "R3_dip2": "R3_低吸2",
    "bu_ma20": "回踩MA20买入",
    "sl_ma20": "回踩SL",
    "R_ma20": "R_MA20",
    "R1_ma20": "R1_MA20",
    "R2_ma20": "R2_MA20",
    "R3_ma20": "R3_MA20",
    "chand_sub_25": "Chand(2.5×ATR)减数",
    "chand_sub_30": "Chand(3×ATR)减数",
    "code_next": "_代码_下行",
    "is_last": "_is_last_for_code",
    "last_key": "_last_key",
    "atr_med": "ATR%_median_60",
    "atr_dyn_low": "ATR%_dyn_low",
    "atr_dyn_high": "ATR%_dyn_high",
    "score_break": "Score_突破",
    "score_dip": "Score_低吸",
    "score_ma20": "Score_MA20",
    "score": "策略分",
    "score_th": "阈值_分",
}

OUTPUT_COLS = [
    C["date"], C["dow"], C["code"], C["name"], C["ok_buy"], C["signal"],
    C["pres"], C["psup"], C["ma5"], C["ma10"], C["ma20"], C["ma60"],
    C["cost"], C["max_entry"], C["close"], C["pnow"], C["peval"],
    C["atr"], C["vol10"], C["vol"], C["m_elapsed"], C["ft"], C["rs10"],
    C["vol10_15"], C["vol10_20"], C["lr"], C["lr_adj"], C["atr_pct"],
    C["ma20_prev"], C["ma20_up"], C["s_ma"], C["rs10_ge0"], C["dist_res"],
    C["dist_sup"], C["dist_ma20"], C["hit_break"], C["in_dip_band"], C["in_ma20_band"],
    C["hit_break_vol"], C["hit_dip_vol"], C["hit_ma20_vol"], C["chand_25"], C["chand_30"],
    C["bu_break1"], C["bu_break2"], C["sl_break"],
    C["R_break1"], C["R1_break1"], C["R2_break1"], C["R3_break1"],
    C["R_break2"], C["R1_break2"], C["R2_break2"], C["R3_break2"],
    C["bu_dip1"], C["bu_dip2"], C["sl_dip"],
    C["R_dip1"], C["R1_dip1"], C["R2_dip1"], C["R3_dip1"],
    C["R_dip2"], C["R1_dip2"], C["R2_dip2"], C["R3_dip2"],
    C["bu_ma20"], C["sl_ma20"], C["R_ma20"], C["R1_ma20"], C["R2_ma20"], C["R3_ma20"],
    C["chand_sub_25"], C["chand_sub_30"], C["code_next"], C["is_last"], C["last_key"],
    C["atr_med"], C["atr_dyn_low"], C["atr_dyn_high"],
    C["score_break"], C["score_dip"], C["score_ma20"], C["score"], C["score_th"]
]

# ------------------ 工具函数 ------------------
def _norm_code(x: str) -> str:
    s = str(x).strip().upper()
    if '.' in s:
        return s
    # 不带后缀时自动推断交易所
    if s.startswith(("00", "30", "20")):  # 深市
        return s + ".SZ"
    if s.startswith(("60", "68")):        # 沪市
        return s + ".SH"
    return s

def _to_num(x) -> float:
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)): return np.nan
        if isinstance(x, str) and x.strip() == "": return np.nan
        return float(x)
    except Exception:
        return np.nan

def _ensure_cols(df: pd.DataFrame) -> pd.DataFrame:
    must_have = [C["date"], C["code"], C["name"], C["pres"], C["psup"],
                 C["ma5"], C["ma10"], C["ma20"], C["ma60"], C["close"],
                 C["atr"], C["vol10"], C["vol"], C["m_elapsed"]]
    missing = [c for c in must_have if c not in df.columns]
    if missing:
        raise ValueError(f"输入缺少必要列：{missing}")
    for col in set(OUTPUT_COLS):
        if col not in df.columns:
            df[col] = np.nan
    return df

def _format_and_save(df: pd.DataFrame, output_path: str):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Result")
        wb, ws = writer.book, writer.sheets["Result"]
        fmt_price = wb.add_format({"num_format": "0.00000"})
        fmt_ratio = wb.add_format({"num_format": "0.0000"})
        fmt_pct   = wb.add_format({"num_format": "0.00%"})
        fmt_int   = wb.add_format({"num_format": "0"})
        fmt_bool  = wb.add_format()
        price_keys = ["买", "SL", "R_", "R1_", "R2_", "R3_", "保护线", "Chand(", "MA20", "前高", "前低", "昨收", "评估价", "实时报价", "ATR14", "MA5", "MA10", "MA20_1", "MA60", "成本", "入场以来最高"]
        pct_cols   = [C["atr_pct"], C["dist_res"], C["dist_sup"], C["dist_ma20"], C["ft"], C["atr_dyn_low"], C["atr_dyn_high"]]
        ratio_cols = [C["lr"], C["lr_adj"]]
        int_cols   = [C["dow"], C["vol10"], C["vol10_15"], C["vol10_20"], C["m_elapsed"]]
        bool_cols  = [C["ma20_up"], C["rs10_ge0"], C["hit_break"], C["in_dip_band"], C["in_ma20_band"], C["hit_break_vol"], C["hit_dip_vol"], C["hit_ma20_vol"]]
        header = df.columns.tolist()
        for j, col in enumerate(header):
            if col in pct_cols: ws.set_column(j, j, 12, fmt_pct)
            elif col in ratio_cols: ws.set_column(j, j, 14, fmt_ratio)
            elif col in int_cols: ws.set_column(j, j, 10, fmt_int)
            elif col in bool_cols or col in [C["ok_buy"], C["signal"], C["code_next"], C["is_last"], C["last_key"], C["name"], C["code"], C["date"]]:
                ws.set_column(j, j, 14, fmt_bool)
            elif any(k in col for k in price_keys): ws.set_column(j, j, 16, fmt_price)
            else: ws.set_column(j, j, 14)

# ------------------ 核心计算 ------------------
def compute_row(row: pd.Series, ma20_prev_val: Optional[float]) -> pd.Series:
    r = row.copy()

    pres = _to_num(r.get(C["pres"]))
    psup = _to_num(r.get(C["psup"]))
    ma5  = _to_num(r.get(C["ma5"]))
    ma10 = _to_num(r.get(C["ma10"]))
    ma20 = _to_num(r.get(C["ma20"]))
    ma60 = _to_num(r.get(C["ma60"]))
    cost = _to_num(r.get(C["cost"]))
    max_entry = _to_num(r.get(C["max_entry"]))
    close = _to_num(r.get(C["close"]))
    pnow = _to_num(r.get(C["pnow"]))
    atr = _to_num(r.get(C["atr"]))
    vol10 = _to_num(r.get(C["vol10"]))
    vol = _to_num(r.get(C["vol"]))
    m_elapsed = _to_num(r.get(C["m_elapsed"]))
    rs10 = _to_num(r.get(C["rs10"]))
    atr_med = _to_num(r.get(C["atr_med"]))

    peval = pnow if not np.isnan(pnow) else close
    if np.isnan(m_elapsed): m_elapsed = TOTAL_MINUTES
    ft = min(1.0, max(CFG["ft_floor"], (m_elapsed or 0)/TOTAL_MINUTES))
    r[C["peval"]] = peval; r[C["ft"]] = ft

    r[C["vol10_15"]] = vol10*1.5 if not np.isnan(vol10) else np.nan
    r[C["vol10_20"]] = vol10*2.0 if not np.isnan(vol10) else np.nan
    r[C["lr"]] = (vol/vol10) if (not np.isnan(vol) and vol10 and vol10!=0) else np.nan
    r[C["lr_adj"]] = (vol/(vol10*ft)) if (not np.isnan(vol) and vol10 and vol10!=0 and ft>0) else np.nan
    r[C["atr_pct"]] = (atr/peval) if (not np.isnan(atr) and peval and peval!=0) else np.nan

    ma20_prev = ma20_prev_val if ma20_prev_val is not None else (ma20 if not np.isnan(ma20) else np.nan)
    r[C["ma20_prev"]] = ma20_prev
    r[C["ma20_up"]] = bool((not np.isnan(ma20)) and (not np.isnan(ma20_prev)) and (ma20 >= ma20_prev))

    s = 0
    if (not np.isnan(peval)) and (not np.isnan(ma5))  and (peval > ma5):  s += 1
    if (not np.isnan(peval)) and (not np.isnan(ma10)) and (peval > ma10): s += 1
    if (not np.isnan(peval)) and (not np.isnan(ma20)) and (peval > ma20): s += 1
    if (not np.isnan(ma5))   and (not np.isnan(ma10)) and (ma5 > ma10):   s += 1
    if (not np.isnan(ma10))  and (not np.isnan(ma20)) and (ma10 > ma20):  s += 1
    if (not np.isnan(ma20))  and (not np.isnan(ma60)) and (ma20 > ma60):  s += 1
    r[C["s_ma"]] = s
    r[C["rs10_ge0"]] = True if np.isnan(rs10) else bool(rs10 >= 0)

    r[C["dist_res"]] = ((peval - pres)/pres) if (not np.isnan(peval) and not np.isnan(pres) and pres!=0) else np.nan
    r[C["dist_sup"]] = ((peval - psup)/psup) if (not np.isnan(peval) and not np.isnan(psup) and psup!=0) else np.nan
    r[C["dist_ma20"]] = ((peval - ma20)/ma20) if (not np.isnan(peval) and not np.isnan(ma20) and ma20!=0) else np.nan

    # 买点/SL
    if not np.isnan(pres) and not np.isnan(atr):
        bu_break1 = pres*(1+CFG["breakout_eps"])
        bu_break2 = bu_break1 + CFG["add_atr_break2"]*atr
        sl_break  = pres - CFG["sl_atr_break"]*atr
    else:
        bu_break1 = bu_break2 = sl_break = np.nan

    if (not np.isnan(psup)) and (not np.isnan(atr)):
        bu_dip1 = psup + CFG["dip_b1_atr"] * atr
        bu_dip2 = psup + CFG["dip_b2_atr"] * atr
        sl_dip = psup - CFG["dip_sl_atr"] * atr
    else:
        bu_dip1 = bu_dip2 = sl_dip = np.nan

    if (not np.isnan(ma20)) and (not np.isnan(atr)):
        bu_ma20 = ma20 - CFG["ma20_b_atr"] * atr
        sl_ma20 = ma20 - CFG["ma20_sl_atr"] * atr
    else:
        bu_ma20 = sl_ma20 = np.nan

    r[C["bu_break1"]]=bu_break1; r[C["bu_break2"]]=bu_break2; r[C["sl_break"]]=sl_break
    r[C["bu_dip1"]]=bu_dip1; r[C["bu_dip2"]]=bu_dip2; r[C["sl_dip"]]=sl_dip
    r[C["bu_ma20"]]=bu_ma20; r[C["sl_ma20"]]=sl_ma20

    def _fill_R(base, sl, k):
        if np.isnan(base) or np.isnan(sl):
            r[k[0]]=r[k[1]]=r[k[2]]=r[k[3]]=np.nan; return
        R = base - sl
        r[k[0]]=R; r[k[1]]=base+1*R; r[k[2]]=base+2*R; r[k[3]]=base+3*R

    _fill_R(bu_break1, sl_break, (C["R_break1"], C["R1_break1"], C["R2_break1"], C["R3_break1"]))
    _fill_R(bu_break2, sl_break, (C["R_break2"], C["R1_break2"], C["R2_break2"], C["R3_break2"]))
    _fill_R(bu_dip1,   sl_dip,   (C["R_dip1"],   C["R1_dip1"],   C["R2_dip1"],   C["R3_dip1"]))
    _fill_R(bu_dip2,   sl_dip,   (C["R_dip2"],   C["R1_dip2"],   C["R2_dip2"],   C["R3_dip2"]))
    _fill_R(bu_ma20,   sl_ma20,  (C["R_ma20"],   C["R1_ma20"],   C["R2_ma20"],   C["R3_ma20"]))

    base_for_chand = max(x for x in [max_entry, close] if not np.isnan(x)) if not (np.isnan(max_entry) and np.isnan(close)) else np.nan
    if not np.isnan(base_for_chand) and not np.isnan(atr):
        r[C["chand_25"]] = base_for_chand - CFG["chand_k1"]*atr
        r[C["chand_30"]] = base_for_chand - CFG["chand_k2"]*atr
        r[C["chand_sub_25"]] = CFG["chand_k1"]*atr
        r[C["chand_sub_30"]] = CFG["chand_k2"]*atr
    else:
        r[C["chand_25"]] = r[C["chand_30"]] = r[C["chand_sub_25"]] = r[C["chand_sub_30"]] = np.nan

    r[C["hit_break"]] = bool((not np.isnan(peval)) and (not np.isnan(pres)) and (not np.isnan(bu_break1)) and (peval >= pres or peval >= bu_break1))
    lo, hi = (min(bu_dip1, bu_dip2), max(bu_dip1, bu_dip2)) if (not np.isnan(bu_dip1) and not np.isnan(bu_dip2)) else (np.nan, np.nan)
    r[C["in_dip_band"]] = bool((not np.isnan(peval)) and (not np.isnan(lo)) and (not np.isnan(hi)) and (lo <= peval <= hi))
    lo_m, hi_m = (bu_ma20, ma20) if (not np.isnan(bu_ma20) and not np.isnan(ma20)) else (np.nan, np.nan)
    r[C["in_ma20_band"]] = bool((not np.isnan(peval)) and (not np.isnan(lo_m)) and (not np.isnan(hi_m)) and (lo_m <= peval <= hi_m))

    def _hit(mult):
        if np.isnan(vol) or np.isnan(vol10) or vol10==0 or np.isnan(ft) or ft==0: return False
        return bool(vol >= mult*vol10*ft)

    r[C["hit_break_vol"]] = _hit(CFG["vol_mult_break"])
    r[C["hit_dip_vol"]]   = _hit(CFG["vol_mult_dip"])
    r[C["hit_ma20_vol"]]  = _hit(CFG["vol_mult_ma20"])

    # ATR 动态带（保留上下限常数）
    r[C["atr_dyn_low"]]  = CFG["atr_min_pct"]
    r[C["atr_dyn_high"]] = CFG["atr_max_pct"]

    base = s*10
    score_break = base + (20 if r[C["hit_break"]] else 0) + (10 if (r[C["hit_break"]] and r[C["hit_break_vol"]]) else 0)
    score_dip   = base + (20 if r[C["in_dip_band"]] else 0) + (10 if (r[C["in_dip_band"]] and r[C["hit_dip_vol"]]) else 0)
    score_ma20  = base + (20 if r[C["in_ma20_band"]] else 0) + (10 if (r[C["in_ma20_band"]] and r[C["hit_ma20_vol"]]) else 0)

    r[C["score_break"]] = score_break
    r[C["score_dip"]]   = score_dip
    r[C["score_ma20"]]  = score_ma20
    r[C["score"]]       = max(score_break, score_dip, score_ma20)
    r[C["score_th"]]    = CFG["signal_threshold"]

    sig = "无"
    if r[C["score"]] >= CFG["signal_threshold"]:
        if score_break >= CFG["signal_threshold"] and score_break >= max(score_dip, score_ma20):
            sig = "突破"
        elif score_dip >= CFG["signal_threshold"] and score_dip >= score_ma20:
            sig = "低吸"
        else:
            sig = "MA20回踩"
        ok = "是"
    else:
        ok = "否"
    r[C["signal"]] = sig
    r[C["ok_buy"]] = ok

    return r

# ------------------ 主流程 ------------------
def load_input_df() -> pd.DataFrame:
    if not INPUT_FILE:
        # —— 示例模式：为 CODES 中的每只股票各造一行 —— #
        name_map = {
            "002028.SZ": "思源电气",
            "002335.SZ": "科华数据",
            "002979.SZ": "雷赛智能",
        }
        base = {
            C["date"]: "2025-10-30",
            C["dow"]: 4,
            C["pres"]: 135.85, C["psup"]: 100.32,
            C["ma5"]: 124.606, C["ma10"]: 119.727, C["ma20"]: 113.132, C["ma60"]: 96.289,
            C["cost"]: 0, C["max_entry"]: 0,
            C["close"]: 133.76, C["pnow"]: 132.22,
            C["atr"]: 6.861, C["vol10"]: 10, C["vol"]: 13.142,
            C["m_elapsed"]: 89, C["rs10"]: 0,
            C["atr_med"]: np.nan,
        }
        rows = []
        for code in CODES:
            code_n = _norm_code(code)
            row = base.copy()
            row[C["code"]] = code_n
            row[C["name"]] = name_map.get(code_n, code_n)  # 无映射时用代码占位
            rows.append(row)
        return pd.DataFrame(rows)

    # —— 文件模式 —— #
    if INPUT_FILE.lower().endswith(".csv"):
        return pd.read_csv(INPUT_FILE)
    return pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME or 0)

def main():
    df = load_input_df()

    # 规范化输入里的代码，避免 002028 vs 002028.SZ 不匹配
    if C["code"] not in df.columns:
        raise ValueError("输入缺少【代码】列。")
    df[C["code"]] = df[C["code"]].apply(_norm_code)
    codes_norm = [_norm_code(c) for c in CODES]

    df = _ensure_cols(df)

    # 仅保留目标代码
    df = df[df[C["code"]].isin(codes_norm)].copy()

    # 解析日期并排序：先按 CODES 顺序，再按日期升序（解析失败按原顺序）
    dt = pd.to_datetime(df[C["date"]], errors="coerce")
    df["_sort_dt"] = dt
    df["_orig_idx"] = np.arange(len(df))
    df[C["code"]] = pd.Categorical(df[C["code"]], categories=codes_norm, ordered=True)
    df = df.sort_values(by=[C["code"], "_sort_dt", "_orig_idx"], kind="stable").reset_index(drop=True)

    # —— 后续计算逻辑不变 —— #
    out_rows = []
    prev_ma20 = {}
    for _, row in df.iterrows():
        code = str(row.get(C["code"]))
        prev_val = prev_ma20.get(code)
        new_row = compute_row(row, prev_val)
        cur_ma20 = _to_num(new_row.get(C["ma20"]))
        if not np.isnan(cur_ma20):
            prev_ma20[code] = cur_ma20
        out_rows.append(new_row)

    df_out = pd.DataFrame(out_rows)

    codes = df_out[C["code"]].astype(str).tolist()
    next_codes = codes[1:] + [""]
    df_out[C["code_next"]] = next_codes
    df_out[C["is_last"]] = (df_out[C["code"]].astype(str) != df_out[C["code_next"]]).astype(int)
    df_out[C["last_key"]] = np.where(df_out[C["is_last"]] == 1, df_out[C["code"]].astype(str) + "|LAST", "")

    for col in OUTPUT_COLS:
        if col not in df_out.columns:
            df_out[col] = np.nan
    df_out = df_out[OUTPUT_COLS]

    _format_and_save(df_out, OUTPUT_FILE)
    print(f"已生成：{os.path.abspath(OUTPUT_FILE)}")
    print(f"行数: {len(df_out)}, 股票数: {df_out[C['code']].astype(str).nunique()}, 日期范围: {df_out[C['date']].min()} ~ {df_out[C['date']].max()}")

if __name__ == "__main__":
    main()
