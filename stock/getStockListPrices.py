# -*- coding: utf-8 -*-
"""
实时价格 + 盘中量比（VOL10 来自腾讯 fqkline，与“稳定版”脚本一致）
- 价格/当日量：新浪 (hq.sinajs.cn)；当日量单位=股 -> 换算为“手”（/100）
- VOL10（手）：腾讯 fqkline（前复权可选），按“基准日”口径取到昨日为止的10日均量
- 盘中进度 ft：A股时段(9:30-11:30, 13:00-15:00)，可设最小夹值避免早盘极端放大
- 输出：获取时间 + “股票名称\t价格\t盘中量比”
"""
import re
import math
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, time, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from zoneinfo import ZoneInfo  # py>=3.9
except Exception:
    ZoneInfo = None

# ========= 配置 =========
CODES = [
    # AI算力（服务器/IDC/散热/光模块/PCB/连接器/封测/UPS）
    "603019.SH",  # 中科曙光
    "601138.SH",  # 工业富联
    "603881.SH",  # 数据港
    "002837.SZ",  # 英维克
    "002156.SZ",  # 通富微电
    "600183.SH",  # 生益科技
    "002463.SZ",  # 沪电股份
    "002916.SZ",  # 深南电路
    "002475.SZ",  # 立讯精密
    "002281.SZ",  # 光迅科技
    "600487.SH",  # 亨通光电
    "603986.SH",  # 兆易创新
    "002518.SZ",  # 科士达
    "002335.SZ",  # 科华数据

    # 电网数字化/特高压
    "603556.SH",  # 海兴电力
    "601567.SH",  # 三星医疗
    "600268.SH",  # 国电南自
    "601877.SH",  # 正泰电器
    "000400.SZ",  # 许继电气
    "600312.SH",  # 平高电气
    "600406.SH",  # 国电南瑞
    "601126.SH",  # 四方股份
    "601179.SH",  # 中国西电
    "603530.SH",  # 神马电力
    "002270.SZ",  # 华明装备
    "002028.SZ",  # 思源电气
    "600089.SH",  # 特变电工
    "600885.SH",  # 宏发股份

    # 航天军工/低空经济/通信
    "601698.SH",  # 中国卫通
    "600118.SH",  # 中国卫星
    "002389.SZ",  # 航天彩虹
    "002111.SZ",  # 威海广泰

    # 消费电子/渠道/ODM/结构件
    "600745.SH",  # 闻泰科技
    "002241.SZ",  # 歌尔股份
    "605133.SH",  # 华勤技术
    "002600.SZ",  # 领益智造
    "002624.SZ",  # 完美世界

    # 机器人/工控
    "000559.SZ",  # 万向钱潮
    "002050.SZ",  # 三花智控
    "601100.SH",  # 恒立液压
    "002979.SZ",  # 雷赛智能
    "603416.SH",  # 信捷电气
    "603728.SH",  # 鸣志电器
    "603283.SH",  # 赛腾股份
    "600592.SH",  # 龙溪股份

    # 有色/资源
    "600111.SH",  # 北方稀土
    "600366.SH",  # 宁波韵升
    "600392.SH",  # 盛和资源
    "601600.SH",  # 中国铝业
    "000807.SZ",  # 云铝股份
    "002532.SZ",  # 天山铝业
    "000612.SZ",  # 焦作万方
    "601899.SH",  # 紫金矿业
    "603993.SH",  # 洛阳钼业
    "603799.SH",  # 华友钴业
    "600549.SH",  # 厦门钨业

    # 锂电/材料
    "002466.SZ",  # 天齐锂业
    "002460.SZ",  # 赣锋锂业
    "002074.SZ",  # 国轩高科
    "002709.SZ",  # 天赐材料
    "603026.SH",  # 石大胜华
    "002759.SZ",  # 天际股份
    "002407.SZ",  # 多氟多

    # 智能电动车
    "601689.SH",  # 拓普集团
    "605255.SH",  # 天普股份

    # 公用事业/风电/核电
    "601985.SH",  # 中国核电
    "003816.SZ",  # 中国广核
    "600021.SH",  # 上海电力
    "002202.SZ",  # 金风科技

    # 金融/软件/环保
    "601211.SH",  # 国泰海通
    "601009.SH",  # 南京银行
    "600797.SH",  # 浙大网新

    # 半导体特气/化学品/医药
    "002549.SZ",  # 凯美特气
    "002409.SZ",  # 雅克科技
    "600867.SH",  # 通化东宝

    # 新增
    "600057.SH",  # 厦门象屿
    "600593.SH",  # 大连圣亚
    "000555.SZ",  # 神州信息
]
USE_QFQ = True                  # 腾讯K线是否用前复权
KLINE_LIMIT = 260               # fqkline 取多少根（足够算10日均量即可）
REQ_TIMEOUT = 5                 # 单请求超时（秒）
RETRY_TOTAL = 2                 # 重试次数（腾讯/新浪）
CONCURRENCY = 12                # 并发抓K线
BASE_DAY_FOR_VOL10 = "yesterday"  # 'today' or 'yesterday'，盘中推荐 'yesterday'

