# 用户增强方案草稿 v1.2

## 一、阶段目标

第一阶段优先服务个人用户。Team 不是独立于个人体系之外的复杂组织模型，而是个人用户的集合，以及个人之间共享资源、共同使用 Team 配额的协作形式。

目标闭环：

```text
微信扫码登录
  ↓
Profile
  ↓
最近使用空间
  ↓
个人空间 / Team 空间
  ↓
付费用户创建 Team
  ↓
免费用户加入 Team
  ↓
邀请链接
  ↓
Team 创建自有资源
  ↓
个人资源授权给 Team 可见和可用
  ↓
Team 基于共享资源进行 Chat / Ask / 新增资料
  ↓
权限阻断
  ↓
滚动 30 天配额
  ↓
管理员配置套餐、模型档位与 Team 限制
```

暂不包含：

- Podcast
- 通用输出物抽象
- 支付链路
- 企业 SSO
- 单资源 ACL
- 资源移动
- Team 解散审计记录
- 公开后撤回

## 二、登录与 Profile

第一阶段只做微信 Web 扫码登录。

登录流程：

```text
微信扫码授权
  ↓
系统识别微信身份
  ↓
已绑定则登录
  ↓
未绑定则创建用户
  ↓
进入最近使用空间；不可用则进入个人空间
```

Profile 包含：

- 昵称
- 头像
- 登录方式
- 绑定状态
- 所属 Team
- 当前套餐
- 配额概览
- 最近使用空间

## 三、资源归属与共享模型

资源关系参考科研论文、期刊收录和论文引用来理解，但第一阶段实现保持轻量：

| 学术系统 | Open Notebook |
| --- | --- |
| 论文原文 | Notebook / Source / Note 原始资源 |
| 作者 | `created_by` |
| 当前所在单位或课题组 | `current_scope`，个人或 Team |
| 期刊发表 / 数据库收录 | `TeamResourceGrant` |
| 论文引用 | `ResourceReference` |
| 撤稿 / 删除 | 原资源 `deleted`，共享授权或引用展示为失效 |

第一阶段只保留三个核心概念：

```text
Resource              资源原件
TeamResourceGrant     个人资源授权给 Team 可见和可用
ResourceReference     Notebook / Note / Source 之间的内容引用
```

资源本身记录当前归属空间：

```text
current_scope_type: user | team
current_scope_id
created_by
status: active | deleted
```

规则：

- 个人空间创建的资源，`current_scope_type = user`
- Team 空间创建的资源，`current_scope_type = team`
- `created_by` 表示实际创建者，类似作者，永远保留
- Team 解散后，Team 自有资源转为 owner 的个人资源，`current_scope` 更新为 owner 的个人空间
- 转移后仍保留原 `created_by`
- 可见性、引用关系和配额消耗不混入 `current_scope`
- 前端维护当前操作空间，后端每次校验

关系边界：

| 场景 | 当前归属 | 可见性 | 是否可编辑原件 | 配额消耗 |
| --- | --- | --- | --- | --- |
| 用户在个人空间创建资源 | 用户个人空间 | 个人可见 | owner 可编辑 | 用户配额 |
| Team 创建资源 | Team 空间 | Team 成员按角色可见 | Team 成员按角色编辑 | Team 配额 |
| 个人资源授权给 Team | 仍是用户个人空间 | 整个 Team 可见 | Team 不可编辑原件 | 授权不计 Team 创建配额 |
| Team 基于共享资源 Chat / Ask | 仍是用户个人空间 | Team 通过授权使用 | Team 不可编辑原件 | Team 模型配额 |
| Team 基于共享资源新增内容 | 新内容属于 Team 空间 | Team 成员按角色可见 | Team 成员按角色编辑 | Team 配额 |

后续文档统一使用以下概念：

```text
Resource              资源原件
current_scope         当前归属空间
created_by            创建者 / 作者
TeamResourceGrant     共享授权 / 收录到 Team
ResourceReference     内容引用关系
active_scope          当前操作空间
billing_scope         配额消耗空间
```

