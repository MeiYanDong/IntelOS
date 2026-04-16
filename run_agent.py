#!/usr/bin/env python3
"""
Agent Runner — 通用子 Agent 执行器
用法：python3 run_agent.py robinhood
"""

import os, sys, json, datetime, subprocess, urllib.request
import markdown as md

READWISE_TOKEN     = os.environ.get("READWISE_TOKEN")
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))


def read_file(path):
    try:
        with open(path) as f:
            return f.read()
    except:
        return ""


def fetch_url(url, timeout=15):
    """抓取网页内容，返回纯文本"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research bot)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
        # 简单去除 HTML 标签
        import re
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    except Exception as e:
        return f"抓取失败: {e}"


def fetch_sec_filings(cik, days_back=30):
    """从 SEC EDGAR 获取最近的 8-K 公告，并抓取正文摘要"""
    try:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        req = urllib.request.Request(url, headers={"User-Agent": "research@example.com"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        filings = data["filings"]["recent"]
        cutoff = (datetime.date.today() - datetime.timedelta(days=days_back)).isoformat()

        results = []
        for i, form in enumerate(filings["form"]):
            if form == "8-K" and filings["filingDate"][i] >= cutoff:
                accession = filings["accessionNumber"][i].replace("-", "")
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession}/{filings['primaryDocument'][i]}"
                results.append({
                    "date": filings["filingDate"][i],
                    "accession": filings["accessionNumber"][i],
                    "url": filing_url,
                })
        return results
    except Exception as e:
        return []


def fetch_robinhood_ir():
    """抓取 Robinhood 官方 IR 新闻页"""
    url = "https://investors.robinhood.com/news-releases"
    text = fetch_url(url, timeout=15)
    return text[:3000]


def fetch_robinhood_newsroom():
    """抓取 Robinhood Newsroom 产品公告页"""
    url = "https://newsroom.robinhood.com"
    text = fetch_url(url, timeout=15)
    return text[:3000]


def fetch_sec_10q(cik, days_back=100):
    """检测最近是否有新的 10-Q / 10-K 季报/年报"""
    try:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        req = urllib.request.Request(url, headers={"User-Agent": "research@example.com"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        filings = data["filings"]["recent"]
        cutoff = (datetime.date.today() - datetime.timedelta(days=days_back)).isoformat()

        results = []
        for i, form in enumerate(filings["form"]):
            if form in ("10-Q", "10-K") and filings["filingDate"][i] >= cutoff:
                accession = filings["accessionNumber"][i].replace("-", "")
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession}/{filings['primaryDocument'][i]}"
                results.append({
                    "form": form,
                    "date": filings["filingDate"][i],
                    "url": filing_url,
                })
        return results
    except Exception:
        return []


def call_claude(prompt):
    """调用 Claude API"""
    payload = json.dumps({
        "model": "claude-opus-4-6",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    req = urllib.request.Request(
        f"{ANTHROPIC_BASE_URL}/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["content"][0]["text"]


def save_to_readwise(title, content, date_str, tags):
    payload = json.dumps({
        "url":            f"https://agent-update.local/{tags[0]}/{date_str}",
        "title":          title,
        "author":         f"{tags[0].capitalize()} Agent",
        "category":       "article",
        "tags":           tags,
        "published_date": date_str,
        "html":           md.markdown(content, extensions=["extra"]),
    }).encode()
    req = urllib.request.Request(
        "https://readwise.io/api/v3/save/",
        data=payload,
        headers={"Authorization": f"Token {READWISE_TOKEN}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        return f"https://read.readwise.io/read/{data['id']}"


def run_agent(agent_name):
    agent_dir = os.path.join(AGENTS_DIR, agent_name)
    agent_md  = read_file(os.path.join(agent_dir, "agent.md"))
    memory_md = read_file(os.path.join(agent_dir, "memory.md"))
    sources_md = read_file(os.path.join(agent_dir, "sources.md"))
    today = datetime.date.today().isoformat()

    print(f"\n🤖 运行 {agent_name} Agent — {today}\n")

    # Robinhood 专用：从 SEC 拉最近 30 天公告 + 抓 IR / Newsroom 页面
    new_filings_text = ""
    quarterly_text = ""
    ir_text = ""
    newsroom_text = ""
    if agent_name == "robinhood":
        # 8-K 公告
        filings = fetch_sec_filings("0001783398", days_back=30)
        if filings:
            new_filings_text = f"### 最新 SEC 8-K 公告（过去30天，共{len(filings)}条）\n"
            for f in filings[:10]:
                new_filings_text += f"- {f['date']} | {f['accession']} | {f['url']}\n"
            print(f"  发现 {len(filings)} 条 SEC 8-K 公告")
        else:
            print("  无新 SEC 8-K 公告")

        # 10-Q / 10-K 季报/年报
        quarterly = fetch_sec_10q("0001783398", days_back=100)
        if quarterly:
            quarterly_text = f"### 最新季报/年报（过去100天，共{len(quarterly)}份）\n"
            for q in quarterly[:5]:
                quarterly_text += f"- {q['date']} | {q['form']} | {q['url']}\n"
            print(f"  发现 {len(quarterly)} 份季报/年报")
        else:
            print("  无新季报/年报")

        print("  📡 抓取 Robinhood IR 页面...")
        ir_text = fetch_robinhood_ir()

        print("  📡 抓取 Robinhood Newsroom...")
        newsroom_text = fetch_robinhood_newsroom()

    prompt = f"""## 角色/role

