# User Enhancement Follow-up TODO

> Status: future work after the 2026-05-05 model/runtime permission closure
> Scope: This list tracks product and engineering work that intentionally remains after team membership, public sharing, profile, admin users/teams, and team model-default runtime enforcement.

## 已闭环基线

本轮已经完成并可作为后续功能基础：

- 系统管理员、团队管理员、普通用户/团队成员的权限边界已落入后端策略。
- Team 成员管理、Team 模型/转换 allowlist、Team 五项默认模型配置已实现。
- 运行时模型解析已支持 team context：chat、embedding、transformation、tools、large context。
- 普通用户不能通过 `model_override` 或 Ask 模型参数绕过系统/团队默认模型。
- Public 内容浏览、公开/私密/team 可见性、公开撤回默认策略文档已固化。
- 侧边栏、public 页面、profile、登录/注册流、admin users/teams 页面已调整到当前产品形态。

## P0: 权限与运行时收口

- [ ] **向量与 KG 按 workspace/team scope 重构**
  - 当前状态：资源已经 workspace-aware，但 `source_embedding`、`source_insight`、`note.embedding`、`kg_entity`、`kg_relation` 仍偏全局，搜索后再按资源权限过滤。
  - 目标状态：团队 workspace 的向量和 KG 按团队创建、维护和查询，团队之间不共享底层向量索引或 KG entity/relation。
  - 团队 KG entity 不能再只用全局名称 slug 合并，应使用 scoped id 或 `(scope, normalized_name, type)` 唯一约束。
  - 团队查询 embedding 必须使用团队有效 embedding model，避免写入时 team-aware、查询时 system-default 的模型不一致。
  - 主要文件：新 migration、`commands/embedding_commands.py`、`open_notebook/graphs/knowledge_graph.py`、`open_notebook/database/repositories/search_repository.py`、`open_notebook/domain/notebook.py`、`api/routers/search.py`。
  - 验收：两个团队抽取同名实体不会合并；团队 A 搜索/KG 扩展不返回团队 B 的节点；团队 A 向量重建不影响团队 B 或个人 workspace。

- [ ] **拆分 scoped 向量/KG维护接口**
  - 当前全局 `/api/embeddings/rebuild` 只能保留为系统级维护，不能直接开放给 Team owner。
  - 新增 workspace scoped maintenance：`POST /workspaces/{workspace_id}/maintenance/embeddings/rebuild`、`POST /workspaces/{workspace_id}/maintenance/kg/rebuild`。
  - Team owner/admin 只能维护自己管理的 team workspace；普通成员不能维护；系统 admin 负责系统级/行业级维护。
  - 前端“高级”页面对团队 owner 显示团队 scoped 工具，不显示全库维护工具。
  - 主要文件：新增 `api/routers/workspace_maintenance.py`、`api/services/workspace_maintenance_service.py`、命令 payload、`frontend/src/app/(dashboard)/advanced/page.tsx`。
  - 验收：团队 owner 可重建当前团队向量/KG；传入其它团队 workspace 返回 403；审计日志记录 scope、actor、job id、资源数量和结果。

- [ ] **系统 KG 按行业标签划分**
  - 系统 KG 不是团队 KG，也不应是无限增长的单一全局 KG。
  - 新增 `industry_tag` 概念，系统 KG 资源和 rebuild/search 必须绑定行业标签，例如 `biopharma`、`life-science`、`materials`。
  - 团队 KG 可只读引用系统行业 KG 作为背景知识，但不能把团队私有实体写入或合并到系统 KG。
  - 主要文件：新 migration、系统 KG repository/service/router、admin UI、KG extraction/import flow。
  - 验收：系统 KG 可按行业标签重建和查询；无行业标签的系统 KG 写入被拒绝；团队 KG 与系统 KG 私有写入隔离。

- [ ] **引入 Workspace 资源归属模型**
  - 详细设计见 `docs/7-DEVELOPMENT/workspace-architecture.md`。
  - 当前 team context 主要从 `share_grant` 推断，多个 team grant 时会返回 `None`，行为安全但不够精确。
  - 下一阶段不再把“显式 owning team 字段”作为长期方向，而是新增 `workspace_id`，通过 `resource.workspace_id -> workspace.team_id` 解析 team context。
  - Workspace 作为资源归属和协作权限边界；Team 继续负责成员、订阅、可用模型/转换和团队默认模型。
  - 先支持将个人资源移动到团队 workspace，保留后续 copy API 入口。
  - 主要文件：新 migration、`open_notebook/database/repositories/` 下新增 workspace repository、`api/models.py`、新增 `api/routers/workspaces.py`、`api/services/workspace_service.py`、`open_notebook/domain/notebook.py`、`api/services/source_service.py`、前端 workspace selector/move dialog。
  - 测试：个人 workspace、team workspace、资源移动、成员新增来源/笔记、成员不能删除团队资源、通过 workspace 解析 team 默认模型。

