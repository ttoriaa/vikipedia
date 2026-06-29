const latestQuotesFile = "./data/quotes_latest.json";
const snapshotIndexFile = "./data/snapshots_index.json";
const latestAlertsFile = "./data/alerts/latest_alerts.json";
const latestDigestFile = "./data/digest/latest_digest.json";

let snapshotIndex = [];
let selectedDate = "latest";
let selectedType = "all";
let currentSnapshotType = "intraday";

function fmtNum(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }
  return Number(value).toFixed(digits);
}

function signedClass(value) {
  const num = Number(value);
  if (Number.isNaN(num)) {
    return "";
  }
  return num >= 0 ? "up" : "down";
}

function snapshotFileByDate(date) {
  const hit = snapshotIndex.find((item) => item.date === date);
  if (!hit || !hit.file) {
    return latestQuotesFile;
  }

  let f = String(hit.file).replace(/^\.\//, "");
  if (f.startsWith("market_watch/")) {
    f = f.slice("market_watch/".length);
  }
  return `./${f}`;
}

async function loadJson(path) {
  const resp = await fetch(path, { cache: "no-cache" });
  if (!resp.ok) {
    throw new Error(`load failed: ${path}`);
  }
  return resp.json();
}

function renderMeta(meta) {
  const node = document.getElementById("dataMeta");
  if (!node) return;
  if (!meta) {
    node.textContent = "暂无数据";
    return;
  }
  currentSnapshotType = meta.snapshot_type || "intraday";
  node.textContent = `日期 ${meta.snapshot_date || "-"} | 类型 ${meta.snapshot_type || "-"} | 更新时间 ${meta.generated_at || "-"}`;
}

function renderOverview(quotes) {
  const node = document.getElementById("overviewCards");
  if (!node) return;

  const byCategory = {};
  quotes.forEach((item) => {
    const key = item.category_display || item.category || "未知";
    byCategory[key] = byCategory[key] || [];
    byCategory[key].push(item);
  });

  const cards = Object.entries(byCategory).map(([name, rows]) => {
    const valid = rows
      .map((r) => Number(r.change_pct))
      .filter((n) => !Number.isNaN(n));
    const avg = valid.length ? valid.reduce((a, b) => a + b, 0) / valid.length : null;
    const lead = rows[0] || {};
    return `
      <article class="card">
        <h3>${name}</h3>
        <div class="kpi ${signedClass(avg)}">${avg === null ? "-" : `${fmtNum(avg)}%`}</div>
        <p>样本数 ${rows.length}</p>
        <p>关注标的 ${lead.symbol || "-"}</p>
      </article>
    `;
  });

  node.innerHTML = cards.join("") || "<p>暂无概览</p>";
}

function renderQuotes(quotes) {
  const node = document.getElementById("quoteBody");
  if (!node) return;

  const rows = quotes
    .filter(() => selectedType === "all" || currentSnapshotType === selectedType)
    .map((item) => {
      const pct = Number(item.change_pct);
      const pctText = Number.isNaN(pct) ? "-" : `${fmtNum(pct)}%`;
      return `
      <tr>
        <td>${item.category_display || item.category || "-"}</td>
        <td>${item.symbol || "-"}</td>
        <td>${fmtNum(item.price)}</td>
        <td class="${signedClass(pct)}">${pctText}</td>
        <td>${fmtNum(item.volume, 0)}</td>
        <td>${item.source || "-"}</td>
      </tr>
    `;
    })
    .join("");

  node.innerHTML = rows || "<tr><td colspan=\"6\">暂无行情</td></tr>";
}

function renderAlerts(payload) {
  const node = document.getElementById("alertsPanel");
  if (!node) return;
  let alerts = Array.isArray(payload?.alerts) ? payload.alerts : [];
  if (selectedType !== "all") {
    alerts = alerts.filter((a) => a.snapshot_type === selectedType);
  }
  if (!alerts.length) {
    node.innerHTML = "<p>暂无触发告警</p>";
    return;
  }

  node.innerHTML = alerts
    .map(
      (a) => `
      <article class="alert-item alert-${a.severity || "medium"}">
        <strong>[${a.severity || "medium"}] ${a.symbol || "-"}</strong>
        <p>${a.message || ""}</p>
      </article>
    `
    )
    .join("");
}

function renderDigest(payload) {
  const node = document.getElementById("digestPanel");
  if (!node) return;
  const sections = Array.isArray(payload?.sections) ? payload.sections : [];
  if (!sections.length) {
    node.innerHTML = "<p>暂无快讯摘要</p>";
    return;
  }

  node.innerHTML = sections
    .map((sec) => {
      const headlines = Array.isArray(sec.headlines) ? sec.headlines : [];
      const list = headlines.length
        ? `<ul>${headlines.map((h) => `<li>${h}</li>`).join("")}</ul>`
        : "<p>暂无头条</p>";
      const quality = sec.quality && typeof sec.quality.headlines_count === "number"
        ? `<p>头条数量: ${sec.quality.headlines_count}</p>`
        : "";
      return `
        <article class="digest-item">
          <strong>${sec.category_display || sec.category || "-"}</strong>
          <p>${sec.summary || ""}</p>
          ${quality}
          ${list}
        </article>
      `;
    })
    .join("");
}

function renderSnapshotOptions() {
  const node = document.getElementById("snapshotDateFilter");
  if (!node) return;
  const opts = ["<option value=\"latest\">最新数据</option>"];
  snapshotIndex.forEach((item) => {
    opts.push(`<option value=\"${item.date}\">${item.date} (${item.snapshot_type || "-"})</option>`);
  });
  node.innerHTML = opts.join("");
  node.value = selectedDate;
}

async function loadSnapshotIndex() {
  try {
    const payload = await loadJson(snapshotIndexFile);
    snapshotIndex = Array.isArray(payload.snapshots)
      ? payload.snapshots.slice().sort((a, b) => String(b.date).localeCompare(String(a.date)))
      : [];
  } catch (err) {
    snapshotIndex = [];
  }
  renderSnapshotOptions();
}

async function refresh() {
  const quotePath = selectedDate === "latest" ? latestQuotesFile : snapshotFileByDate(selectedDate);

  let quotePayload = null;
  let alertPayload = null;
  let digestPayload = null;

  try {
    quotePayload = await loadJson(quotePath);
  } catch (err) {
    quotePayload = { meta: null, quotes: [] };
  }

  try {
    if (selectedDate === "latest") {
      alertPayload = await loadJson(latestAlertsFile);
      digestPayload = await loadJson(latestDigestFile);
    } else {
      alertPayload = await loadJson(`./data/alerts/history/${selectedDate}/alerts.json`);
      digestPayload = await loadJson(`./data/digest/history/${selectedDate}/digest.json`);
    }
  } catch (err) {
    alertPayload = { alerts: [] };
    digestPayload = { sections: [] };
  }

  const quotes = Array.isArray(quotePayload.quotes) ? quotePayload.quotes : [];
  renderMeta(quotePayload.meta || null);
  renderOverview(quotes);
  renderQuotes(quotes);
  renderAlerts(alertPayload);
  renderDigest(digestPayload);
}

function bindEvents() {
  const dateNode = document.getElementById("snapshotDateFilter");
  const typeNode = document.getElementById("snapshotTypeFilter");
  if (dateNode) {
    dateNode.addEventListener("change", async () => {
      selectedDate = dateNode.value;
      await refresh();
    });
  }

  if (typeNode) {
    typeNode.addEventListener("change", async () => {
      selectedType = typeNode.value;
      await refresh();
    });
  }
}

async function init() {
  bindEvents();
  await loadSnapshotIndex();
  await refresh();
}

init();
