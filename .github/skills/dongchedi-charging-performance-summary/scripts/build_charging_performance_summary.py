from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
REPORT_ROOT = ROOT / "reports" / "dongchedi_daily"

OUTPUT_FILENAME = "charging_performance_summary.md"
FIELD_ORDER = [
    "车系ID",
    "车型",
    "纯电续航里程(km)工信部",
    "纯电续航里程(km)CLTC",
    "高压快充平台",
    "充电时间",
    "充电电量",
]


def _clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


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


def _normalize_row(row: dict[str, str]) -> dict[str, str]:
    charge_window = _clean(row.get("充电电量")) or _clean(row.get("快充电量(%)")) or "未明确显示"
    return {
        "车系ID": _clean(row.get("车系ID")) or "未明确显示",
        "车型": _clean(row.get("车型")) or "未明确显示",
        "纯电续航里程(km)工信部": _clean(row.get("纯电续航里程(km)工信部")) or "未明确显示",
        "纯电续航里程(km)CLTC": _clean(row.get("纯电续航里程(km)CLTC")) or "未明确显示",
        "高压快充平台": _clean(row.get("高压快充平台")) or "未明确显示",
        "充电时间": _clean(row.get("充电时间")) or "未明确显示",
        "充电电量": charge_window,
    }


def _build_markdown(rows: list[dict[str, str]], report_date: str) -> str:
    unresolved_items: list[str] = []

    lines = [
        f"# Dongchedi Charging Performance Summary ({report_date})",
        "",
        "## 中文结论",
        f"共覆盖 {len(rows)} 个车型，按统一口径输出了续航、平台电压与快充信息，可直接用于日报或周报横向对比。",
        "",
        "## English Conclusion",
        f"This summary covers {len(rows)} models with normalized EV range and fast-charging fields, ready for cross-model comparison in reports.",
        "",
        "| " + " | ".join(FIELD_ORDER) + " |",
        "|" + "|".join(["---"] * len(FIELD_ORDER)) + "|",
    ]

    for row in rows:
        values = [row.get(col, "未明确显示") for col in FIELD_ORDER]
        lines.append("| " + " | ".join(values) + " |")
        for col, value in zip(FIELD_ORDER, values):
            if value == "未明确显示":
                unresolved_items.append(f"{row.get('车型', '未明确显示')} - {col}")

    lines.extend([
        "",
        "## 质量备注 / Quality Notes",
        "- 映射规则: 若源字段为 快充电量(%)，统一输出为 充电电量。",
        f"- 未明确显示字段数量: {len(unresolved_items)}",
    ])

    if unresolved_items:
        lines.append("- 未明确显示明细:")
        for item in unresolved_items[:50]:
            lines.append(f"  - {item}")
        if len(unresolved_items) > 50:
            lines.append(f"  - ... 其余 {len(unresolved_items) - 50} 项省略")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build charging performance summary markdown from daily filtered.csv")
    parser.add_argument("--date", help="Report date in YYYY-MM-DD; default latest")
    args = parser.parse_args()

    report_date = args.date or _latest_report_date()
    report_dir = REPORT_ROOT / report_date
    csv_path = report_dir / "filtered.csv"
    output_path = report_dir / OUTPUT_FILENAME

    if not report_dir.exists():
        raise FileNotFoundError(f"Report folder not found: {report_dir}")
    if not csv_path.exists():
        raise FileNotFoundError(f"Required file not found: {csv_path}")

    raw_rows = _load_rows(csv_path)
    rows = [_normalize_row(row) for row in raw_rows]
    markdown = _build_markdown(rows, report_date)

    output_path.write_text(markdown, encoding="utf-8")
    print(f"Resolved date: {report_date}")
    print(f"Output: {output_path}")
    print(f"Rows: {len(rows)}")


if __name__ == "__main__":
    main()
