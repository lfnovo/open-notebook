Re: [lfnovo/open-notebook] Feat/localization tests docker (PR #371)
cubic-dev-ai[bot]<notifications@github.com>
由
noreply
@
github.com
代发
lfnovo/open-notebook<open-notebook@noreply.github.com>
mison<1360962086@qq.com>
,
Author<author@noreply.github.com>
@cubic-dev-ai[bot] commented on this pull request.

10 issues found across 17 files (changes from recent commits).

Prompt for AI agents (all issues)
Reply with feedback, questions, or to request a fix. Tag @cubic-dev-ai to re-run a review.

In frontend/src/lib/locales/en-US/index.ts:

> - statusCompleted: "Completed",

- statusFailed: "Failed",
- statusPreparingDesc: "Preparing to process",
- statusQueuedDesc: "Waiting to be processed",
- statusProcessingDesc: "Being processed",
- statusCompletedDesc: "Successfully processed",
- statusFailedDesc: "Processing failed",
- failedToLoad: "Failed to load sources",
- allSourcesDesc: "View all your sources here. You can add new sources or manage existing ones.",
- allSources: "All Sources",
- insights: "Insights",
- yes: "Yes",
- no: "No",
- loadingMore: "Loading more...",
- noSourcesYet: "No sources yet",
- addNew: "Add New Source",
  P2: Duplicate addNew key in sources object. This key already exists earlier in the same object (line 244). Remove this duplicate entry.

Prompt for AI agents

In frontend/src/lib/locales/en-US/index.ts:

> +export const enUS = {

- common: {
- search: "Search...",
- create: "New",
- new: "New",
- cancel: "Cancel",
- delete: "Delete",
- edit: "Edit",
- theme: "Theme",
- signOut: "Sign Out",
- noMatches: "No matches found",
- tryDifferentSearch: "Try using a different search term.",
- light: "Light",
- dark: "Dark",
- system: "System",
- loading: "Loading...",
  P1: Duplicate loading key in common object. The second occurrence on line 59 will overwrite this value. Either remove this line or consolidate the two values.

Prompt for AI agents

In frontend/src/lib/locales/zh-CN/index.ts:

> - failedToUpdateNote: "更新笔记失败",

- noteDeletedSuccess: "笔记删除成功",
- failedToDeleteNote: "删除笔记失败",
- createNew: "创建新笔记本",
- createNewDesc: "输入名称和可选描述以开始。",
- descPlaceholder: "在此添加有关此笔记本的更多信息...",
- createSuccess: "笔记本创建成功",
- updateSuccess: "笔记本更新成功",
- deleteSuccess: "笔记本删除成功",
- },
- sources: {
- title: "来源",
- add: "添加来源",
- addNew: "添加新来源",
- addExisting: "添加现有来源",
- addNew: "添加新来源",
  P2: Duplicate key addNew in the sources object. This key already exists earlier in the object. Remove this duplicate entry.

Prompt for AI agents

In frontend/src/lib/locales/zh-CN/index.ts:

> - connectErrorHint: "无法连接到服务器。请检查 API 是否正在运行。",

- },
- navigation: {
- collect: "采集",
- process: "处理",
- create: "创作",
- manage: "管理",
- sources: "来源",
- notebooks: "笔记本",
- askAndSearch: "询问与搜索",
- search: "搜索",
- ask: "提问",
- podcasts: "播客",
- models: "模型",
- transformations: "转换",
- transformation: "转换",
  P2: Duplicate key transformation in the navigation object. This key was already added earlier in the same object. Remove this duplicate entry.

Prompt for AI agents

In frontend/src/lib/locales/zh-CN/index.ts:

> - saveChanges: "保存更改",

- name: "名称",
- default: "默认",
- notFound: "未找到",
- reasoning: "推理过程",
- searchTerms: "搜索词",
- strategy: "策略",
- individualAnswers: "独立回答 ({count})",
- finalAnswer: "最终回答",
- notebookLabel: "笔记本: {name}",
- itemNotFound: "未找到该 {type}",
- accessibility: {
-      navigation: "导航",
-      transformationViews: "转换视图",
-      searchKB: "向知识库提问或搜索",
-      searchNotebooks: "搜索笔记本",
  P2: Duplicate key searchNotebooks in the accessibility object. This key was already added earlier in the same object. Remove this duplicate entry.

Prompt for AI agents

In frontend/src/lib/locales/zh-CN/index.ts:

> - edit: "编辑",

- actions: "快捷操作",
- theme: "主题",
- signOut: "退出登录",
- loading: "加载中...",
- note: "笔记",
- insight: "洞察",
- newSource: "新建来源",
- newNotebook: "新建笔记本",
- newPodcast: "新建播客",
- noMatches: "没有找到匹配项",
- tryDifferentSearch: "请尝试使用不同的关键词搜索。",
- light: "亮色",
- dark: "暗色",
- system: "系统",
- loading: "加载中...",
  P1: Duplicate key loading in the common object. This key was already added earlier in this same PR. The second occurrence will override the first. Remove this duplicate block (lines with loading, note, insight, newSource, newNotebook, newPodcast).

Prompt for AI agents

In frontend/src/lib/locales/zh-TW/index.ts:

> - failedToUpdateNote: "更新筆記失敗",

- noteDeletedSuccess: "筆記刪除成功",
- failedToDeleteNote: "刪除筆記失敗",
- createNew: "新增筆記本",
- createNewDesc: "輸入名稱和可選描述以開始。",
- descPlaceholder: "在此新增有關此筆記本的更多資訊...",
- createSuccess: "筆記本新增成功",
- updateSuccess: "筆記本更新成功",
- deleteSuccess: "筆記本刪除成功",
- },
- sources: {
- title: "來源",
- add: "新增來源",
- addNew: "新增新來源",
- addExisting: "新增現有來源",
- addNew: "新增新來源",
  P2: Duplicate key addNew in sources object. This key already exists earlier in the same object. Remove this duplicate line.

Prompt for AI agents

In frontend/src/lib/locales/zh-TW/index.ts:

> - default: "預設",

- modelConfiguration: "模型設定",
- resetToDefault: "重置為預設",
- notFound: "未找到",
- reasoning: "推理過程",
- searchTerms: "搜尋詞",
- strategy: "策略",
- individualAnswers: "獨立回答 ({count})",
- finalAnswer: "最終回答",
- notebookLabel: "筆記本: {name}",
- itemNotFound: "未找到該 {type}",
- accessibility: {
-      navigation: "導覽",
-      transformationViews: "轉換視圖",
-      searchKB: "向知識庫提問或搜尋",
-      searchNotebooks: "搜尋筆記本",
  P2: Duplicate key searchNotebooks in common.accessibility object. This key is defined twice within the same object block. Remove this duplicate line.

Prompt for AI agents

In frontend/src/lib/locales/zh-TW/index.ts:

> - actions: "快捷操作",

- theme: "主題",
- signOut: "登出",
- loading: "載入中...",
- note: "筆記",
- insight: "洞察",
- newSource: "新增來源",
- newNotebook: "新增筆記本",
- newPodcast: "新增播客",
- nameRequired: "此為必填項",
- noMatches: "沒有找到匹配項",
- tryDifferentSearch: "請嘗試使用不同的關鍵詞搜尋。",
- light: "亮色",
- dark: "暗色",
- system: "系統",
- loading: "載入中...",
  P1: Duplicate keys in common object: loading, note, insight, newSource, newNotebook, newPodcast are defined twice. In JavaScript objects, duplicate keys cause the later value to silently override the earlier one. This appears to be a copy-paste error. Remove these 6 duplicate lines.

Prompt for AI agents

In frontend/src/components/podcasts/SpeakerProfilesPanel.tsx:

> @@ -104,8 +106,8 @@ export function SpeakerProfilesPanel({

                       className="text-xs"
                     >
                       {usageCount > 0

-                        ? `Used by ${usageCount} episode${usageCount === 1 ? '' : 's'}`
-                        : 'Unused'}

*                        ? (usageCount === 1 ? t.podcasts.usedByCount_one : t.podcasts.usedByCount_other.replace('{count}', usageCount.toString()))
  P1: Missing translation keys usedByCount_one and usedByCount_other in zh-CN locale. Simplified Chinese users will see untranslated key paths like "podcasts.usedByCount_one" instead of proper translations. Add these keys to the zh-CN locale file.

Prompt for AI agents

—
Reply to this email directly, view it on GitHub, or unsubscribe.
You are receiving this because you authored the thread.
