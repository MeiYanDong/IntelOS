# IntelOS

持续追踪外部世界动态的情报系统。每个追踪目标（公司、项目、生态）对应一个独立的子 Agent 目录，拥有独立的记忆、指令和数据源配置。

## 架构

```
IntelOS/
├── run_agent.py          # 通用 Agent 执行器
├── robinhood/            # Robinhood 追踪 Agent
│   ├── agent.md          # 追踪维度与输出格式定义
│   ├── memory.md         # 持久化历史记忆（自动更新）
│   └── sources.md        # 数据源配置
└── ...                   # 未来更多 Agent
```

## 每个 Agent 目录

| 文件 | 说明 |
|---|---|
| `agent.md` | 追踪什么、输出格式、更新频率 |
| `memory.md` | 已知状态快照，每次运行自动 diff 更新 |
| `sources.md` | SEC EDGAR / RSS / 搜索关键词 |

## 运行

```bash
python3 run_agent.py robinhood
```

## 工作流程

1. 读取 agent.md / memory.md / sources.md
2. 拉取 SEC EDGAR 最新公告 + DuckDuckGo 搜索
3. Claude 对比 memory 生成 diff 报告
4. 有实质更新 → 写入 Readwise Reader（标签：`agent-update`）
5. 自动更新 memory.md

## 当前追踪目标

- **Robinhood** — 月度交易量、季报、产品动态
