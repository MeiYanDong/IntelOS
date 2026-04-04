#!/usr/bin/env python3
"""
Agent Runner — 通用子 Agent 执行器
用法：python3 run_agent.py robinhood
"""

import os, sys, json, datetime, subprocess, urllib.request
import markdown as md

READWISE_TOKEN     = os.environ.get("READWISE_TOKEN")     or "KdNIlPZ2Tus2qVqsOUpNP5PXcS1vHRfHZ97eM5h5sAWUU4HgnO"
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY")  or "sk-9vj9M2U8pZEuWNTiiE6NARw8prlNkmx14DSO7aRc0veqsXWH"

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))


def read_file(path):
    try:
        with open(path) as f:
            return f.read()
    except:
        return ""


def web_search(query):
    """用 DuckDuckGo 搜索，返回摘要文本"""
    encoded = urllib.request.quote(query)
    url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_redirect=1&no_html=1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        results = []
        if data.get("AbstractText"):
            results.append(data["AbstractText"])
        for r in data.get("RelatedTopics", [])[:5]:
            if isinstance(r, dict) and r.get("Text"):
                results.append(r["Text"])
        return "\n".join(results)
    except Exception as e:
        return f"搜索失败: {e}"


def fetch_sec_filings(cik, days_back=4):
    """从 SEC EDGAR 获取最近的 8-K 公告"""
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
                results.append({
                    "date": filings["filingDate"][i],
                    "accession": filings["accessionNumber"][i],
                    "form": form,
                })
        return results
    except Exception as e:
        return []


def call_claude(prompt):
    """调用 Claude API"""
    payload = json.dumps({
        "model": "claude-opus-4-6",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    req = urllib.request.Request(
        "https://yunwu.ai/v1/messages",
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

    # Robinhood 专用：从 SEC 拉最新公告
    new_filings_text = ""
    if agent_name == "robinhood":
        filings = fetch_sec_filings("0001783398", days_back=4)
        if filings:
            new_filings_text = "### 最新 SEC 公告（过去4天）\n"
            for f in filings:
                new_filings_text += f"- {f['date']} | 8-K | {f['accession']}\n"
            print(f"  发现 {len(filings)} 条新 SEC 公告")
        else:
            print("  无新 SEC 公告")

    # 用搜索补充最新新闻
    search_query = f"Robinhood Markets HOOD {today[:7]} news trading volumes earnings" if agent_name == "robinhood" else agent_name
    search_text = web_search(search_query)

    # 让 Claude 分析：对比 memory 和新数据，生成 diff
    prompt = f"""你是一个专门追踪 {agent_name} 的 Agent。

## 你的任务说明
{agent_md}

## 你的历史记忆（上次已知状态）
{memory_md}

## 今天新发现的信息

### SEC 新公告
{new_filings_text or "无"}

### 搜索到的最新信息
{search_text[:3000]}

---

请做两件事：

**第一：生成更新报告**
格式：
```
## {agent_name.capitalize()} 更新 — {today}

### 变化（与上次记忆对比）
- 有什么新的数据或事件？
- 哪些数字发生了变化（从 X → Y）？
- 如果没有实质变化，直接说"本轮无实质更新"

### 当前状态快照
- 最新关键指标摘要
```

**第二：输出更新后的完整 memory.md 内容**
在报告末尾，用 <MEMORY_UPDATE> 和 </MEMORY_UPDATE> 包裹更新后的完整 memory.md 文本。
保持原有格式，更新数字和日期，补充新事件。
"""

    print("  🧠 Claude 分析中...")
    result = call_claude(prompt)

    # 提取 memory 更新
    import re
    memory_match = re.search(r"<MEMORY_UPDATE>(.*?)</MEMORY_UPDATE>", result, re.DOTALL)
    report = result.replace(memory_match.group(0), "").strip() if memory_match else result

    # 判断是否有实质更新
    has_update = "无实质更新" not in report and "no significant" not in report.lower()

    print(f"\n{'─'*60}")
    print(report)
    print(f"{'─'*60}\n")

    # 更新 memory.md
    if memory_match:
        new_memory = memory_match.group(1).strip()
        with open(os.path.join(agent_dir, "memory.md"), "w") as f:
            f.write(new_memory)
        print("  ✅ memory.md 已更新")

    # 有实质更新才写入 Readwise
    if has_update:
        url = save_to_readwise(
            title=f"Robinhood 更新 — {today}",
            content=report,
            date_str=today,
            tags=["agent-update", "robinhood"]
        )
        print(f"  ✅ 已写入 Reader：{url}")
    else:
        print("  ℹ️  无实质更新，跳过写入 Reader")


if __name__ == "__main__":
    agent_name = sys.argv[1] if len(sys.argv) > 1 else "robinhood"
    run_agent(agent_name)
