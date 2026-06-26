#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import requests

try:
  from tailor_resume_for_jd import (
    _clean,
    _generate_with_openai,
    _html_to_text,
    _normalize_payload,
    _write_html_with_preserved_layout,
  )
except ModuleNotFoundError:
  from scripts.tailor_resume_for_jd import (
    _clean,
    _generate_with_openai,
    _html_to_text,
    _normalize_payload,
    _write_html_with_preserved_layout,
  )

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "reports" / "resume_tailoring"


def _resolve_llm_api_key() -> str:
  return os.getenv("GLM_API_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip()


def _resolve_llm_base_url(default: str = "https://api.openai.com/v1") -> str:
  configured = os.getenv("OPENAI_BASE_URL", "").strip()
  if configured:
    return configured.rstrip("/")
  if os.getenv("GLM_API_KEY", "").strip():
    return os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4").strip().rstrip("/")
  return default.rstrip("/")

INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Resume Tailor Studio</title>
  <style>
    :root {
      --bg: #f5efe4;
      --panel: #fffdfa;
      --ink: #1d2f38;
      --muted: #5a6b74;
      --line: rgba(29, 47, 56, 0.2);
      --accent: #0f6a63;
      --accent-2: #a4492e;
      --radius: 16px;
      --shadow: 0 14px 34px rgba(21, 35, 44, 0.14);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: "Source Han Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 12% 8%, rgba(15, 106, 99, 0.18), transparent 44%),
        radial-gradient(circle at 88% 14%, rgba(164, 73, 46, 0.16), transparent 38%),
        linear-gradient(150deg, #f8f3ea, var(--bg));
      min-height: 100vh;
      padding: 20px 14px 40px;
    }

    .wrap {
      max-width: 980px;
      margin: 0 auto;
      display: grid;
      gap: 14px;
    }

    .hero {
      border-radius: 24px;
      padding: 22px;
      color: #ecf5f3;
      background: linear-gradient(130deg, #114f4c 0%, #253a58 54%, #3b3148 100%);
      box-shadow: 0 18px 40px rgba(14, 33, 47, 0.24);
    }

    .hero h1 { margin: 0; font-size: clamp(24px, 4vw, 38px); }
    .hero p { margin: 8px 0 0; line-height: 1.6; color: rgba(236, 245, 243, 0.95); }

    .panel {
      background: rgba(255, 253, 250, 0.9);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 16px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(2px);
    }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .field {
      display: grid;
      gap: 6px;
      margin-bottom: 10px;
    }

    label {
      font-size: 13px;
      color: var(--muted);
    }

    input[type="text"],
    textarea,
    select {
      width: 100%;
      border: 1px solid rgba(29, 47, 56, 0.25);
      border-radius: 10px;
      padding: 10px 12px;
      font-size: 14px;
      background: #fff;
      color: var(--ink);
      outline: none;
    }

    textarea {
      min-height: 180px;
      resize: vertical;
      line-height: 1.5;
    }

    input[type="file"] {
      width: 100%;
      border: 1px dashed rgba(29, 47, 56, 0.35);
      border-radius: 10px;
      padding: 10px;
      background: #fff;
    }

    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 8px;
    }

    button {
      border: 0;
      border-radius: 999px;
      background: linear-gradient(135deg, var(--accent), #135f5a);
      color: #edf7f6;
      padding: 10px 18px;
      font-size: 14px;
      cursor: pointer;
      transition: transform 160ms ease, box-shadow 160ms ease;
      box-shadow: 0 8px 18px rgba(15, 106, 99, 0.28);
    }

    button:hover {
      transform: translateY(-1px);
    }

    button.secondary {
      background: linear-gradient(135deg, var(--accent-2), #8d3f2a);
      box-shadow: 0 8px 18px rgba(164, 73, 46, 0.24);
    }

    .hint {
      font-size: 12px;
      color: var(--muted);
      line-height: 1.45;
    }

    .result {
      display: none;
      margin-top: 6px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: #fff;
      padding: 12px;
    }

    .result.show { display: block; }

    .status {
      font-size: 14px;
      min-height: 20px;
      color: #24444a;
    }

    .error {
      color: #8a2a2a;
    }

    .link-row {
      display: grid;
      gap: 6px;
      margin-top: 8px;
    }

    .link-row a {
      color: #0d5964;
      word-break: break-all;
    }

    @media (max-width: 860px) {
      .grid { grid-template-columns: 1fr; }
      textarea { min-height: 150px; }
    }
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <h1>Resume Tailor Studio</h1>
      <p>输入现有简历 HTML 链接 + 新 JD（文本或图片），自动生成一份适配后的新简历 HTML 页面。保持原页面结构，只更新经历要点文本。</p>
    </section>

    <section class="panel">
      <div class="grid">
        <div>
          <div class="field">
            <label for="resumeHtmlUrl">简历 HTML 链接或本地路径</label>
            <input id="resumeHtmlUrl" type="text" placeholder="例如: file:///C:/.../vickie_resume_profile.html 或 https://..." />
          </div>

          <div class="field">
            <label for="jobTitle">目标岗位（可选）</label>
            <input id="jobTitle" type="text" placeholder="例如: AI Agent 产品经理" />
          </div>

          <div class="field">
            <label for="language">输出语言</label>
            <select id="language">
              <option value="zh" selected>中文</option>
              <option value="en">English</option>
              <option value="bilingual">中英双语</option>
            </select>
          </div>

          <div class="field">
            <label for="version">改写力度</label>
            <select id="version">
              <option value="conservative">conservative</option>
              <option value="balanced">balanced</option>
              <option value="aggressive" selected>aggressive</option>
            </select>
          </div>
        </div>

        <div>
          <div class="field">
            <label for="jdText">JD 文本（优先）</label>
            <textarea id="jdText" placeholder="直接粘贴岗位职责、要求、关键词等内容"></textarea>
          </div>

          <div class="field">
            <label for="jdImage">JD 图片（可选，文本为空时使用 OCR）</label>
            <input id="jdImage" type="file" accept="image/*" />
          </div>

          <p class="hint">说明：如果只上传图片，后端会尝试基于 OPENAI_API_KEY 进行图片文字提取。未配置时会提示失败原因。</p>
        </div>
      </div>

      <div class="actions">
        <button id="generateBtn" type="button">生成适配简历页面</button>
        <button id="fillDemoBtn" class="secondary" type="button">填充当前编辑页示例</button>
      </div>

      <p id="status" class="status"></p>

      <section id="resultBox" class="result">
        <strong>生成结果</strong>
        <div class="link-row" id="resultLinks"></div>
      </section>
    </section>
  </main>

  <script>
    const generateBtn = document.getElementById("generateBtn");
    const fillDemoBtn = document.getElementById("fillDemoBtn");
    const statusEl = document.getElementById("status");
    const resultBox = document.getElementById("resultBox");
    const resultLinks = document.getElementById("resultLinks");

    function setStatus(text, isError = false) {
      statusEl.textContent = text || "";
      statusEl.classList.toggle("error", Boolean(isError));
    }

    function clearResult() {
      resultLinks.innerHTML = "";
      resultBox.classList.remove("show");
    }

    async function fileToDataUrl(file) {
      if (!file) return "";
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result || "");
        reader.onerror = () => reject(new Error("读取图片失败"));
        reader.readAsDataURL(file);
      });
    }

    function renderLinks(data) {
      const lines = [];
      if (data.output_html_file_url) {
        lines.push(["本地文件 URL", data.output_html_file_url]);
      }
      if (data.output_html_abs_path) {
        lines.push(["文件路径", data.output_html_abs_path]);
      }
      if (data.output_html_rel_path) {
        lines.push(["相对路径", data.output_html_rel_path]);
      }
      if (data.summary_json_path) {
        lines.push(["摘要 JSON", data.summary_json_path]);
      }

      for (const pair of lines) {
        const row = document.createElement("div");
        const label = document.createElement("span");
        label.textContent = pair[0] + ": ";
        const link = document.createElement("a");
        link.href = pair[1];
        link.textContent = pair[1];
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        row.appendChild(label);
        row.appendChild(link);
        resultLinks.appendChild(row);
      }

      resultBox.classList.add("show");
    }

    generateBtn.addEventListener("click", async () => {
      clearResult();
      setStatus("正在生成，请稍候...");

      try {
        const jdImageFile = document.getElementById("jdImage").files[0];
        const jdImageDataUrl = await fileToDataUrl(jdImageFile);

        const body = {
          resume_html_url: document.getElementById("resumeHtmlUrl").value.trim(),
          jd_text: document.getElementById("jdText").value.trim(),
          jd_image_data_url: jdImageDataUrl,
          job_title: document.getElementById("jobTitle").value.trim(),
          language: document.getElementById("language").value,
          version: document.getElementById("version").value,
        };

        const res = await fetch("/api/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });

        const data = await res.json();
        if (!res.ok || !data.ok) {
          throw new Error(data.error || "生成失败");
        }

        setStatus("生成完成。你可以直接打开新页面预览。", false);
        renderLinks(data);
      } catch (err) {
        setStatus(err.message || "生成失败", true);
      }
    });

    fillDemoBtn.addEventListener("click", () => {
      document.getElementById("resumeHtmlUrl").value = "reports/resume_tailoring/2026-06-23_html_preserve/vickie_resume_profile_jd_tailored.html";
      document.getElementById("jobTitle").value = "AI Agent 产品经理";
      document.getElementById("language").value = "zh";
      document.getElementById("version").value = "aggressive";
      if (!document.getElementById("jdText").value.trim()) {
        document.getElementById("jdText").value = "负责 AI Agent 产品从需求定义到上线迭代的全流程，联动研发与业务团队，推动多场景落地并对结果指标负责。";
      }
      setStatus("示例已填充，可直接点击生成。", false);
    });
  </script>
</body>
</html>
"""


def _json_response(handler: BaseHTTPRequestHandler, status: int, body: dict[str, Any]) -> None:
    content = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(content)))
    handler.end_headers()
    handler.wfile.write(content)


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    size = int(handler.headers.get("Content-Length", "0") or "0")
    raw = handler.rfile.read(size) if size > 0 else b""
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _resolve_resume_html_source(source: str) -> tuple[str, str]:
    src = _clean(source)
    if not src:
        raise ValueError("resume_html_url 不能为空")

    if re.match(r"^https?://", src, flags=re.IGNORECASE):
        resp = requests.get(src, timeout=30)
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "")
        if "text/html" not in ctype and "application/xhtml+xml" not in ctype:
            # Still allow if body appears html-like.
            if "<html" not in resp.text.lower():
                raise ValueError("提供的链接未返回 HTML 内容")
        return resp.text, src

    if src.lower().startswith("file://"):
        parsed = urlparse(src)
        file_path = unquote(parsed.path or "")
        if re.match(r"^/[A-Za-z]:", file_path):
            file_path = file_path[1:]
        path = Path(file_path)
    else:
        path = Path(src)
        if not path.is_absolute():
            path = (ROOT / path).resolve()

    if not path.exists():
        raise ValueError(f"HTML 文件不存在: {path}")

    text = path.read_text(encoding="utf-8")
    return text, path.as_uri()


def _extract_jd_text_from_image(data_url: str) -> str:
    data = _clean(data_url)
    if not data:
        return ""

    api_key = _resolve_llm_api_key()
    if not api_key:
      raise ValueError("未检测到 GLM_API_KEY/OPENAI_API_KEY，无法对 JD 图片做文字提取")

    if not data.lower().startswith("data:image/"):
        raise ValueError("JD 图片格式无效，需为 data URL")

    base_url = _resolve_llm_base_url("https://api.openai.com/v1")
    endpoint = f"{base_url}/chat/completions"
    model = os.getenv("RESUME_JD_OCR_MODEL", "gpt-4.1-mini")

    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "You extract job description text from an image. Output plain text only.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all readable JD content from this image and return plain text."},
                    {"type": "image_url", "image_url": {"url": data}},
                ],
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(endpoint, headers=headers, data=json.dumps(payload, ensure_ascii=False), timeout=120)
        response.raise_for_status()
        body = response.json()
        text = _clean(body.get("choices", [{}])[0].get("message", {}).get("content"))
        if not text:
            raise ValueError("图片文字提取结果为空")
        return text
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"JD 图片文字提取失败: {exc}") from exc


def _safe_name(value: str, fallback: str = "job") -> str:
    text = _clean(value) or fallback
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^A-Za-z0-9_\-\u4e00-\u9fff]", "", text)
    text = text[:48]
    return text or fallback


def _build_summary_block(payload: dict[str, Any], job_title: str, version: str, jd_text: str, source_label: str) -> str:
    focus_items = payload.get("jd_focus", [])[:8]
    gap_items = payload.get("gaps", [])[:4]
    keyword_items = payload.get("versions", {}).get(version, {}).get("keyword_coverage", [])[:10]

    focus_html = "".join(f"<li>{_clean(item)}</li>" for item in focus_items if _clean(item))
    gap_html = "".join(f"<li>{_clean(item)}</li>" for item in gap_items if _clean(item))
    keyword_html = "".join(f"<span>{_clean(item)}</span>" for item in keyword_items if _clean(item))

    jd_excerpt = _clean(jd_text)
    if len(jd_excerpt) > 420:
        jd_excerpt = jd_excerpt[:420].rstrip() + "..."

    return f"""
    <section style="margin: 0 0 16px; padding: 18px 20px; border-radius: 20px; background: linear-gradient(135deg, rgba(15, 106, 99, 0.1), rgba(164, 73, 46, 0.08)); border: 1px solid rgba(29, 47, 56, 0.16); box-shadow: 0 10px 24px rgba(27, 36, 48, 0.08);">
      <div style="display:grid; gap:14px; grid-template-columns: 1.25fr 1fr; align-items:start;">
        <div>
          <div style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
            <span style="padding:4px 10px; border-radius:999px; background:rgba(15, 106, 99, 0.14); color:#0f5f59; font-size:12px;">JD 适配摘要</span>
            <span style="padding:4px 10px; border-radius:999px; background:rgba(178, 82, 44, 0.12); color:#9d4625; font-size:12px;">{_clean(version)}</span>
            <span style="padding:4px 10px; border-radius:999px; background:rgba(29, 47, 56, 0.08); color:#40505a; font-size:12px;">{_clean(job_title) or 'N/A'}</span>
          </div>
          <h2 style="margin:0 0 8px; font-size:24px; color:#16343f;">这份简历是按这个 JD 重新对齐的</h2>
          <p style="margin:0; line-height:1.65; color:#344650;">来源: {_clean(source_label)}。当前版本保留原简历骨架，但会围绕 JD 关键词重写经历要点，并把适配重点前置到页面顶部。</p>
          <div style="margin-top:12px; line-height:1.65; color:#344650;">
            <strong>JD 摘要：</strong>{jd_excerpt}
          </div>
        </div>
        <div>
          <h3 style="margin:0 0 8px; font-size:16px; color:#16343f;">重点匹配</h3>
          <ul style="margin:0; padding-left:18px; display:grid; gap:6px; line-height:1.55; color:#33444f;">{focus_html}</ul>
          <h3 style="margin:14px 0 8px; font-size:16px; color:#16343f;">可补强点</h3>
          <ul style="margin:0; padding-left:18px; display:grid; gap:6px; line-height:1.55; color:#33444f;">{gap_html}</ul>
          <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:12px;">
            {keyword_html}
          </div>
        </div>
      </div>
    </section>
    """


def _inject_summary_block(html_text: str, summary_block: str) -> str:
    body_match = re.search(r"<body[^>]*>", html_text, flags=re.IGNORECASE)
    if not body_match:
        return summary_block + html_text

    insert_at = body_match.end()
    return html_text[:insert_at] + "\n  " + summary_block.strip() + "\n" + html_text[insert_at:]


def _run_tailor(
    resume_html_url: str,
    jd_text: str,
    jd_image_data_url: str,
    job_title: str,
    language: str,
    version: str,
) -> dict[str, Any]:
    html_text, source_label = _resolve_resume_html_source(resume_html_url)

    final_jd_text = _clean(jd_text)
    if not final_jd_text and _clean(jd_image_data_url):
        final_jd_text = _extract_jd_text_from_image(jd_image_data_url)

    if not final_jd_text:
        raise ValueError("请提供 JD 文本，或上传可识别的 JD 图片")

    resume_text = _html_to_text(html_text)
    versions = [version] if version in {"conservative", "balanced", "aggressive"} else ["aggressive"]

    raw_payload = _generate_with_openai(
        resume_text=resume_text,
        jd_text=final_jd_text,
        language=language if language in {"zh", "en", "bilingual"} else "zh",
        versions=versions,
        model=os.getenv("RESUME_TAILOR_MODEL", "gpt-4o-mini"),
        job_title=job_title,
    )
    payload = _normalize_payload(raw_payload, versions)

    run_date = dt.date.today().isoformat()
    stamp = dt.datetime.now().strftime("%H%M%S")
    out_dir = OUT_ROOT / (run_date + "_web")
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_job = _safe_name(job_title or "job")
    output_name = f"resume_tailored_{safe_job}_{versions[0]}_{stamp}.html"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as tmp:
      tmp.write(html_text)
      template_path = Path(tmp.name)

    try:
        output_html_path = out_dir / output_name
        ok, message = _write_html_with_preserved_layout(
            template_html_path=template_path,
            output_html_path=output_html_path,
            payload=payload,
            version=versions[0],
        )
        if not ok:
            raise ValueError(message)

        rendered_html = output_html_path.read_text(encoding="utf-8")
        summary_block = _build_summary_block(payload, job_title, versions[0], final_jd_text, source_label)
        rendered_html = _inject_summary_block(rendered_html, summary_block)
        output_html_path.write_text(rendered_html, encoding="utf-8")
    finally:
        try:
            template_path.unlink(missing_ok=True)
        except Exception:
            pass

    summary = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "source_resume": source_label,
        "job_title": _clean(job_title),
        "language": language,
        "version": versions[0],
        "provider": payload.get("meta", {}).get("provider", "unknown"),
        "jd_focus": payload.get("jd_focus", []),
        "gaps": payload.get("gaps", []),
        "output_html": str(output_html_path),
    }

    summary_path = output_html_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "output_html_abs_path": str(output_html_path.resolve()),
        "output_html_rel_path": str(output_html_path.relative_to(ROOT)).replace("\\", "/"),
        "output_html_file_url": output_html_path.resolve().as_uri(),
        "summary_json_path": str(summary_path.resolve().as_uri()),
        "provider": payload.get("meta", {}).get("provider", "unknown"),
    }


class ResumeTailorHandler(BaseHTTPRequestHandler):
    server_version = "ResumeTailorHTTP/1.0"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        # Keep terminal output concise.
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/index.html"}:
            content = INDEX_HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        _json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/generate":
            _json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"})
            return

        try:
            data = _read_json_body(self)
            result = _run_tailor(
                resume_html_url=_clean(data.get("resume_html_url")),
                jd_text=_clean(data.get("jd_text")),
                jd_image_data_url=_clean(data.get("jd_image_data_url")),
                job_title=_clean(data.get("job_title")),
                language=_clean(data.get("language")) or "zh",
                version=_clean(data.get("version")) or "aggressive",
            )
            _json_response(self, HTTPStatus.OK, result)
        except Exception as exc:  # noqa: BLE001
            _json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local web UI for HTML resume tailoring by JD text/image.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8787, help="Port to bind")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), ResumeTailorHandler)
    print(f"Resume Tailor Studio running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
