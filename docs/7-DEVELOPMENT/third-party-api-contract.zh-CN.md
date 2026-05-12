# Lumina 第三方 API 接入契约

本文档定义第三方 HTTP 插件服务接入 Lumina 的 v1 契约。第三方服务可以向 Lumina 提供外部资料来源检索、资料详情获取，以及输出产物生成能力。

v1 的管理模型如下：

- Lumina 系统管理员统一配置第三方服务的 endpoint 和 API key。
- 系统管理员创建来源定义，并授权给指定团队使用。
- 团队用户只能使用已授权的来源。
- Quota 由 Lumina 按“团队 + 第三方来源 + 自然月”管理。

## 鉴权

Lumina 调用第三方服务时，每个请求都会携带：

```http
Authorization: Bearer <api_key>
X-Lumina-Request-Id: <uuid>
Content-Type: application/json
```

说明：

- `api_key` 由 Lumina 系统管理员配置，不会暴露给团队用户。
- 第三方服务应校验 `Authorization`。
- `X-Lumina-Request-Id` 可作为链路追踪和幂等键。
- 第三方服务返回错误时，应使用结构化错误体，便于 Lumina 展示和记录。

## 必需端点

第三方服务必须支持以下端点：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/.well-known/lumina-plugin.json` | 插件 manifest，声明服务信息、版本和能力。 |
| `GET` | `/lumina/v1/health` | 连接测试和服务健康检查。 |
| `POST` | `/lumina/v1/sources/search` | 检索外部资料来源。 |
| `POST` | `/lumina/v1/sources/fetch` | 获取检索结果条目的完整内容。 |
| `POST` | `/lumina/v1/outputs/generate` | 生成第三方输出产物。 |
| `GET` | `/lumina/v1/jobs/{external_job_id}` | 查询异步任务状态。 |

## Manifest

`GET /.well-known/lumina-plugin.json` 返回示例：

```json
{
  "schema_version": "lumina-plugin-v1",
  "name": "Paper Search",
  "provider": "Example Labs",
  "version": "1.0.0",
  "capabilities": ["search", "fetch", "output"],
  "sources": [
    {
      "key": "paper_search",
      "name": "Paper Search",
      "description": "Search papers and fetch paper details.",
      "capabilities": ["search", "fetch", "output"]
    }
  ]
}
```

字段说明：

- `schema_version`：固定为 `lumina-plugin-v1`。
- `name`：插件名称。
- `provider`：服务提供方名称。
- `version`：插件版本。
- `capabilities`：插件整体能力，可包含 `search`、`fetch`、`output`。
- `sources`：可被 Lumina 配置和授权的来源列表。
- `sources[].key`：来源唯一 key，Lumina 调用 search/fetch/generate 时会传入。
- `sources[].name`：来源显示名称，Lumina 导入资料后会将其作为来源标签显示。

## 异步响应规则

`search`、`fetch` 和 `generate` 可以同步完成，也可以返回异步任务。

同步完成：

```json
{
  "status": "completed",
  "data": {}
}
```

接受异步任务：

```json
{
  "status": "accepted",
  "external_job_id": "job_123",
  "next_poll_after_seconds": 2
}
```

Lumina 会调用 `GET /lumina/v1/jobs/{external_job_id}` 轮询任务。轮询响应必须是以下状态之一：

```json
{
  "status": "accepted",
  "external_job_id": "job_123",
  "next_poll_after_seconds": 2
}
```

```json
{
  "status": "completed",
  "external_job_id": "job_123",
  "data": {}
}
```

```json
{
  "status": "failed",
  "external_job_id": "job_123",
  "error": {
    "code": "provider_error",
    "message": "..."
  }
}
```

## 来源检索

请求：

```json
{
  "source_key": "paper_search",
  "query": "graph retrieval",
  "limit": 10,
  "filters": {
    "year_from": 2022
  }
}
```

同步完成响应：

```json
{
  "status": "completed",
  "data": {
    "items": [
      {
        "external_id": "arxiv:2401.00001",
        "title": "Graph Retrieval for Research Agents",
        "summary": "A concise abstract or snippet.",
        "url": "https://example.org/paper/2401.00001",
        "authors": ["Ada Lovelace"],
        "published_at": "2026-01-15",
        "metadata": {
          "venue": "ExampleConf"
        }
      }
    ]
  }
}
```

说明：

- `external_id` 必须能被后续 `fetch` 使用。
- `title` 建议必填，用于 Lumina 搜索结果和导入后的来源标题。
- `summary` 用于结果列表预览。
- `metadata` 可携带第三方自定义字段。
- 检索本身不消耗 Lumina 来源 quota。

## 来源获取

当用户点击“加入”并实际导入外部资料时，Lumina 会调用 `fetch`。

请求：

```json
{
  "source_key": "paper_search",
  "external_id": "arxiv:2401.00001",
  "metadata": {}
}
```

同步完成响应：

```json
{
  "status": "completed",
  "data": {
    "external_id": "arxiv:2401.00001",
    "title": "Graph Retrieval for Research Agents",
    "content_markdown": "# Graph Retrieval\n\nFull paper text or detail.",
    "url": "https://example.org/paper/2401.00001",
    "metadata": {
      "pdf_url": "https://example.org/paper.pdf"
    }
  }
}
```

说明：

- `content_markdown` 是 Lumina 导入为本地来源的主要内容。
- 如果第三方只返回 URL 或文件地址，建议在 `metadata` 中提供可追踪字段。
- Lumina v1 的来源 quota 只在 `fetch` 被发送并用于实际导入时消耗。

## 输出生成

请求：

```json
{
  "source_key": "paper_search",
  "prompt": "Create a structured evidence table.",
  "input_text": "Optional user text",
  "items": [],
  "output_kind": "markdown",
  "options": {}
}
```

同步完成响应：

```json
{
  "status": "completed",
  "data": {
    "kind": "markdown",
    "title": "Evidence Table",
    "content": "| Claim | Evidence |\n| --- | --- |",
    "metadata": {}
  }
}
```

支持的输出类型：

- `markdown`
- `json`
- `file`
- `url`

## 错误格式

第三方服务应使用标准 HTTP 状态码，并返回结构化错误体：

```json
{
  "error": {
    "code": "invalid_request",
    "message": "query is required",
    "retryable": false
  }
}
```

推荐错误码：

| HTTP | code | 含义 |
| --- | --- | --- |
| `400` | `invalid_request` | 请求体格式错误或字段不支持。 |
| `401` | `invalid_api_key` | API key 缺失或无效。 |
| `403` | `forbidden` | API key 有效，但无权使用该来源。 |
| `404` | `not_found` | 外部条目或任务不存在。 |
| `429` | `rate_limited` | 第三方服务侧限流。Lumina quota 单独计算。 |
| `500` | `provider_error` | 第三方服务不可重试错误。 |
| `503` | `temporarily_unavailable` | 第三方服务临时不可用，可重试。 |

## Lumina Quota 规则

Lumina v1 的 quota 由 Lumina 内部控制，第三方服务不需要实现团队 quota。

规则：

- 维度：`team + external source + calendar month`。
- 月份按自然月聚合，格式为 `YYYY-MM`。
- `search` 只检查团队授权，不消耗 quota。
- 只有用户触发“加入”，并且 Lumina 向第三方发送 `fetch` 请求用于实际导入来源时，才消耗 1 次 quota。
- 第三方 job polling 不额外消耗 quota。
- Lumina 内部 retry 不额外消耗 quota。
- 如果 Lumina 本地校验失败，且请求尚未发送到第三方，则不消耗 quota。
- 如果请求已经发送给第三方，即使第三方失败、超时或返回错误，Lumina 会保留该次消耗记录。

## Lumina 管理端配置建议

系统管理员在 Lumina 中配置第三方服务时，通常需要填写：

- 连接名称：例如 `QA Paper Search`
- Endpoint：例如 `http://localhost:8099`
- API key：例如 `dev-paper-key`
- 接入目标：来源或输出产物
- 来源 key：例如 `paper_search`
- 能力：`search`、`fetch`、`output`
- 团队授权：选择可使用该来源的团队
- 月度 quota：例如 `100`

团队用户在工作区中看到的入口：

- 新建来源页面：`深度检索`
- 笔记本添加来源：`深度检索`
- 导入后的来源标签：第三方来源名称，例如 `Paper Search`

## 示例程序

本接入包包含一个可运行的 FastAPI 示例：

```text
examples/plugins/paper_search_plugin/
```

启动方式：

```bash
cd examples/plugins/paper_search_plugin
cp .env.example .env
uvicorn main:app --reload --port 8099
```

默认 API key：

```text
dev-paper-key
```

示例调用：

```bash
./client_examples/search.sh
python client_examples/client.py
```
