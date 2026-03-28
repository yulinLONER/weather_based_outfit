# 服装商品管理系统 - API 接口文档 (交付标准 4)

## 1. 概述
本系统通过统一的标准化数据模型处理来自淘宝、京东、拼多多等平台的服装商品数据。所有 API 调用均包含频率控制与自动重试机制。

## 2. 核心 API 说明

### 2.1 淘宝商品详情 API (淘宝开放平台)
- **方法**: `taobao.item.get`
- **输入**: `num_iid` (商品 ID)
- **输出**: 标准化 `Product` 对象。
- **映射规则**: 
  - `title` 映射到 `title`
  - `price` 映射到 `base_price`
  - `skus` 映射到 `product_skus` 表中。

### 2.2 拼多多商品搜索 API (多多进宝)
- **方法**: `pdd.ddk.goods.search`
- **输入**: `keyword` (关键词)
- **输出**: `List[Product]`。
- **映射规则**: `min_group_price / 100` 映射到 `base_price`。

### 2.3 京东联盟商品查询 API
- **方法**: `jd.union.open.goods.query`
- **输入**: `skuIds` (SKU ID 列表)
- **输出**: 标准化 `Product` 详情。

## 3. 系统技术特性

### 3.1 频率控制 (Rate Limiting)
- **淘宝**: 1000ms 间隔 (1 QPS)
- **拼多多**: 500ms 间隔 (2 QPS)
- **京东**: 800ms 间隔 (1.25 QPS)

### 3.2 缓存机制 (Caching)
- **策略**: 使用 SQLite `api_cache` 表。
- **有效期**: 默认 60 分钟。
- **存储格式**: JSON 序列化存储原始响应数据。

### 3.3 数据同步策略
- **实时同步**: 调用 `ProductSyncService.sync_product(platform, id)`。
- **定时任务**: 定期轮询 `products` 表中状态为 `pending` 或过期的商品。

## 4. 异常处理与报警
- 失败的 API 调用将记录在 `sync_logs` 表中。
- **监控指标**: `data_quality_score` 用于衡量获取数据的完整性 (如必填字段是否齐全)。
- **报警**: 当 `sync_logs` 中错误率超过阈值时，建议对接外部告警系统 (如邮件、钉钉)。
