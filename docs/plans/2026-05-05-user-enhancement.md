# Lumina 用户增强详细设计

> Status: Design frozen; implementation started
> Date: 2026-05-05
> Scope: 在现有用户名/密码、JWT、注册/找回密码、公开/私密内容隔离能力之上，补齐多用户产品化所需的用户资料、角色权限、用户管理、所有权治理和审计基础。

## 背景

当前仓库已经完成了用户体系的第一阶段：

- `app_user` 表保存 `username` 与 `hashed_password`
- `/api/auth/login` 签发带 `sub`、`username`、`auth_version` 的 JWT
- `/api/auth/change-password`、`/api/auth/register`、`/api/auth/reset-password` 支持基础账号生命周期
- `source` 与 `notebook` 已有 `owner_id`、`visibility`
- 后端中间件会把 JWT 用户身份写入 `request.state.user_id` 与 `request.state.username`
- 前端 sidebar 目前用 `username === 'admin'` 判断管理入口可见性

这些能力让系统可以登录和区分内容归属，但还缺少稳定的“用户对象”语义：没有角色字段、状态字段、个人资料、管理员用户管理 API、服务端权限依赖、用户级资源统计和审计记录。下一步应该先把这些边界设计清楚，再进入实现。

## 目标

1. 建立明确的用户模型：邮箱/用户名、显示名、角色、状态、最近登录、密码变更时间、偏好设置。
2. 用服务端角色权限替代前端 `username === 'admin'` 的脆弱判断。
3. 提供管理员用户管理：列表、创建、更新角色/状态、重置密码、删除或禁用用户。
4. 提供个人资料能力：查看/更新自己、修改显示名/语言偏好/主题偏好。
5. 补齐所有权治理：未归属历史数据、用户禁用/删除后的内容归属策略、公共内容展示作者信息。
6. 为安全事件留审计基础：登录、登出、密码变更、管理员操作、用户状态变更。
7. 保持自托管友好：单用户部署仍低摩擦，默认 `admin/admin` 迁移路径可控。
8. 实现 Team/Group 成员管理，并将“全网公开”表达为一个系统内置 `public` 组。
9. 建立用户操作指导闭环：关键操作入口给出标准步骤，动作前提示影响，动作后可通过当前状态和审计日志回看。

## 非目标

- 不在本阶段做 OAuth/OIDC/SAML。
- 不做复杂组织/租户层级、跨组织计费或企业目录同步；本阶段实现 Team/Group 成员管理和资源分享所需的最小权限模型。
- 不做细粒度 ACL 或 Notebook 协作编辑。
- 不迁移 AI provider credentials 到用户级私有凭据；本阶段 credentials 仍是全局配置，仅系统 admin 可管理。
- 不实现邮件邀请入组流程；本阶段管理员或 team owner/admin 直接添加已有 active 用户。

## 设计原则

- 服务端是权限真相来源，前端只负责展示。
- 管理员操作必须可审计，避免“谁改了谁”不可追踪。
- 禁用优先于硬删除，硬删除只用于无数据或明确清理场景。
- 兼容当前数据：已有 `app_user:admin`、已有 `owner_id`、已有 JWT 均应平滑过渡。
- SurrealQL 继续集中在 repository 或 service 层，路由只处理 HTTP 语义。
- `public` 应该是一个特殊共享主体，而不是散落在各处的特殊分支。
- 用户引导必须贴近操作现场：页面提示负责降低误操作，用户文档负责沉淀标准流程，审计日志负责闭环回看。

## 实施前决策

这些决策作为本阶段实现输入，除非产品明确变更，否则实现时不再重新讨论：

| 议题 | 决策 |
| --- | --- |
| Credentials 隔离 | 本阶段不做用户/Team 隔离，保持全局 credentials 和模型配置，仅系统 admin 可管理。 |
| Team 分享权限 | 只有资源 owner 和系统 admin 可以创建或撤销资源 share grant；team owner/admin 只管理成员，不自动获得分享他人资源的权限。 |
| Public 撤回默认策略 | 默认采用 `preserve_references`：撤回全网公开后，匿名访问失效，已有引用者保留只读 grant。 |
| Public 撤回配置 | 新增 `PUBLIC_SHARE_REVOCATION_MODE=preserve_references|block_if_referenced|revoke_all`，默认 `preserve_references`。 |
| Team 删除 | 普通 team 如存在 active members、share grants 或资源依赖，禁止删除并返回 409 与引用数量；必须先移除成员和清理授权。 |
| Notebook 公开撤回 | 与 Source 一致采用 `preserve_references`；撤回后 public browse/匿名访问失效，公开期间已保存或引用该 notebook 的用户保留只读访问。 |
| 邀请流程 | 本阶段不发送 team 邀请邮件；`invited` 状态仅 schema 预留，UI/API 默认添加为 `active`。 |
| 用户 email 修改 | 本阶段不允许管理员或用户修改 email，避免绕过邮箱验证流程。 |
| 用户禁用后的 public 内容 | public 内容继续可读；禁用影响登录与私有内容访问，不 retroactively 隐藏已公开内容。 |

## 用户模型

### `app_user` 字段扩展

新增 migration `21.surrealql`：

```sql
DEFINE FIELD IF NOT EXISTS email ON TABLE app_user TYPE option<string>;
DEFINE FIELD IF NOT EXISTS display_name ON TABLE app_user TYPE option<string>;
DEFINE FIELD IF NOT EXISTS role ON TABLE app_user TYPE string DEFAULT 'user';
DEFINE FIELD IF NOT EXISTS status ON TABLE app_user TYPE string DEFAULT 'active';
DEFINE FIELD IF NOT EXISTS locale ON TABLE app_user TYPE option<string>;
DEFINE FIELD IF NOT EXISTS theme ON TABLE app_user TYPE option<string>;
DEFINE FIELD IF NOT EXISTS last_login_at ON TABLE app_user TYPE option<datetime>;
DEFINE FIELD IF NOT EXISTS password_changed_at ON TABLE app_user TYPE option<datetime>;
DEFINE FIELD IF NOT EXISTS created_by ON TABLE app_user TYPE option<record<app_user>>;

DEFINE FIELD IF NOT EXISTS role ON TABLE app_user ASSERT $value IN ['admin', 'user'];
DEFINE FIELD IF NOT EXISTS status ON TABLE app_user ASSERT $value IN ['active', 'disabled'];

DEFINE INDEX IF NOT EXISTS idx_app_user_role ON TABLE app_user COLUMNS role;
DEFINE INDEX IF NOT EXISTS idx_app_user_status ON TABLE app_user COLUMNS status;
DEFINE INDEX IF NOT EXISTS idx_app_user_email ON TABLE app_user COLUMNS email UNIQUE;

UPDATE app_user SET
  role = IF username = 'admin' THEN 'admin' ELSE role END,
  status = status ?? 'active',
  display_name = display_name ?? username,
  email = IF string::contains(username, '@') THEN username ELSE email END,
  password_changed_at = password_changed_at ?? updated;
```

