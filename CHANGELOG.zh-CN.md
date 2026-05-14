# 变更日志

本文档记录本项目的重要变更。英文版本见 [CHANGELOG.md](CHANGELOG.md)。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，项目遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [未发布]

### 新增
- 新增多用户管理基础能力：用户列表、创建、更新、个人资料编辑、角色/状态管理、密码重置/修改，以及审计日志查看界面。
- 新增团队管理能力：支持 owner/admin/member/viewer 团队角色、团队成员管理、团队模型与转换 allowlist，以及团队感知的默认模型解析。
- 新增私有、团队共享、公开内容的资源分享能力，包括分享弹窗、公开浏览页面、public/team 授权、资源可见性标识，以及访问变更审计事件。
- 新增 Workspace 架构基础：personal/team workspace 模型、工作区切换、Notebook/Source 工作区归属、Workspace 策略、资源能力判断，以及 Notebook 移动 API/UI。
- 新增第三方 External API 集成：支持外部服务提供 Source 搜索/拉取和输出生成，包含管理员配置界面、命令执行、团队授权、配额追踪、OpenAPI/文档，以及 paper-search 示例插件。
- 新增微信开放平台网页扫码登录/注册，包含 OAuth 回调、i18n 错误提示、可选用户绑定/创建，以及部署环境变量配置。
- 新增面向 `lumina.yinhour.com` 的 GitHub 源码部署路径：通过一键脚本从 `origin/online` 部署到阿里云，应用服务使用 systemd，Nginx/Certbot 负责公网入口，环境变量持久化到服务器，SurrealDB 由 Docker Compose 托管。
- 新增 Lumina 在线测试站首页合规 footer，包含公司版权、隐私政策、法律声明、ICP备案和公安备案链接。

### 变更
- 将基于用户名判断管理员的逻辑替换为后端角色与权限检查，覆盖管理入口、设置、模型选择、Source/Notebook 操作和命令面板可见性。
- Notebook、Source、Note、搜索、聊天、转换和 Source 处理流程统一接入 owner/team/share/workspace 感知的权限与能力检查。
- 聊天、Source Chat、Ask/搜索、转换、工具、Embedding 和大上下文默认模型使用团队感知的运行时模型策略。
- 优化访客/公开页面与认证页面结构：增加共享访客页面壳、独立公开布局、嵌入式登录/注册面板，以及一致的访客导航。
- 扩展管理、分享、Workspace、External API、认证和权限相关界面的 i18n 覆盖。
- 微信首次登录自动创建用户时遵守 `ALLOW_PUBLIC_REGISTRATION`，线上关闭公开注册时仅允许已绑定微信身份的用户登录。
- 强化阿里云部署流程：仅从已同步的 `origin/online` 更新服务器，保留 `/opt/lumina/shared/.env`，部署时重启 API/worker/frontend，并以 `lumina` 服务用户身份输出已部署 commit。

### 修复
- 修复 Note API、Chat Session 删除、Source 删除、Notebook-Source 移除、可见性变更和 Source 详情操作中的权限缺口。
- 撤回公开访问时保留 Notebook Source 授权和既有只读引用，避免已保存引用失效。
- 修复 Source 列表分组、创建者展示、Insight/Reference 计数，以及共享/公开资源的只读 UI 状态。
- 修复团队创建/删除边界、团队成员可见性、可分配用户查询，以及切换用户后的 Profile/Team 状态刷新。
- 修复认证与个人资料体验，包括历史用户资料保存、语言/主题偏好持久化、密码修改入口，以及微信登录 loading/disabled 视觉状态。
- 修复数据库迁移加载逻辑，确保所有编号迁移都能被一致执行。
- 修复首次阿里云上线过程中暴露的部署兼容和运行问题：旧版 `uv` 命令行为、服务器 checkout 权限检测、SurrealDB 就绪等待、公网 IP 查询超时边界、命令队列表结构迁移，以及 Next.js standalone 静态资源缺失导致的前端 chunk 404。

### 文档
- 补充用户/团队/分享操作流程、权限模型闭环、Workspace 架构演进、向量/KG scoped 维护后续计划、第三方 API 合约，以及非 Docker 在线部署文档。
- 补充微信网页登录环境变量部署说明，并说明微信首次创建用户与 `ALLOW_PUBLIC_REGISTRATION` 的关系。
- 补充 2026-05-13 阿里云在线测试站上线记录，包括 GitHub `online` 同步、服务器验证命令、SurrealDB Docker Compose 运维、外网依赖超时/代理处理、静态资源排障和密钥处理规则。
- 移除过时的本地计划文件，将仍有效的计划沉淀到项目文档结构中。
