const preferredRoles = ["车辆项目管理", "数据产品经理", "数据项目管理", "技术售前支持"];
const resumeStrengths = [
  "cross-functional",
  "data governance",
  "data pipeline",
  "powertrain data",
  "ai agent",
  "rag",
  "project delivery",
  "analytics",
  "client communication",
  "requirements"
];
const industryWeight = { "车企": 14, "互联网": 10, "机器人与具身智能": 12 };
const statusOptions = ["未投递", "已投递", "面试中", "Offer"];
const statusStorageKey = "job_market_hub_applications_v1";
const latestDataFile = "./data/jobs.json";
const snapshotIndexFile = "./data/snapshots_index.json";

let jobs = [];
let jobDataMeta = null;
let snapshotIndex = [];
let selectedSnapshotDate = "latest";
let applicationState = loadApplicationState();

function loadApplicationState() {
  try {
    const raw = localStorage.getItem(statusStorageKey);
    return raw ? JSON.parse(raw) : {};
  } catch (error) {
    return {};
  }
}

function persistApplicationState() {
  localStorage.setItem(statusStorageKey, JSON.stringify(applicationState));
}

function getJobStatus(jobId) {
  return applicationState[jobId]?.status || "未投递";
}

function setJobStatus(jobId, status) {
  applicationState[jobId] = {
    status,
    updatedAt: new Date().toISOString()
  };
  persistApplicationState();
}

function scoreJob(job) {
  const requirements = Array.isArray(job.requirements) ? job.requirements : [];
  const roleBonus = preferredRoles.includes(job.role) ? 38 : 8;
  const domainBonus = industryWeight[job.industry] || 6;
  const skillMatches = requirements.filter((req) => resumeStrengths.includes(req)).length;
  const skillBonus = skillMatches * 10;
  return Math.min(roleBonus + domainBonus + skillBonus, 99);
}

function sortByScore(jobList) {
  return [...jobList].sort((a, b) => scoreJob(b) - scoreJob(a));
}

function statusPill(status) {
  return `<span class="status-pill status-${status}">${status}</span>`;
}

function statusSelect(jobId, currentStatus) {
  const options = statusOptions
    .map((status) => {
      const selected = status === currentStatus ? "selected" : "";
      return `<option value="${status}" ${selected}>${status}</option>`;
    })
    .join("");

  return `<select class="status-select" data-job-id="${jobId}">${options}</select>`;
}

function cardTemplate(job) {
  const score = scoreJob(job);
  const status = getJobStatus(job.id);
  const source = job.source || "#";
  const salary = job.salary || "薪资待补充";
  const city = job.city || "城市待补充";
  const description = job.description || "岗位描述待补充";

  return `
    <article class="job-card">
      <span class="score">匹配度 ${score}</span>
      <h3>${job.title}</h3>
      <div class="job-meta">
        <span class="badge">${job.company}</span>
        <span class="badge">${job.industry}</span>
        <span class="badge">${job.role}</span>
        <span class="badge">${city}</span>
        <span class="badge">${salary}</span>
      </div>
      <p class="job-desc">${description}</p>
      <div class="job-foot">
        ${statusPill(status)}
        ${statusSelect(job.id, status)}
      </div>
      <a class="job-link" href="${source}" target="_blank" rel="noopener noreferrer">查看来源</a>
    </article>
  `;
}

function renderJobs(containerId, jobList) {
  const container = document.getElementById(containerId);
  if (!container) {
    return;
  }

  if (!jobList.length) {
    container.innerHTML = "<p>当前筛选条件下暂无岗位，请切换筛选条件。</p>";
    return;
  }

  container.innerHTML = sortByScore(jobList).map(cardTemplate).join("");
}

function renderStatusBoard() {
  const statusBoard = document.getElementById("statusBoard");
  if (!statusBoard) {
    return;
  }

  const counts = { "未投递": 0, "已投递": 0, "面试中": 0, Offer: 0 };
  jobs.forEach((job) => {
    const status = getJobStatus(job.id);
    counts[status] += 1;
  });

  statusBoard.innerHTML = statusOptions
    .map((status) => {
      return `
        <article class="status-item">
          <strong>${counts[status] || 0}</strong>
          <span>${status}</span>
        </article>
      `;
    })
    .join("");
}