## 四、Team 与邀请

免费用户：

- 可以加入 Team
- 不能创建 Team
- 在 Team 空间使用 Team 配额
- 在个人空间使用免费个人配额

付费用户：

- 可按套餐创建 Team
- 创建 Team 数、成员数等受管理员配置限制

邀请采用链接 token。

邀请链接支持：

- 过期时间
- 最大使用次数
- 已使用次数
- 邀请角色
- 撤销
- 防重复加入

Team 限制由系统管理员配置。

## 五、角色权限

| 角色 | 权限 |
| --- | --- |
| owner | 管理 Team、成员、配额、解散 Team |
| admin | 邀请成员、管理 Team 资源、删除有引用资源 |
| member | 创建/编辑 Team 资源，删除自己创建且无引用资源 |
| viewer | 查看 Team 资源和共享资源，发起临时 Chat / Ask，不能创建 Source / Note |

Viewer：

- 可以查看 Team 自有资源
- 可以查看已授权给 Team 的个人资源
- 可以发起 Chat / Ask
- 聊天记录不保存
- 消耗 Team 模型配额
- 不能创建 Source / Note
- 不能创建持久引用或修改 Team 状态
- 尝试创建时前后端阻断并提示

## 六、个人资源授权给 Team

个人资源授权给 Team，不改变资源归属，语义上类似论文被某个资料库收录：Team 获得查看和使用资格，但不能编辑原件。

建议模型：

```text
TeamResourceGrant
  team_id
  resource_type
  resource_id
  granted_by
  granted_at
  status: active | stale
  irreversible: true
```

授权规则：

- 个人资源可以授权给整个 Team
- 只有资源 owner 可以授权自己的个人资源
- 资源 owner 必须是目标 Team 的成员
- viewer 不能创建 TeamResourceGrant
- 授权后不可收回
- 不可收回是用户侧规则；系统管理员可因合规、异常处置或资源风险手动失效
- 授权前需要二次确认
- UI 明显标识已共享给 Team
- Team 不能编辑原个人资源
- Team 可以查看、检索、Chat / Ask 该资源
- Team 可以基于该资源创建自己的 Source / Note
- 原资源仍属于个人空间
- 授权动作不消耗 Team 创建配额
- TeamResourceGrant 不计入 Team 配额
- owner 退出 Team 不影响已经授权给 Team 的资源

授权不是移动，也不是复制。

```text
个人资源原件
  ↓
TeamResourceGrant：授权给 Team
  ↓
Team 成员按角色查看和使用
  ↓
Team 新增内容保存为 Team 自有资源
```

## 七、ResourceReference

ResourceReference 表示资源之间的内容引用，例如 Note 引用了 Source，或 Notebook 引用了某个共享资源。它不是跨空间权限对象。

建议模型：

```text
ResourceReference
  from_resource_type
  from_resource_id
  to_resource_type
  to_resource_id
  created_by
  created_at
  status: active | stale
```

第一阶段引用定义：

```text
被其他 Notebook 引用
被其他 Note 引用
```

规则：

- Team 创建 ResourceReference 的前提是用户对引用目标有访问权
- 如果引用目标是个人资源，必须存在有效的 TeamResourceGrant
- Viewer 不能创建持久 ResourceReference
- ResourceReference 不计入配额
- 原资源被强制删除后，相关 ResourceReference 标记为 stale

## 八、共享资源上下文新增内容

当 Team 成员在共享 Notebook 或共享 Source 的上下文中新增内容：

- 只有 owner/admin/member 可以新增 Source / Note
- 只有 owner/admin/member 可以创建持久 ResourceReference
- viewer 只能查看共享资源并发起临时 Chat / Ask
- 新 Source / Note 是 Team 自己的新资源
- 新资源的 `current_scope_type = team`
- 新资源的 `created_by = 当前用户`
- 新资源可以通过 ResourceReference 记录与共享资源的引用关系
- 消耗 Team 配额
- 不写回原个人资源
- 原个人资源保持只读