Rollback `21_down.surrealql` 只移除新增索引和字段，不删除用户记录。

### 字段语义

| 字段 | 说明 |
| --- | --- |
| `username` | 登录标识，保持唯一。注册用户当前使用邮箱作为 username。 |
| `email` | 联系邮箱，可为空；注册路径默认等于 username。 |
| `display_name` | UI 展示名称；默认 username。 |
| `role` | `admin` 或 `user`。管理员可管理系统设置与用户。 |
| `status` | `active` 或 `disabled`。禁用用户不能登录，现有 JWT 失效。 |
| `locale` | 用户语言偏好，前端可覆盖浏览器检测。 |
| `theme` | 用户主题偏好，取值先复用前端已有主题枚举。 |
| `last_login_at` | 登录成功后更新。 |
| `password_changed_at` | 修改/重置密码后更新，并作为 JWT `auth_version` 的候选来源。 |
| `created_by` | 管理员创建用户时记录操作者。 |

## Team/Group 与 public 组

### 设计判断

当前系统已有 `visibility = 'private' | 'public'`，足够支撑第一阶段的公开浏览。但如果后续要引入 Team，就不应该再新增一套完全不同的分享语义。更稳的做法是把“全网公开”看成分享给一个系统内置组：

- `team:public` 是一个虚拟系统组。
- 所有匿名访问者与登录用户都隐式属于 `team:public`。
- 分享给 `team:public` 等价于“向全网 share”。
- 当前 `visibility = 'public'` 继续作为兼容字段和高频查询投影。

这样，未来的 Team 内共享、指定用户共享、全网公开可以落在同一套访问判断上：

```text
resource owner
  OR share_grant(target = current_user)
  OR share_grant(target = user's teams)
  OR share_grant(target = team:public)
```

### 本阶段交付模型

本阶段需要完整落地 Team 成员管理和资源分享所需的最小模型：

```sql
DEFINE TABLE IF NOT EXISTS team SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS slug ON TABLE team TYPE string;
DEFINE FIELD IF NOT EXISTS name ON TABLE team TYPE string;
DEFINE FIELD IF NOT EXISTS type ON TABLE team TYPE string DEFAULT 'workspace';
DEFINE FIELD IF NOT EXISTS created_by ON TABLE team TYPE option<record<app_user>>;
DEFINE FIELD IF NOT EXISTS created ON TABLE team TYPE datetime DEFAULT time::now();
DEFINE FIELD IF NOT EXISTS updated ON TABLE team TYPE datetime VALUE time::now();
DEFINE FIELD IF NOT EXISTS type ON TABLE team ASSERT $value IN ['workspace', 'system'];
DEFINE INDEX IF NOT EXISTS idx_team_slug ON TABLE team COLUMNS slug UNIQUE;

DEFINE TABLE IF NOT EXISTS team_member SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS team ON TABLE team_member TYPE record<team>;
DEFINE FIELD IF NOT EXISTS user ON TABLE team_member TYPE record<app_user>;
DEFINE FIELD IF NOT EXISTS role ON TABLE team_member TYPE string DEFAULT 'member';
DEFINE FIELD IF NOT EXISTS status ON TABLE team_member TYPE string DEFAULT 'active';
DEFINE FIELD IF NOT EXISTS created ON TABLE team_member TYPE datetime DEFAULT time::now();
DEFINE FIELD IF NOT EXISTS role ON TABLE team_member ASSERT $value IN ['owner', 'admin', 'member', 'viewer'];
DEFINE FIELD IF NOT EXISTS status ON TABLE team_member ASSERT $value IN ['active', 'invited', 'disabled'];
DEFINE INDEX IF NOT EXISTS idx_team_member_team_user ON TABLE team_member COLUMNS team, user UNIQUE;
DEFINE INDEX IF NOT EXISTS idx_team_member_user ON TABLE team_member COLUMNS user;

DEFINE TABLE IF NOT EXISTS share_grant SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS resource_type ON TABLE share_grant TYPE string;
DEFINE FIELD IF NOT EXISTS resource_id ON TABLE share_grant TYPE string;
DEFINE FIELD IF NOT EXISTS target_type ON TABLE share_grant TYPE string;
DEFINE FIELD IF NOT EXISTS target_id ON TABLE share_grant TYPE string;
DEFINE FIELD IF NOT EXISTS permission ON TABLE share_grant TYPE string DEFAULT 'read';
DEFINE FIELD IF NOT EXISTS created_by ON TABLE share_grant TYPE option<record<app_user>>;
DEFINE FIELD IF NOT EXISTS created ON TABLE share_grant TYPE datetime DEFAULT time::now();
DEFINE FIELD IF NOT EXISTS resource_type ON TABLE share_grant ASSERT $value IN ['source', 'notebook'];
DEFINE FIELD IF NOT EXISTS target_type ON TABLE share_grant ASSERT $value IN ['user', 'team'];
DEFINE FIELD IF NOT EXISTS permission ON TABLE share_grant ASSERT $value IN ['read', 'write', 'owner'];
DEFINE INDEX IF NOT EXISTS idx_share_grant_resource ON TABLE share_grant COLUMNS resource_type, resource_id;
DEFINE INDEX IF NOT EXISTS idx_share_grant_target ON TABLE share_grant COLUMNS target_type, target_id;

CREATE team:public SET
  slug = 'public',
  name = 'Public',
  type = 'system',
  created = time::now(),
  updated = time::now();
```

