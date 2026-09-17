import {t,language} from './i18n.js?v=20260916sound';
// Public project URLs checked on 2026-09-15. See link-audit.json.
export const zones=[
 {id:'home',title:'Vickie 的个人主页',en:'ORIGINAL HOMEPAGE',x:0,z:15,color:0xae8bc7,url:'https://ttoriaa.github.io/vikipedia/?lang=en',desc:'在 3D 世界里直接浏览 Vickie 的原版个人主页。',resources:[]},
 {id:'auto',title:'汽车数据中心',en:'BATTERY & CHARGING',x:-25,z:-13,color:0x7faaa0,url:'https://ttoriaa.github.io/automotive-benchmarking/',desc:'从电池参数到充电表现，在数据里理解每一辆车。',resources:[{title:'Automotive Product Manager Hub',url:'https://ttoriaa.github.io/product-manager/',desc:'汽车产品架构、PRD 与产品评分工作台'}]},
 {id:'ai',title:'AI 实验室',en:'VIKIPEDIAI / TOOLS / WORKFLOWS',x:23,z:-13,color:0x9e85c5,url:'https://ttoriaa.github.io/VikipediAi/',desc:'从 VikipediAi 开始探索 AI 版图、开发工具与内容创作。',resources:[{title:'Podcast Creator',url:'https://ttoriaa.github.io/podcast_creator/',desc:'独立的播客创作工具入口'},{title:'GitHub Copilot 快速指南',url:'https://ttoriaa.github.io/vikipedia/copilot_quickstart_guide.html',desc:'搭建、使用方式与应用示例'},{title:'AI 硬件产业链看板',url:'https://ttoriaa.github.io/vikipedia/ai_hardware_industry_chain_dashboard.html',desc:'产业链、供应商与相关专题'}]},
 {id:'podcast',title:'播客工作室',en:'MAKE SOME GOOD NOISE',x:24,z:15,color:0xd19878,url:'https://ttoriaa.github.io/shimai-podcast-site/index.html?lang=zh#home',desc:'在熵增世界里，做内容的熵减。这里收藏声音与表达。',resources:[]},
 {id:'gaming',title:'///M 游戏试车场',en:'CHESS / 2048 / SUDOKU / SNAKE',x:-26,z:17,color:0x6f91b1,url:'https://ttoriaa.github.io/gaming-vikipedia/',desc:'抵达试车场，打开 ///M Playground。在园区里体验 Chess、2048、Sudoku 与 Snake。',resources:[]},
 {id:'knowledge',title:'Token 知识花园',en:'SKILLS / NOTES / DECISIONS',x:-16,z:2,color:0x8aa776,url:'https://ttoriaa.github.io/vikipedia/assets/token/index.html',desc:'技能快照、项目记录与决策日志，把每一次探索变成可回看的知识。',resources:[{title:'Interview Depot',url:'https://ttoriaa.github.io/interview-depot/',desc:'IT 产品、SaaS 集成与案例知识库'}]},
 {id:'regulation',title:'C7 OTA 法规馆',en:'REGULATION / OTA HUB',x:0,z:-19,color:0x7e9faa,url:'https://ttoriaa.github.io/C7-OTA-Hub/',desc:'从统一入口浏览 C7 OTA 法规与模块，连接汽车产品与监管场景。',resources:[]},
 {id:'market',title:'Market Watch 观察站',en:'MARKET / INDUSTRY / SIGNALS',x:17,z:0,color:0xc4a56b,url:'https://ttoriaa.github.io/vikipedia/market_watch/',desc:'查看市场概览、资讯与行业线索，持续观察技术与产业变化。',resources:[]}
];

for(const zone of zones){zone.title=t(zone.title);zone.desc=t(zone.desc);for(const resource of zone.resources){resource.title=t(resource.title);resource.desc=t(resource.desc);}}
zones[0].url=`https://ttoriaa.github.io/vikipedia/?lang=${language}`;