- [ ] **运行时强制 Team transformation allowlist**
  - 当前 Team 可配置可用转换，但 source create / transformation execution 需要进一步校验 active team 是否允许该 transformation。
  - 主要文件：`api/services/source_service.py`、`commands/source_commands.py`、`open_notebook/graphs/source.py`、`api/services/team_service.py`。
  - 验收：团队成员不能对团队资源运行不在 Team allowlist 中的转换；系统管理员仍可配置 allowlist。

- [ ] **补齐 team-aware model defaults 的前端展示**
  - 当前后端已经使用 team defaults，但部分前端仍展示系统默认模型名称。
  - 增加“有效模型配置”查询接口，返回 system/team fallback 后的最终模型。
  - 主要文件：`api/routers/models.py`、`open_notebook/ai/model_resolution.py`、`frontend/src/lib/hooks/use-models.ts`、`frontend/src/app/(dashboard)/search/page.tsx`、`frontend/src/components/source/ModelSelector.tsx`。
  - 验收：团队资源页面显示团队生效模型；非团队资源显示系统默认模型。

- [ ] **扩展 model override 策略为可配置产品策略**
  - 当前策略：普通用户只能使用有效默认模型，系统管理员可显式选择任意模型。
  - 后续可增加开关：团队管理员允许成员从 Team allowlist 中临时选择模型。
  - 建议配置：`TEAM_MEMBER_MODEL_SELECTION=default_only|team_allowlist`，默认 `default_only`。
  - 主要文件：`api/services/model_policy_service.py`、`frontend/src/components/source/ModelSelector.tsx`、`frontend/src/components/search/AdvancedModelsDialog.tsx`。

## P1: Team 设置与订阅用户能力

- [ ] **实现 Team 非模型设置**
  - 系统管理员继续配置全局上限和默认值；团队管理员只能在系统允许范围内选择团队设置。
  - 第一批设置建议包括：默认 embedding 行为、是否允许 web search、Tavily include domains 的团队级收窄配置、默认内容处理引擎。
  - 主要文件：新 migration、`api/models.py`、`api/routers/teams.py`、`api/services/team_service.py`、新增 `open_notebook/database/repositories/team_settings_repository.py`、`frontend/src/app/(dashboard)/settings/teams/page.tsx`。
  - 验收：团队 owner/admin 可配置团队设置；普通成员只读；系统设置缺失或关闭时团队不能强行启用。

- [ ] **建立订阅/配额基础模型**
  - 产品设计中团队管理员是订阅用户；需要独立建模 subscription，而不是复用 team role。
  - 建议先支持手动状态：`free | trial | active | past_due | disabled`，并记录 seats、模型权限、到期时间。
  - 主要文件：新 `subscription` migration、`api/routers/teams.py`、`api/services/team_service.py`、admin UI。
  - 验收：团队状态可由系统管理员查看/更新；禁用订阅后团队成员仍能查看历史内容，但不能触发新 AI 任务。

- [ ] **Team 成员邀请流程**
  - 当前只能添加已有 active 用户；后续支持邀请邮箱、接受邀请、过期、撤销。
  - 主要文件：`api/routers/teams.py`、`api/services/team_service.py`、`open_notebook/database/repositories/team_repository.py`、`frontend/src/app/(dashboard)/settings/teams/page.tsx`。
  - 验收：owner/admin 可邀请邮箱；被邀请用户注册或登录后加入团队；邀请可撤销并审计。

## P1: Public 与分享治理

- [ ] **公开撤回策略配置 UI**
  - 目前默认策略已写入设计：`preserve_references`，并提示公开资源可能被其它用户只读引用。
  - 后续在系统设置中显示当前策略，并允许系统管理员选择 `preserve_references | block_if_referenced | revoke_all`。
  - 主要文件：`api/routers/settings.py`、`open_notebook/domain/content_settings.py`、`frontend/src/app/(dashboard)/settings/components/SettingsForm.tsx`。
  - 验收：撤回公开内容时，UI 明确提示当前策略和影响。

- [ ] **引用关系可视化**
  - 撤回 public 或删除团队前，应能看到哪些 notebook/source/team/user 仍在引用。
  - 主要文件：`open_notebook/database/repositories/share_repository.py`、`api/routers/shares.py` 或现有 share router、资源详情页。
  - 验收：owner/admin 能在操作前查看引用数量和引用对象列表。

- [ ] **公开内容作者与来源治理**
  - Public 页面应稳定展示作者、所属团队、公开时间、撤回状态。
  - 主要文件：public list repositories、`api/routers/public.py` 或现有 public endpoints、`frontend/src/app/public/page.tsx`、`frontend/src/app/discover/page.tsx`。
  - 验收：匿名访问不泄露私密字段；登录用户能看到足够的来源信息。

## P1: 审计与运维闭环

- [ ] **审计事件补齐**
  - 已有 team created / deleted / allowlist / defaults 事件基础；后续补齐：system default model change、settings change、public revoke strategy change、team settings change、subscription status change。
  - 主要文件：`open_notebook/database/repositories/audit_log_repository.py`、`api/routers/models.py`、`api/routers/settings.py`、`api/services/team_service.py`。
  - 验收：高级审计日志可按 actor、target、action、时间过滤。