FT_MIN_CLAMP = 0.03             # 盘中进度最小夹值（早盘避免量比极端放大）
PRINT_DEBUG  = False            # 打印调试日志
DISABLE_SYSTEM_PROXY = True     # 忽略系统代理（如需走系统代理改为 False）
PROXIES = None                  # 也可自定义: {"http":"http://127.0.0.1:7890","https":"http://127.0.0.1:7890"}

# ========= 公共函数 =========
def norm6(code: str) -> str:
    m = re.search(r"(\d{6})", code)
    if not m:
        raise ValueError(f"无效代码: {code}")
    return m.group(1)

def to_sina_symbol(code: str) -> str:
    c6 = norm6(code)
    return ("sh" if code.upper().endswith(".SH") else "sz") + c6

def to_tencent_symbol(code: str) -> str:
    c6 = norm6(code)
    if code.upper().endswith(".SH") or c6.startswith(("5","6","9")):
        return f"sh{c6}"
    return f"sz{c6}"

def make_session():
    s = requests.Session()
    retry = Retry(
        total=RETRY_TOTAL, connect=RETRY_TOTAL, read=RETRY_TOTAL,
        backoff_factor=0.4,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Connection": "close"
    })
    if DISABLE_SYSTEM_PROXY:
        s.trust_env = False
    if PROXIES:
        s.proxies.update(PROXIES)
    return s

# ========= 盘中进度 =========
def trading_progress_now() -> float:
    """A股盘中进度 ft∈[0,1]，午休固定 0.5；盘后为 1.0。"""
    try:
        now = datetime.now(ZoneInfo("Asia/Shanghai")) if ZoneInfo else datetime.utcnow() + timedelta(hours=8)
    except Exception:
        now = datetime.utcnow() + timedelta(hours=8)
    t = now.time()
    am_start, am_end = time(9,30), time(11,30)
    pm_start, pm_end = time(13,0), time(15,0)
    total = 240  # 分钟

    if t < am_start:
        return 0.0
    if am_start <= t <= am_end:
        elapsed = (t.hour*60 + t.minute) - (9*60 + 30)
        return max(0.0, min(1.0, elapsed/total))
    if am_end < t < pm_start:
        return 120/total
    if pm_start <= t <= pm_end:
        elapsed = 120 + (t.hour*60 + t.minute - 13*60)
        return max(0.0, min(1.0, elapsed/total))
    return 1.0

# ========= 新浪：价格 + 当日量(股) =========
def fetch_price_and_vol_hand_by_sina(codes: list) -> dict:
    """
    返回 {c6: {"name": 名称, "price": "现价", "vol_hand": 当日量(手)}}
    """
    sess = make_session()
    syms = [to_sina_symbol(c) for c in codes]
    out = {}
    for i in range(0, len(syms), 60):
        batch = syms[i:i+60]
        url = "https://hq.sinajs.cn/list=" + ",".join(batch)
        r = sess.get(url, headers={"Referer": "https://finance.sina.com.cn"}, timeout=REQ_TIMEOUT)
        r.encoding = "gbk"
        for line in r.text.strip().splitlines():
            m = re.match(r'var hq_str_(sh|sz)(\d{6})="([^"]*)";', line)
            if not m:
                continue
            c6 = m.group(2)
            payload = m.group(3)
            parts = payload.split(",")
            name, price, vol_hand = "", "", None
            if len(parts) >= 9:
                name = parts[0].strip()
                price = parts[3].strip()  # 现价
                try:
                    vol_shares = float(parts[8].strip())  # 成交量（股）
                    vol_hand = vol_shares / 100.0
                except Exception:
                    vol_hand = None
            out[c6] = {"name": name, "price": price, "vol_hand": vol_hand}
    return out

