from __future__ import annotations

import csv
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
REPORT_ROOT = ROOT / "reports" / "dongchedi_daily"
SITE_ROOT = ROOT / "site"


def _report_dirs() -> list[Path]:
    if not REPORT_ROOT.exists():
        return []

    dirs: list[Path] = []
    for path in REPORT_ROOT.iterdir():
        if not path.is_dir():
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", path.name):
            continue
        if (path / "filtered.csv").exists() and (path / "charging_visualization_dashboard.html").exists():
            dirs.append(path)
    return sorted(dirs)


def _latest_report_dir() -> Path:
    dirs = _report_dirs()
    if not dirs:
        raise FileNotFoundError("No generated Dongchedi report found under reports/dongchedi_daily")
    return dirs[-1]


def _copy_report_dir(report_dir: Path) -> None:
    target = SITE_ROOT / "reports" / report_dir.name
    target.mkdir(parents=True, exist_ok=True)

    for item in report_dir.iterdir():
        if item.is_file() and item.suffix.lower() in {".html", ".csv", ".json", ".md"}:
            shutil.copy2(item, target / item.name)

    summary_md = report_dir / "summary.md"
    if summary_md.exists():
        summary_html = "<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>摘要</title><style>body{font-family:Segoe UI,PingFang SC,Microsoft YaHei,sans-serif;line-height:1.7;margin:24px;background:#faf7f2;color:#12202b}pre{white-space:pre-wrap;word-break:break-word;background:#fff;border:1px solid rgba(18,32,43,.14);border-radius:16px;padding:20px;box-shadow:0 10px 28px rgba(0,0,0,.05)}</style></head><body><pre>"
        summary_html += html.escape(summary_md.read_text(encoding="utf-8"))
        summary_html += "</pre></body></html>"
        (target / "summary.html").write_text(summary_html, encoding="utf-8")


def _write_latest_alias(report_dir: Path) -> None:
    latest_dir = SITE_ROOT / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)

    dashboard_src = report_dir / "charging_visualization_dashboard.html"
    shutil.copy2(dashboard_src, latest_dir / "charging_visualization_dashboard.html")

    index_html = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta http-equiv="refresh" content="0; url=charging_visualization_dashboard.html" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>最新懂车帝充电数据可视化</title>
</head>
<body>
  <p>正在跳转到最新可视化页面。若未自动跳转，请打开 <a href="charging_visualization_dashboard.html">charging_visualization_dashboard.html</a>。</p>
