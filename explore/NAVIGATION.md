# 3D 世界导航与链接检查

检查日期：2026-09-15。来源：公开 Vikipedia 首页、assets/github-projects.json、GitHub 仓库目录。对 15 个候选入口执行 HTTP 请求并检查页面标题。详情见 link-audit.json。HTTP 200 表示页面可访问，不等于验证所有后台功能。

## 已配置的八个站点

| 站点 | 内容与入口 |
| --- | --- |
| Vickie 的个人主页 | 原站公开中英介绍、工作经历、教育、能力、兴趣；可在园区内打开完整原主页 |
| 汽车数据中心 | automotive-benchmarking；关联 product-manager 工作台 |
| AI 实验室 | VikipediAi；关联 Podcast Creator、Copilot 指南、AI 硬件产业链看板 |
| 播客工作室 | shimai-podcast-site |
| ///M 游戏试车场 | gaming-vikipedia：Chess、2048、Sudoku、Snake |
| Token 知识花园 | Token 知识库；关联 Interview Depot |
| C7 OTA 法规馆 | C7-OTA-Hub |
| Market Watch 观察站 | vikipedia/market_watch |

## 404 处理

原 Creator Studio 地址 `/vikipedia/shimai_creator_studio_app/pages/dashboard.html` 确认返回 404，公开仓库当前目录也没有该路径。AI 实验室主入口改为返回 200 的 VikipediAi。Podcast Creator 是另一个可用的独立创作工具，作为关联资源提供；这不表示已修复原远程 Creator Studio 服务。

## 分组取舍

- AI 硬件产业链与 Copilot 指南归入 AI 实验室；适合深入浏览，不增加独立地图建筑。
- Interview Depot 归入知识花园；汽车产品经理工作台归入汽车数据中心。
- `market-research/` 与 `vikipedia/market_watch/` 当前均展示 Market Watch，保留一个主站点，避免重复。
- `assets/github-projects.json` 标记的生成日期为 2026-07-28，仅作候选来源；所有已加入的主入口重新检查了实时 HTTP 状态。

## 导航行为

本地默认首页进入 3D 世界。旧列表保留为 `/portfolio.html`。品牌标志和“个人主页”打开世界内的个人面板。项目和关联资源默认在覆盖于 3D 场景上的 iframe 面板打开，关闭后移除 iframe 并回到停车位置；始终提供新标签入口以应对外部网站的嵌入限制。

当前仅修改本地 demo，未更改 GitHub Pages 上的原站。
