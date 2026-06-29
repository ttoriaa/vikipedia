from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import shutil
import statistics
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
REPORT_ROOT = ROOT / "reports" / "dongchedi_daily"

BUBBLE_EXCLUDED_MODEL_KEYWORDS = [
    "奔驰EQS SUV",
]


def _parse_exclude_keywords(raw_text: str) -> list[str]:
    return [x.strip() for x in raw_text.split(",") if x.strip()]


def _is_bubble_excluded(model_name: str, exclude_keywords: list[str]) -> bool:
    return any(keyword in model_name for keyword in exclude_keywords)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_float(text: str) -> float | None:
    t = _clean(text)
    if not t or t == "未明确显示":
        return None
    try:
        return float(t)
    except ValueError:
        return None

def _median(values: list[float]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


def _parse_platform_voltage(voltage_text: str, platform_text: str) -> float | None:
    direct = _to_float(voltage_text)
    if direct is not None:
        return direct

    t = _clean(platform_text)
    m = re.search(r"(\d{3,4})\s*V", t, flags=re.IGNORECASE)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _voltage_group(voltage: float | None) -> str:
    if voltage is None:
        return "未明确"
    if voltage >= 900:
        return "900V+"
    if voltage >= 800:
        return "800V"
    if voltage >= 400:
        return "400V"
    return "未明确"

def _validate_generated_html_js(html: str) -> tuple[str, str]:
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, flags=re.IGNORECASE | re.DOTALL)
    scripts = [s.strip() for s in scripts if s.strip()]
    if not scripts:
        raise RuntimeError("JS syntax check failed: no inline <script> blocks found in generated HTML")

    node_path = shutil.which("node")
    if not node_path:
        # Keep generation working even when Node.js is unavailable.
        return ("skipped", "Node.js not found; JS syntax check skipped")

    combined_js = "\n\n".join(scripts)
    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
            tf.write(combined_js)
            temp_path = tf.name

        proc = subprocess.run(
            [node_path, "--check", temp_path],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(f"JS syntax check failed via Node.js: {detail}")
        return ("passed", "Node.js syntax check passed")
    finally:
        if temp_path and Path(temp_path).exists():
            Path(temp_path).unlink(missing_ok=True)


def _latest_report_date() -> str:
    if not REPORT_ROOT.exists():
        raise FileNotFoundError(f"Report root not found: {REPORT_ROOT}")

    dates = [p.name for p in REPORT_ROOT.iterdir() if p.is_dir() and p.name[:4].isdigit()]
    if not dates:
        raise FileNotFoundError("No report date folders found under reports/dongchedi_daily")
    return sorted(dates)[-1]


def _load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict((k, _clean(v)) for k, v in row.items()) for row in csv.DictReader(f)]


def _density_bucket(value: float) -> str:
    if value < 150:
        return "<150"
    if value < 160:
        return "150-159"
    if value < 170:
        return "160-169"
    if value <= 175:
        return "170-175"
    if value < 180:
        return "176-179"
    if value <= 185:
        return "180-185"
    if value <= 190:
        return "186-190"
    return ">=190"


def _battery_group(raw: str) -> str:
    t = _clean(raw)
    if "三元" in t and "磷酸" in t:
        return "混合"
    if "三元" in t:
        return "三元锂"
    if "磷酸" in t:
        return "磷酸铁锂"
    return "其他/未明确"


