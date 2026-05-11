# Workspace Architecture Evolution

> Status: 下一阶段架构方案
> Last updated: 2026-05-06

本文档记录 Lumina 下一阶段资源协作架构演进方向。它不替代当前已经落地的用户增强和团队权限实现，而是为后续从 `team + share_grant + owner_id` 迁移到更清晰的 workspace 资源边界提供设计依据。

核心结论：

> Team 管成员、订阅和可用能力；Workspace 管资源归属、协作权限和资源生命周期。

---

## 1. 背景

当前用户增强阶段已经实现：

- 系统管理员、团队管理员、普通用户/团队成员的角色边界。
- Team 成员管理。
- Team 可用模型、可用转换、默认模型配置。
- Public/team/private 可见性。
- 基于 owner 和 share grant 的资源访问。

试用后发现，团队笔记本需要更自然的协作权限：

- 团队成员可以查看团队资源。
- 团队成员可以向团队笔记本新增来源和笔记。
- 团队成员可以维护自己创建的内容。
- 团队成员不应随意删除会影响团队知识库结构的资源。
- 团队 owner/admin 和系统 admin 需要更高管理权限。

如果继续只用 `team`、`share_grant`、`owner_id` 拼接规则，权限会散落在 notebook、source、note、chat、share 多处，容易出现“为了禁止删除，误伤新增/编辑”的问题。

Workspace 用一个显式资源容器解决这个边界问题。下一阶段应把它作为资源归属、协作权限和运行时 team context 的主入口，而不是继续扩大 share grant 的职责。

---

## 2. 概念分层

### 2.1 User

User 表示账号和个人身份。

User 负责：

- 登录、profile、locale、theme。
- 系统角色，例如 `admin | user`。
- 个人默认工作区。

User 不直接表达团队资源协作策略。

### 2.2 Team

Team 表示成员关系、订阅和团队能力边界。

Team 负责：

- 成员和成员角色。
- 团队 owner/admin/member。
- 订阅、席位、状态。
- 系统管理员授权的可用模型范围。
- 系统管理员授权的可用转换范围。
- 团队默认 5 项模型。

Team 不直接作为资源容器。一个团队可以拥有一个或多个 workspace。

当前阶段可以先实现“每个 team 一个默认 workspace”，后续再扩展到多个 workspace。

### 2.3 Workspace

Workspace 表示资源归属和协作边界。

Workspace 负责：

- notebook/source/note/chat_session 的归属。
- 成员在该资源空间内能做哪些动作。
- 资源移动、归档、删除、发布 public 的权限入口。
- 审计和影响预览。

Workspace 类型：

| Type | 说明 |
| --- | --- |
| `personal` | 用户个人工作区。每个用户默认拥有一个。 |
| `team` | 团队工作区。属于某个 team，成员来自 team membership。 |

Public 不建议建成特殊 workspace。公开发布仍然是资源 visibility 或 public grant，因为 public 是全网只读传播状态，不是资源协作空间。

### 2.4 Public

Public 表示全网只读传播状态。

Public 负责：

- 匿名访问公开内容。
- 已登录用户只读引用公开内容。
- 公开撤回策略和影响提示。

Public 不负责：

- 成员协作。
- 资源归属。
- 团队模型或转换上下文。

公开资源仍属于原 workspace。公开后，其它用户可能只读引用该资源；撤回公开时应遵循当前系统策略，例如保留已有只读引用、防止新引用。

---

## 3. 数据模型草案

### 3.1 Workspace

```text
workspace
  id
  name
  type: personal | team
  owner_user_id: option<app_user>
  team_id: option<team>
  created
  updated
  archived
```

约束：

- `type = personal` 时必须有 `owner_user_id`，不应有 `team_id`。
- `type = team` 时必须有 `team_id`，`owner_user_id` 可为空。
- 每个用户至少有一个 personal workspace。
- 每个 team 至少有一个 default team workspace。

### 3.2 资源归属字段

下一阶段资源应显式记录 workspace 归属：

```text
notebook.workspace_id
source.workspace_id
note.workspace_id
chat_session.workspace_id
```

建议保留 creator 字段：

```text
notebook.creator_id
source.creator_id
note.creator_id
chat_session.creator_id
```

`owner_id` 可在迁移期保留，用于兼容旧数据和个人资源。长期语义应逐步收敛为：