字段语义：

| 表 | 字段 | 说明 |
| --- | --- | --- |
| `team` | `slug` | URL/查询稳定标识；`public` 为系统保留 slug。 |
| `team` | `type` | `workspace` 为普通团队，`system` 为系统内置组。 |
| `team_member` | `role` | 团队内角色；`owner/admin` 可管理成员，`member/viewer` 只能使用被授权资源。 |
| `team_member` | `status` | `invited` 可用于后续邮件邀请；本阶段管理员直接添加用户时为 `active`。 |
| `share_grant` | `permission` | 本阶段实现 `read`；`write/owner` 先保留 schema，不开放 UI。 |

`team:public` 不创建任何 `team_member` 记录，访问判断中通过规则隐式匹配。

### 与现有 `visibility` 的关系

短期保留现有字段：

- `visibility = 'private'`：默认只允许 owner 与 admin 管理。
- `visibility = 'public'`：等价于存在 `share_grant(target_type='team', target_id='team:public', permission='read')`。

迁移策略：

1. 对现有 `visibility = 'public'` 的 source/notebook 补写 `share_grant` 到 `team:public`。
2. 新的“Share to web”动作同时写 `share_grant` 并更新 `visibility = 'public'`。
3. 查询 public 页面时仍可优先走 `visibility` 索引；查询“我可访问的资源”时需要合并 owner、普通 team grants 和 `team:public` grant。
4. 公开可撤回，但撤回只影响未来发现和匿名访问；已在公开期间被其它用户或 team 引用的资源，需要保留显式只读访问，避免已有 notebook 断链。

### 公开撤回策略

公开内容采用“可撤回，但保护已有引用”的默认策略。产品默认行为固定为 B+：公开页和匿名访问可撤回，已引用者保留只读访问。实现上用 `PUBLIC_SHARE_REVOCATION_MODE` 支持部署方调整策略：

- `preserve_references`：默认。撤回 public grant，并为已有引用者补写显式只读 grant。
- `block_if_referenced`：只要存在其它 notebook 引用，就拒绝撤回并返回 409。
- `revoke_all`：强制撤回，不保留已有引用者访问；不建议默认启用。

| 方案 | 规则 | 优点 | 代价 |
| --- | --- | --- | --- |
| A. 不可撤回 | 分享给 `team:public` 后不能删除 public grant；只能继续 public。 | 心智简单，和当前“一次公开”一致，避免外部链接失效。 | 用户误公开时无法补救，隐私风险较高。 |
| B. 可撤回 | owner/admin 可删除 `team:public` grant，并把 `visibility` 回写为 `private`。 | 符合常见分享产品预期，降低误操作风险。 | 公开链接会失效，需要清晰提示和审计。 |
| B+. 可撤回且保护已有引用 | owner/admin 可撤回全网公开；撤回时为已有引用者补写显式只读 grant。 | 兼顾撤回能力和已有 notebook 稳定性。 | 撤回不等于收回所有既有引用，需要明确告知用户。 |

本阶段默认采用 B+。UI 必须在“公开”和“撤回公开”两个动作上明确告知：

- 公开时：任何人都可以查看该资源；其他用户或 team 可以把它作为只读资源引用到自己的 notebook。
- 撤回时：资源会从公开浏览和匿名访问中移除；已经引用该资源的用户或 team 会继续拥有只读访问，不会因为撤回而断链。
- 已被外部下载、复制或导出的内容不受系统控制。

### 撤回对已有引用的影响

按当前实现，`Add existing source` 不是复制 Source，而是在 notebook 与同一个 source 之间创建 `reference` 关系。因此如果公开 source 被其它用户加入了自己的 notebook，随后 owner 撤回 public：

- 其它用户仍可能保留 notebook -> source 的 `reference` 关系。
- 但 source 的读权限会从 `public` 变回 owner-only 或显式 grant-only。
- 其它用户不再满足 source access check，打开 source 详情、下载文件、查看 status/insights、基于该 source 搜索或聊天时会失败或出现不可用状态。
- 当前系统已经禁止删除“有引用的 public source”，说明这类跨 notebook 引用被视为活跃依赖；撤回如果不处理，也会产生类似的断链问题。

因此 public 撤回不能只删除 `team:public` grant。需要选择一种引用保护策略：

| 策略 | 行为 | 适用性 |
| --- | --- | --- |
| 保守不可撤回 | 只要资源已被其它 notebook 引用，就禁止撤回 public grant，返回 409 并提示引用数量。 | 最贴近当前“public source 有引用不可删除”的策略，最安全，但用户误公开难补救。 |
| 撤回只影响未来发现 | 删除 `team:public` grant，但为所有已有引用者或其 team 补写 `share_grant(permission='read')`。 | 默认策略；公开页消失，匿名访问失效，但已引用的成员工作区不破。 |
| 复制/快照 | 用户引用 public source 时创建自己的副本或快照，撤回只影响原始资源。 | 隐私边界清晰，但存储、嵌入、更新语义更复杂。 |
| 强制断链 | 允许撤回并保留不可读 reference，UI 显示“资源已撤回”。 | 实现简单，但对用户体验和任务稳定性最差，不建议默认。 |

本阶段采用“撤回只影响未来发现”：

1. 撤回 `team:public` 时，查询该 source/notebook 的现有 `reference` 关系。
2. 对已引用该资源的 notebook owner，补写显式 `share_grant(target_type='user', permission='read')`；如果 notebook 属于 team，也可补写给对应 team。
3. 删除 `team:public` grant，并将 `visibility` 回写为 `private`。
4. public browse 与匿名访问立即失效。
5. 已经引用的成员继续只读可用，但不能编辑、删除、重试处理或变更分享。
6. audit log 记录 `share.public_revoked`，metadata 包含 preserved_grants_count 与 affected_reference_count。

这样既能撤回全网公开，又不会让其它成员已经建立的 notebook 变成不可用。

Notebook 公开撤回采用同样原则：

