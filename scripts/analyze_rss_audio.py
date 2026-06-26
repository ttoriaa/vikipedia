from __future__ import annotations

import argparse
from collections import Counter
import csv
import datetime as dt
import json
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_ROOT = ROOT / "reports" / "rss_audio_analysis"

EN_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "at",
    "by",
    "from",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "that",
    "this",
    "it",
    "as",
    "we",
    "you",
    "they",
    "i",
    "he",
    "she",
    "them",
    "his",
    "her",
    "our",
    "your",
}

ZH_STOPWORDS = {
    "我们",
    "你们",
    "他们",
    "以及",
    "然后",
    "因为",
    "所以",
    "这个",
    "那个",
    "一个",
    "一些",
    "就是",
    "其实",
    "如果",
    "但是",
    "而且",
    "还有",
    "进行",
    "可以",
    "已经",
    "没有",
    "自己",
    "问题",
    "时候",
    "这样",
    "什么",
}

TOPIC_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("科技与AI", ("ai", "人工智能", "模型", "算法", "大模型", "机器学习", "deep learning", "llm")),
    ("商业与创业", ("创业", "商业", "公司", "融资", "投资", "市场", "营收", "用户增长", "strategy")),
    ("职场与管理", ("管理", "团队", "领导", "绩效", "协作", "组织", "招聘", "面试")),
    ("教育与学习", ("学习", "课程", "教育", "学校", "训练", "考试", "知识")),
    ("心理与关系", ("情绪", "焦虑", "心理", "关系", "依恋", "沟通", "压力", "therapy")),
    ("财经与投资", ("股票", "基金", "债券", "利率", "通胀", "经济", "financial", "投资组合")),
    ("汽车与出行", ("汽车", "新能源", "电池", "充电", "续航", "驾驶", "座舱", "智驾")),
    ("文化与生活", ("生活", "电影", "音乐", "文化", "旅行", "读书", "创作", "艺术")),
]

TOPIC_IDEA_TEMPLATES: dict[str, list[str]] = {
    "科技与AI": [
        "{keyword} 在未来 12 个月的实际落地场景",
        "从 {keyword} 看普通用户最容易踩的 3 个坑",
        "{keyword} 与组织效率：哪些岗位会先改变",
    ],
    "商业与创业": [
        "围绕 {keyword} 的商业模式拆解与收入路径",
        "{keyword} 相关产品从 0 到 1 的最小验证方案",
        "用一集讲清楚 {keyword} 的供需错配机会",
    ],
    "职场与管理": [
        "团队在 {keyword} 场景下的协作流程升级",
        "管理者如何通过 {keyword} 提升复盘质量",
        "围绕 {keyword} 的一周执行计划模板",
    ],
    "教育与学习": [
        "把 {keyword} 做成可持续学习路径",
        "初学者学习 {keyword} 的误区与纠偏",
        "围绕 {keyword} 的高效知识内化方法",
    ],
    "心理与关系": [
        "在 {keyword} 情境下改善沟通的具体练习",
        "如何识别 {keyword} 引发的情绪模式",
        "基于 {keyword} 的边界感建立指南",
    ],
    "财经与投资": [
        "{keyword} 对个人资产配置的影响",
        "从 {keyword} 看中长期风险与机会",
        "普通人理解 {keyword} 的三层框架",
    ],
    "汽车与出行": [
        "围绕 {keyword} 的用车决策模型",
        "{keyword} 技术路线与用户体验差异",
        "一集看懂 {keyword} 的关键指标",
    ],
    "文化与生活": [
        "{keyword} 如何改变日常生活方式",
        "围绕 {keyword} 的创作灵感与表达路径",
        "从 {keyword} 出发的个人成长主题策划",
    ],
    "综合话题": [
        "围绕 {keyword} 的跨领域对话主题",
        "从 {keyword} 延展出的 5 个下一期方向",
        "把 {keyword} 做成系列内容的方法",
    ],
}