- `workspace_id` 表示资源归属。
- `creator_id` 表示内容贡献者。
- `owner_id` 只用于旧数据迁移或 personal workspace 快捷查询。

---

## 4. 移动与复制语义

### 4.1 默认采用移动

个人资源进入团队时，默认是移动到团队 workspace，而不是 share 给 team。

移动行为：

- 更新资源的 `workspace_id` 为目标 team workspace。
- 资源进入目标 workspace 的权限策略控制。
- 原个人 owner 不再拥有独立删除权。
- 保留 `creator_id`，用于“编辑/删除自己创建的内容”等细粒度规则。
- 写入审计事件：`resource.moved_to_workspace`。
- UI 必须明确提示：移动后资源将受团队权限管理。

移动适合表达“这是团队知识库的一部分”。

### 4.2 Notebook 移动的资源范围

移动 notebook 时需要明确其子资源处理方式，避免出现“notebook 属于团队，但内部内容仍在个人 workspace”的混合状态。

MVP 建议：

- notebook 本体移动到目标 workspace。
- notebook 内的 notes 和 chat sessions 随 notebook 移动。
- 由当前用户创建、且只服务于该 notebook 的 personal sources，可在确认后一起移动。
- 已经属于目标 workspace 的 sources 保持不变。
- 已公开或被其它 workspace 引用的 sources 不自动移动，只保留只读引用，除非后续提供更明确的 copy/move 影响预览。
- 每个被移动的资源保留 `creator_id`，用于后续“只能编辑/删除自己创建的内容”规则。

移动前 UI 应展示影响预览：

- 将移动哪些资源。
- 哪些来源会保持引用而不移动。
- 移动后谁可以查看、新增、编辑和删除。
- 当前用户是否会失去个人删除权。

### 4.3 预留复制接口

当前阶段可以只实现 move，但 API 需要为后续 copy 预留形态。

推荐接口：

```http
POST /workspaces/{workspace_id}/resources/move
```

请求：

```json
{
  "resource_type": "notebook",
  "resource_id": "notebook:xxx",
  "mode": "move"
}
```

后续可增加：

```http
POST /workspaces/{workspace_id}/resources/copy
```

或复用 body：

```json
{
  "resource_type": "notebook",
  "resource_id": "notebook:xxx",
  "mode": "copy"
}
```

复制语义后续再定义，例如是否复制 sources、notes、chat sessions、insights、embeddings、files。当前实现不应把 copy 做成隐式 fallback；当用户选择移动时就是移动，后续 copy 应作为独立能力提供。

---

## 5. Workspace 权限策略

下一阶段权限配置应挂在 workspace，而不是直接挂在 team。

有效权限公式：

```text
effective_permission =
  system_workspace_permission_limit
  && workspace_permission_policy
  && role_or_creator_condition
```

### 5.1 系统全局上限

系统管理员定义这个部署实例允许团队 workspace 打开什么行为。

示例：

- 是否允许成员删除自己创建的来源。
- 是否允许成员从团队 workspace 移除来源。
- 是否允许成员删除自己创建的笔记。
- 是否允许成员处理自己创建的来源。

系统上限代表部署实例的整体治理策略。即使 workspace manager 想打开某个权限，只要系统上限禁止，最终权限仍然禁止。

系统上限不只是 UI 配置项，后端写接口必须强制执行。前端可以展示“被系统策略锁定”的状态，但不能作为唯一校验来源。

### 5.2 Workspace 权限策略

Workspace manager 在系统上限内配置本 workspace 的协作方式。

默认策略建议：

| 权限项 | 默认 |
| --- | --- |
| 成员可查看 workspace 内容 | 开 |
| 成员可新增来源 | 开 |
| 成员可编辑自己添加的来源 | 开 |
| 成员可处理自己添加的来源 | 开 |
| 成员可删除自己添加的来源 | 关 |
| 成员可从 workspace 移除来源 | 关 |
| 成员可新增笔记 | 开 |
| 成员可编辑自己创建的笔记 | 开 |
| 成员可删除自己创建的笔记 | 开 |
| 成员可删除对话 | 关 |
| 成员可修改 notebook 信息 | 关 |

默认策略对应当前产品判断：

- 团队资源不能由普通成员随意删除。
- 团队成员可以查看团队资源。
- 团队成员可以新增来源和笔记。
- 团队成员可以编辑/删除自己创建的笔记。
- 团队成员不能编辑或删除其他人创建的笔记。
- 团队成员不能删除 notebook。