1. 撤回 `team:public` 时，识别公开期间已保存、引用或加入访问入口的 notebook 使用者。
2. 为这些既有使用者或其 team 补写 notebook 级 `share_grant(permission='read')`。
3. Notebook 从 public browse 移除，匿名访问失效。
4. 既有使用者仍可只读打开 notebook，并继续读取其中他们已获授权的 sources。
5. 如果 notebook 内包含未单独授权的 private sources，撤回流程需要同步为这些 source 补写只读 grant，或在预检中列出将不可用的 source 并阻止撤回。

### 权限语义

`team:public` 只授予 `read`：

- 匿名用户可读 public source/notebook。
- 登录用户可读 public source/notebook。
- 只有 owner 或 admin 可编辑、删除、重试处理、生成 insight、变更 visibility。
- public group 不出现在普通 Team 成员管理 UI 中，避免用户误以为可以管理全网成员。

### Team 与分享 API

当前阶段可继续使用：

- `PATCH /api/sources/{source_id}/visibility`
- `PATCH /api/notebooks/{notebook_id}/visibility`

本阶段新增：

| Method | Path | 说明 |
| --- | --- | --- |
| `POST` | `/api/share-grants` | 创建分享，target 可为 user 或 team；target=`team:public` 即全网公开 |
| `GET` | `/api/share-grants?resource_type=&resource_id=` | 查看资源分享状态 |
| `DELETE` | `/api/share-grants/{grant_id}` | 撤销分享；若配置为公开不可逆，则 public grant 返回 409 |
| `GET` | `/api/teams` | 列出当前用户所在 team；admin 可看全部 |
| `POST` | `/api/teams` | admin 创建 team |
| `GET` | `/api/teams/{team_id}` | 查看 team 详情和成员摘要 |
| `PATCH` | `/api/teams/{team_id}` | admin 或 team owner 更新 team 名称 |
| `DELETE` | `/api/teams/{team_id}` | admin 删除无成员、无分享、无资源依赖的普通 team；禁止删除 `team:public` |
| `GET` | `/api/teams/{team_id}/members` | 列出成员 |
| `POST` | `/api/teams/{team_id}/members` | 添加成员，或把 invited/disabled 成员恢复 active |
| `PATCH` | `/api/teams/{team_id}/members/{user_id}` | 修改团队角色或状态 |
| `DELETE` | `/api/teams/{team_id}/members/{user_id}` | 移除成员 |

权限规则：

- 系统级 admin 可管理全部 team。
- team owner/admin 可管理本 team 成员，但不能管理 `team:public`。
- 普通 team 至少保留一个 active owner。
- 普通用户可读取自己所在 team 列表和成员摘要。
- `share_grant` 创建者必须是资源 owner 或系统 admin；team owner/admin 不因为管理 team 而获得分享他人资源的权限。
- 删除普通 team 前必须确认 active members、share grants 和资源依赖均为 0；否则返回 409，响应中包含阻塞计数。

### 前端表达

分享 UI 不建议只写“Public/Private”，而应逐步过渡为“Share”语义：

- `Private`：Only me
- `Team`：Specific team
- `Public`：Anyone with access to the web

本阶段新增 Share dialog，`Public` 出现在 target 列表中，作为一个带 globe icon 的系统组。当前 VisibilitySelector 可以保留为快捷入口，但内部应调用 share grant 用例，避免两套逻辑分叉。

## 认证与权限设计

### JWT payload

新增 `role` 与 `status`，保留当前字段：

```json
{
  "sub": "app_user:admin",
  "username": "admin",
  "role": "admin",
  "status": "active",
  "auth_version": "2026-05-05T10:00:00.000000+00:00",
  "exp": 1770000000,
  "iat": 1769913600
}
```

`validate_jwt_token()` 必须在数据库中重新读取用户，并拒绝：

- 用户不存在
- `status != 'active'`
- token 中 `auth_version` 与当前用户认证版本不一致

认证版本优先级：

1. `password_changed_at`
2. `updated`
3. `created`

这样管理员禁用用户、重置密码、用户自己改密码，都能让旧 token 失效。

### 权限依赖

在 `api/auth.py` 增加：

```python
class CurrentUser(BaseModel):
    id: str
    username: str
    role: Literal["admin", "user"]
    status: Literal["active", "disabled"]
    display_name: str | None = None
    email: str | None = None

async def get_current_user(request: Request) -> CurrentUser:
    ...

async def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    ...
```

使用规则：

- 公开浏览 API 继续允许匿名。
- 普通私有 API 使用 `get_current_user` 或当前 `request.state.user_id`。
- 管理 API 必须使用 `require_admin`。
- 前端管理入口根据 `/auth/me.role` 渲染，但后端仍强制校验。

### Legacy password 模式

`OPEN_NOTEBOOK_AUTH_MODE=password` 下没有真实用户上下文。增强计划采用保守策略：

- legacy token 只能访问普通功能，不拥有管理员 API 权限。
- 若数据库已有 `admin` 用户，建议登录数据库用户获得 admin 权限。
- `/auth/status` 返回 `auth_method='legacy'` 时，前端管理用户页面显示迁移提示。

## API 设计

### Auth API 扩展

#### `GET /api/auth/me`

返回：

```json
{
  "id": "app_user:admin",
  "username": "admin",
  "email": null,
  "display_name": "Admin",
  "role": "admin",
  "status": "active",
  "locale": "zh-CN",
  "theme": "system",
  "created": "...",
  "updated": "...",
  "last_login_at": "..."
}
```

#### `PATCH /api/auth/me`

普通用户可更新：

- `display_name`
- `locale`
- `theme`

不可更新：

- `role`
- `status`
- `username`
- `email`，除非后续做邮箱验证变更流程

#### `POST /api/auth/login`

登录成功后：

- 检查用户 `status == 'active'`
- 更新 `last_login_at`
- 签发包含 `role` 的 JWT
- 写入 audit log

### 用户管理 API

新增 `api/routers/users.py`，prefix `/api/users`，全部需要 `require_admin`。