_FW_MODEL_CACHE: dict[tuple[str, str, str], Any] = {}
_OW_MODEL_CACHE: dict[str, Any] = {}


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def clean_env_value(value: str | None, default: str = "") -> str:
    text = clean_text(value)
    if not text:
        return default
    return text.strip().strip('"').strip("'")


def resolve_llm_api_key() -> str:
    # Prefer GLM key, fallback to OpenAI key for backward compatibility.
    return clean_env_value(os.getenv("GLM_API_KEY")) or clean_env_value(os.getenv("OPENAI_API_KEY"))


def resolve_llm_base_url(default: str = "https://api.openai.com/v1") -> str:
    configured = clean_env_value(os.getenv("OPENAI_BASE_URL"))
    if configured:
        return configured.rstrip("/")
    if clean_env_value(os.getenv("GLM_API_KEY")):
        glm_base = clean_env_value(os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"))
        return glm_base.rstrip("/")
    return default.rstrip("/")


def safe_name(value: str, limit: int = 80) -> str:
    text = clean_text(value)
    if not text:
        return "untitled"
    text = re.sub(r"[\\/:*?\"<>|]", "_", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] or "untitled"


def fetch_rss(session: requests.Session, rss_url: str, timeout: int = 30) -> str:
    resp = session.get(rss_url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def _find_text(node: ET.Element, tags: list[str]) -> str:
    for tag in tags:
        child = node.find(tag)
        if child is not None and child.text:
            return clean_text(child.text)
    return ""


def parse_rss_items(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    items = root.findall(".//item")

    parsed: list[dict[str, str]] = []
    for item in items:
        title = _find_text(item, ["title", "{http://purl.org/rss/1.0/}title"])
        pub_date = _find_text(item, ["pubDate", "published", "{http://purl.org/dc/elements/1.1/}date"])
        guid = _find_text(item, ["guid", "id"])
        link = _find_text(item, ["link"])

        enclosure = item.find("enclosure")
        audio_url = ""
        audio_type = ""
        audio_length = ""

        if enclosure is not None:
            audio_url = clean_text(enclosure.attrib.get("url"))
            audio_type = clean_text(enclosure.attrib.get("type"))
            audio_length = clean_text(enclosure.attrib.get("length"))

        if not audio_url:
            for child in item:
                tag = child.tag.lower()
                if tag.endswith("content") or tag.endswith("link"):
                    href = clean_text(child.attrib.get("url") or child.attrib.get("href"))
                    if href and re.search(r"\.(mp3|m4a|aac|wav|ogg)(\?|$)", href, flags=re.IGNORECASE):
                        audio_url = href
                        break

        parsed.append(
            {
                "title": title,
                "pub_date": pub_date,
                "guid": guid,
                "link": link,
                "audio_url": audio_url,
                "audio_type": audio_type,
                "audio_length": audio_length,
            }
        )

    return parsed


def resolve_local_audio_files(inputs: list[str]) -> list[Path]:
    exts = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac"}
    resolved: list[Path] = []
    seen: set[Path] = set()

    for raw in inputs:
        text = clean_text(raw)
        if not text:
            continue

        p = Path(text)
        if not p.is_absolute():
            p = ROOT / p

        if p.is_dir():
            candidates = sorted([x for x in p.rglob("*") if x.is_file() and x.suffix.lower() in exts])
            for c in candidates:
                if c not in seen:
                    resolved.append(c)
                    seen.add(c)
            continue

        if p.exists() and p.is_file():
            if p.suffix.lower() in exts and p not in seen:
                resolved.append(p)
                seen.add(p)
            continue

        # Support simple glob patterns like ./audio/*.m4a
        parent = p.parent if p.parent.exists() else ROOT
        pattern = p.name
        for c in sorted(parent.glob(pattern)):
            if c.is_file() and c.suffix.lower() in exts and c not in seen:
                resolved.append(c)
                seen.add(c)

    return resolved


def infer_audio_suffix(url: str, content_type: str) -> str:
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix.lower()
    if ext in {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac"}:
        return ext
    ct = content_type.lower()
    if "mpeg" in ct or "mp3" in ct:
        return ".mp3"
    if "mp4" in ct or "m4a" in ct:
        return ".m4a"
    if "wav" in ct:
        return ".wav"
    if "ogg" in ct:
        return ".ogg"
    return ".bin"


def download_audio(session: requests.Session, url: str, out_file: Path, timeout: int = 120) -> tuple[str, int]:
    with session.get(url, timeout=timeout, stream=True) as resp:
        resp.raise_for_status()
        content_type = clean_text(resp.headers.get("Content-Type"))
        total = 0
        with out_file.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                f.write(chunk)
                total += len(chunk)
    return content_type, total


def transcribe_with_openai(session: requests.Session, audio_file: Path, model: str, timeout: int = 600) -> str:
    api_key = resolve_llm_api_key()
    if not api_key:
        raise RuntimeError("GLM_API_KEY/OPENAI_API_KEY is not set")

    base_url = resolve_llm_base_url("https://api.openai.com/v1")
    endpoint = f"{base_url}/audio/transcriptions"

    with audio_file.open("rb") as f:
        files = {
            "file": (audio_file.name, f, "application/octet-stream"),
        }
        data = {
            "model": model,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        resp = session.post(endpoint, headers=headers, data=data, files=files, timeout=timeout)

    resp.raise_for_status()
    body = resp.json()
    return clean_text(body.get("text"))


def transcribe_with_local_whisper(
    audio_file: Path,
    model_name: str,
    language: str,
    device: str,
    compute_type: str,
) -> str:
    lang = clean_text(language) or None

    try:
        from faster_whisper import WhisperModel  # type: ignore

        key = (model_name, device, compute_type)
        model = _FW_MODEL_CACHE.get(key)
        if model is None:
            model = WhisperModel(model_name, device=device, compute_type=compute_type)
            _FW_MODEL_CACHE[key] = model

        segments, _info = model.transcribe(str(audio_file), language=lang, vad_filter=True)
        text = " ".join(clean_text(seg.text) for seg in segments if clean_text(seg.text))
        if clean_text(text):
            return clean_text(text)
    except ImportError:
        pass

    try:
        import whisper  # type: ignore

        model = _OW_MODEL_CACHE.get(model_name)
        if model is None:
            model = whisper.load_model(model_name)
            _OW_MODEL_CACHE[model_name] = model

        result = model.transcribe(str(audio_file), language=lang)
        text = clean_text(result.get("text"))
        if text:
            return text
    except ImportError as exc:
        raise RuntimeError(
            "Local Whisper fallback unavailable: install faster-whisper or openai-whisper."
        ) from exc

    raise RuntimeError("Local Whisper fallback produced empty transcript")


def _extract_json_object(raw: str) -> dict[str, Any]:
    text = clean_text(raw)
    if not text:
        raise ValueError("Empty model response")

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("No JSON object found in model response")
    parsed = json.loads(m.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("Model response JSON is not an object")
    return parsed


def analyze_text_with_openai(session: requests.Session, text: str, model: str, timeout: int = 120) -> dict[str, Any]:
    api_key = resolve_llm_api_key()
    if not api_key:
        raise RuntimeError("GLM_API_KEY/OPENAI_API_KEY is not set")

    base_url = resolve_llm_base_url("https://api.openai.com/v1")
    endpoint = f"{base_url}/chat/completions"

    prompt = (
        "请分析以下播客转写文本，返回严格 JSON，字段为: "
        "topic(字符串，简短主题分类), summary_zh(字符串，中文摘要80-150字), "
        "keywords(字符串数组，3-8个关键词，中文优先)。"
    )

    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": "你是中文内容分析助手，只输出 JSON。"},
            {"role": "user", "content": prompt + "\n\n文本如下:\n" + text[:12000]},
        ],
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    resp = session.post(endpoint, headers=headers, data=json.dumps(payload, ensure_ascii=False), timeout=timeout)
    resp.raise_for_status()
    body = resp.json()
    content = clean_text(body.get("choices", [{}])[0].get("message", {}).get("content"))
    parsed = _extract_json_object(content)

    keywords = parsed.get("keywords")
    if isinstance(keywords, str):
        keywords = [k.strip() for k in re.split(r"[,，;；]", keywords) if k.strip()]
    if not isinstance(keywords, list):
        keywords = []

    return {
        "topic": clean_text(parsed.get("topic")),
        "summary_zh": clean_text(parsed.get("summary_zh")),
        "keywords": [clean_text(k) for k in keywords if clean_text(k)],
    }


def infer_topic_by_rules(text: str) -> str:
    lower = text.lower()
    best_topic = "综合话题"
    best_score = 0
    for topic, keys in TOPIC_RULES:
        score = sum(1 for k in keys if k.lower() in lower)
        if score > best_score:
            best_topic = topic
            best_score = score
    return best_topic


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?\.])\s+|\n+", clean_text(text))
    return [p.strip() for p in parts if p.strip()]


def fallback_summary_zh(text: str, max_chars: int = 140) -> str:
    sents = split_sentences(text)
    if not sents:
        return "未提取到可用文本。"

    buf = []
    total = 0
    for sent in sents[:5]:
        if total + len(sent) > max_chars and buf:
            break
        buf.append(sent)
        total += len(sent)
        if total >= max_chars:
            break
    summary = "".join(buf)
    if len(summary) > max_chars:
        summary = summary[:max_chars].rstrip()
    return summary or sents[0][:max_chars]


def extract_keywords_fallback(text: str, top_n: int = 6) -> list[str]:
    # Chinese token chunks with 2-6 chars, excluding stopwords.
    zh_tokens = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
    zh_filtered = [t for t in zh_tokens if t not in ZH_STOPWORDS]

    # English words fallback.
    en_tokens = [t.lower() for t in re.findall(r"\b[a-zA-Z][a-zA-Z\-']{2,}\b", text)]
    en_filtered = [t for t in en_tokens if t not in EN_STOPWORDS]

    counts = Counter(zh_filtered + en_filtered)
    return [token for token, _ in counts.most_common(top_n)]


def analyze_text_fallback(text: str) -> dict[str, Any]:
    topic = infer_topic_by_rules(text)
    summary = fallback_summary_zh(text)
    keywords = extract_keywords_fallback(text)
    return {
        "topic": topic,
        "summary_zh": summary,
        "keywords": keywords,
    }


def _split_keywords(value: str) -> list[str]:
    raw = clean_text(value)
    if not raw:
        return []
    parts = [p.strip() for p in re.split(r"[,，;；、]", raw) if p.strip()]
    return parts


def build_topic_ideas(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, str]]:
    analyzed = [r for r in rows if clean_text(r.get("summary_zh"))]
    if not analyzed:
        return []

    topic_counts = Counter(clean_text(r.get("topic")) or "综合话题" for r in analyzed)
    keyword_counts: Counter[str] = Counter()
    for r in analyzed:
        keyword_counts.update(_split_keywords(clean_text(r.get("keywords"))))

    top_topics = [t for t, _ in topic_counts.most_common(3)]
    top_keywords = [k for k, _ in keyword_counts.most_common(12)]
    if not top_keywords:
        top_keywords = ["核心议题"]

    ideas: list[dict[str, str]] = []
    used_titles: set[str] = set()

    for topic in top_topics:
        templates = TOPIC_IDEA_TEMPLATES.get(topic) or TOPIC_IDEA_TEMPLATES["综合话题"]
        topic_related_keywords = [k for k in top_keywords if len(k) >= 2][:4]
        if not topic_related_keywords:
            topic_related_keywords = ["核心议题"]

        for i, tpl in enumerate(templates):
            kw = topic_related_keywords[i % len(topic_related_keywords)]
            title = tpl.format(keyword=kw)
            if title in used_titles:
                continue
            used_titles.add(title)
            ideas.append(
                {
                    "idea_title": title,
                    "seed_topic": topic,
                    "seed_keywords": ", ".join(topic_related_keywords[:3]),
                    "why": f"近期内容中“{topic}”出现频次较高，且与关键词“{kw}”关联紧密。",
                }
            )

    # Add cross-topic ideas based on top keywords to keep recommendations fresh.
    for kw in top_keywords[:6]:
        title = f"跨主题深挖：{kw} 在不同人群中的真实应用差异"
        if title in used_titles:
            continue
        used_titles.add(title)
        ideas.append(
            {
                "idea_title": title,
                "seed_topic": "跨主题",
                "seed_keywords": kw,
                "why": f"关键词“{kw}”在多期内容中重复出现，适合做横向比较。",
            }
        )

    return ideas[: max(1, limit)]


def count_text_metrics(text: str) -> dict[str, int]:
    cn_chars = re.findall(r"[\u4e00-\u9fff]", text)
    en_words = re.findall(r"\b[a-zA-Z][a-zA-Z\-']*\b", text)
    return {
        "char_count": len(text),
        "cn_char_count": len(cn_chars),
        "en_word_count": len(en_words),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        fieldnames = [
            "index",
            "title",
            "pub_date",
            "audio_url",
            "audio_file",
            "audio_bytes",
            "transcript_file",
            "transcribe_method",
            "char_count",
            "cn_char_count",
            "en_word_count",
            "topic",
            "keywords",
            "summary_zh",
            "analysis_method",
            "status",
            "error",
        ]
    else:
        fieldnames = list(rows[0].keys())

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_markdown(
    path: Path,
    rss_url: str,
    rows: list[dict[str, Any]],
    generated_at: str,
    topic_ideas: list[dict[str, str]] | None = None,
) -> None:
    ok_count = sum(1 for r in rows if clean_text(r.get("status")) == "ok")
    transcribed_count = sum(1 for r in rows if clean_text(r.get("transcript_file")))

    lines = [
        "# RSS Audio Analysis",
        "",
        f"- RSS URL: {rss_url}",
        f"- Generated At (UTC): {generated_at}",
        f"- Items Processed: {len(rows)}",
        f"- Items Downloaded: {ok_count}",
        f"- Items Transcribed: {transcribed_count}",
        "",
        "## Item Summary",
        "",
        "| # | Title | Pub Date | Audio | Transcript | Topic | Keywords | Status |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for r in rows:
        title = clean_text(r.get("title")) or "(no title)"
        pub_date = clean_text(r.get("pub_date")) or ""
        audio_url = clean_text(r.get("audio_url"))
        status = clean_text(r.get("status"))
        transcript_file = clean_text(r.get("transcript_file"))
        topic = clean_text(r.get("topic"))
        keywords = clean_text(r.get("keywords"))

        audio_md = f"[link]({audio_url})" if audio_url else ""
        transcript_md = transcript_file if transcript_file else ""

        lines.append(
            f"| {r.get('index', '')} | {title.replace('|', '\\|')} | {pub_date.replace('|', '\\|')} | {audio_md} | {transcript_md} | {topic.replace('|', '\\|')} | {keywords.replace('|', '\\|')} | {status} |"
        )

    with_analysis = [r for r in rows if clean_text(r.get("summary_zh"))]
    if with_analysis:
        lines.extend(["", "## Chinese Summaries", ""])
        for r in with_analysis:
            title = clean_text(r.get("title")) or "(no title)"
            method = clean_text(r.get("analysis_method"))
            lines.append(f"### {r.get('index', '')}. {title}")
            lines.append("")
            lines.append(f"- Topic: {clean_text(r.get('topic'))}")
            lines.append(f"- Keywords: {clean_text(r.get('keywords'))}")
            lines.append(f"- Method: {method}")
            lines.append(f"- Summary: {clean_text(r.get('summary_zh'))}")
            lines.append("")

    if topic_ideas:
        lines.extend(["", "## New Topic Ideas", ""])
        lines.append("| # | Idea | Based On Topic | Seed Keywords | Why This Works |")
        lines.append("|---|---|---|---|---|")
        for i, idea in enumerate(topic_ideas, start=1):
            lines.append(
                f"| {i} | {clean_text(idea.get('idea_title')).replace('|', '\\|')} | {clean_text(idea.get('seed_topic')).replace('|', '\\|')} | {clean_text(idea.get('seed_keywords')).replace('|', '\\|')} | {clean_text(idea.get('why')).replace('|', '\\|')} |"
            )

    errors = [r for r in rows if clean_text(r.get("error"))]
    if errors:
        lines.extend(["", "## Errors", ""])
        for r in errors:
            lines.append(f"- #{r.get('index')}: {clean_text(r.get('error'))}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_dirs(base_dir: Path) -> dict[str, Path]:
    audio_dir = base_dir / "audio"
    transcript_dir = base_dir / "transcripts"
    audio_dir.mkdir(parents=True, exist_ok=True)
    transcript_dir.mkdir(parents=True, exist_ok=True)
    return {"audio": audio_dir, "transcripts": transcript_dir}


def run(args: argparse.Namespace) -> int:
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if args.output_dir:
        out_dir = Path(args.output_dir)
        if not out_dir.is_absolute():
            out_dir = ROOT / out_dir
    else:
        stamp = dt.datetime.now().strftime("%Y-%m-%d")
        out_dir = DEFAULT_OUT_ROOT / stamp

    dirs = ensure_dirs(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    if args.no_proxy:
        session.trust_env = False

    xml_text = ""
    rss_source = ""
    local_audio_inputs = resolve_local_audio_files(args.audio_files or [])

    if local_audio_inputs:
        items = [
            {
                "title": p.stem,
                "pub_date": "",
                "guid": str(p),
                "link": "",
                "audio_url": str(p),
                "audio_type": "local",
                "audio_length": "",
                "_local_path": str(p),
            }
            for p in local_audio_inputs
        ]
        rss_source = "local-audio-files"
    else:
        if args.rss_file:
            rss_file = Path(args.rss_file)
            if not rss_file.is_absolute():
                rss_file = ROOT / rss_file
            if not rss_file.exists():
                raise FileNotFoundError(f"RSS file not found: {rss_file}")
            xml_text = rss_file.read_text(encoding="utf-8")
        elif args.rss_url:
            try:
                xml_text = fetch_rss(session, args.rss_url, timeout=args.timeout)
            except requests.RequestException as exc:
                raise RuntimeError(
                    "Failed to fetch RSS URL. Check proxy/network settings, try --no-proxy, or use --rss-file with a local XML file."
                ) from exc
        else:
            raise RuntimeError("Provide either --rss-url/--rss-file or --audio-files")

        items = parse_rss_items(xml_text)
        rss_source = args.rss_url if args.rss_url else str(args.rss_file)

    if args.max_items > 0:
        items = items[: args.max_items]

    rows: list[dict[str, Any]] = []

    for idx, item in enumerate(items, start=1):
        title = clean_text(item.get("title")) or f"episode_{idx}"
        pub_date = clean_text(item.get("pub_date"))
        audio_url = clean_text(item.get("audio_url"))
        local_path = clean_text(item.get("_local_path"))

        row: dict[str, Any] = {
            "index": idx,
            "title": title,
            "pub_date": pub_date,
            "audio_url": audio_url,
            "audio_file": "",
            "audio_bytes": "",
            "transcript_file": "",
            "transcribe_method": "",
            "char_count": "",
            "cn_char_count": "",
            "en_word_count": "",
            "topic": "",
            "keywords": "",
            "summary_zh": "",
            "analysis_method": "",
            "status": "skipped",
            "error": "",
        }

        try:
            if local_path:
                src = Path(local_path)
                if not src.exists() or not src.is_file():
                    raise RuntimeError(f"Local audio file not found: {src}")

                suffix = src.suffix if src.suffix else ".bin"
                final_file = dirs["audio"] / f"{idx:03d}_{safe_name(title)}{suffix}"
                shutil.copy2(src, final_file)
                total_bytes = final_file.stat().st_size
            else:
                if not audio_url:
                    raise RuntimeError("No audio enclosure URL in this item")

                temp_file = dirs["audio"] / f"{idx:03d}_{safe_name(title)}.bin"
                content_type, total_bytes = download_audio(session, audio_url, temp_file, timeout=args.audio_timeout)
                suffix = infer_audio_suffix(audio_url, content_type)
                final_file = temp_file.with_suffix(suffix)
                temp_file.replace(final_file)

            row["audio_file"] = str(final_file.relative_to(out_dir)).replace("\\", "/")
            row["audio_bytes"] = total_bytes
            row["status"] = "ok"

            if args.transcribe:
                try:
                    transcript = transcribe_with_openai(
                        session,
                        final_file,
                        model=args.transcribe_model,
                        timeout=args.transcribe_timeout,
                    )
                    row["transcribe_method"] = "openai-api"
                except Exception:
                    if args.transcribe_fallback != "local-whisper":
                        raise

                    transcript = transcribe_with_local_whisper(
                        final_file,
                        model_name=args.local_whisper_model,
                        language=args.local_whisper_language,
                        device=args.local_whisper_device,
                        compute_type=args.local_whisper_compute_type,
                    )
                    row["transcribe_method"] = "local-whisper-fallback"

                transcript_file = dirs["transcripts"] / f"{idx:03d}_{safe_name(title)}.txt"
                transcript_file.write_text(transcript + "\n", encoding="utf-8")
                row["transcript_file"] = str(transcript_file.relative_to(out_dir)).replace("\\", "/")

                metrics = count_text_metrics(transcript)
                row.update(metrics)

                if args.analyze:
                    analysis: dict[str, Any]
                    if args.analysis_provider == "openai":
                        analysis = analyze_text_with_openai(
                            session,
                            transcript,
                            model=args.analysis_model,
                            timeout=args.analysis_timeout,
                        )
                        row["analysis_method"] = "openai"
                    elif args.analysis_provider == "rule":
                        analysis = analyze_text_fallback(transcript)
                        row["analysis_method"] = "rule"
                    else:
                        try:
                            analysis = analyze_text_with_openai(
                                session,
                                transcript,
                                model=args.analysis_model,
                                timeout=args.analysis_timeout,
                            )
                            row["analysis_method"] = "openai"
                        except Exception:
                            analysis = analyze_text_fallback(transcript)
                            row["analysis_method"] = "rule-fallback"

                    row["topic"] = clean_text(analysis.get("topic"))
                    kws = analysis.get("keywords", [])
                    if isinstance(kws, list):
                        row["keywords"] = ", ".join(clean_text(k) for k in kws if clean_text(k))
                    else:
                        row["keywords"] = clean_text(kws)
                    row["summary_zh"] = clean_text(analysis.get("summary_zh"))

        except Exception as exc:  # noqa: BLE001
            row["status"] = "error"
            row["error"] = str(exc)

        rows.append(row)

    json_path = out_dir / "episodes.json"
    csv_path = out_dir / "episodes.csv"
    md_path = out_dir / "summary.md"
    rss_path = out_dir / "rss.xml"
    ideas_path = out_dir / "topic_ideas.json"

    topic_ideas: list[dict[str, str]] = []
    if args.suggest_topics:
        topic_ideas = build_topic_ideas(rows, limit=args.topic_idea_count)

    if xml_text:
        rss_path.write_text(xml_text, encoding="utf-8")
    else:
        rss_path.write_text("<!-- local audio mode: no rss xml source -->\n", encoding="utf-8")
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    ideas_path.write_text(json.dumps(topic_ideas, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(csv_path, rows)
    write_markdown(md_path, rss_source, rows, generated_at, topic_ideas=topic_ideas)

    print(f"[done] Output directory: {out_dir}")
    print(f"[done] Summary: {md_path}")
    print(f"[done] CSV: {csv_path}")
    print(f"[done] JSON: {json_path}")
    print(f"[done] Topic Ideas: {ideas_path}")

    ok_count = sum(1 for r in rows if r.get("status") == "ok")
    err_count = sum(1 for r in rows if r.get("status") == "error")
    print(f"[stats] total={len(rows)} ok={ok_count} error={err_count} transcribe={bool(args.transcribe)}")

    return 0 if (ok_count > 0 or len(rows) == 0) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download podcast audio from RSS and generate transcript-ready analysis files.")
    parser.add_argument("--rss-url", default="", help="RSS feed URL")
    parser.add_argument("--rss-file", default="", help="Local RSS XML file path")
    parser.add_argument(
        "--audio-files",
        nargs="+",
        default=[],
        help="Local audio files/directories/glob patterns; when provided, RSS fetching is skipped",
    )
    parser.add_argument("--max-items", type=int, default=5, help="Max items to process; 0 means all")
    parser.add_argument("--output-dir", default="", help="Output directory (absolute or relative to workspace root)")

    parser.add_argument("--timeout", type=int, default=30, help="RSS fetch timeout seconds")
    parser.add_argument("--audio-timeout", type=int, default=180, help="Audio download timeout seconds")
    parser.add_argument("--no-proxy", action="store_true", help="Do not use system proxy settings for HTTP requests")

    parser.add_argument("--transcribe", action="store_true", help="Transcribe audio with OpenAI transcription API")
    parser.add_argument("--transcribe-model", default="gpt-4o-mini-transcribe", help="Transcription model name")
    parser.add_argument("--transcribe-timeout", type=int, default=900, help="Transcription timeout seconds")
    parser.add_argument(
        "--transcribe-fallback",
        choices=["none", "local-whisper"],
        default="local-whisper",
        help="Fallback when remote transcription fails",
    )
    parser.add_argument("--local-whisper-model", default="base", help="Local Whisper model name for fallback")
    parser.add_argument("--local-whisper-language", default="zh", help="Language hint for local Whisper fallback")
    parser.add_argument("--local-whisper-device", default="auto", help="Device for faster-whisper (cpu/cuda/auto)")
    parser.add_argument(
        "--local-whisper-compute-type",
        default="int8",
        help="Compute type for faster-whisper (int8/float16/float32)",
    )

    parser.add_argument("--analyze", action="store_true", help="Analyze transcript for topic, Chinese summary and keywords")
    parser.add_argument(
        "--analysis-provider",
        choices=["auto", "openai", "rule"],
        default="auto",
        help="Text analysis engine: auto prefers OpenAI and falls back to rule-based",
    )
    parser.add_argument("--analysis-model", default="gpt-4o-mini", help="OpenAI model for text analysis")
    parser.add_argument("--analysis-timeout", type=int, default=120, help="Text analysis timeout seconds")
    parser.add_argument("--suggest-topics", action="store_true", help="Generate new topic ideas based on analyzed content")
    parser.add_argument("--topic-idea-count", type=int, default=8, help="Number of topic ideas to generate")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
