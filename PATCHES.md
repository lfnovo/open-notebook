# Open Notebook Fork Patch 台账（SPK-03）

> Task ID: SPK-03（GitHub Issue #19，repo: HiFiBiO-Therapeutics/RDLens）
> 日期：2026-08-06
> 基准 commit：`30c7e2a6`（上游 v1.14.0，BASE-01 固定）
> 分支：`feat/spk-03-embedded-adapter`
> 责任台账模板见 RDLens `deploy/research/BASELINE.md` §5

## 1. 目标

在内部 Fork 证明嵌入式模式的禁用边界（Fork 侧）：

- REQ-DIS-01：保存 Source/Note 后无 `embed_note` / `source_embedding`（vectorize）
- REQ-DIS-02：原生 Provider/原生 AI 路径禁用，LLM 固定绑定 Research Gateway，
  词法搜索失败不回退向量搜索
- REQ-DIS-03：Transformation 仅 prompt-only，无代码/工具/URL/市场字段
- REQ-SCOPE-03：全局 Notebook、认证、系统设置、Provider/凭据、媒体、
  直接上传/URL 来源被屏蔽
- REQ-AUTH-03：客户端不能获取或切换非固定 Notebook ID

所有能力默认关闭（`RD_EMBEDDED_MODE` 未启用时完全保持上游行为），
由 RDLens 侧部署通过环境变量开启。

## 2. Patch 清单（相对基准 commit 30c7e2a6）

| 文件 | 类型 | 行数 | 说明 |
|---|---|---:|---|
| `open_notebook/config.py` | 配置 | +13 | `RD_EMBEDDED_MODE` / `RD_EMBEDDED_NOTEBOOK_ID` / `RD_AI_GATEWAY_URL` / `RD_AI_GATEWAY_MODEL` / `RD_AI_GATEWAY_API_KEY`；模块属性调用时读取 |
| `open_notebook/domain/notebook.py` | 行为守卫 | +15 | `Note.save()` 跳过 `embed_note`；`Source.vectorize()` fail-closed（InvalidInputError）；`text_search` 词法失败不再回退向量搜索 |
| `open_notebook/graphs/source.py` | 行为守卫 | +4/-1 | `save_source` 跳过 `source.vectorize()` |
| `open_notebook/ai/gateway.py` | 新增适配器 | +34 | 绑定 Gateway 的 `ChatOpenAI`；未配置 URL 时 `ConfigurationError`（fail-closed） |
| `open_notebook/ai/provision.py` | 行为守卫 | +6 | 嵌入式分支直接返回 Gateway 模型，跳过 `model_manager` 与用户 `model_id` |
| `api/embedded_scope.py` | 新增中间件 | +83 | API 屏蔽矩阵（`is_blocked` 纯函数 + ASGI 中间件，403） |
| `api/main.py` | 注册 | +5 | 最外层注册 `EmbeddedScopeMiddleware` |
| `tests/test_embedded_scope.py` | 测试 | +265 | 12 个边界测试（REQ-DIS-01/02/03、REQ-SCOPE-03、REQ-AUTH-03） |

合计：8 文件，+424/-1 行；**生产代码 6 文件 +160 行**，未改写 Domain/DB/Schema，
零数据库迁移。

## 3. 改动边界与成本评估（REQ-POC-02）

- **未触碰**：Domain/DB 数据模型（零迁移）；SurrealDB；前端 Next.js；
  docker-compose.yml（镜像固定由 SPK-01 `deploy/research/compose.yaml` 与 FND-02 负责）。
- 所有守卫为「配置开关 + 2~4 行分支」，默认关闭 → 上游 rebase 冲突面小。
- **rebase 成本估算**：下一小版本预计 ≤ 1 工程日（仅 5 个后端文件 + 2 新模块 + 1 测试文件）。

## 4. 未覆盖 / 待验证项（显式清单）

- **CSP frame-ancestors / postMessage 绑定（REQ-EMB-01）**：RDLens 侧 UI-01 交付；
  Fork 前端 next.config 安全头未改，本 Spike 不验证前端构建。
- **Token 内存生命周期（REQ-EMB-02）**：RDLens 侧 SPK-02 已覆盖 Token 签发/校验/不落存储；
  Fork 前端刷新/登出/销毁消息处理留待 UI-01。
- **端到端 API 网络录制**：Gateway AI 端点未实现（FND-06）；本 Spike 以单元级绑定断言
  （`model.openai_api_base == RD_AI_GATEWAY_URL` 且 `model_manager` 未被调用）代替；
  端到端网络录制在 SPK-04 / GATE-01。
- **内部 Registry**：未就绪（BASELINE.md §4）；SPK-03 为纯代码 Spike，不构建镜像，不阻塞。
- **Fork 公开状态**：`lingyun-hifibio/open-notebook-rdlens` 为 public fork；
  是否迁移 org 私有由负责人决策。