| Method | Path | 说明 |
| --- | --- | --- |
| `GET` | `/users` | 用户列表，支持分页、搜索、role/status 过滤 |
| `POST` | `/users` | 管理员创建用户，可选择发送临时密码或返回一次性密码 |
| `GET` | `/users/{user_id}` | 用户详情 + 资源统计 |
| `PATCH` | `/users/{user_id}` | 修改 `display_name`、`role`、`status` |
| `POST` | `/users/{user_id}/reset-password` | 管理员重置密码，返回一次性临时密码或发送邮件 |
| `DELETE` | `/users/{user_id}` | 仅允许删除无内容用户；否则要求先禁用 |

#### 列表查询

请求：

```http
GET /api/users?q=wang&role=user&status=active&limit=50&offset=0
```

响应：

```json
{
  "items": [
    {
      "id": "app_user:abc",
      "username": "user@example.com",
      "display_name": "User",
      "email": "user@example.com",
      "role": "user",
      "status": "active",
      "last_login_at": "...",
      "created": "...",
      "source_count": 12,
      "notebook_count": 3
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

#### 创建用户

请求：

```json
{
  "username": "researcher@example.com",
  "email": "researcher@example.com",
  "display_name": "Researcher",
  "role": "user",
  "password": "optional-manual-password"
}
```

规则：

- `username` 唯一。
- `role` 默认为 `user`。
- 如果 `password` 为空，后端生成一次性临时密码并只在响应中返回一次。
- 本阶段不支持 `send_invite` 邮件邀请；如请求中传入该字段，后端返回 422，避免用户误以为邮件邀请已生效。

#### 修改用户

规则：

- 不能把最后一个 active admin 降级或禁用。
- 管理员不能删除/禁用自己；可以修改自己的 display_name。
- 修改 `role`、`status` 后必须更新 `updated`，使旧 JWT 失效。
- 每次变更写 audit log。

## 用户服务与仓库

新增：

- `api/services/user_service.py`
- `api/services/team_service.py`
- `api/services/share_service.py`
- `open_notebook/database/repositories/user_repository.py`
- `open_notebook/database/repositories/team_repository.py`
- `open_notebook/database/repositories/share_repository.py`

`UserRepository` 负责 SurrealQL：

- `list_users(q, role, status, limit, offset)`
- `count_users(q, role, status)`
- `get_user(user_id)`
- `get_user_by_username(username)`
- `create_user(data)`
- `update_user(user_id, data)`
- `count_active_admins(excluding_user_id=None)`
- `user_resource_counts(user_id)`

`TeamRepository` 负责 SurrealQL：

- `list_teams(user_id, include_all_for_admin, q, limit, offset)`
- `get_team(team_id)`
- `get_team_by_slug(slug)`
- `create_team(data)`
- `update_team(team_id, data)`
- `delete_team(team_id)`
- `list_members(team_id, q, role, status, limit, offset)`
- `get_member(team_id, user_id)`
- `upsert_member(team_id, user_id, role, status)`
- `remove_member(team_id, user_id)`
- `count_active_owners(team_id, excluding_user_id=None)`
- `user_team_ids(user_id)`

`ShareRepository` 负责 SurrealQL：

- `list_resource_grants(resource_type, resource_id)`
- `create_grant(resource_type, resource_id, target_type, target_id, permission, created_by)`
- `delete_grant(grant_id)`
- `resource_has_public_grant(resource_type, resource_id)`
- `accessible_resource_ids(user_id, team_ids, resource_type)`

`UserService` 负责业务规则：

- 防止最后一个 admin 被降级/禁用/删除
- 生成临时密码
- 哈希密码
- 写 audit log
- 将数据库行转换为 response schema

`TeamService` 负责业务规则：

- 禁止修改或删除 `team:public`。
- 创建普通 team 时自动把创建者加入为 `owner`。
- 防止普通 team 失去最后一个 active owner。
- 只有系统 admin 或 team owner/admin 可以管理成员。
- 添加成员前验证 user 存在且 status 为 active。
- 本阶段直接添加 active 成员，不发送邀请邮件，不创建 invited 成员。
- 删除 team 前检查 active members、share grants、资源依赖；存在任一依赖则返回 409。
- 成员角色/status 变更写 audit log。

`ShareService` 负责业务规则：

- 验证资源存在与操作者权限。
- 分享给普通 team 前验证 team 存在且不是 disabled/system 异常状态。
- 分享给 `team:public` 时同步 `visibility = 'public'`。
- 如果启用公开撤回，删除 `team:public` grant 后同步 `visibility = 'private'`。
- 如果禁用公开撤回，删除 `team:public` grant 返回 409。
- 分享创建/撤回写 audit log。

## 审计日志设计

新增 table `audit_log`：

```sql
DEFINE TABLE IF NOT EXISTS audit_log SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS actor_id ON TABLE audit_log TYPE option<record<app_user>>;
DEFINE FIELD IF NOT EXISTS actor_username ON TABLE audit_log TYPE option<string>;
DEFINE FIELD IF NOT EXISTS action ON TABLE audit_log TYPE string;
DEFINE FIELD IF NOT EXISTS target_type ON TABLE audit_log TYPE option<string>;
DEFINE FIELD IF NOT EXISTS target_id ON TABLE audit_log TYPE option<string>;
DEFINE FIELD IF NOT EXISTS metadata ON TABLE audit_log TYPE option<object>;
DEFINE FIELD IF NOT EXISTS ip_address ON TABLE audit_log TYPE option<string>;
DEFINE FIELD IF NOT EXISTS user_agent ON TABLE audit_log TYPE option<string>;
DEFINE FIELD IF NOT EXISTS created ON TABLE audit_log TYPE datetime DEFAULT time::now();