### 5.3 角色与 creator 条件

运行时仍需判断：

- 当前用户是否系统 admin。
- 当前用户是否 workspace manager。
- 当前用户是否 workspace member。
- 当前用户是否资源 creator。

示例：

```text
can_delete_note =
  system_limit.member_delete_own_note
  && workspace_policy.member_delete_own_note
  && note.creator_id == actor.id
```

```text
can_delete_any_note =
  actor.is_system_admin || actor.is_workspace_manager
```

---

## 6. Team 与 Workspace 的边界

Team 继续负责：

- 成员管理。
- 成员角色。
- 订阅和席位。
- 可用模型和可用转换范围。
- 团队默认模型。

Workspace 负责：

- 资源归属。
- 资源协作权限。
- 资源生命周期。
- 资源级审计。
- public 发布入口和撤回影响提示。

模型解析可以通过 workspace 找到 team context：

```text
resource.workspace_id -> workspace.team_id -> team defaults/allowlist
```

这样运行时不需要从 share grant 反推团队上下文。

因此，当前 follow-up 中的“显式 owning team 字段”不应再作为长期方向。下一阶段应直接进入 `workspace_id`，team context 通过 workspace 解析得到。

---

## 7. 向量与 KG 边界

Workspace 不只约束资源 CRUD，也应约束资源派生索引。当前系统的 source/note/insight embeddings 和 KG 存储仍偏全局，查询后再按资源权限过滤。下一阶段要把向量与 KG 维护纳入 workspace 架构，避免团队资源在底层知识结构中互相混合。

### 7.1 团队向量索引

团队 workspace 的向量索引按团队创建和维护。

原则：

- `source_embedding`、`source_insight`、`note.embedding` 或其后续独立 embedding 表必须能追溯到 `workspace_id`。
- 团队 workspace 的 embedding 生成使用该团队的有效 embedding model。
- 团队 workspace 的 query embedding 也必须使用同一团队上下文，不能只用系统默认 embedding model。
- 团队之间不共享向量索引；一个团队 workspace 的向量重建不能影响其它团队或个人 workspace。
- 个人 workspace 继续使用系统默认 embedding model，除非后续设计个人订阅模型。

建议模型：

```text
embedding_scope
  scope_type: personal | team | system
  workspace_id: option<workspace>
  team_id: option<team>
  industry_tag_id: option<industry_tag>
```

MVP 可以不新建 `embedding_scope` 表，而是先在 embedding 记录上冗余写入：

```text
source_embedding.workspace_id
source_embedding.team_id
source_insight.workspace_id
source_insight.team_id
note.workspace_id
```

长期方向是让所有检索入口都显式传入 `workspace_id` 或 `team_id`，并在 repository 层先按 scope 过滤，再做相似度排序。

### 7.2 团队 KG

团队 KG 按团队创建，团队之间不关联。

原则：

- 团队 workspace 内抽取的 KG entity/relation 必须带 `workspace_id` 和 `team_id`。
- KG entity 的唯一性不能只用全局 slug，例如 `kg_entity:insulin`，否则不同团队会合并同名实体。
- 团队 KG entity id 应包含 scope，例如 `kg_entity:{team_slug}:{entity_slug}`，或使用系统生成 id 并增加唯一索引 `(scope, normalized_name, type)`。
- 团队 KG 查询只在当前团队 KG scope 内扩展关系，不跨团队做 1-hop 或多跳关联。
- 删除或重建团队 KG 只影响当前团队 workspace。

这条原则比“查询后过滤”更严格：KG 的图结构本身不能跨团队连边，否则即使最终结果过滤，关系扩展阶段也可能受到其它团队知识影响。

### 7.3 系统 KG 与行业标签

系统 KG 用于公共、行业级或平台级知识，不应无限增长成一个全局混杂知识库。系统 KG 应按行业标签划分。

建议新增概念：

```text
industry_tag
  id
  slug
  name
  parent_id: option<industry_tag>
  status: active | archived
```

系统 KG scope：

```text
system_kg_scope
  id
  industry_tag_id
  name
  status
```

系统 KG 原则：