# ========= 腾讯 fqkline（日K，复用“稳定版”口径） =========
def fetch_hist_tencent(code_raw: str, use_qfq: bool=True, limit: int=1200) -> list:
    """
    返回数组 rows: [[date, open, close, high, low, volume], ...]
    volume 单位=手
    """
    symbol = to_tencent_symbol(code_raw)
    adj = "qfq" if use_qfq else ""
    params = {"param": f"{symbol},day,,,{limit},{adj}"}
    bases = ["http://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
             "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"]
    last_err = None
    for base in bases:
        try:
            sess = make_session()
            j = sess.get(base, params=params, timeout=REQ_TIMEOUT).json()
            data = j.get("data", {}) or {}
            node = data.get(symbol, {}) or {}
            arr = node.get("qfqday" if use_qfq else "day") or node.get("day")
            if not arr:
                raise RuntimeError("empty kline")
            rows = []
            for it in arr:
                parts = it.split(",") if isinstance(it, str) else it
                if len(parts) < 6:
                    continue
                rows.append([parts[0], float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5])])
            return rows
        except Exception as e:
            last_err = e
            continue
    raise last_err if last_err else RuntimeError(f"kline failed: {code_raw}")

def choose_base_index(n: int, base_day: str) -> int:
    if n <= 0:
        return 0
    if base_day == "yesterday" and n >= 2:
        return n - 2
    return n - 1

def calc_vol10_hand_from_rows(rows: list, base_day: str="yesterday") -> float:
    """
    rows: [[date, open, close, high, low, volume(手)], ...]
    返回：到“基准日”为止的 10 日均量（手）
    """
    if not rows:
        return float("nan")
    base_idx = choose_base_index(len(rows), base_day)
    # 取到基准日（含）
    vols = [r[5] for r in rows[:base_idx+1] if len(r) >= 6]
    if len(vols) < 10:
        return float("nan")
    # 取最近10个（基准日含在内）
    last10 = vols[-10:]
    return float(sum(last10) / 10.0)

def build_vol10_map_tencent_concurrent(codes: list, use_qfq: bool=True, base_day: str="yesterday") -> dict:
    """
    并发抓腾讯K线，返回 {c6: vol10_hand}
    """
    out = {}
    if not codes:
        return out

    def worker(code):
        try:
            rows = fetch_hist_tencent(code, use_qfq=use_qfq, limit=KLINE_LIMIT)
            vol10 = calc_vol10_hand_from_rows(rows, base_day=base_day)
            if PRINT_DEBUG:
                print(f"[DBG-vol10] {code} via tencent: {vol10}", flush=True)
            return norm6(code), vol10
        except Exception as e:
            if PRINT_DEBUG:
                print(f"[DBG-vol10-err] {code}: {e}", flush=True)
            return norm6(code), float("nan")

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futs = [ex.submit(worker, code) for code in codes]
        for fu in as_completed(futs):
            c6, v = fu.result()
            out[c6] = v
    return out

# ========= 主流程 =========
def main():
    try:
        fetch_time = (datetime.now(ZoneInfo("Asia/Shanghai")) if ZoneInfo else datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        fetch_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    print(f"获取时间：{fetch_time}")
    print("股票名称\t价格\t盘中量比")

    if not CODES:
        return

    # 1) 新浪：名称、现价、当日量(手)
    sina_map = fetch_price_and_vol_hand_by_sina(CODES)

    # 2) 腾讯：VOL10(手) 口径与“稳定版”一致（到“昨日”为止）
    vol10_map = build_vol10_map_tencent_concurrent(CODES, use_qfq=USE_QFQ, base_day=BASE_DAY_FOR_VOL10)

    # 3) 盘中进度
    ft = trading_progress_now()
    ft_eff = max(FT_MIN_CLAMP, ft) if 0.0 < ft < 1.0 else ft  # 盘中用夹值；盘前0/盘后1不动

    # 4) 输出
    for code in CODES:
        c6 = norm6(code)
        row = sina_map.get(c6, {})
        name = row.get("name") or code
        price = row.get("price") or ""
        vol_hand = row.get("vol_hand", None)
        vol10 = vol10_map.get(c6, float("nan"))

        lb = ""
        if vol_hand is not None and isinstance(vol_hand, (int, float)) and vol_hand == vol_hand \
           and isinstance(vol10, (int, float)) and vol10 == vol10 and vol10 > 0 and ft_eff > 0:
            lb_val = vol_hand / (vol10 * ft_eff)
            # 容错：极端值截断到 4 位小数
            if math.isfinite(lb_val) and lb_val >= 0:
                lb = f"{lb_val:.3f}"
        if PRINT_DEBUG:
            bad = (vol_hand is None, not (isinstance(vol10, (int,float)) and vol10==vol10 and vol10>0), ft_eff<=0)
            print(f"[DBG] {name}: ft={ft:.3f} eff={ft_eff:.3f} vol_hand={vol_hand} vol10={vol10} bad={bad}", flush=True)

        print(f"{name}\t{price}\t{lb}")

if __name__ == "__main__":
    main()