function renderMeta() {
  const metaNode = document.getElementById("dataMeta");
  if (!metaNode) {
    return;
  }

  if (!jobDataMeta) {
    metaNode.textContent = `数据总量 ${jobs.length} 条`;
    return;
  }

  const generatedAt = jobDataMeta.generated_at || "未知时间";
  const sourceNames = Array.isArray(jobDataMeta.sources) ? jobDataMeta.sources.join(" / ") : "未知来源";
  const snapshotDate = jobDataMeta.snapshot_date || selectedSnapshotDate;
  const viewLabel = snapshotDate === "latest" ? "最新" : snapshotDate;
  metaNode.textContent = `数据总量 ${jobs.length} 条 | 查看日期 ${viewLabel} | 更新时间 ${generatedAt} | 来源 ${sourceNames}`;
}

function renderHome() {
  const roleFilter = document.getElementById("roleFilter");
  const roleValue = roleFilter ? roleFilter.value : "all";

  let selected = jobs;
  if (roleValue !== "all") {
    selected = jobs.filter((job) => job.role === roleValue);
  }

  renderJobs("recommendationGrid", selected);
  renderStatusBoard();
}

function renderAllPanels() {
  renderHome();
  renderJobs("autoGrid", jobs.filter((job) => job.industry === "车企"));
  renderJobs("robotGrid", jobs.filter((job) => job.industry === "机器人与具身智能"));
  renderMeta();
}

function setupTabs() {
  const buttons = document.querySelectorAll(".tab-btn");
  const panels = document.querySelectorAll(".tab-panel");

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;

      buttons.forEach((item) => item.classList.remove("active"));
      panels.forEach((panel) => panel.classList.remove("active"));

      btn.classList.add("active");
      const panel = document.getElementById(`tab-${tab}`);
      if (panel) {
        panel.classList.add("active");
      }
    });
  });
}

function bindEvents() {
  const roleFilter = document.getElementById("roleFilter");
  if (roleFilter) {
    roleFilter.addEventListener("change", renderHome);
  }

  const snapshotDateFilter = document.getElementById("snapshotDateFilter");
  if (snapshotDateFilter) {
    snapshotDateFilter.addEventListener("change", async () => {
      selectedSnapshotDate = snapshotDateFilter.value;
      await loadJobs(selectedSnapshotDate);
      renderAllPanels();
    });
  }

  document.body.addEventListener("change", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLSelectElement)) {
      return;
    }

    if (!target.classList.contains("status-select")) {
      return;
    }

    const jobId = target.dataset.jobId;
    if (!jobId || !statusOptions.includes(target.value)) {
      return;
    }

    setJobStatus(jobId, target.value);
    renderAllPanels();
  });
}

function getSnapshotFileByDate(snapshotDate) {
  const hit = snapshotIndex.find((item) => item.date === snapshotDate);
  if (!hit || !hit.file) {
    return latestDataFile;
  }

  let filePath = String(hit.file).replace(/^\.\//, "");
  if (filePath.startsWith("job_market_hub/")) {
    filePath = filePath.slice("job_market_hub/".length);
  }
  return `./${filePath}`;
}

function renderSnapshotOptions() {
  const snapshotDateFilter = document.getElementById("snapshotDateFilter");
  if (!snapshotDateFilter) {
    return;
  }

  const options = [
    "<option value=\"latest\">最新数据</option>",
    ...snapshotIndex.map((item) => `<option value=\"${item.date}\">${item.date}</option>`)
  ];

  snapshotDateFilter.innerHTML = options.join("");
  snapshotDateFilter.value = selectedSnapshotDate;
}

async function loadSnapshotIndex() {
  try {
    const response = await fetch(snapshotIndexFile, { cache: "no-cache" });
    if (!response.ok) {
      throw new Error(`index load failed ${response.status}`);
    }

    const payload = await response.json();
    const items = Array.isArray(payload.snapshots) ? payload.snapshots : [];
    snapshotIndex = items
      .filter((item) => item && typeof item.date === "string" && typeof item.file === "string")
      .sort((a, b) => String(b.date).localeCompare(String(a.date)));
  } catch (error) {
    snapshotIndex = [];
  }

  renderSnapshotOptions();
}

async function loadJobs(snapshotDate = "latest") {
  const dataFile = snapshotDate === "latest" ? latestDataFile : getSnapshotFileByDate(snapshotDate);

  try {
    const response = await fetch(dataFile, { cache: "no-cache" });
    if (!response.ok) {
      throw new Error(`load failed ${response.status}`);
    }
    const payload = await response.json();
    jobs = Array.isArray(payload.jobs) ? payload.jobs : [];
    jobDataMeta = payload.meta || {};
    jobDataMeta.snapshot_date = snapshotDate;
  } catch (error) {
    jobs = [];
    jobDataMeta = null;
  }
}

async function init() {
  setupTabs();
  bindEvents();
  await loadSnapshotIndex();
  await loadJobs(selectedSnapshotDate);
  renderAllPanels();
}

init();