- 系统 KG 只能由系统管理员维护。
- 系统 KG 资源必须绑定一个或多个行业标签，例如 `biopharma`、`life-science`、`materials`。
- 检索系统 KG 时必须指定行业标签或使用用户/团队配置的默认行业标签集合。
- 团队 KG 可以选择引用系统行业 KG 作为只读背景，但不能写入系统 KG，也不能把团队私有实体合并进系统 KG。
- 行业标签是控制 KG 规模和召回范围的第一层边界，避免系统 KG 过大后影响查询质量和成本。

### 7.4 维护接口

旧的全局 embedding rebuild 不应直接开放给团队 owner。下一阶段需要拆成 scoped maintenance API。

建议接口：

```http
POST /workspaces/{workspace_id}/maintenance/embeddings/rebuild
POST /workspaces/{workspace_id}/maintenance/kg/rebuild
GET /workspaces/{workspace_id}/maintenance/jobs/{command_id}
```

系统级接口：

```http
POST /system/maintenance/embeddings/rebuild
POST /system/maintenance/kg/rebuild
POST /system/kg/industry-tags/{tag_id}/rebuild
```

权限：

- Team owner/admin 只能维护自己管理的 team workspace。
- 普通成员不能执行维护任务。
- 系统 admin 可以维护系统 KG、行业 KG、公共索引，并可观察团队维护状态；默认不对个人 workspace 执行资源级写操作。
- 维护任务必须写审计事件，并记录 scope、资源数量、模型版本、发起人和结果。

---

## 8. 权限矩阵草案

| 对象 | Workspace member | Resource creator | Workspace manager | System admin |
| --- | --- | --- | --- | --- |
| Workspace 内容 | 查看 | 查看 | 查看/管理 | 查看/管理 |
| Notebook | 查看 | 按策略编辑自己创建的 notebook | 管理所有 notebook | 管理所有 notebook |
| Source | 查看、新增 | 按策略编辑/处理自己添加的 source | 管理所有 source | 管理所有 source |
| Source 移出 workspace | 默认不允许 | 按策略可允许 | 允许 | 允许 |
| Source 删除 | 默认不允许 | 按策略可允许，但受引用/public 策略限制 | 允许，受引用/public 策略限制 | 允许，受引用/public 策略限制 |
| Note | 查看、新增 | 按策略编辑/删除自己创建的 note | 管理所有 note | 管理所有 note |
| Chat session | 使用/新建 | 使用/新建 | 删除/管理 | 删除/管理 |
| Workspace 权限策略 | 不允许 | 不允许 | 在系统上限内配置 | 配置上限和任意 workspace |
| Team 模型/转换库存 | 不允许 | 不允许 | 不允许 | 配置 |
| Team 默认模型 | 不允许 | 不允许 | 在 allowlist 内配置 | 配置 |

---

## 9. 迁移策略

建议分阶段演进，避免一次性重写权限系统。

### Phase 1: 引入 Workspace 表和默认 workspace

- 新增 `workspace` 表。
- 新增系统 workspace permission limits。
- 为每个现有用户创建 personal workspace。
- 为每个现有 team 创建 default team workspace。
- 新资源创建时写入 `workspace_id`。
- 旧资源无 `workspace_id` 时，运行时 fallback 到 `owner_id` 和 share grant。

### Phase 2: 资源显式归属迁移

- 为现有 notebook/source/note/chat_session 回填 workspace。
- owner 私有资源进入 owner personal workspace。
- 明确 team 归属资源进入 default team workspace。
- 多 team share 的旧资源暂留在 owner personal workspace，并保留 share grant，等待用户主动移动。

### Phase 3: Workspace 权限服务

- 新增 workspace permission resolver。
- 后端写接口统一调用 resolver。
- 前端 action menu、按钮、编辑器只消费后端返回的 capability 或统一 hook。
- 将 notebook/source/note/chat 的删除、编辑、移除、发布入口逐步收口到同一套 capability。

### Phase 4: 移动资源到 workspace

- 实现 move API。
- UI 在 notebook/source 详情、share dialog 或 workspace picker 中提供“移动到团队工作区”。
- 移动前展示影响预览。
- 写入审计。

### Phase 5: Workspace 权限配置 UI

- 系统管理员配置全局 workspace permission limits。
- Workspace manager 在上限内配置 workspace policy。
- UI 展示最终生效权限，避免团队管理员误以为能越过系统上限。

### Phase 6: 预留复制

- 设计 copy API 的深拷贝范围。
- 支持复制 notebook 到另一个 workspace，保留个人副本。
- 复制策略应明确 source、note、chat、file、embedding、insight 的复制或复用规则。

