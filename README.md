# china-a-share-fund-flow-examples

用 [Apify](https://apify.com) 拉取**全 A 股（沪深京约 5,900 只）的主力资金流向**——超大单 / 大单 / 中单 / 小单的净额与占比，外加价格和涨跌幅，输出干净 JSON。

底层 Actor：[`jfishpw/china-a-share-fund-flow`](https://apify.com/jfishpw/china-a-share-fund-flow) — A股资金流 · Eastmoney，$3.9/次全市场快照。

---

## 30 秒上手

```python
from apify_client import ApifyClient

client = ApifyClient("<YOUR_API_TOKEN>")
run = client.actor("jfishpw/china-a-share-fund-flow").call(
    run_input={"mode": "single", "codes": ["002112", "600519"]},
)
for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    print(item["code"], item["name"], item["main_net"], item["main_ratio"])
```

## 它解决什么问题

「主力资金流向」是 A股短线最常用的指标之一，但免费数据源有三个坑：

1. **字段是 `f62`/`f66`/`f72` 这种东财内部编码**，得自己对照文档解码
2. **有些字段返回的是垃圾常数**——比如 `clist` 接口的 `f69`（超大单净占比）对所有股票都恒等于约 -17.9，看着像数据其实不是
3. **单个接口拿不到全部五档**，得自己拼多个端点

这个 Actor 把这些全处理了，并且**每个字段都标注了可靠性**：

```json
{
  "code": "002112",
  "name": "三变科技",
  "price": 12.0,
  "change_pct": -2.44,
  "main_net": -1834716.0,
  "super_large_net": -1779763.0,
  "large_net": -54953.0,
  "medium_net": 5227471.0,
  "small_net": -3392755.0,
  "main_ratio": -1.27,
  "super_large_ratio": -1.23,
  "large_ratio": -0.04,
  "medium_ratio": 3.62,
  "small_ratio": -2.35,
  "timestamp": 1794898488,
  "has_data": true,
  "main_net_check": true
}
```

`main_net_check` 是**恒等式自检**：为 `true` 表示 `super_large_net + large_net == main_net`，你可以自己验证每一行。

## 三种模式

| mode | 输入 | 输出 | 价格 |
|---|---|---|---|
| `single` | `codes` | 每只股票一条 | $0.005 / 只 |
| `market` | 无 | 全市场约 5,900 条 | $3.9 / 次 |
| `history` | `codes` + `historyDays` | 每只股票每天一条 | $0.02 / 股/日 |

`mode` 默认是 `single`。`single` 和 `history` 模式下如果 `codes` 为空，会用示例股票 `["002112", "600519"]`。

## 实战场景

### 1. 全市场主力资金快照

```python
from apify_client import ApifyClient

client = ApifyClient("<YOUR_API_TOKEN>")
run = client.actor("jfishpw/china-a-share-fund-flow").call(run_input={"mode": "market"})

rows = list(client.dataset(run["defaultDatasetId"]).iterate_items())
print(f"拿到 {len(rows)} 只")

# 主力净流入 TOP 10
for r in sorted(rows, key=lambda x: x["main_net"] or 0, reverse=True)[:10]:
    print(f"{r['code']} {r['name']:8s} {r['main_net']/1e8:>8.2f}亿  {r['main_ratio']}%")

# 只保留有数据的（过滤退市/停牌）
live = [r for r in rows if r["has_data"]]
print(f"{len(live)} 只有真实资金流数据，{len(rows)-len(live)} 只是退市/停牌")
```

### 2. 自选股追踪

```python
WATCHLIST = ["002112", "600519", "000001", "300750"]

run = client.actor("jfishpw/china-a-share-fund-flow").call(
    run_input={"mode": "single", "codes": WATCHLIST},
)

for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    tier = "主力净流入" if (item["main_net"] or 0) > 0 else "主力净流出"
    print(f"{item['code']} {item['name']:8s} {tier} {item['main_net']/1e8:.2f}亿 ({item['main_ratio']}%)")
```

### 3. 判断主力是在持续流入还是流出

```python
run = client.actor("jfishpw/china-a-share-fund-flow").call(
    run_input={"mode": "history", "codes": ["600519"], "historyDays": 30},
)

history = list(client.dataset(run["defaultDatasetId"]).iterate_items())
# 按日期升序算近 5 日主力净额累计
recent = history[-5:]
cumulative = sum(r["main_net"] or 0 for r in recent)
print(f"近 5 个交易日主力净额累计 {cumulative/1e8:.2f}亿")
print("持续流入" if cumulative > 0 else "持续流出")
```

### 4. 找主力净流入 TOP 榜（配合 pandas）

```python
import pandas as pd

run = client.actor("jfishpw/china-a-share-fund-flow").call(run_input={"mode": "market"})
df = pd.DataFrame(client.dataset(run["defaultDatasetId"]).list_items())

df = df[df["has_data"]].copy()
df["main_net_yi"] = df["main_net"] / 1e8
df["change_pct"] = pd.to_numeric(df["change_pct"], errors="coerce")

top = df.nlargest(20, "main_net_yi")[["code", "name", "main_net_yi", "main_ratio", "change_pct", "price"]]
print(top.to_string(index=False))
```

### 5. 命令行一行调用

```bash
curl "https://api.apify.com/v2/acts/jfishpw/china-a-share-fund-flow/runs?token=$APIFY_TOKEN" \
  -X POST -H "Content-Type: application/json" \
  -d '{"mode":"single","codes":["002112","600519"]}'
```

## 接入 AI agent

```bash
claude mcp add --transport http apify "https://mcp.apify.com?tools=jfishpw/china-a-share-fund-flow"
```

```json
{
  "mcpServers": {
    "apify": {
      "url": "https://mcp.apify.com?tools=jfishpw/china-a-share-fund-flow"
    }
  }
}
```

## 数据口径说明

- **金额单位是人民币元**。`1e8` = 1 亿，`1e4` = 1 万。
- **`main_net == super_large_net + large_net` 恒成立**——这是东财对「主力」的定义。每行都带 `main_net_check` 供你验证。
- **`super_large_ratio` 在 market 模式下恒为 `null`**：东财全市场接口对该字段返回固定常数，不是真实占比，所以宁可返回 null 也不伪造。该字段在 `single` 和 `history` 模式（走另一个端点）下有真实值。
- **退市股、停牌股没有资金流数据**，会以 `has_data: false` 返回，金额字段为 null，方便过滤；也可以设 `includeQuote: false` 精简体积。
- 数据源：东方财富（Eastmoney）公开行情接口。

## 相关链接

- Actor 主页：https://apify.com/jfishpw/china-a-share-fund-flow
- 在线体验（个股主力资金）：https://apify.com/jfishpw/china-a-share-fund-flow/examples/a-share-main-force-money-flow
- 在线体验（历史资金流）：https://apify.com/jfishpw/china-a-share-fund-flow/examples/single-stock-fund-flow-history
- 另一个 Actor：抖音/B站视频转文字 https://apify.com/jfishpw/chinese-video-transcript

## License

MIT