UI 需要提示：

```text
你正在 Team 空间中使用共享资源，新内容将保存到当前 Team。
```

## 九、删除与引用

Team 资源删除规则：

```text
无引用：
  创建者可删除
  admin/owner 可删除

有引用：
  admin/owner 可删除
```

个人资源删除规则：

- owner 可以强制删除
- 若已授权给 Team，删除后原资源标记为 deleted
- 相关 TeamResourceGrant 标记为 stale
- 相关 ResourceReference 标记为 stale
- Team 中显示失效共享资源

TeamResourceGrant 失效情况：

- 原资源被 owner 强制删除
- 原资源不可访问
- Team 解散
- 系统管理员因异常情况手动失效

owner 退出 Team 不会让 TeamResourceGrant 失效。

## 十、Team 解散

Team 解散规则：

- 只有 owner 可解散
- Team 自有资源转为 owner 个人资源
- 被授权给 Team 的个人资源不转移
- TeamResourceGrant 失效
- 转移后的 Team 自有资源内部 ResourceReference 保留
- 指向原 TeamResourceGrant 共享资源的 ResourceReference 标记为 stale
- Team 成员关系失效
- Team 不再出现在空间切换器中
- 转移后的资源保留原 `created_by`

提示文案方向：

```text
Team 资源将转为你的个人资源，成员将失去访问权限。
```

## 十一、配额

周期：

```text
滚动 30 天
```

作用域：

```text
个人空间操作 → 用户配额
Team 空间操作 → Team 配额
```

配额跟随操作发生空间，而不是简单跟随资源当前归属：

```text
active_scope → billing_scope
```

指标：

| 指标 | 类型 |
| --- | --- |
| Notebook 数 | 限制型 |
| Source 数 | 限制型 |
| 存储容量 | 用量型 |
| embedding tokens | 用量型 |
| chat tokens | 用量型 |
| generation tokens | 用量型 |
| Team 成员数 | 限制型 |
| Team 数 | 限制型 |

共享 / 引用规则：

- TeamResourceGrant 不消耗 Team 创建配额
- ResourceReference 不计入 Team 配额
- 基于共享资源发起 Chat / Ask，消耗 Team 模型配额
- 在共享资源上下文中新增 Source / Note，消耗 Team Source / Note 配额

## 十二、模型档位

模型档位由系统管理员配置。

系统识别：

```text
basic
standard
advanced
premium
```

管理员配置：

```text
provider + model → tier
```

套餐配置：

```text
plan → allowed_model_tiers
plan → rolling_30_day_limits
plan → team_limits
```

模型调用前检查：

- 空间访问权
- 角色权限
- 模型档位权限
- 滚动 30 天 token 余额

## 十三、管理员配置

系统管理员配置：

- 套餐
- 个人配额
- Team 配额
- Team 创建上限
- Team 成员上限
- 邀请链接最大使用次数
- 邀请链接有效期
- 模型档位映射
- 每个套餐可用模型档位

## 十四、闭环校验

这版可以用更轻量的方式达成第一阶段闭环：

```text
用户能登录
用户有个人空间
用户能查看 Profile
付费用户能创建 Team
免费用户能加入 Team
Team 能邀请成员
Team 能创建自有资源
个人资源能通过 TeamResourceGrant 授权给 Team
Team 能查看和使用共享资源
Team 能基于共享资源创建自己的内容
角色权限能阻断不允许的操作
Viewer 能临时对话但不落历史
资源删除有引用和失效规则
Team 解散有资源归属规则
配额按滚动 30 天生效
模型档位由管理员配置
```

后续详细设计可以围绕这版继续拆：

- 数据模型
- API 边界
- 权限矩阵
- 配额计算
- 前端页面与交互
- 迁移策略
- 测试计划