DEFINE INDEX IF NOT EXISTS idx_audit_log_actor ON TABLE audit_log COLUMNS actor_id;
DEFINE INDEX IF NOT EXISTS idx_audit_log_action ON TABLE audit_log COLUMNS action;
DEFINE INDEX IF NOT EXISTS idx_audit_log_created ON TABLE audit_log COLUMNS created;
```

第一阶段记录动作：

- `auth.login.success`
- `auth.login.failed`
- `auth.password.changed`
- `auth.password.reset`
- `user.created`
- `user.updated`
- `user.disabled`
- `user.enabled`
- `user.role_changed`
- `user.deleted`
- `team.created`
- `team.updated`
- `team.deleted`
- `team.member_added`
- `team.member_updated`
- `team.member_removed`
- `share.created`
- `share.revoked`
- `share.public_enabled`
- `share.public_revoked`

API：

- `GET /api/audit-log`，admin only，支持 `actor_id`、`action`、`target_id`、时间范围、分页。

审计 metadata 禁止存储明文密码、验证码、JWT、API key。

## 所有权与数据治理

### 历史数据补齐

当前已有 `owner_id` 字段，但旧数据可能为空。设计一个管理命令或迁移后 startup repair：

- 如果只有一个 admin 用户：把 `owner_id = NONE` 的 private source/notebook 归属给 admin。
- 如果有多个用户：保持为空，但在 admin UI 中显示“未归属内容”筛选。
- public 内容 owner 为空时仍可浏览，但只有 admin 可管理。

### 用户禁用

禁用用户后：

- 不能登录。
- 已签发 token 因 `updated/auth_version` 失效。
- 其 private 内容保持不可被其他普通用户访问。
- admin 可查看资源统计，后续可转移归属。

### 用户删除

硬删除仅允许：

- 用户没有 source/notebook/note/episode 等内容。
- 用户不是最后一个 active admin。

有内容时返回 409，建议执行禁用。后续可扩展“转移归属后删除”。

### 作者展示

公共浏览接口可返回轻量 owner 信息：

```json
{
  "owner": {
    "id": "app_user:abc",
    "display_name": "Researcher"
  }
}
```

不返回 email，除非用户显式公开。

## 前端设计

### 导航

管理区不再用 `username === 'admin'` 判断。`auth-store` 增加：

```ts
role: 'admin' | 'user' | null
displayName: string | null
```

`checkAuth()` 调用 `/auth/me` 后更新 role。`AppSidebar` 按 `role === 'admin'` 显示：

- Models
- Transformations
- Settings
- Advanced
- Users
- Teams
- Audit Log

### 个人资料页

路径：`/settings/profile`

能力：

- 显示 username、role、status、last login
- 修改 display name
- 修改语言偏好
- 修改主题偏好
- 跳转修改密码

普通用户至少能看到 profile 与 change password，不暴露系统管理设置。

### 用户管理页

路径：`/settings/users` 或 `/admin/users`

建议放在现有 Settings/Advanced 管理区中，避免新增大规模布局。

页面结构：

- 顶部工具栏：搜索、role/status 筛选、创建用户按钮
- 表格：display name、username/email、role、status、last login、资源数、操作
- 行操作：编辑、启用/禁用、重置密码、删除
- 创建/编辑弹窗：复用 shadcn dialog + form

关键交互：

- 禁用/降级最后一个 admin 时，后端返回 400，前端展示明确错误。
- 重置密码成功时显示一次性密码，弹窗关闭后不再可见。
- 用户状态修改后 invalidates `['users']` 与当前 `/auth/me`。

### Team 管理页

路径：`/settings/teams` 或 `/admin/teams`

页面结构：

- 顶部工具栏：搜索、创建 team。
- Team 表格：name、slug、成员数、资源分享数、created、操作。
- 详情抽屉或详情页：成员列表、角色、状态、添加成员按钮。
- 行操作：编辑 team 名称、删除空 team、进入成员管理。

关键交互：

- `team:public` 以系统组展示在只读区域，不能编辑成员、删除或改名。
- 创建普通 team 后，创建者自动成为 owner。
- 添加成员时从 active 用户中搜索选择。
- 修改成员角色时，最后一个 owner 保护错误必须可见。
- 移除成员后 invalidates `['teams']`、`['team', id, 'members']`、相关 share grants 查询。

### Share Dialog

资源页面和列表操作中新增 share dialog：

- target selector：`Public`、当前用户可见 teams，后续可扩展指定用户。
- permission selector：本阶段固定 `read`，UI 可显示但不可切换。
- current grants：显示已分享给哪些 teams/public。
- revoke：普通 team grant 可撤回；public grant 根据产品配置决定是否允许。

公开确认文案必须包含：

- 全网用户都可以查看该资源。
- 其他用户或 team 可以把该资源只读引用到自己的 notebook。
- 公开后即使撤回，已有只读引用仍会继续可用。

撤回确认文案必须包含：

- 资源会从公开浏览和匿名访问中移除。
- 已经引用该资源的用户或 team 会保留只读访问，避免已有 notebook 断链。
- 外部下载、复制或导出的内容无法被系统收回。

如果配置为 public 不可撤回，UI 展示“已公开，不能撤回”的说明；默认配置应允许撤回并保留已有引用者只读访问。

### 审计日志页

路径：`/advanced/audit-log`

第一阶段只做只读表格：

- action
- actor
- target
- created
- metadata 摘要

### 指导闭环与标准操作引导

本阶段的用户增强不只交付功能入口，还需要让敏感操作形成“看得见、改得准、查得到”的闭环：

1. **操作前引导**：用户管理、Team 管理和 Share Dialog 显示简短标准流程，提醒操作者先确认目标、再按最小权限变更。
2. **动作中确认**：公开分享和撤回公开必须二次确认，并明确提示公开资源可以被其他用户或团队只读引用。
3. **动作后回看**：当前授权列表、用户/Team 状态和 Audit Log 共同构成回看入口，管理员可以确认谁在什么时候改了什么。
4. **文档沉淀**：新增用户操作标准文档，覆盖用户创建/禁用、Team 成员维护、资源分享、公开撤回和审计复核。

页面级标准流程：

| 页面 | 标准引导 |
| --- | --- |
| Settings -> Users | 确认身份与状态 -> 应用最小角色变更 -> 通过用户状态和审计日志确认结果 |
| Settings -> Teams | 创建/选择正确团队 -> 分配最小必要角色 -> 回看分享授权和审计事件 |
| Share Dialog | 选择公开或 Team 目标 -> 确认只读范围与公开引用行为 -> 保存/撤回后检查当前授权 |

文档入口：`docs/3-USER-GUIDE/user-management-and-sharing.md`。

## i18n

所有前端新增文案必须覆盖至少：

- `en-US`
- `zh-CN`

新增 key 分组：

```ts
users: {
  title
  createUser
  editUser
  resetPassword
  disableUser
  enableUser
  role
  status
  lastLogin
  resourceCounts
}
teams: {
  title
  createTeam
  editTeam
  deleteTeam
  members
  addMember
  removeMember
  teamOwner
  teamAdmin
  member
  viewer
  publicTeam
}
sharing: {
  title
  shareToWeb
  shareToTeam
  revokeShare
  publicShareWarning
  publicRevokeWarning
  publicNotRevocable
}
profile: {
  title
  displayName
  languagePreference
  themePreference
  saveProfile
}
auditLog: {
  title
  action
  actor
  target
  created
}
```

后续语言可先 fallback 到英文，但不能缺 key 导致运行时展示 key path。

## 测试计划

### 后端

新增或扩展：

- `tests/test_users_api.py`
- `tests/test_teams_api.py`
- `tests/test_share_grants_api.py`
- `tests/test_auth_roles.py`
- `tests/test_audit_log.py`

覆盖：

- admin 可列出/创建/禁用/启用用户。
- user 访问 `/api/users` 返回 403。
- 禁用用户不能登录。
- 禁用用户的旧 JWT 不能继续访问。
- 最后一个 active admin 不能被禁用、降级、删除。
- 登录成功更新 `last_login_at`。
- 修改密码更新 `password_changed_at` 并使旧 token 失效。
- 用户管理操作写 audit log。
- admin 可创建/更新/删除普通 team。
- 删除存在成员、share grants 或资源依赖的 team 返回 409 和阻塞计数。
- team owner/admin 可添加、更新、移除成员。
- 普通成员不能管理 team 成员。
- 不能删除或编辑 `team:public`。
- 普通 team 不能失去最后一个 active owner。
- 分享给普通 team 后，team 成员可读资源，非成员不可读 private 资源。
- 分享给 `team:public` 后匿名用户可读资源。
- public 默认撤回策略生效：匿名访问失效，已有引用者保留只读访问；如配置为不可撤回则返回 409。
- Notebook public 撤回时，已有引用者保留 notebook 只读访问，且 notebook 内 sources 不断链。
- 公开确认响应或前端文案明确提示“公开资源可以被其他人只读引用”。
- legacy password 模式不能访问 admin-only users API。

### 前端

新增或扩展：

- `frontend/src/components/layout/AppSidebar.test.tsx`
- `frontend/src/lib/stores/auth-store.test.ts`
- `frontend/src/app/(dashboard)/settings/users/page.test.tsx`
- `frontend/src/app/(dashboard)/settings/teams/page.test.tsx`
- `frontend/src/components/share/ShareDialog.test.tsx`

覆盖：

- role 为 admin 时显示管理入口。
- role 为 user 时隐藏管理入口。
- `/auth/me` 返回 role 后 store 正确保存。
- 用户列表筛选和分页调用正确 API。
- 禁用最后 admin 的错误能展示。
- Team 成员列表、添加成员、角色修改调用正确 API。
- Share dialog 可展示 public 和 teams，并处理 public 可撤回/不可撤回两种状态。
- Share dialog 在公开前提示“公开资源可以被其他人只读引用”，在撤回前提示“已有引用者会继续保留只读访问”。

### 安全回归

扩展：

- `tests/test_jwt_auth_security.py`
- `tests/test_auth_modes.py`

重点：

- token 缺 role 不应被前端视为 admin。
- 后端不能信任前端 role。
- audit metadata 不包含 password/token/code。

## 实施阶段

### 当前落地进展

已开始按本设计推进首批实现：

- 已新增 migration 21，覆盖 `app_user` 扩展、`team`、`team_member`、`share_grant`、`audit_log` 和 `team:public` 初始化。
- 已新增用户、Team、分享和审计 repository/service/router 基础结构。
- JWT 与 `/api/auth/me` 已带出 `role/status/display_name/email`，禁用用户会被登录与 JWT 校验拒绝。
- 资源读取和列表查询已接入 owner、public、直接用户 grant、team grant 的统一 read access 判断。
- Public 撤回默认策略已落到 `PUBLIC_SHARE_REVOCATION_MODE=preserve_references`，source 撤回会为已有引用 owner 保留只读 grant。
- 前端 auth-store 已保存 role/displayName/status，sidebar 已改为按 `role === 'admin'` 控制管理入口，并新增 Team 列表页面第一版。
- Team 管理页面已扩展为可创建/编辑普通 Team、查看成员、添加成员、修改成员 role/status、移除成员；`team:public` 在 UI 中只读展示。
- 用户管理页面已新增，可搜索/过滤用户、创建用户、编辑 display name/role/status、重置临时密码。
- Share Dialog 已新增并接入 Source/Notebook 列表入口，可管理 Public 与 Team 只读授权；公开和撤回公开均包含“可被只读引用/已有引用保留访问”的提示。
- Audit Log 查询 API 与只读页面已新增，系统 admin 可按 actor/action/target 过滤查看审计事件。
- 用户管理、Team 管理和 Share Dialog 已补充标准操作引导；用户文档已新增 `user-management-and-sharing.md`，用于串联确认、变更、审计回看。

尚未完成的实施项继续按下面 Phase 5 推进：未归属内容治理、Team 依赖阻塞提示的 UI 细化，以及 profile 偏好页。

### Phase 1: 后端基础

1. Migration 21：扩展 `app_user`，新增 `team`、`team_member`、`share_grant`、`audit_log`。
2. 更新 `AsyncMigrationManager` 的 up/down migration 列表。
3. 新增 `UserRepository`、`TeamRepository`、`ShareRepository` 与 `AuditLogRepository`。
4. 更新 JWT 创建和校验逻辑，加入 role/status。
5. 新增 `CurrentUser`、`get_current_user`、`require_admin`。
6. 初始化 `team:public`，并为现有 public source/notebook 补写 share grant。

验收：

- `uv run pytest tests/test_jwt_auth_security.py tests/test_auth_modes.py`
- 手动登录 admin 后 `/auth/me` 返回 role/status。
- public 页面仍能读取现有公开内容，且对应资源有 `team:public` grant。

### Phase 2: 用户、Team 与分享 API

1. 新增 Pydantic schemas。
2. 新增 `api/services/user_service.py`。
3. 新增 `api/routers/users.py` 并注册到 `api/main.py`。
4. 新增 `api/services/team_service.py`、`api/routers/teams.py`。
5. 新增 `api/services/share_service.py`、`api/routers/share_grants.py`。
6. 登录、改密码、重置密码、用户变更、Team 变更、分享变更写 audit log。

验收：

- `uv run pytest tests/test_users_api.py tests/test_teams_api.py tests/test_share_grants_api.py tests/test_auth_roles.py tests/test_audit_log.py`
- OpenAPI 中可看到 users、teams、share-grants endpoints，非授权访问返回 403。

### Phase 3: 前端身份状态

1. 扩展 `frontend/src/lib/types/auth.ts`。
2. 扩展 `auth-store` 保存 role/displayName/status。
3. 修改 `AppSidebar`，用 role 控制管理入口。
4. 新增 profile API/hook。
5. 新增 teams/share-grants API module 与 hooks。

验收：

- admin 能看到管理入口。
- 普通用户看不到管理入口，但后端仍能拦截直接访问 API。
- 当前用户可获取自己的 teams，并在 share dialog 中作为候选项。

### Phase 4: 用户与 Team 管理 UI

1. 新增 users API module 和 hooks。
2. 新增用户管理页面。
3. 新增创建/编辑/禁用/重置密码 dialog。
4. 新增 Team 管理页面。
5. 新增 Team 创建/编辑、成员添加/移除/角色修改 dialog。
6. 补齐 en-US、zh-CN 文案。

验收：

- 管理员可完整创建、禁用、启用、重置密码。
- 管理员和 team owner/admin 可完整管理普通 team 成员。
- `team:public` 在 UI 中只读展示，不能被编辑成员或删除。
- 普通用户没有入口且直接访问页面会显示 403/无权限状态。

### Phase 5: 分享 UI、审计与治理

1. 新增资源 Share dialog。
2. 接入 public 与 team share grant 创建/撤回。
3. 新增 audit log 页面。
4. 管理页显示用户和 team 资源统计。
5. 增加未归属内容检查脚本或 admin-only repair endpoint。
6. 更新 docs/security 和 API reference。
7. 在用户、Team 和分享入口补充标准操作引导，并新增用户操作指南。

验收：

- 用户管理关键动作可在 audit log 中看到。
- Team 成员管理和分享动作可在 audit log 中看到。
- Share dialog 能向 `team:public` 或普通 team 授权读取资源。
- 撤回 public 后，public browse/匿名访问失效，已有引用 notebook 不断链。
- 删除存在依赖的 Team 会被阻止，并在 UI 中展示阻塞原因。
- 未归属数据处理策略文档化。

## 风险与处理

| 风险 | 处理 |
| --- | --- |
| 当前 migration down 列表维护成本高 | 新 migration 时顺手校正 down migration 顺序，或新增测试确保 rollback 顺序正确。 |
| `username === 'admin'` 已在前端存在 | Phase 3 必须替换为服务端 role。 |
| 禁用用户旧 token 继续有效 | `validate_jwt_token()` 必须重新读 DB 并比较 status/auth_version。 |
| 创建用户返回临时密码泄漏 | 只在响应中返回一次，不写 audit metadata，不写日志。 |
| 用户删除导致孤儿内容 | 第一阶段禁止删除有内容用户，使用禁用替代。 |
| Legacy password 用户无 user_id | legacy 不给 admin 权限，引导迁移到数据库用户。 |
| Team 权限和系统 admin 权限混淆 | 明确区分系统 admin 与 team owner/admin；资源管理仍以 owner/share grant 判断为准。 |
| `team:public` 被误当成普通 team 管理 | service 层禁止成员管理、改名、删除，前端只读展示。 |
| 公开撤回策略变更影响已有链接 | 用配置和审计保护，UI 二次确认；撤回时为已有引用者保留显式只读 grant，避免 notebook 断链。 |
| Notebook 撤回时内部 Source 授权不完整 | 撤回预检必须列出 notebook 内 sources，并同步补写只读 grant；无法补齐时阻止撤回。 |
| Team 删除导致授权孤儿 | 删除前检查 members、share grants、资源依赖，存在依赖时返回 409，不做隐式级联删除。 |

## 剩余非阻塞事项

以下事项不阻塞本阶段实现，但应在后续 roadmap 中单独设计：

1. 邮箱修改与重新验证流程。
2. 用户内容转移归属，包括禁用/离职用户资产交接。
3. Credentials 用户级或 Team 级隔离。
4. 邮件邀请入组、邀请过期、邀请接受页。
5. Team 级默认 workspace、组织/租户、多 Team 层级。
6. `write/owner` share grant 和协作编辑。

## Definition of Done

- 后端有明确 role/status 权限模型。
- `/auth/me` 返回完整当前用户信息。
- 管理员可通过 UI 管理用户。
- 管理员可通过 UI 管理 Team，team owner/admin 可管理本 Team 成员。
- `team:public` 作为系统组存在，且不能被普通 Team 管理功能修改。
- 普通用户不能看到或调用系统管理功能；team owner/admin 只能管理自己有权限的普通 team。
- 禁用/降级/密码变更能使旧 token 失效。
- 用户管理关键动作进入 audit log。
- 向 `team:public` 分享的动作可被审计，并与当前 public visibility 兼容。
- 向普通 Team 分享后，Team 成员可读授权资源，非成员不可读 private 资源。
- public 撤回策略有配置、测试和清晰 UI 行为；已有引用者不会因撤回全网公开而失去只读访问。
- Team 删除有依赖预检，禁止隐式破坏授权或成员关系。
- Credentials 保持全局配置，仅系统 admin 可管理。
- 本阶段不出现发送 team 邀请邮件的 UI 或 API 行为。
- 测试覆盖 admin/user/legacy 三类认证场景。
- 文档更新到 `docs/7-DEVELOPMENT/api-reference.md` 与 `docs/5-CONFIGURATION/security.md`。