</body>
</html>
"""
    (latest_dir / "index.html").write_text(index_html, encoding="utf-8")


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict((k, str(v).strip()) for k, v in row.items()) for row in csv.DictReader(f)]


def _num(value: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)", str(value or ""))
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _top_brands(rows: list[dict[str, str]], top_n: int = 8) -> list[tuple[str, int]]:
    cnt: dict[str, int] = {}
    for r in rows:
        brand = (r.get("品牌") or "未明确").strip()
        cnt[brand] = cnt.get(brand, 0) + 1
    return sorted(cnt.items(), key=lambda x: (-x[1], x[0]))[:top_n]


def _base_style() -> str:
    return """
  <style>
    :root {
      --bg1: #fff6eb;
      --bg2: #edf5ff;
      --ink: #12202b;
      --muted: #5d6874;
      --line: rgba(18, 32, 43, 0.14);
      --card: rgba(255, 255, 255, 0.88);
      --accent: #c55300;
      --accent-2: #ff8a00;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(900px 480px at 0% 0%, #ffd9b7 0%, transparent 55%),
        radial-gradient(1000px 520px at 100% 10%, #c4e0ff 0%, transparent 55%),
        linear-gradient(145deg, var(--bg1), var(--bg2));
      min-height: 100vh;
      padding: 20px;
    }
    .shell { max-width: 1280px; margin: 0 auto; }
    .nav {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 14px;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 10px;
      box-shadow: 0 12px 30px rgba(0,0,0,.06);
    }
    .nav a {
      text-decoration: none;
      color: var(--ink);
      padding: 8px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: #fff;
      font-weight: 600;
      font-size: 14px;
    }
    .nav a.active {
      color: #fff;
      border-color: transparent;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
    }
    .panel {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 22px;
      box-shadow: 0 16px 42px rgba(0,0,0,.08);
    }
    h1 { margin: 0 0 8px; font-size: 34px; }
    h2 { margin: 0 0 8px; font-size: 22px; }
    .sub { color: var(--muted); line-height: 1.7; margin: 6px 0 0; }
    .meta { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
    .pill {
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 13px;
      color: var(--muted);
    }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; margin-top: 14px; }
    .card {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: #fff;
      padding: 14px;
    }
    .table-wrap {
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      margin-top: 14px;
    }
    table { border-collapse: collapse; width: 100%; font-size: 13px; }
    th, td { border-bottom: 1px solid #edf0f3; padding: 8px 10px; text-align: left; white-space: nowrap; }
    th { position: sticky; top: 0; background: #f8fafc; z-index: 1; }
    .frame {
      width: 100%;
      height: min(78vh, 920px);
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      margin-top: 12px;
    }
    .foot { margin-top: 12px; color: var(--muted); font-size: 12px; }
    @media (max-width: 700px) {
      body { padding: 10px; }
      h1 { font-size: 26px; }
      .frame { height: min(68vh, 680px); }
    }
  </style>
"""


def _nav(active: str) -> str:
    tabs = [
        ("index.html", "首页简介", "intro"),
        ("data.html", "数据表", "data"),
        ("dashboard.html", "可视化", "dash"),
        ("insights.html", "趋势总结", "insights"),
    ]
    links: list[str] = []
    for href, label, key in tabs:
        cls = "active" if key == active else ""
        links.append(f"<a class=\"{cls}\" href=\"{href}\">{html.escape(label)}</a>")
    return f"<nav class=\"nav\">{''.join(links)}</nav>"


def _build_intro_html(latest_date: str, report_dirs: list[Path]) -> str:
    hist_cards: list[str] = []
    for report_dir in reversed(report_dirs[:12]):
        hist_cards.append(
            "<article class=\"card\">"
            f"<h3>{html.escape(report_dir.name)}</h3>"
            f"<p class=\"sub\">日报归档与对应图表。</p>"
            f"<p><a href=\"reports/{report_dir.name}/summary.html\">summary</a> | "
            f"<a href=\"reports/{report_dir.name}/charging_visualization_dashboard.html\">dashboard</a></p>"
            "</article>"
        )

    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>EV Charging Benchmarking</title>
{_base_style()}
</head>
<body>
  <div class=\"shell\">
    {_nav('intro')}
    <section class=\"panel\">
      <h1>EV Charging Benchmarking</h1>
      <p class=\"sub\">这是一个电动车充电与电池性能 benchmarking 网站，用于持续对比不同车型在快充速度、续航、电池指标上的表现，支持定期更新与趋势追踪。</p>
      <div class=\"meta\">
        <span class=\"pill\">最新数据日期: {latest_date}</span>
        <span class=\"pill\">数据源: 懂车帝参数页 + 日报处理结果</span>
        <span class=\"pill\">Purpose: 性能对比、选型参考、趋势监控</span>
      </div>
      <div class=\"grid\">
        <article class=\"card\"><h3>数据源</h3><p class=\"sub\">来自懂车帝车型参数页抓取与日报筛选（纯电、价格阈值）。</p></article>
        <article class=\"card\"><h3>Benchmark 维度</h3><p class=\"sub\">快充时间、充电窗口、高压平台、电池容量、电池能量密度、CLTC续航等。</p></article>
        <article class=\"card\"><h3>使用方式</h3><p class=\"sub\">先看数据表，再看可视化，最后在趋势页查看关键 takeaway。</p></article>
      </div>
      <h2 style=\"margin-top:16px\">历史归档</h2>
      <div class=\"grid\">{''.join(hist_cards)}</div>
      <p class=\"foot\">注: 页面 2/3/4 默认基于最新日期数据构建。</p>
    </section>
  </div>
</body>
</html>
"""


def _build_data_html(latest_date: str, rows: list[dict[str, str]]) -> str:
    if not rows:
        table_html = "<p class=\"sub\">暂无数据。</p>"
    else:
        headers = list(rows[0].keys())
        thead = "<tr>" + "".join(f"<th>{html.escape(h)}</th>" for h in headers) + "</tr>"
        body = []
        for r in rows:
            body.append("<tr>" + "".join(f"<td>{html.escape(str(r.get(h, '')))}</td>" for h in headers) + "</tr>")
        table_html = f"<div class=\"table-wrap\"><table><thead>{thead}</thead><tbody>{''.join(body)}</tbody></table></div>"

    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Charging & Battery Data</title>
{_base_style()}
</head>
<body>
  <div class=\"shell\">
    {_nav('data')}
    <section class=\"panel\">
      <h1>Charging & Battery 参数数据表</h1>
      <p class=\"sub\">此页展示最新抓取与处理后的 benchmarking 表格，供横向对比和二次分析。该页会随日报定期更新。</p>
      <div class=\"meta\">
        <span class=\"pill\">数据日期: {latest_date}</span>
        <span class=\"pill\">记录数: {len(rows)}</span>
        <span class=\"pill\">数据文件: reports/{latest_date}/filtered.csv</span>
      </div>
      {table_html}
    </section>
  </div>
</body>
</html>
"""


def _build_dashboard_html(latest_date: str) -> str:
    dashboard = f"reports/{latest_date}/charging_visualization_dashboard.html"
    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Charging Dashboard</title>
{_base_style()}
</head>
<body>
  <div class=\"shell\">
    {_nav('dash')}
    <section class=\"panel\">
      <h1>可视化 Dashboard</h1>
      <p class=\"sub\">该可视化由数据表页同源数据自动生成，用于快速观察车型分布、充电效率与关键指标差异。</p>
      <div class=\"meta\">
        <span class=\"pill\">数据日期: {latest_date}</span>
        <span class=\"pill\">来源: data.html 同批数据</span>
      </div>
      <iframe class=\"frame\" src=\"{dashboard}\" title=\"Charging Dashboard\"></iframe>
    </section>
  </div>
</body>
</html>
"""


def _build_insights_html(latest_date: str, rows: list[dict[str, str]]) -> str:
    total = len(rows)
    fast_values = [x for x in (_num(r.get("快充时间(分钟)", "")) for r in rows) if x is not None]
    avg_fast = (sum(fast_values) / len(fast_values)) if fast_values else None
    high_voltage = sum(1 for r in rows if (_num(r.get("高压平台电压(V)", "")) or 0) >= 800)
    high_ratio = (high_voltage / total * 100) if total else 0

    by_fast = []
    for r in rows:
        t = _num(r.get("快充时间(分钟)", ""))
        if t is not None:
            by_fast.append((t, r))
    by_fast.sort(key=lambda x: x[0])
    fastest = by_fast[:5]
    slowest = by_fast[-5:]

    brands = _top_brands(rows)

    def _render_rank(items: list[tuple[float, dict[str, str]]]) -> str:
        if not items:
            return "<p class=\"sub\">暂无可用数据</p>"
        cards = []
        for val, row in items:
            cards.append(
                "<article class=\"card\">"
                f"<h3>{html.escape(row.get('车型', '未命名车型'))}</h3>"
                f"<p class=\"sub\">品牌: {html.escape(row.get('品牌', '未明确'))}</p>"
                f"<p class=\"sub\">快充时间: {val:.1f} 分钟</p>"
                "</article>"
            )
        return "<div class=\"grid\">" + "".join(cards) + "</div>"

    brand_html = "".join(
        f"<li>{html.escape(name)}: {count} 款</li>" for name, count in brands
    ) or "<li>暂无</li>"

    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Insights & Takeaways</title>
{_base_style()}
</head>
<body>
  <div class=\"shell\">
    {_nav('insights')}
    <section class=\"panel\">
      <h1>趋势总结与 Takeaways</h1>
      <p class=\"sub\">基于数据表页同批数据，提炼关键趋势与可执行结论，帮助你快速做车型性能 benchmarking 决策。</p>
      <div class=\"meta\">
        <span class=\"pill\">数据日期: {latest_date}</span>
        <span class=\"pill\">样本数: {total}</span>
        <span class=\"pill\">800V及以上占比: {high_ratio:.1f}%</span>
        <span class=\"pill\">平均快充时间: {f'{avg_fast:.1f} 分钟' if avg_fast is not None else '未明确'}</span>
      </div>

      <h2 style=\"margin-top:16px\">Top 品牌分布</h2>
      <ul>{brand_html}</ul>

      <h2 style=\"margin-top:16px\">最快快充车型（Top 5）</h2>
      {_render_rank(fastest)}

      <h2 style=\"margin-top:16px\">最慢快充车型（Bottom 5）</h2>
      {_render_rank(slowest)}

      <h2 style=\"margin-top:16px\">Takeaways</h2>
      <div class=\"grid\">
        <article class=\"card\"><h3>1. 高压平台渗透</h3><p class=\"sub\">高压平台占比可用于判断高功率快充基础能力，适合持续按周追踪其变化。</p></article>
        <article class=\"card\"><h3>2. 充电效率分化</h3><p class=\"sub\">同价位车型快充时间差异明显，建议结合充电窗口与电池容量做综合比较。</p></article>
        <article class=\"card\"><h3>3. 品牌策略差异</h3><p class=\"sub\">品牌在电池容量和快充时间上的取舍不同，可用于产品定位和竞品研究。</p></article>
      </div>
    </section>
  </div>
</body>
</html>
"""


def main() -> None:
  latest_report = _latest_report_dir()
  report_dirs = _report_dirs()
  latest_date = latest_report.name
  latest_csv = latest_report / "filtered.csv"
  latest_rows = _load_rows(latest_csv) if latest_csv.exists() else []

  SITE_ROOT.mkdir(parents=True, exist_ok=True)

  for report_dir in report_dirs:
    _copy_report_dir(report_dir)

  _write_latest_alias(latest_report)
  (SITE_ROOT / "index.html").write_text(_build_intro_html(latest_date, report_dirs), encoding="utf-8")
  (SITE_ROOT / "data.html").write_text(_build_data_html(latest_date, latest_rows), encoding="utf-8")
  (SITE_ROOT / "dashboard.html").write_text(_build_dashboard_html(latest_date), encoding="utf-8")
  (SITE_ROOT / "insights.html").write_text(_build_insights_html(latest_date, latest_rows), encoding="utf-8")

  print(
    json.dumps(
      {
        "status": "ok",
        "latest_report": latest_report.name,
        "reports": len(report_dirs),
        "pages": ["index.html", "data.html", "dashboard.html", "insights.html"],
      },
      ensure_ascii=False,
      indent=2,
    )
  )


if __name__ == "__main__":
  main()
