#!/usr/bin/env python3
"""Generate a daily semiconductor scoring report with company-type weighted signals."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, request


def str_to_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "y", "on"}


def fetch_text(url: str, timeout: int = 20) -> str:
    req = request.Request(url)
    req.add_header("User-Agent", "semiconductor-daily-scoring/1.0")
    req.add_header("Accept", "text/html,application/xhtml+xml")
    with request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def parse_price_change(page_text: str) -> tuple[float | None, float | None]:
    # Matches patterns like: 2,901,000.00+137,000.00(+4.96%)
    m = re.search(r"([0-9][0-9,]*\.?[0-9]*)\s*([+-][0-9][0-9,]*\.?[0-9]*)\s*\(([+-][0-9]+\.?[0-9]*)%\)", page_text)
    if not m:
        return None, None
    try:
        price = float(m.group(1).replace(",", ""))
        pct = float(m.group(3))
        return price, pct
    except ValueError:
        return None, None


def contains_any(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(k.lower() in lower for k in keywords)


def keyword_signal(
    text: str,
    positive_keywords: list[str],
    negative_keywords: list[str],
) -> tuple[int, str]:
    lower = text.lower()
    pos_hits = [k for k in positive_keywords if k.lower() in lower]
    neg_hits = [k for k in negative_keywords if k.lower() in lower]

    if len(pos_hits) > len(neg_hits):
        return 1, f"positive_keywords={','.join(pos_hits[:3])}"
    if len(neg_hits) > len(pos_hits):
        return -1, f"negative_keywords={','.join(neg_hits[:3])}"
    if pos_hits and neg_hits:
        return 0, "mixed_keyword_signal"
    return 0, "no_keyword_signal"


def score_core_factors(
    quote_text: str,
    news_text: str,
    policy_text: str,
    company_type: str,
) -> tuple[list[int], dict[str, str]]:
    # 12 factors; only first six + #12 are auto-evaluated, others default to neutral.
    signals = [0] * 12
    evidence: dict[str, str] = {}

    type_compute_threshold = {
        "Fabless": 1.5,
        "Foundry": 1.8,
        "IDM": 2.0,
        "Equipment": 1.8,
        "OSAT": 1.8,
    }
    compute_up = type_compute_threshold.get(company_type, 2.0)
    compute_down = -compute_up

    price, pct = parse_price_change(quote_text)
    if pct is not None:
        if pct >= compute_up:
            signals[1] = 1
            evidence["compute_expansion"] = f"daily_move={pct:.2f}%>=threshold={compute_up:.2f}%"
        elif pct <= compute_down:
            signals[1] = -1
            evidence["compute_expansion"] = f"daily_move={pct:.2f}%<=threshold={compute_down:.2f}%"
        else:
            evidence["compute_expansion"] = f"daily_move={pct:.2f}%,within_threshold"
    else:
        evidence["compute_expansion"] = "source_unavailable"

    signals[0], evidence["application_demand"] = keyword_signal(
        news_text,
        ["ai", "agent", "autonomous", "robot", "inference", "datacenter demand", "model rollout"],
        ["demand weak", "slowdown", "guidance cut", "cautious demand"],
    )

    memory_positive = ["hbm", "high-bandwidth memory", "dram", "memory tight", "price increase", "price rises"]
    memory_negative = ["memory glut", "oversupply", "price decline", "inventory correction", "downcycle"]
    if company_type in {"IDM", "Foundry"}:
        memory_positive += ["allocation", "long-term agreement"]
    signals[2], evidence["memory_tightness"] = keyword_signal(news_text, memory_positive, memory_negative)

    signals[3], evidence["delivery_feasibility"] = keyword_signal(
        news_text,
        ["ship", "shipment", "mass production", "qualified", "yield improvement", "volume production"],
        ["delay", "postpone", "yield issue", "qualification issue", "ramp challenge"],
    )

    packaging_positive = ["cowos", "2.5d", "3d", "packaging expansion", "substrate supply improves", "osat capacity"]
    packaging_negative = ["packaging bottleneck", "substrate shortage", "capacity constraint", "backlog extends"]
    if company_type == "OSAT":
        packaging_positive += ["utilization", "capacity ramp"]
    signals[4], evidence["advanced_packaging"] = keyword_signal(news_text, packaging_positive, packaging_negative)

    signals[5], evidence["infrastructure_readiness"] = keyword_signal(
        news_text,
        ["electricity investment", "power expansion", "liquid cooling", "grid upgrade", "data center build"],
        ["power shortage", "grid constraint", "capacity cap", "cooling bottleneck"],
    )

    geo_mix = f"{news_text}\n{policy_text}"
    geo_signal, geo_ev = keyword_signal(
        geo_mix,
        ["tariff relief", "license approved", "policy support"],
        ["export control", "tariff", "sanction", "national security", "trade restriction", "china scrutiny"],
    )
    signals[11] = geo_signal
    evidence["geo_policy_risk"] = geo_ev

    return signals, evidence


def weighted_score(signals: list[int], weights: list[int]) -> int:
    return sum(s * w for s, w in zip(signals, weights))


def score_label(score: int) -> str:
    if score >= 35:
        return "strong_bullish"
    if score >= 15:
        return "bullish"
    if score <= -35:
        return "strong_bearish"
    if score <= -15:
        return "bearish"
    return "neutral"


def parse_companies(raw: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for part in [p.strip() for p in raw.split(",") if p.strip()]:
        bits = [b.strip() for b in part.split(":")]
        if len(bits) != 3:
            raise ValueError(f"Invalid company spec: {part}. Expected SYMBOL:SCOPE:TYPE")
        items.append({"symbol": bits[0], "scope": bits[1], "type": bits[2], "name": bits[0]})
    return items


def get_companies(config: dict[str, Any], universe: str, custom_companies: str | None) -> list[dict[str, str]]:
    if custom_companies:
        return parse_companies(custom_companies)
    universes = config.get("universes", {})
    if universe not in universes:
        raise ValueError(f"Unknown universe: {universe}")
    return universes[universe]


def maybe_git_commit(report_path: Path, auto_push: bool) -> tuple[str, str]:
    try:
        subprocess.run(["git", "add", str(report_path)], check=True)
        subprocess.run(["git", "commit", "-m", f"chore: add semiconductor daily scoring report {report_path.stem}"], check=True)
        if auto_push:
            subprocess.run(["git", "push"], check=True)
            return "success", "success"
        return "success", "skipped"
    except subprocess.CalledProcessError as exc:
        return f"failed({exc.returncode})", "skipped_or_failed"


def render_markdown(
    report_date: str,
    rows: list[dict[str, Any]],
    factor_names: list[str],
    output_path: Path,
) -> None:
    lines: list[str] = []
    lines.append(f"# Semiconductor Daily Scoring - {report_date}")
    lines.append("")
    lines.append("## Summary")
    lines.append("| Company | Type | Score | Label |")
    lines.append("|---|---|---:|---|")
    for row in rows:
        lines.append(f"| {row['name']} ({row['symbol']}) | {row['type']} | {row['score']} | {row['label']} |")

    for row in rows:
        lines.append("")
        lines.append(f"## {row['name']} ({row['symbol']})")
        lines.append(f"- Type: {row['type']}")
        lines.append(f"- Total score: {row['score']} ({row['label']})")
        lines.append(f"- Quote source: {row['quote_url']}")
        lines.append(f"- News source: {row['news_url']}")
        lines.append("")
        lines.append("| Factor | Signal | Evidence |")
        lines.append("|---|---:|---|")
        for idx, factor in enumerate(factor_names):
            ev = row["evidence"].get(factor, "")
            lines.append(f"| {factor} | {row['signals'][idx]} | {ev} |")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_json_payload(report_date: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "date": report_date,
        "company_count": len(rows),
        "companies": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run daily semiconductor weighted scoring")
    parser.add_argument("--config", default="config/default_universe.json")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--universe", default="core3")
    parser.add_argument("--companies", default="")
    parser.add_argument("--output-dir", default="reports/semiconductor_daily")
    parser.add_argument("--emit-json", default="")
    parser.add_argument("--dry-run", default="true")
    parser.add_argument("--auto-commit", action="store_true")
    parser.add_argument("--auto-push", action="store_true")
    args = parser.parse_args()

    cfg_path = Path(args.config)
    config = json.loads(cfg_path.read_text(encoding="utf-8"))
    factor_names: list[str] = config["factor_names"]

    companies = get_companies(config, args.universe, args.companies or None)
    source_urls = config["source_urls"]

    policy_texts: list[str] = []
    for purl in source_urls.get("policy_pages", []):
        try:
            policy_texts.append(fetch_text(purl))
        except (error.URLError, TimeoutError):
            policy_texts.append("source_unavailable")
    policy_text = "\n".join(policy_texts)

    rows: list[dict[str, Any]] = []
    for company in companies:
        ctype = company.get("type", "IDM")
        weights = config["weights"].get(ctype, config["weights"]["IDM"])

        quote_url = source_urls["sg_quote"].format(symbol=company["symbol"])
        news_url = source_urls["sg_news"].format(symbol=company["symbol"])

        try:
            quote_text = fetch_text(quote_url)
        except (error.URLError, TimeoutError):
            quote_text = "source_unavailable"

        try:
            news_text = fetch_text(news_url)
        except (error.URLError, TimeoutError):
            news_text = "source_unavailable"

        signals, evidence = score_core_factors(quote_text, news_text, policy_text, ctype)
        score = weighted_score(signals, weights)
        label = score_label(score)

        rows.append(
            {
                "name": company.get("name", company["symbol"]),
                "symbol": company["symbol"],
                "type": ctype,
                "signals": signals,
                "weights": weights,
                "score": score,
                "label": label,
                "evidence": evidence,
                "quote_url": quote_url,
                "news_url": news_url,
            }
        )

    output_dir = Path(args.output_dir)
    report_path = output_dir / f"semiconductor_daily_{args.date}.md"
    render_markdown(args.date, rows, factor_names, report_path)

    emit_json_path = Path(args.emit_json) if args.emit_json else None
    if emit_json_path:
        emit_json_path.parent.mkdir(parents=True, exist_ok=True)
        emit_json_path.write_text(
            json.dumps(render_json_payload(args.date, rows), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    dry_run = str_to_bool(args.dry_run)
    commit_status = "skipped"
    push_status = "skipped"
    if not dry_run and args.auto_commit:
        commit_status, push_status = maybe_git_commit(report_path, args.auto_push)

    print(json.dumps(
        {
            "date": args.date,
            "companies": [r["symbol"] for r in rows],
            "report": str(report_path),
            "emit_json": str(emit_json_path) if emit_json_path else "skipped",
            "commit": commit_status,
            "push": push_status,
        },
        ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
