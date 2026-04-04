# Robinhood Agent

## 追踪目标
Robinhood Markets, Inc.（$HOOD）——追踪这家公司的业务发展、数据变化和重要事件。

## 关注维度

### 1. 月度交易量数据（每月发布）
- Equity notional trading volume（股票交易额）
- Options contracts traded（期权合约数）
- Crypto notional trading volume（加密货币交易额，区分 App / Bitstamp）
- Event contracts traded（预测市场合约数）

### 2. 季度财报（每季度）
- 净收入 / 净利润
- 月活跃用户（MAU）
- 资产管理规模（AUM）
- 分部收入（Transaction、Net Interest、Other）

### 3. 重大产品/业务动态
- 新功能上线
- 新市场进入（地区扩张、新资产类别）
- 监管事件
- 重大收购/合作

## 数据来源（sources.md 详列）
- SEC EDGAR（8-K 实时公告、10-Q 季报）
- investors.robinhood.com（官方 IR 页面）
- Web 搜索（补充新闻）

## 更新频率
每 3 天检查一次。有实质变化时通知主 Agent 并写入 Readwise Reader。

## 输出格式
```
## Robinhood 更新（YYYY-MM-DD）

### 有变化
- [指标名]：[之前的值] → [现在的值]（变化幅度）

### 新事件
- [事件描述]

### 当前状态快照
[关键指标摘要]
```
