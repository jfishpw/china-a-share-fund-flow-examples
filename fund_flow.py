#!/usr/bin/env python3
"""拉取 A股主力资金流向。

用法：
    export APIFY_TOKEN=your_token

    # 全市场快照
    python fund_flow.py --market

    # 指定股票
    python fund_flow.py 002112 600519

    # 历史资金流
    python fund_flow.py --history 600519 --days 30
"""
from __future__ import annotations

import os
import sys

from apify_client import ApifyClient

ACTOR = "jfishpw/china-a-share-fund-flow"


def fmt_yi(v: float | None) -> str:
    return "-" if v is None else f"{v / 1e8:+.2f}亿"


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1

    token = os.environ.get("APIFY_TOKEN")
    if not token:
        print("缺少 APIFY_TOKEN 环境变量")
        return 1

    client = ApifyClient(token)

    if "--market" in args:
        run_input = {"mode": "market"}
    elif "--history" in args:
        idx = args.index("--history")
        codes = [args[idx + 1]] if idx + 1 < len(args) else []
        days = 30
        if "--days" in args:
            days = int(args[args.index("--days") + 1])
        run_input = {"mode": "history", "codes": codes, "historyDays": days}
    else:
        run_input = {"mode": "single", "codes": [a for a in args if not a.startswith("--")]}

    run = client.actor(ACTOR).call(run_input=run_input)
    rows = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    if run_input["mode"] == "market":
        live = [r for r in rows if r.get("has_data")]
        print(f"全市场 {len(rows)} 只，其中 {len(live)} 只有资金流数据\n")
        print(f"{'代码':<8}{'名称':<10}{'主力净额':>12}{'主力占比':>10}{'涨跌%':>8}")
        print("-" * 50)
        for r in sorted(live, key=lambda x: x["main_net"] or 0, reverse=True)[:20]:
            print(f"{r['code']:<8}{r['name']:<10}{fmt_yi(r['main_net']):>12}"
                  f"{r['main_ratio']:>9}%{r['change_pct']:>7}%")
    elif run_input["mode"] == "history":
        print(f"{'代码':<8}{'日期':<13}{'主力净额':>12}{'主力占比':>10}{'收盘':>9}")
        print("-" * 55)
        for r in sorted(rows, key=lambda x: x.get("date") or ""):
            print(f"{r['code']:<8}{r.get('date',''):<13}{fmt_yi(r.get('main_net')):>12}"
                  f"{(r.get('main_ratio') or 0):>9}%{(r.get('close_price') or 0):>9}")
    else:
        print(f"{'代码':<8}{'名称':<10}{'主力净额':>12}{'主力占比':>10}{'价格':>9}{'涨跌%':>8}")
        print("-" * 60)
        for r in rows:
            print(f"{r['code']:<8}{r['name']:<10}{fmt_yi(r['main_net']):>12}"
                  f"{r['main_ratio']:>9}%{r['price']:>9}{r['change_pct']:>7}%")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