def build_visualization_html(
    rows: list[dict[str, str]],
    report_date: str,
    radar_show_zero_buckets: bool = False,
    bubble_exclude_keywords: list[str] | None = None,
) -> str:
    bubble_rows: list[dict[str, Any]] = []
    brand_agg: dict[str, dict[str, Any]] = {}
    density_missing = 0
    density_total = len(rows)
    active_bubble_exclude_keywords = bubble_exclude_keywords or BUBBLE_EXCLUDED_MODEL_KEYWORDS

    radar_axes = ["<150", "150-159", "160-169", "170-175", "176-179", "180-185", "186-190", ">=190"]
    radar_groups = ["三元锂", "磷酸铁锂", "混合", "其他/未明确"]
    radar_counts: dict[str, dict[str, int]] = {
        g: {axis: 0 for axis in radar_axes} for g in radar_groups
    }

    for row in rows:
        model = _clean(row.get("车型"))
        brand = _clean(row.get("品牌"))
        price = _to_float(_clean(row.get("价格(万元)")))
        cltc = _to_float(_clean(row.get("纯电续航里程(km)CLTC")))
        fast_charge_min = _to_float(_clean(row.get("快充时间(分钟)")))
        battery_kwh = _to_float(_clean(row.get("电池容量(kWh)")))
        platform_text = _clean(row.get("高压快充平台"))
        platform_voltage = _parse_platform_voltage(_clean(row.get("高压平台电压(V)")), platform_text)
        voltage_group = _voltage_group(platform_voltage)
        platform = platform_text or "未明确"

        if price is not None and cltc is not None and not _is_bubble_excluded(model, active_bubble_exclude_keywords):
            item = {
                "model": model,
                "brand": brand,
                "price": round(price, 3),
                "cltc": round(cltc, 1),
                "fastChargeMin": round(fast_charge_min, 2) if fast_charge_min is not None else None,
                "batteryKwh": round(battery_kwh, 2) if battery_kwh is not None else None,
                "platform": platform,
                "platformVoltage": round(platform_voltage, 1) if platform_voltage is not None else None,
                "voltageGroup": voltage_group,
            }
            bubble_rows.append(item)

            if brand not in brand_agg:
                brand_agg[brand] = {
                    "count": 0,
                    "fast": [],
                    "cltc": [],
                    "hv_count": 0,
                }
            brand_agg[brand]["count"] += 1
            brand_agg[brand]["cltc"].append(float(item["cltc"]))
            if item["fastChargeMin"] is not None:
                brand_agg[brand]["fast"].append(float(item["fastChargeMin"]))
            if item["platformVoltage"] is not None and float(item["platformVoltage"]) >= 800:
                brand_agg[brand]["hv_count"] += 1

        density = _to_float(_clean(row.get("电池能量密度(Wh/kg)")))
        if density is None:
            density_missing += 1
            continue

        bucket = _density_bucket(density)
        group = _battery_group(_clean(row.get("电池类型")))
        radar_counts[group][bucket] += 1

    if radar_show_zero_buckets:
        radar_axes_active = radar_axes
    else:
        radar_axes_active = [
            axis for axis in radar_axes if any(radar_counts[group][axis] > 0 for group in radar_groups)
        ]
        if not radar_axes_active:
            radar_axes_active = radar_axes

    radar_series = []
    for group in radar_groups:
        radar_series.append({"name": group, "value": [radar_counts[group][a] for a in radar_axes_active]})

    brand_rows = []
    for brand, agg in brand_agg.items():
        count = int(agg["count"])
        median_fast = _median(agg["fast"])
        median_cltc = _median(agg["cltc"])
        hv_share = 0.0 if count == 0 else (float(agg["hv_count"]) / count) * 100.0
        brand_rows.append(
            {
                "brand": brand,
                "count": count,
                "medianFast": round(median_fast, 2) if median_fast is not None else None,
                "medianCltc": round(median_cltc, 1) if median_cltc is not None else None,
                "hvShare": round(hv_share, 1),
            }
        )

    brand_rows.sort(key=lambda x: (-x["count"], x["brand"]))
    brand_rows = brand_rows[:14]

    cltc_values = [r["medianCltc"] for r in brand_rows if r["medianCltc"] is not None]
    fast_values = [r["medianFast"] for r in brand_rows if r["medianFast"] is not None]
    hv_values = [r["hvShare"] for r in brand_rows if r["hvShare"] is not None]

    def _score(value: float | None, lo: float, hi: float, reverse: bool = False) -> float:
        if value is None:
            return 0.0
        if hi <= lo:
            return 1.0
        raw = (value - lo) / (hi - lo)
        if reverse:
            raw = 1.0 - raw
        return max(0.0, min(1.0, raw))

    cltc_lo, cltc_hi = (min(cltc_values), max(cltc_values)) if cltc_values else (0.0, 1.0)
    fast_lo, fast_hi = (min(fast_values), max(fast_values)) if fast_values else (0.0, 1.0)
    hv_lo, hv_hi = (min(hv_values), max(hv_values)) if hv_values else (0.0, 1.0)

    for row in brand_rows:
        row["fastScore"] = round(_score(row["medianFast"], fast_lo, fast_hi, reverse=True), 4)
        row["cltcScore"] = round(_score(row["medianCltc"], cltc_lo, cltc_hi, reverse=False), 4)
        row["hvScore"] = round(_score(row["hvShare"], hv_lo, hv_hi, reverse=False), 4)

    density_available = density_total - density_missing
    missing_ratio = 0.0 if density_total == 0 else density_missing / density_total

    payload = {
        "reportDate": report_date,
        "generatedAt": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bubbleRows": bubble_rows,
        "brandHeatmapRows": brand_rows,
        "radarAxes": radar_axes_active,
        "radarSeries": radar_series,
        "stats": {
            "totalModels": density_total,
            "densityAvailable": density_available,
            "densityMissing": density_missing,
            "densityMissingRatio": round(missing_ratio * 100, 1),
            "bubblePoints": len(bubble_rows),
            "radarBucketsShown": len(radar_axes_active),
            "radarShowZeroBuckets": radar_show_zero_buckets,
            "bubbleExcludeKeywords": active_bubble_exclude_keywords,
            "brandCount": len(brand_rows),
        },
    }

    payload_json = json.dumps(payload, ensure_ascii=False)

    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>懂车帝充电数据可视化 {report_date}</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {{
      --bgA: #fff3e8;
      --bgB: #eaf5ff;
      --ink: #14202b;
      --muted: #5f6b77;
      --line: rgba(20, 32, 43, 0.15);
      --card: rgba(255,255,255,0.84);
      --accent: #d15a00;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(900px 500px at -15% -10%, #ffd7b0 0%, transparent 55%),
        radial-gradient(1000px 560px at 120% 5%, #b9dbff 0%, transparent 55%),
        linear-gradient(140deg, var(--bgA), var(--bgB));
      min-height: 100vh;
      padding: 22px;
    }}

    .wrap {{
      max-width: 1400px;
      margin: 0 auto;
      border: 1px solid var(--line);
      border-radius: 18px;
      overflow: hidden;
      background: var(--card);
      backdrop-filter: blur(8px);
      box-shadow: 0 14px 48px rgba(0,0,0,0.08);
    }}

    .head {{
      padding: 18px 22px 6px;
      border-bottom: 1px solid var(--line);
    }}

    h1 {{
      margin: 0;
      font-size: 28px;
      letter-spacing: 0.3px;
    }}

    .sub {{
      margin: 8px 0 4px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.55;
    }}

    .stats {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      padding: 0 22px 16px;
    }}

    .pill {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 6px 12px;
      font-size: 12px;
      background: rgba(255,255,255,0.72);
    }}

    .grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0;
    }}

    .panel {{
      border-top: 1px solid var(--line);
      border-right: 1px solid var(--line);
      min-height: 520px;
      padding: 10px 12px 12px;
    }}

    .panel:nth-child(2n) {{
      border-right: none;
    }}

    .panel-wide {{
      grid-column: 1 / -1;
      border-right: none;
    }}

    .panel-title {{
      font-size: 15px;
      font-weight: 600;
      padding: 8px 8px 0;
    }}

    .chart {{
      width: 100%;
      height: 470px;
    }}

    .foot {{
      border-top: 1px solid var(--line);
      padding: 10px 22px 16px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.6;
    }}

    .warn {{ color: var(--accent); font-weight: 600; }}

    @media (max-width: 980px) {{
      body {{ padding: 8px; }}
      .grid {{ grid-template-columns: 1fr; }}
      .panel {{ border-right: none; min-height: 500px; }}
      .chart {{ height: 460px; }}
      h1 {{ font-size: 22px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <h1>懂车帝充电数据可视化 Dashboard</h1>
      <p class="sub">日期: {report_date} | 含雷达、帕累托前沿、平台箱线、品牌热力、续航分布、价格-续航与价格-快充双Bubble图。</p>
    </div>
    <div class="stats" id="stats"></div>
    <div class="grid">
      <section class="panel">
        <div class="panel-title">1) 电池能量密度雷达分布</div>
        <div id="radarChart" class="chart"></div>
      </section>
      <section class="panel">
        <div class="panel-title">2) 帕累托前沿图（价格↓ 续航↑ 快充时间↓）</div>
        <div id="paretoChart" class="chart"></div>
      </section>
      <section class="panel">
        <div class="panel-title">3) 平台电压 vs 快充时间 箱线图</div>
        <div id="platformBoxChart" class="chart"></div>
      </section>
      <section class="panel">
        <div class="panel-title">4) 续航里程分布图（CLTC）</div>
        <div id="rangeDistChart" class="chart"></div>
      </section>
      <section class="panel panel-wide">
        <div class="panel-title">5) 品牌充电能力热力图（速度得分/续航得分/高压占比）</div>
        <div id="brandHeatmapChart" class="chart"></div>
      </section>
      <section class="panel">
        <div class="panel-title">6) 价格 + 续航里程 Bubble 图</div>
        <div id="priceRangeBubbleChart" class="chart"></div>
      </section>
      <section class="panel">
        <div class="panel-title">7) 价格 + 快充时间 Bubble 图</div>
        <div id="priceFastBubbleChart" class="chart"></div>
      </section>
    </div>
    <div class="foot" id="foot"></div>
  </div>

  <script>
    const payload = {payload_json};

    const statsEl = document.getElementById("stats");
    const footEl = document.getElementById("foot");

    const statItems = [
      `总车型: ${{payload.stats.totalModels}}`,
      `能量密度可用: ${{payload.stats.densityAvailable}}`,
      `能量密度缺失: ${{payload.stats.densityMissing}} (${{payload.stats.densityMissingRatio}}%)`,
      `Bubble 点位: ${{payload.stats.bubblePoints}}`,
      `热力图品牌数: ${{payload.stats.brandCount}}`,
      `Bubble 排除词: ${{payload.stats.bubbleExcludeKeywords.join(" | ") || "无"}}`,
      `雷达轴模式: ${{payload.stats.radarShowZeroBuckets ? "完整轴" : "紧凑轴"}}`,
      `生成时间: ${{payload.generatedAt}}`
    ];
    statItems.forEach(s => {{
      const node = document.createElement("span");
      node.className = "pill";
      node.textContent = s;
      statsEl.appendChild(node);
    }});

    const maxRadar = Math.max(
      3,
      ...payload.radarSeries.flatMap(s => s.value)
    );

    const radarTraces = payload.radarSeries.map(series => {{
      const values = [...series.value, series.value[0]];
      const theta = [...payload.radarAxes, payload.radarAxes[0]];
      return {{
        type: "scatterpolar",
        r: values,
        theta,
        name: series.name,
        opacity: 0.48,
        fill: "toself",
        hovertemplate: `${{series.name}}<br>%{{theta}}: %{{r}} 台<extra></extra>`
      }};
    }});

    Plotly.newPlot("radarChart", radarTraces, {{
      margin: {{ l: 50, r: 40, t: 12, b: 20 }},
      paper_bgcolor: "rgba(0,0,0,0)",
      polar: {{
        bgcolor: "rgba(255,255,255,0.55)",
        radialaxis: {{
          visible: true,
          range: [0, maxRadar],
          gridcolor: "rgba(20, 32, 43, 0.18)",
          tickfont: {{ size: 11 }}
        }},
        angularaxis: {{
          gridcolor: "rgba(20, 32, 43, 0.15)",
          tickfont: {{ size: 12 }}
        }}
      }},
      legend: {{ orientation: "h", y: -0.1, x: 0 }},
      font: {{ family: "Segoe UI, PingFang SC, Microsoft YaHei, sans-serif", color: "#14202b" }}
    }}, {{ responsive: true, displaylogo: false }});

    const colorByVoltage = {{
      "400V": "#457b9d",
      "800V": "#1f7a8c",
      "900V+": "#e07a5f",
      "未明确": "#9c6644"
    }};

        const rows = payload.bubbleRows;
        const fastRows = rows.filter(r => r.fastChargeMin !== null && !Number.isNaN(r.fastChargeMin));

        const groupedRange = {{}};
        rows.forEach(d => {{
          if (!groupedRange[d.voltageGroup]) groupedRange[d.voltageGroup] = [];
          groupedRange[d.voltageGroup].push(d);
        }});

        const rangeTraces = Object.entries(groupedRange).map(([group, items]) => ({{
          type: "scatter",
          mode: "markers",
          name: group,
          x: items.map(d => d.price),
          y: items.map(d => d.cltc),
          text: items.map(d => d.model),
          customdata: items.map(d => [d.brand, d.batteryKwh, d.fastChargeMin]),
          marker: {{
            size: items.map(d => Math.max(9, (d.batteryKwh || 70) * 0.26)),
            color: colorByVoltage[group] || "#6d597a",
            opacity: 0.72,
            line: {{ width: 1.0, color: "rgba(20,32,43,0.42)" }}
          }},
          hovertemplate:
            "<b>%{{text}}</b>" +
            "<br>品牌: %{{customdata[0]}}" +
            "<br>价格: %{{x}} 万元" +
            "<br>CLTC续航: %{{y}} km" +
            "<br>快充时间: %{{customdata[2]}} 分钟" +
            "<br>电池容量: %{{customdata[1]}} kWh" +
            "<extra></extra>"
        }}));

        Plotly.newPlot("priceRangeBubbleChart", rangeTraces, {{
          margin: {{ l: 62, r: 20, t: 10, b: 55 }},
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(255,255,255,0.55)",
          xaxis: {{ title: "价格 (万元)", gridcolor: "rgba(20, 32, 43, 0.12)", zeroline: false }},
          yaxis: {{ title: "CLTC续航 (km)", gridcolor: "rgba(20, 32, 43, 0.12)", zeroline: false }},
          legend: {{ orientation: "h", y: 1.12, x: 0 }},
          font: {{ family: "Segoe UI, PingFang SC, Microsoft YaHei, sans-serif", color: "#14202b" }}
        }}, {{ responsive: true, displaylogo: false }});

        const fastGrouped = {{}};
        fastRows.forEach(d => {{
          if (!fastGrouped[d.voltageGroup]) fastGrouped[d.voltageGroup] = [];
          fastGrouped[d.voltageGroup].push(d);
        }});

        const fastBubbleTraces = Object.entries(fastGrouped).map(([group, items]) => ({{
          type: "scatter",
          mode: "markers",
          name: group,
          x: items.map(d => d.price),
          y: items.map(d => d.fastChargeMin),
          text: items.map(d => d.model),
          customdata: items.map(d => [d.brand, d.cltc, d.batteryKwh]),
          marker: {{
            size: items.map(d => Math.max(9, (d.batteryKwh || 70) * 0.26)),
            color: colorByVoltage[group] || "#6d597a",
            opacity: 0.72,
            line: {{ width: 1.0, color: "rgba(20,32,43,0.42)" }}
          }},
          hovertemplate:
            "<b>%{{text}}</b>" +
            "<br>品牌: %{{customdata[0]}}" +
            "<br>价格: %{{x}} 万元" +
            "<br>快充时间: %{{y}} 分钟" +
            "<br>CLTC续航: %{{customdata[1]}} km" +
            "<br>电池容量: %{{customdata[2]}} kWh" +
            "<extra></extra>"
        }}));

        Plotly.newPlot("priceFastBubbleChart", fastBubbleTraces, {{
          margin: {{ l: 62, r: 20, t: 10, b: 55 }},
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(255,255,255,0.55)",
          xaxis: {{ title: "价格 (万元)", gridcolor: "rgba(20, 32, 43, 0.12)", zeroline: false }},
          yaxis: {{ title: "快充时间 (分钟，越小越好)", autorange: "reversed", gridcolor: "rgba(20, 32, 43, 0.12)", zeroline: false }},
          legend: {{ orientation: "h", y: 1.12, x: 0 }},
          font: {{ family: "Segoe UI, PingFang SC, Microsoft YaHei, sans-serif", color: "#14202b" }}
        }}, {{ responsive: true, displaylogo: false }});

        const rangeValues = rows.map(r => r.cltc).filter(v => v !== null && !Number.isNaN(v));
        Plotly.newPlot("rangeDistChart", [{{
          type: "histogram",
          x: rangeValues,
          marker: {{ color: "#1f7a8c", opacity: 0.78, line: {{ width: 1, color: "rgba(20,32,43,0.3)" }} }},
          nbinsx: 18,
          hovertemplate: "续航区间: %{{x}} km<br>车型数: %{{y}}<extra></extra>"
        }}], {{
          margin: {{ l: 62, r: 20, t: 10, b: 55 }},
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(255,255,255,0.55)",
          xaxis: {{ title: "CLTC续航 (km)", gridcolor: "rgba(20, 32, 43, 0.12)" }},
          yaxis: {{ title: "车型数", gridcolor: "rgba(20, 32, 43, 0.12)" }},
          font: {{ family: "Segoe UI, PingFang SC, Microsoft YaHei, sans-serif", color: "#14202b" }}
        }}, {{ responsive: true, displaylogo: false }});

        const paretoRows = fastRows.slice();
        const dominates = (a, b) =>
          a.price <= b.price && a.cltc >= b.cltc && a.fastChargeMin <= b.fastChargeMin &&
          (a.price < b.price || a.cltc > b.cltc || a.fastChargeMin < b.fastChargeMin);

        const frontier = paretoRows.filter((p, i) => !paretoRows.some((q, j) => i !== j && dominates(q, p)));
        const frontierSet = new Set(frontier.map(x => x.model + "|" + x.price + "|" + x.cltc));
        const others = paretoRows.filter(x => !frontierSet.has(x.model + "|" + x.price + "|" + x.cltc));
        const frontierSorted = frontier.slice().sort((a, b) => a.price - b.price);

        Plotly.newPlot("paretoChart", [
          {{
            type: "scatter",
            mode: "markers",
            name: "其他车型",
            x: others.map(d => d.price),
            y: others.map(d => d.cltc),
            text: others.map(d => d.model),
            customdata: others.map(d => [d.fastChargeMin, d.brand]),
            marker: {{ size: 8, color: "rgba(100,116,139,0.35)" }},
            hovertemplate: "<b>%{{text}}</b><br>品牌: %{{customdata[1]}}<br>价格: %{{x}} 万元<br>CLTC: %{{y}} km<br>快充: %{{customdata[0]}} 分钟<extra></extra>"
          }},
          {{
            type: "scatter",
            mode: "markers+lines",
            name: "帕累托前沿",
            x: frontierSorted.map(d => d.price),
            y: frontierSorted.map(d => d.cltc),
            text: frontierSorted.map(d => d.model),
            customdata: frontierSorted.map(d => [d.fastChargeMin, d.brand]),
            marker: {{ size: 11, color: "#c1121f", line: {{ width: 1, color: "#780000" }} }},
            line: {{ color: "#c1121f", width: 2 }},
            hovertemplate: "<b>%{{text}}</b><br>品牌: %{{customdata[1]}}<br>价格: %{{x}} 万元<br>CLTC: %{{y}} km<br>快充: %{{customdata[0]}} 分钟<extra></extra>"
          }}
        ], {{
          margin: {{ l: 62, r: 20, t: 10, b: 55 }},
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(255,255,255,0.55)",
          xaxis: {{ title: "价格 (万元，越左越优)", gridcolor: "rgba(20, 32, 43, 0.12)" }},
          yaxis: {{ title: "CLTC续航 (km，越高越优)", gridcolor: "rgba(20, 32, 43, 0.12)" }},
          legend: {{ orientation: "h", y: 1.12, x: 0 }},
          font: {{ family: "Segoe UI, PingFang SC, Microsoft YaHei, sans-serif", color: "#14202b" }}
        }}, {{ responsive: true, displaylogo: false }});

        const voltageOrder = ["400V", "800V", "900V+", "未明确"];
        const boxTraces = voltageOrder
          .filter(v => fastRows.some(r => r.voltageGroup === v))
          .map(v => {{
            const items = fastRows.filter(r => r.voltageGroup === v);
            return {{
              type: "box",
              name: v,
              y: items.map(r => r.fastChargeMin),
              boxmean: "sd",
              marker: {{ color: colorByVoltage[v] || "#6d597a" }},
              line: {{ width: 1.2 }},
              hovertemplate: `${{v}}<br>快充时间: %{{y}} 分钟<extra></extra>`
            }};
          }});

        Plotly.newPlot("platformBoxChart", boxTraces, {{
          margin: {{ l: 62, r: 20, t: 10, b: 55 }},
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(255,255,255,0.55)",
          xaxis: {{ title: "平台电压分组" }},
          yaxis: {{ title: "快充时间 (分钟，越小越好)", autorange: "reversed", gridcolor: "rgba(20, 32, 43, 0.12)" }},
          font: {{ family: "Segoe UI, PingFang SC, Microsoft YaHei, sans-serif", color: "#14202b" }}
        }}, {{ responsive: true, displaylogo: false }});

        const brandRows = payload.brandHeatmapRows;
        const heatmapX = ["快充速度得分", "续航得分", "高压占比得分"];
        const heatmapY = brandRows.map(r => `${{r.brand}} (${{r.count}})`);
        const heatmapZ = brandRows.map(r => [r.fastScore, r.cltcScore, r.hvScore]);
        const heatmapText = brandRows.map(r => [
          r.medianFast === null ? "-" : `${{r.medianFast}} min`,
          r.medianCltc === null ? "-" : `${{r.medianCltc}} km`,
          `${{r.hvShare}}%`
        ]);

        Plotly.newPlot("brandHeatmapChart", [{{
          type: "heatmap",
          x: heatmapX,
          y: heatmapY,
          z: heatmapZ,
          text: heatmapText,
          texttemplate: "%{{text}}",
          colorscale: "YlGnBu",
          zmin: 0,
          zmax: 1,
          hovertemplate: "品牌: %{{y}}<br>指标: %{{x}}<br>原始值: %{{text}}<br>得分: %{{z:.2f}}<extra></extra>"
        }}], {{
          margin: {{ l: 110, r: 20, t: 10, b: 40 }},
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(255,255,255,0.55)",
          xaxis: {{ side: "top" }},
          yaxis: {{ automargin: true }},
          font: {{ family: "Segoe UI, PingFang SC, Microsoft YaHei, sans-serif", color: "#14202b" }}
        }}, {{ responsive: true, displaylogo: false }});

    footEl.innerHTML =
      `数据说明: Radar 仅统计有数值的电池能量密度。` +
      ` <span class="warn">当前能量密度缺失率 ${{payload.stats.densityMissingRatio}}%</span>，分布解读需谨慎。` +
      ` 帕累托前沿以价格、续航、快充时间联合判定；Bubble 排除词对所有 Bubble 与帕累托图生效。`;
  </script>