- [ ] **管理员操作确认与回滚指引**
  - 高风险操作包括：删除团队、禁用用户、撤回公开、修改默认模型、修改 Team allowlist。
  - 主要文件：对应 admin/team UI dialog、`frontend/src/lib/locales/*/index.ts`。
  - 验收：每个高风险弹窗展示影响、确认文案、完成后的状态入口。

- [ ] **自动清理测试用户与测试数据工具化**
  - 本轮已经手动清理 `lumina*` 测试用户；后续提供受控 admin action 或 dev script。
  - 建议脚本：`scripts/cleanup_test_users.py --prefix lumina --dry-run`。
  - 验收：默认 dry-run，明确列出将删除/禁用的用户、团队、share grants。

## P2: 前端体验与引导

- [ ] **统一 role-aware navigation source**
  - Sidebar 与 Command Palette 当前分别构造导航项，后续应提取成单一 `navigation-policy.ts`。
  - 主要文件：`frontend/src/lib/navigation-policy.ts`、`frontend/src/components/layout/AppSidebar.tsx`、`frontend/src/components/common/CommandPalette.tsx`。
  - 验收：新增角色入口只需改一个导航策略文件。

- [ ] **Team dashboard**
  - 当前 Team 管理集中在 settings/teams；后续可以为团队成员提供轻量 dashboard：所属团队、可用模型、可用转换、公开/团队资源入口。
  - 主要文件：`frontend/src/app/(dashboard)/settings/teams/page.tsx` 或新增 `frontend/src/app/(dashboard)/teams/page.tsx`。
  - 验收：普通 team member 能清楚看到“自己能用什么”，但不能编辑。

- [ ] **用户操作标准引导补文档化**
  - 将页面内引导沉淀成用户文档：如何创建团队、配置模型、分享给 public、撤回 public、查看审计。
  - 主要文件：`docs/3-USER-GUIDE/user-management-and-sharing.md`、`docs/index.md`。
  - 验收：新管理员可以按文档完成完整配置闭环。

- [ ] **搜索匹配项图片显示**
  - 当前搜索匹配项已经支持 Markdown/GFM 渲染，但相对路径图片（如 `images/*.jpg`）暂不展示。
  - 后续需要为来源提取产物建立受权限控制的 asset 存储与访问链路：提取阶段保留图片文件，新增 `GET /api/sources/{source_id}/assets/{asset_path}`，复用 source `can_read` 权限，并防止路径穿越。
  - 第一阶段优先支持 source 匹配项图片；note/artifact 中引用图片可在 artifact 抽象落地后扩展。
  - 主要文件：`open_notebook/content_extractors/`、`open_notebook/graphs/source.py`、`api/routers/sources.py`、`open_notebook/database/repositories/search_repository.py`、`frontend/src/app/(dashboard)/search/page.tsx`。
  - 验收：搜索 `BSD` 展开 PDF 来源匹配项时，Markdown 图片能通过权限校验接口正常显示；无权限用户不能直接访问图片资源。

## P2: 测试与发布质量

- [ ] **补端到端权限用例**
  - 覆盖 admin、team owner、team admin、team member、普通用户、匿名访问。
  - 建议用例：团队模型默认生效、非 admin 不能 override、public 匿名可读、public 撤回后匿名不可读、引用者只读保留。
  - 主要文件：新增 Playwright 或 API integration tests；若不引入 Playwright，先补 FastAPI integration tests。

- [ ] **OpenAPI 类型生成纳入 CI**
  - 已使用 `scripts/generate_openapi_types.py --check` 验证；后续把它加入 CI。
  - 验收：后端 schema 变化但前端 generated types 未更新时 CI 失败。

- [ ] **Locale parity 修复**
  - 当前 `frontend/src/lib/locales/index.test.ts` 仍有既有 missing/unused key 问题。
  - 验收：locale parity test 可作为前端 gating check。

## 建议实施顺序

1. 完成当前 Workspace MVP 人工验证，不再扩大旧 owner/share 逻辑。
2. P0: 向量与 KG 按 workspace/team scope 重构。
3. P0: scoped 向量/KG维护接口，恢复团队 owner 可用的团队“高级”工具。
4. P0: 系统 KG 按行业标签划分。
5. P0: Transformation allowlist runtime enforcement。
6. P0: Effective model defaults API + 前端展示。
7. P1: Team 非模型设置。
8. P1: 审计事件补齐。
9. P1: Public 撤回策略 UI 与引用可视化。
10. P2: 统一 navigation policy 与用户文档。

## 验证基线

每个后续批次至少运行：

```bash
uv run pytest tests/test_permission_model.py tests/test_team_service.py tests/test_team_repository.py tests/test_model_resolution.py tests/test_model_policy_service.py tests/test_team_context_service.py -q
uv run python scripts/generate_openapi_types.py --check
```

前端批次至少运行：

```bash
cd frontend
npm test -- --run 'src/app/(dashboard)/settings/teams/page.test.tsx'
npm run lint
npm run build
```