### Phase 7: 向量与 KG scope 化

- 为 source_embedding、source_insight、note embedding、kg_entity、kg_relation 增加 workspace/team/system scope。
- 迁移现有 KG entity id，避免继续使用全局 name slug 合并团队实体。
- 搜索和 Graph RAG 查询先限定 scope，再执行相似度/BM25/图扩展。
- 拆分 maintenance API：team workspace rebuild、system rebuild、industry-tag rebuild。
- 团队“高级”页面只接入 team workspace scoped maintenance，不接入全局维护。

---

## 10. API 草案

```http
GET /workspaces
POST /workspaces
GET /workspaces/{workspace_id}
PATCH /workspaces/{workspace_id}
GET /workspaces/{workspace_id}/policy
PATCH /workspaces/{workspace_id}/policy
GET /workspaces/system-policy
PATCH /workspaces/system-policy
POST /workspaces/{workspace_id}/resources/move
```

后续预留：

```http
POST /workspaces/{workspace_id}/resources/copy
```

维护接口预留：

```http
POST /workspaces/{workspace_id}/maintenance/embeddings/rebuild
POST /workspaces/{workspace_id}/maintenance/kg/rebuild
GET /workspaces/{workspace_id}/maintenance/jobs/{command_id}
POST /system/kg/industry-tags/{tag_id}/rebuild
```

资源 API 应逐步支持：

```http
GET /notebooks?workspace_id=...
GET /sources?workspace_id=...
GET /notes?workspace_id=...
```

---

## 11. 前端体验

需要新增或调整：

- Workspace selector：个人工作区 / 团队工作区。
- Resource move dialog：移动前提示权限变化。
- Workspace settings：权限策略配置。
- Workspace advanced：仅展示当前 workspace 可执行的 scoped maintenance，例如重建当前团队向量和 KG。
- Team settings：继续负责成员、订阅、模型/转换范围、默认模型。
- Resource details：展示 workspace、creator、权限状态。
- Action menus：从 capability 结果决定显示/禁用，而不是前端复制权限判断。

建议文案：

> 移动后，此资源将进入团队工作区，并受团队工作区权限管理。你仍会被记录为创建者，但删除和共享等操作可能由团队管理员控制。

---

## 12. 审计要求

以下事件必须审计：

- `workspace.created`
- `workspace.updated`
- `workspace.policy.updated`
- `workspace.system_policy.updated`
- `resource.moved_to_workspace`
- `resource.copy_requested`
- `resource.workspace_changed`
- `resource.deleted`
- `resource.public_published`
- `resource.public_revoked`
- `workspace.embeddings.rebuild_requested`
- `workspace.kg.rebuild_requested`
- `system.kg.industry_rebuild_requested`

审计元数据应包含：

- actor
- source workspace
- target workspace
- resource type
- resource id
- previous policy/effective policy where relevant
- operation mode: move/copy
- maintenance scope and model ids where relevant
- industry tag ids where relevant

---

## 13. 非目标

下一阶段不做：

- 每个成员单独 ACL。
- 任意自定义角色权限编辑器。
- 多层组织/企业目录同步。
- 完整资源复制深拷贝实现。
- Public 作为 workspace。
- 团队 KG 跨团队自动合并。
- 无行业标签的无限全局系统 KG。

这些能力可以后续扩展，但当前阶段应先完成 workspace 作为资源归属和协作边界的基础模型。

---

## 14. 验收标准

下一阶段 workspace 架构落地后，应满足：

- 新建资源都有明确 `workspace_id`。
- 团队资源权限不再依赖 share grant 推断。
- 团队成员可以在 workspace policy 允许范围内新增和维护自己的贡献内容。
- 团队成员不能越过 workspace policy 删除团队资源。
- 系统 admin 可以设置全局 workspace 权限上限。
- Workspace manager 只能在系统上限内配置本 workspace。
- 资源从个人 workspace 移动到团队 workspace 后，权限立即按团队 workspace 生效。
- 运行时模型解析可以通过 workspace 找到 team context。
- 旧数据在迁移期有安全 fallback，不会突然扩大权限。
- 团队向量重建只影响当前团队 workspace。
- 团队 KG 查询和关系扩展不跨团队。
- 系统 KG 可以按行业标签重建和查询，避免单一全局 KG 失控。