</body>
</html>
'''


def main() -> None:
    parser = argparse.ArgumentParser(description="Build charging visualization dashboard from daily report CSV")
    parser.add_argument("--date", help="Report date, e.g. 2026-06-12. Default: latest available")
    parser.add_argument("--input", help="Optional explicit CSV path (filtered.csv)")
    parser.add_argument("--output", help="Optional output HTML path")
    parser.add_argument(
        "--radar-show-zero-buckets",
        choices=["true", "false"],
        default="false",
        help="Whether to keep zero-value buckets on radar axis. Default: false (compact).",
    )
    parser.add_argument(
        "--bubble-exclude-keywords",
        default=",".join(BUBBLE_EXCLUDED_MODEL_KEYWORDS),
        help="Comma-separated model keywords to exclude from bubble chart points.",
    )
    args = parser.parse_args()

    report_date = args.date or _latest_report_date()

    if args.input:
        csv_path = Path(args.input)
        if not csv_path.is_absolute():
            csv_path = ROOT / csv_path
    else:
        csv_path = REPORT_ROOT / report_date / "filtered.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    out_path = Path(args.output) if args.output else (REPORT_ROOT / report_date / "charging_visualization_dashboard.html")
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = _load_rows(csv_path)
    radar_show_zero_buckets = args.radar_show_zero_buckets.lower() == "true"
    bubble_exclude_keywords = _parse_exclude_keywords(args.bubble_exclude_keywords)
    html = build_visualization_html(
        rows,
        report_date=report_date,
        radar_show_zero_buckets=radar_show_zero_buckets,
        bubble_exclude_keywords=bubble_exclude_keywords,
    )

    js_check_status, js_check_message = _validate_generated_html_js(html)
    out_path.write_text(html, encoding="utf-8")

    print(json.dumps({
        "status": "ok",
        "date": report_date,
        "input": str(csv_path),
        "output": str(out_path),
        "rows": len(rows),
        "radar_show_zero_buckets": radar_show_zero_buckets,
        "bubble_exclude_keywords": bubble_exclude_keywords,
        "js_syntax_check": js_check_status,
        "js_syntax_message": js_check_message,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
