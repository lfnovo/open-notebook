# 用户增强方案草稿 v1.1

## 一、阶段目标

第一阶段建立多用户协作与配额闭环：

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
Team 资源共享
  ↓
个人资源发表/收录到整个 Team
  ↓
Team 通过 ResourceCitation 引用公开资源
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

## 三、资源归属模型

资源关系参考科研论文、期刊发表和论文引用来设计：

| 学术系统 | Open Notebook |
| --- | --- |
| 论文原文 | Notebook / Source / Note 原始资源 |
| 作者 | `created_by` / 后续可扩展 contributors |
| 作者单位或课题组 | `home_scope`，个人或 Team |
| 期刊发表 / 数据库收录 | `ResourcePublication` |
| 论文引用 | `ResourceCitation` |
| 新论文引用旧论文 | Team 基于公开资源创建自己的 Source / Note / Notebook |
| 撤稿 / 删除 | 原资源 `deleted`，引用变 `stale` |

资源本身只有一个原始归属空间，类似论文原文档案：

```text
home_scope_type: user | team
home_scope_id
created_by
status: active | deleted
```

规则：

- 个人空间创建的资源，`home_scope_type = user`
- Team 空间创建的资源，`home_scope_type = team`
- `created_by` 表示实际创建者，类似作者，永远保留
- Team 解散转移后，Team 资源成为 owner 的个人资源
- 转移后仍保留原 `created_by`
- 资源可见性、引用关系和配额消耗不直接混入原始归属字段
- 前端维护当前操作空间，后端每次校验

关系边界：

| 场景 | 原始归属 | 可见性 | 是否可编辑原件 | 配额消耗 |
| --- | --- | --- | --- | --- |
| 用户在个人空间创建资源 | 用户个人空间 | 个人可见 | owner 可编辑 | 用户配额 |
| Team 创建资源 | Team 空间 | Team 成员按角色可见 | Team 成员按角色编辑 | Team 配额 |
| 个人资源发表/收录到 Team | 仍是用户个人空间 | 整个 Team 可见 | Team 不可编辑原件 | 发表动作不计 Team 创建配额 |
| Team 引用个人资源 | 仍是用户个人空间 | Team 通过引用使用 | Team 不可编辑原件 | 引用不计配额 |
| Team 基于引用资源新增内容 | 新内容属于 Team 空间 | Team 成员按角色可见 | Team 成员按角色编辑 | Team 配额 |

后续文档统一使用以下概念：

```text
Resource               原始资源，类似论文原文
home_scope             原始归属空间
created_by             作者 / 创建者
ResourcePublication    发表 / 收录 / 公开授权
ResourceCitation       引用关系
active_scope           当前操作空间
billing_scope          配额消耗空间
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
| viewer | 查看资源、引用资源、发起临时 Chat / Ask，不能创建 Source / Note |

Viewer：

- 可以发起 Chat / Ask
- 聊天记录不保存
- 消耗 Team 模型配额
- 不能创建 Source / Note
- 尝试创建时前后端阻断并提示

## 六、个人资源发表/收录到 Team

个人资源公开给 Team，不改变原始归属，语义上类似论文发表到期刊、或被资料库收录。

建议模型：

```text
ResourcePublication
  resource_type
  resource_id
  published_from_scope
  published_to_team_id
  published_by
  published_at
  status: active | stale
  irreversible: true
```

发表/收录规则：

- 个人资源可以公开给整个 Team
- 公开后不可收回
- 公开前需要二次确认
- UI 明显标识已公开 / 已收录到 Team
- Team 不能编辑原个人资源
- Team 只能引用原资源，不能获得所有权
- 原资源仍属于个人空间
- 公开动作不消耗 Team 创建配额
- Team 中的引用不计入配额

公开不是移动，也不是复制。

```text
个人资源原文
  ↓
ResourcePublication：发表/收录到 Team
  ↓
Team 创建 ResourceCitation
  ↓
Team 成员通过引用使用
```

## 七、ResourceCitation

ResourceCitation 表示 Team 对公开资源的引用，类似论文参考文献，而不是文件系统链接。

Team 创建 ResourceCitation 的前提是存在有效的 ResourcePublication。没有发表/收录关系，Team 不能直接引用其他个人空间的资源。

建议模型：

```text
ResourceCitation
  citing_scope_type: team
  citing_scope_id
  cited_resource_type
  cited_resource_id
  cited_publication_id
  cited_by
  cited_at
  status: active | stale
```

引用范围：

```text
整个 Team 可见
```

引用状态：

```text
active | stale
```

变为 stale 的情况：

- 原资源被 owner 强制删除
- 原资源不可访问
- 原 owner 退出 Team 后访问条件失效

原 owner 退出 Team：

- 引用关系保留
- 可标记为 stale
- UI 标注引用可能不可用
- Team 不获得编辑权
- 不自动复制原资源

原 owner 强制删除资源：

- 允许删除
- 原资源标记为删除
- 相关 ResourceCitation 标记为 stale
- Team 中展示为失效引用

ResourceCitation 删除规则：

- 没有被其他 Notebook 或 Note 引用时，可以移除
- 已被引用时，普通成员不可移除
- admin/owner 可以管理引用

## 八、公开 Notebook 上下文新增内容

当 Team 成员在公开引用的 Notebook 上下文中新增内容，语义上类似新论文引用旧论文：

- 新 Source / Note 是 Team 自己的新资源
- 新资源的 `home_scope_type = team`
- 新资源的 `created_by = 当前用户`
- 新资源通过 ResourceCitation 引用了原个人 Notebook
- 消耗 Team 配额
- 不写回原个人 Notebook
- 原 Notebook 保持只读

UI 需要提示：

```text
你正在 Team 空间中使用公开引用的 Notebook，新内容将保存到当前 Team。
```

## 九、删除与引用

第一阶段引用定义：

```text
被其他 Notebook 引用
被其他 Note 引用
```

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
- 若已公开并被 Team 引用，删除后原资源标记为 deleted
- 相关 ResourceCitation 标记为 stale
- Team 中显示失效引用

## 十、Team 解散

Team 解散规则：

- 只有 owner 可解散
- Team 自有资源转为 owner 个人资源
- 被公开到 Team 的个人资源不转移
- Team ResourceCitation 失效
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

配额跟随操作发生空间，而不是简单跟随资源原始归属：

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

公开 / 引用规则：

- ResourcePublication 不消耗 Team 创建配额
- ResourceCitation 不计入 Team 配额
- 基于引用资源发起 Chat / Ask，消耗 Team 模型配额
- 在公开 Notebook 上下文中新增 Source / Note，消耗 Team Source / Note 配额

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

这版已经可以达成第一阶段闭环：

```text
用户能登录
用户有个人空间
用户能查看 Profile
付费用户能创建 Team
免费用户能加入 Team
Team 能邀请成员
Team 能共享自有资源
个人资源能发表/收录到 Team
Team 能通过 ResourceCitation 使用公开资源
角色权限能阻断不允许的操作
Viewer 能临时对话但不落历史
资源删除有引用规则
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