你是 Robinhood Markets ($HOOD) 的业务追踪者，为持仓或关注 $HOOD 的投资者写每周简报。
读者画像：了解 Robinhood 是什么，可能持有 $HOOD，但不会每天盯着 SEC EDGAR。他们需要你回答一个问题：**"这周 Robinhood 有什么值得知道的事？"**

## 背景记忆/context

上次已知状态（不要在输出中重复这些数字，只在有变化时才提）：

{memory_md}

## 本周新数据/new_data（{today}）

### SEC EDGAR 最新 8-K 公告（过去30天）
{new_filings_text or "无"}

### SEC EDGAR 最新季报/年报（10-Q / 10-K，过去100天）
{quarterly_text or "无"}

### Robinhood 官方 IR 页面
{ir_text[:2000] if ir_text else "抓取失败"}

### Robinhood Newsroom（产品公告）
{newsroom_text[:2000] if newsroom_text else "抓取失败"}

## 任务/task

基于以上数据，写一份让投资者 3 分钟读完、读完能判断"这周要不要关注 $HOOD"的周报。

## 核心原则/principles

排序逻辑（按决策价值从高到低）：
1. **改变判断的信息** — 超预期/低于预期的数据、重大产品发布、监管事件
2. **证明在前进** — 可量化的增长、新里程碑
3. **值得留意** — 有潜力但需后续验证的信号
4. **背景补充** — 丰富理解但不影响决策

写作要求：
- **一件事说三句话**：发生了什么 → 为什么重要 → 一句判断
- **数字要有对比**：不写"交易量增加"，写"股票交易额 $194B，环比 -14%，同比 +X%"
- **有观点不武断**：给判断，标注不确定的地方
- **没有新数据就如实说**，不要硬凑分析

反面约束：
- 不要重复背景记忆里已有的数字，除非本周有更新
- 不要写"建议关注后续进展"这种废话
- 不要把 SEC 公告的 accession number 直接贴出来，翻译成人话
- 如果某个板块本周真的没内容，直接省略

## 输出格式/format

严格按以下格式输出，不要加额外说明：

```
# Robinhood 周报 · {today}

> 一句话：[读完整篇后能跟朋友说的一句话，20字以内]

## 本周重点

### 1. [标题]
[发生了什么] → [为什么重要] → [你的判断]

（最多3条，按决策价值排序；本周无重点则写"本周无重大变化"）

## 数据追踪

| 指标 | 最新值 | 环比 | 同比 |
|---|---|---|---|
| 股票交易额 | | | |
| 期权合约 | | | |
| 加密交易额 | | | |
| 付费用户 | | | |
| 平台资产 | | | |

（只填有数据的格，无数据的格填"—"）

## 下周看点
- [预期将发布的数据或事件，1-3条]
```

然后另起一行，输出更新后的完整 memory.md，用 <MEMORY_UPDATE> 和 </MEMORY_UPDATE> 包裹。
"""

    print("  🧠 Claude 分析中...")
    result = call_claude(prompt)

    # 提取 memory 更新
    import re
    memory_match = re.search(r"<MEMORY_UPDATE>(.*?)</MEMORY_UPDATE>", result, re.DOTALL)
    report = result.replace(memory_match.group(0), "").strip() if memory_match else result

    print(f"\n{'─'*60}")
    print(report)
    print(f"{'─'*60}\n")

    # 更新 memory.md
    if memory_match:
        new_memory = memory_match.group(1).strip()
        with open(os.path.join(agent_dir, "memory.md"), "w") as f:
            f.write(new_memory)
        print("  ✅ memory.md 已更新")

    # 每次都写入 Readwise
    url = save_to_readwise(
        title=f"Robinhood 周报 — {today}",
        content=report,
        date_str=today,
        tags=["agent-update", "robinhood", "weekly-report"]
    )
    print(f"  ✅ 已写入 Reader：{url}")


if __name__ == "__main__":
    agent_name = sys.argv[1] if len(sys.argv) > 1 else "robinhood"
    run_agent(agent_name)
