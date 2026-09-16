const saved=(()=>{try{return localStorage.getItem('vikipedia-drive-language')}catch{return null}})();
export const language=new URLSearchParams(location.search).get('lang')==='en'?'en':new URLSearchParams(location.search).get('lang')==='zh'?'zh':saved==='en'?'en':'zh';
const messages={
 'Vickie 的个人主页':"Vickie's Homepage",'汽车数据中心':'Automotive Data','AI 实验室':'AI Lab','播客工作室':'Podcast Studio','///M 游戏试车场':'///M Playground','Token 知识花园':'Token Garden','C7 OTA 法规馆':'C7 OTA Hub','Market Watch 观察站':'Market Watch',
 '在 3D 世界里直接浏览 Vickie 的原版个人主页。':"Explore Vickie's original homepage inside the 3D world.",
 '从电池参数到充电表现，在数据里理解每一辆车。':'Explore cars through battery specifications and charging data.',
 '汽车产品架构、PRD 与产品评分工作台':'Automotive architecture, PRDs and product scoring',
 '从 VikipediAi 开始探索 AI 版图、开发工具与内容创作。':'Explore the AI landscape, development tools and content creation with VikipediAi.',
 '独立的播客创作工具入口':'A dedicated podcast creation tool','GitHub Copilot 快速指南':'GitHub Copilot Quickstart','搭建、使用方式与应用示例':'Setup, workflows and examples','AI 硬件产业链看板':'AI Hardware Supply Chain','产业链、供应商与相关专题':'Supply chains, suppliers and research',
 '在熵增世界里，做内容的熵减。这里收藏声音与表达。':'Find clarity in a noisy world through voices and storytelling.',
 '抵达试车场，打开 ///M Playground。在园区里体验 Chess、2048、Sudoku 与 Snake。':'Visit ///M Playground for Chess, 2048, Sudoku and Snake inside the world.',
 '技能快照、项目记录与决策日志，把每一次探索变成可回看的知识。':'Turn exploration into reusable knowledge with skills, project notes and decision logs.',
 'IT 产品、SaaS 集成与案例知识库':'IT products, SaaS integrations and case studies',
 '从统一入口浏览 C7 OTA 法规与模块，连接汽车产品与监管场景。':'Connect automotive products and regulatory requirements through C7 OTA resources.',
 '查看市场概览、资讯与行业线索，持续观察技术与产业变化。':'Follow market overviews, news and signals across technology and industry.',
 '开车，去发现。':'Drive to discover.','开车，':'Drive.','发现。':'Discover.','去':'Go ',
 '每一个路口，都是一个新想法。':'A new idea around every corner.','欢迎来到 Vickie 的创意园区。':"Welcome to Vickie's creative world.",
 '可驾驶探索的三维作品园区':'A drivable 3D portfolio world','自由探索':'Free roam','切换声音':'Toggle sound','声音 · 关':'Sound · Off','声音 · 开':'Sound · On','设置':'Settings','个人主页':'Homepage','展区已探索':'destinations explored','打开园区地图':'Open world map','查看作品':'Explore project','驾驶':'Drive','刹车':'Brake','复位':'Reset','园区导航':'World map','展开地图':'Expand map','车辆位置与八个站点':'Car position and eight destinations','欢迎广场':'Welcome plaza','拖动摇杆驾驶':'Drag joystick to drive','交互 E':'Interact E','关闭面板':'Close panel',
 '你的好奇心，':'Your curiosity.','现在可以驾驶了。':'Now on wheels.','正在搭建你的探索世界…':'Building your world…','小车已就位。八个站点，等你探索。':'Your car is ready. Eight destinations await.','静音出发 →':'Start quietly →','有声出发 ♫':'Start with sound ♫','WASD / 方向键驾驶 · 靠近路牌按 E':'WASD / arrows to drive · E near a destination','手机使用左侧摇杆 · 随时打开地图快速到达':'On mobile, use the joystick · Open the map to travel instantly','直接浏览作品列表':'Browse original portfolio',
 '此浏览器暂时无法播放声音，可继续静音探索。':'Audio is unavailable in this browser. You can explore quietly.','探索完成！所有站点都留下了你的足迹 ✳':'All destinations explored! You have been everywhere ✳','已停靠安全位置，继续探索吧。':'Parked safely. Keep exploring!',
 '下一站，去哪里？':'Where to next?','选择一个展区快速到达，也可以关闭地图，沿着道路自由探索。':'Choose a destination to travel instantly, or close the map and follow the roads.','已探索':'Explored','到这里':'Travel here','方向键 / WASD 驾驶 · M 地图 · E 交互 · R 复位':'Arrows / WASD drive · M map · E interact · R reset',
 '按你的节奏探索。':'Explore your way.','开启声音':'Enable sound','环境音乐':'Ambient music','车辆与交互音效':'Car and interaction sounds','画质':'Graphics','高 · 柔和阴影':'High · soft shadows','低 · 流畅优先':'Low · performance','转向灵敏度':'Steering sensitivity','减少装饰动画':'Reduce decorative motion',
 'W / ↑ 前进 · S / ↓ 倒车':'W / ↑ forward · S / ↓ reverse','A D / ← → 转向 · Space 刹车':'A D / ← → steer · Space brake','E 查看作品 · M 地图 · R 车辆复位':'E project · M map · R reset car','手机：拖动摇杆驾驶，点击右侧按钮刹车或交互。':'Mobile: drag the joystick; use the buttons to brake or interact.','画质、音量与操控偏好保存在当前浏览器。每次进入由你选择是否开启声音。':'Graphics, volume and controls are saved in this browser. Sound is always opt-in.','车辆回到欢迎广场':'Return to welcome plaza','重新探索':'Reset exploration',
 '试一试：充电时间估算':'Try it: charging time estimate','演示条件：75 kWh 电池，从 20% 充到 80%。用平均功率估算，不代表实际车型表现。':'Demo: a 75 kWh battery charging from 20% to 80%. Uses average power; not real vehicle performance.','平均充电功率':'Average charging power','分钟':'minutes','45 kWh ÷ 平均功率 × 60':'45 kWh ÷ average power × 60',
 '试一试：Creator Studio':'Try it: Creator Studio','选择一份示例素材':'Choose a sample topic','为什么充电功率不等于充电速度？':'Why is charging power not the same as charging speed?','AI 如何参与一期播客的制作？':'How can AI help create a podcast?','① 选题':'① Topic','② 提纲':'② Outline','③ 脚本':'③ Script','预设内容演示，用于体验创作流程；未连接 AI 服务。':'A scripted workflow demo; no AI service is connected.',
 '面向第一次购买电动车的用户，解释峰值功率、平均功率和实际补能时间的区别。':'Explain peak power, average power and charging time to first-time EV buyers.',
 '01 从一个充电场景切入\n02 拆解电量、功率与时间\n03 解释充电曲线与温度的影响\n04 给出比较参数的方法':'01 Start with a charging scenario\n02 Break down energy, power and time\n03 Explain charging curves and temperature\n04 Show how to compare specifications',
 '“同样写着快充，为什么补能时间不同？\n先看需要补充多少电，再看整个过程的平均功率。峰值只是某个瞬间，真正影响等待时间的是整条充电曲线。”':'“Why do two fast-charging cars take different amounts of time?\nStart with the energy needed, then consider average power. Peak power is a moment; the complete charging curve determines the wait.”',
 '面向内容创作者，探索 AI 在整理素材与生成初稿中的作用。':'Explore how AI can organize research and draft content for creators.',
 '01 创作者面对的信息过载\n02 素材整理与主题归纳\n03 提纲到脚本的迭代\n04 人工核对与表达打磨':'01 Information overload\n02 Organize sources and themes\n03 Iterate from outline to script\n04 Human fact-checking and editing',
 '“一期节目，往往从一堆零散笔记开始。\n我们可以让 AI 协助归纳主题、搭建提纲，再由创作者核对事实、补充判断，把初稿变成自己的表达。”':'“An episode often starts with scattered notes.\nAI can help organize themes and outlines. The creator then checks facts, adds judgment and makes the draft their own.”',
 '试一试：声音灵感台':'Try it: sound playground','点击音符，给你的探索配一小段旋律。':'Tap a note to give your journey a melody.','C · 好奇':'C · Curiosity','E · 灵感':'E · Inspiration','G · 表达':'G · Expression','即时合成的互动音符，并非真实节目片段。完整播客请访问线上站点。':'Synthesized interactive notes, not podcast recordings. Visit the full site for episodes.',
 '打开完整项目':'Open full project','关闭面板即可继续驾驶。':'Close the panel to keep driving.','开到彩色圆形展台旁，再按 E 查看作品。':'Drive near a colored platform, then press E to explore.','已到达':'Arrived at ','，按 E 或点击路牌查看。':'. Press E or click the sign to explore.','沿道路探索，或点击展区路牌快速到达。':'Follow the roads, or click a destination sign to travel.',
 '图形上下文已暂停，请刷新页面恢复，或返回作品列表。':'Graphics paused. Refresh to recover, or open the portfolio.','无法启动 3D 场景，请使用支持 WebGL 的浏览器，或先浏览作品列表。':'Unable to start 3D. Use a WebGL browser or browse the portfolio.','场景加载较慢，请刷新重试，或先浏览作品列表。':'Loading is slow. Refresh or browse the portfolio.',
 '这个展区还有':'More to explore','在园区内打开项目':'Open inside the world','在园区内打开':'Open inside the world','在园区里开始游戏':'Play inside the world','返回展区':'Back to destination','新标签打开':'Open new tab','正在浏览外部项目 · 关闭面板即可回到原来的停车位置。若页面无法显示，请使用右侧的新标签入口。':'Browsing an external project. Close this panel to return to your parking spot. If it does not load, use Open new tab.'
};
const entries=Object.entries(messages).sort((a,b)=>b[0].length-a[0].length);
export function t(text){if(language==='zh'||!/[\u3400-\u9fff]/.test(text))return text;let result=text;for(const [zh,en] of entries)result=result.split(zh).join(en);return result;}
function translateNode(node){
 if(node.nodeType===3){const value=t(node.data);if(value!==node.data)node.data=value;return;}
 if(node.nodeType!==1||['SCRIPT','STYLE','CANVAS','IFRAME'].includes(node.tagName)||node.id==='telemetry')return;
 for(const attr of ['aria-label','title','placeholder'])if(node.hasAttribute(attr)){const value=t(node.getAttribute(attr));if(value!==node.getAttribute(attr))node.setAttribute(attr,value);}
 for(const child of node.childNodes)translateNode(child);
}
export function installLanguageSwitch(){
 document.documentElement.lang=language==='en'?'en':'zh-CN';document.title=t(document.title);
 translateNode(document.body);
 for(const button of document.querySelectorAll('[data-language-switch]')){
  button.textContent=language==='zh'?'EN':'中文';
  button.setAttribute('aria-label',language==='zh'?'Switch to English':'切换为中文');
  button.onclick=()=>{const next=language==='zh'?'en':'zh';try{localStorage.setItem('vikipedia-drive-language',next)}catch{}const url=new URL(location.href);url.searchParams.set('lang',next);location.assign(url);};
 }
 const observer=new MutationObserver(records=>{for(const r of records){if(r.type==='characterData')translateNode(r.target);else for(const node of r.addedNodes)translateNode(node);}});
 observer.observe(document.body,{childList:true,characterData:true,subtree:true});
}
