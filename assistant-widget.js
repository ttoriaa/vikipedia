// Configurable landing-page assistant widget with GLM-friendly request modes.
(function () {
  var DEFAULT_CONFIG = {
    endpoint: "https://resume-tailor-1x7i.onrender.com/api/assistant/query",
    method: "POST",
    provider: "glm",
    model: "glm-4.5",
    context: "Vikipedia landing page",
    titleZh: "问问Jackie",
    titleEn: "Ask Jackie",
    launcherZh: "问问Jackie",
    launcherEn: "Ask Jackie",
    protocol: "assistant_query",
    stream: false,
    headers: {},
    authHeader: "Authorization",
    authScheme: "Bearer",
    authToken: "",
    fields: {
      query: "query",
      mode: "mode",
      style: "style",
      lang: "lang",
      provider: "provider",
      model: "model",
      context: "page_context"
    },
    chatFields: {
      model: "model",
      messages: "messages",
      stream: "stream"
    },
    chatExtraBody: {},
    answerPaths: [
      "answer",
      "output_text",
      "data.answer",
      "choices.0.message.content",
      "choices.0.delta.content",
      "choices.0.text"
    ]
  };

  function mergeConfig(base, override) {
    var merged = Object.assign({}, base, override || {});
    merged.fields = Object.assign({}, base.fields || {}, (override || {}).fields || {});
    merged.chatFields = Object.assign({}, base.chatFields || {}, (override || {}).chatFields || {});
    merged.headers = Object.assign({}, base.headers || {}, (override || {}).headers || {});
    merged.chatExtraBody = Object.assign({}, base.chatExtraBody || {}, (override || {}).chatExtraBody || {});
    if (!Array.isArray(merged.answerPaths) || merged.answerPaths.length === 0) {
      merged.answerPaths = base.answerPaths.slice();
    }
    return merged;
  }

  var userConfig = window.__VIKI_ASSISTANT_CONFIG__ || {};
  var config = mergeConfig(DEFAULT_CONFIG, userConfig);

  var UI = {
    zh: {
      launcher: config.launcherZh || "问问Jackie",
      title: config.titleZh || "问问Jackie",
      contextPrefix: "当前页面：",
      intro: "我是 Jackie。你可以直接问我这个站点里有什么、先看哪块、或者怎么继续迭代。",
      quick1: "这个网站现在重点是什么？",
      quick2: "给我 3 个可执行的下一步",
      quick3: "帮我挑 2 个最值得看的页面",
      placeholder: "例如：用产品经理视角点评这个 landing page",
      send: "发送",
      close: "关闭",
      minimize: "最小化",
      expand: "展开",
      waiting: "等待提问",
      requesting: "正在请求...",
      done: "回答完成",
      failed: "请求失败",
      network: "网络异常",
      empty: "无有效回答",
      style: "风格",
      styleWarm: "温和",
      styleDirect: "直接",
      styleStrategic: "策略",
      language: "回答语言",
      copy: "复制",
      copied: "已复制",
      copyFail: "复制失败",
      sourceLLM: "LLM 回答",
      sourceLocal: "本地兜底"
    },
    en: {
      launcher: config.launcherEn || "Ask Jackie",
      title: config.titleEn || "Ask Jackie",
      contextPrefix: "Context: ",
      intro: "I am Jackie. Ask what this site focuses on, where to start, or what to improve next.",
      quick1: "What is the core focus of this site?",
      quick2: "Give me 3 actionable next steps",
      quick3: "Pick 2 pages I should open first",
      placeholder: "For example: critique this landing page with a PM lens",
      send: "Send",
      close: "Close",
      minimize: "Minimize",
      expand: "Expand",
      waiting: "Waiting for your question",
      requesting: "Requesting...",
      done: "Answer ready",
      failed: "Request failed",
      network: "Network error",
      empty: "No useful answer",
      style: "Style",
      styleWarm: "Warm",
      styleDirect: "Direct",
      styleStrategic: "Strategic",
      language: "Answer language",
      copy: "Copy",
      copied: "Copied",
      copyFail: "Copy failed",
      sourceLLM: "LLM reply",
      sourceLocal: "Local fallback"
    }
  };

  var STYLE_KEY = "vikipedia_widget_style";
  var LANG_KEY = "vikipedia_widget_lang";
  var STATE_KEY = "vikipedia_widget_state";

  function readStorage(key, fallback) {
    try {
      var v = sessionStorage.getItem(key);
      return v == null ? fallback : v;
    } catch (error) {
      return fallback;
    }
  }

  function writeStorage(key, value) {
    try {
      sessionStorage.setItem(key, value);
    } catch (error) {
      // Ignore storage errors.
    }
  }

  function detectLang() {
    var fromStorage = readStorage(LANG_KEY, "");
    if (fromStorage === "zh" || fromStorage === "en") return fromStorage;
    var htmlLang = String(document.documentElement.lang || "").toLowerCase();
    return htmlLang.indexOf("zh") === 0 ? "zh" : "en";
  }

  function ensureStyleTag() {
    if (document.getElementById("vikipedia-assistant-style")) return;
    var style = document.createElement("style");
    style.id = "vikipedia-assistant-style";
    style.textContent = [
      ".viki-assistant{position:fixed;left:18px;bottom:18px;z-index:120;font-family:'Noto Sans SC','Microsoft YaHei',sans-serif;}",
      ".viki-assistant-launcher{border:1px solid rgba(163,189,255,.32);background:linear-gradient(135deg,#7a5bff,#a76dff);color:#fff;border-radius:999px;padding:12px 16px;font-size:13px;font-weight:800;letter-spacing:.01em;cursor:pointer;box-shadow:0 18px 34px rgba(0,0,0,.28);}",
      ".viki-assistant-panel{width:min(360px,calc(100vw - 24px));border-radius:18px;border:1px solid rgba(163,189,255,.25);background:linear-gradient(160deg,rgba(11,18,32,.98),rgba(16,27,46,.95));color:#e7efff;box-shadow:0 26px 58px rgba(0,0,0,.45);overflow:hidden;}",
      ".viki-assistant-header{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;padding:14px 14px 10px;border-bottom:1px solid rgba(163,189,255,.2);}",
      ".viki-assistant-header strong{display:block;font-family:'Space Grotesk','Noto Sans SC',sans-serif;font-size:17px;line-height:1;}",
      ".viki-assistant-header p{margin:6px 0 0;color:#a5bbdc;font-size:11px;line-height:1.35;}",
      ".viki-assistant-actions{display:flex;gap:6px;}",
      ".viki-assistant-actions button{width:30px;height:30px;border-radius:999px;border:1px solid rgba(163,189,255,.22);background:rgba(10,20,36,.88);color:#dbe9ff;cursor:pointer;}",
      ".viki-assistant-body{padding:12px;display:grid;gap:10px;}",
      ".viki-assistant-intro{margin:0;padding:10px 11px;border:1px solid rgba(163,189,255,.16);border-radius:12px;background:rgba(17,31,52,.78);color:#b5c8e4;font-size:12px;line-height:1.45;}",
      ".viki-assistant-chips{display:flex;gap:7px;overflow:auto;padding-bottom:2px;}",
      ".viki-assistant-chip{white-space:nowrap;height:32px;border-radius:999px;border:1px solid rgba(163,189,255,.28);background:rgba(16,26,43,.92);color:#cfdef8;padding:0 10px;font-size:12px;font-weight:700;cursor:pointer;}",
      ".viki-assistant-row{display:flex;align-items:center;justify-content:space-between;gap:8px;}",
      ".viki-assistant-status{margin:0;font-size:11px;color:#9cb3d5;}",
      ".viki-assistant-status strong{color:#e7efff;}",
      ".viki-assistant-meta{display:flex;gap:6px;align-items:center;margin-left:auto;}",
      ".viki-assistant-style{display:inline-flex;align-items:center;gap:5px;color:#9cb3d5;font-size:11px;}",
      ".viki-assistant-style select{height:30px;border-radius:999px;border:1px solid rgba(163,189,255,.26);background:#12223b;color:#e7efff;padding:0 10px;font-size:12px;}",
      ".viki-assistant-lang{display:inline-flex;border:1px solid rgba(163,189,255,.26);border-radius:999px;background:#0f1d33;padding:2px;}",
      ".viki-assistant-lang button{height:24px;border:none;background:transparent;color:#a6bddc;font-size:11px;font-weight:800;padding:0 8px;border-radius:999px;cursor:pointer;}",
      ".viki-assistant-lang button.is-active{background:#7a5bff;color:#fff;}",
      ".viki-assistant-messages{max-height:min(32vh,210px);overflow:auto;border:1px solid rgba(163,189,255,.18);border-radius:12px;padding:10px;background:rgba(8,15,27,.78);}",
      ".viki-assistant-msg{margin-bottom:8px;padding:9px 10px;border-radius:10px;background:rgba(24,41,68,.85);font-size:12px;line-height:1.45;white-space:pre-wrap;}",
      ".viki-assistant-msg.user{background:rgba(122,91,255,.24);text-align:right;}",
      ".viki-assistant-msg.error{background:rgba(165,35,61,.35);}",
      ".viki-assistant-msg.loading{opacity:.8;font-style:italic;}",
      ".viki-assistant-copy{margin-top:8px;height:26px;border-radius:999px;border:1px solid rgba(163,189,255,.26);background:rgba(10,20,36,.86);color:#dbe9ff;font-size:11px;font-weight:700;padding:0 9px;cursor:pointer;}",
      ".viki-assistant-form{display:grid;gap:8px;}",
      ".viki-assistant-form textarea{width:100%;min-height:70px;max-height:140px;resize:vertical;border-radius:11px;border:1px solid rgba(163,189,255,.24);background:rgba(11,19,34,.95);color:#edf4ff;padding:9px 10px;font-size:12px;}",
      ".viki-assistant-form button{justify-self:end;height:34px;border:none;border-radius:999px;background:linear-gradient(135deg,#7a5bff,#a76dff);color:#fff;font-size:12px;font-weight:800;padding:0 14px;cursor:pointer;}",
      ".viki-assistant.is-closed .viki-assistant-panel{display:none;}",
      ".viki-assistant:not(.is-closed) .viki-assistant-launcher{display:none;}",
      "@media (max-width:760px){.viki-assistant{right:10px;left:10px;bottom:10px;}.viki-assistant-panel{width:auto;}.viki-assistant-header p{max-width:180px;}.viki-assistant-messages{max-height:min(28vh,180px);}}"
    ].join("");
    document.head.appendChild(style);
  }

  function createMarkup(lang, state) {
    var t = UI[lang];
    var container = document.createElement("div");
    container.className = "viki-assistant" + (state.closed ? " is-closed" : "");
    container.innerHTML = [
      '<button type="button" class="viki-assistant-launcher" aria-label="' + t.launcher + '">' + t.launcher + "</button>",
      '<section class="viki-assistant-panel" aria-label="' + t.title + '">',
      '  <header class="viki-assistant-header">',
      "    <div>",
      "      <strong>" + t.title + "</strong>",
      '      <p>' + t.contextPrefix + escapeHtml(config.context) + "</p>",
      "    </div>",
      '    <div class="viki-assistant-actions">',
      '      <button type="button" class="viki-min" aria-label="' + t.minimize + '">-</button>',
      '      <button type="button" class="viki-close" aria-label="' + t.close + '">x</button>',
      "    </div>",
      "  </header>",
      '  <div class="viki-assistant-body">',
      '    <p class="viki-assistant-intro">' + t.intro + "</p>",
      '    <div class="viki-assistant-chips">',
      '      <button type="button" class="viki-assistant-chip" data-q="1">' + t.quick1 + "</button>",
      '      <button type="button" class="viki-assistant-chip" data-q="2">' + t.quick2 + "</button>",
      '      <button type="button" class="viki-assistant-chip" data-q="3">' + t.quick3 + "</button>",
      "    </div>",
      '    <div class="viki-assistant-row">',
      '      <p class="viki-assistant-status">Status: <strong>' + t.waiting + "</strong></p>",
      '      <div class="viki-assistant-meta">',
      '        <label class="viki-assistant-style">' + t.style,
      '          <select class="viki-style-select">',
      '            <option value="warm">' + t.styleWarm + "</option>",
      '            <option value="direct">' + t.styleDirect + "</option>",
      '            <option value="strategic">' + t.styleStrategic + "</option>",
      "          </select>",
      "        </label>",
      '        <div class="viki-assistant-lang" role="group" aria-label="' + t.language + '">',
      '          <button type="button" class="viki-lang-btn' + (lang === "zh" ? " is-active" : "") + '" data-lang="zh">中</button>',
      '          <button type="button" class="viki-lang-btn' + (lang === "en" ? " is-active" : "") + '" data-lang="en">EN</button>',
      "        </div>",
      "      </div>",
      "    </div>",
      '    <div class="viki-assistant-messages">',
      '      <div class="viki-assistant-msg">' + t.waiting + "</div>",
      "    </div>",
      '    <form class="viki-assistant-form">',
      '      <textarea required placeholder="' + t.placeholder + '"></textarea>',
      '      <button type="submit">' + t.send + "</button>",
      "    </form>",
      "  </div>",
      "</section>"
    ].join("\n");
    return container;
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function buildPrompt(question, lang) {
    var langHint = lang === "zh" ? "请使用中文回答。" : "Please answer in English.";
    return "[Page Context: " + config.context + "]\n" + question + "\n" + langHint;
  }

  function getByPath(obj, path) {
    if (!obj || !path) return undefined;
    var parts = String(path).split(".");
    var cur = obj;
    for (var i = 0; i < parts.length; i += 1) {
      if (cur == null) return undefined;
      var key = parts[i];
      if (/^\d+$/.test(key)) {
        var idx = Number(key);
        if (!Array.isArray(cur) || idx < 0 || idx >= cur.length) return undefined;
        cur = cur[idx];
      } else {
        cur = cur[key];
      }
    }
    return cur;
  }

  function extractAnswer(payload) {
    if (!payload) return "";

    for (var i = 0; i < config.answerPaths.length; i += 1) {
      var value = getByPath(payload, config.answerPaths[i]);
      if (typeof value === "string" && value.trim()) return value;
    }

    if (Array.isArray(payload.content)) {
      var joined = payload.content
        .map(function (it) {
          if (typeof it === "string") return it;
          if (it && typeof it.text === "string") return it.text;
          return "";
        })
        .filter(Boolean)
        .join("\n");
      if (joined.trim()) return joined;
    }
    return "";
  }

  function setByPath(target, path, value) {
    if (!path) return;
    var parts = String(path).split(".");
    var cur = target;
    for (var i = 0; i < parts.length - 1; i += 1) {
      var k = parts[i];
      if (cur[k] == null || typeof cur[k] !== "object") cur[k] = {};
      cur = cur[k];
    }
    cur[parts[parts.length - 1]] = value;
  }

  function buildHeaders() {
    var headers = Object.assign({ "Content-Type": "application/json" }, config.headers || {});
    var token = String(config.authToken || "").trim();
    if (token) {
      var scheme = String(config.authScheme || "").trim();
      var head = String(config.authHeader || "Authorization").trim() || "Authorization";
      headers[head] = scheme ? scheme + " " + token : token;
    }
    return headers;
  }

  function buildRequestPayload(question, lang, style) {
    var protocol = String(config.protocol || "assistant_query").toLowerCase();
    if (protocol === "chat_completions") {
      var body = Object.assign({}, config.chatExtraBody || {});
      setByPath(body, config.chatFields.model || "model", config.model);
      setByPath(body, config.chatFields.stream || "stream", !!config.stream);
      setByPath(body, config.chatFields.messages || "messages", [
        {
          role: "system",
          content: "You are Jackie on Vikipedia landing page. Provide concise, actionable responses."
        },
        {
          role: "user",
          content: buildPrompt(question, lang)
        }
      ]);
      return body;
    }

    var mapped = {};
    setByPath(mapped, config.fields.query || "query", buildPrompt(question, lang));
    setByPath(mapped, config.fields.mode || "mode", "chat");
    setByPath(mapped, config.fields.style || "style", style || "warm");
    setByPath(mapped, config.fields.lang || "lang", lang);
    setByPath(mapped, config.fields.provider || "provider", config.provider);
    setByPath(mapped, config.fields.model || "model", config.model);
    setByPath(mapped, config.fields.context || "page_context", config.context);
    return mapped;
  }

  async function readSseText(response) {
    if (!response.body || !response.body.getReader) return "";

    var reader = response.body.getReader();
    var decoder = new TextDecoder("utf-8");
    var buffer = "";
    var assembled = "";

    function processLine(line) {
      var contentLine = String(line || "").trim();
      if (!contentLine || contentLine.indexOf("data:") !== 0) return;
      var payloadRaw = contentLine.slice(5).trim();
      if (!payloadRaw || payloadRaw === "[DONE]") return;
      try {
        var payload = JSON.parse(payloadRaw);
        var delta = extractAnswer(payload);
        if (delta) assembled += delta;
      } catch (error) {
        assembled += payloadRaw;
      }
    }

    while (true) {
      var step = await reader.read();
      if (step.done) break;
      buffer += decoder.decode(step.value, { stream: true });
      var lines = buffer.split(/\r?\n/);
      buffer = lines.pop() || "";
      for (var i = 0; i < lines.length; i += 1) {
        processLine(lines[i]);
      }
    }

    if (buffer) processLine(buffer);
    return assembled.trim();
  }

  async function writeClipboard(text) {
    if (!text) return false;
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch (error) {
        // fallback below
      }
    }
    try {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      var ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch (error) {
      return false;
    }
  }

  function mount() {
    if (document.querySelector(".viki-assistant")) return;
    ensureStyleTag();

    var lang = detectLang();
    var closed = readStorage(STATE_KEY, "open") === "closed";
    var style = readStorage(STYLE_KEY, "warm");

    var root = createMarkup(lang, { closed: closed });
    document.body.appendChild(root);

    var launcher = root.querySelector(".viki-assistant-launcher");
    var closeBtn = root.querySelector(".viki-close");
    var minBtn = root.querySelector(".viki-min");
    var body = root.querySelector(".viki-assistant-body");
    var status = root.querySelector(".viki-assistant-status");
    var styleSelect = root.querySelector(".viki-style-select");
    var messages = root.querySelector(".viki-assistant-messages");
    var form = root.querySelector(".viki-assistant-form");
    var textarea = root.querySelector("textarea");
    var chips = root.querySelectorAll(".viki-assistant-chip");
    var langButtons = root.querySelectorAll(".viki-lang-btn");

    if (styleSelect) {
      styleSelect.value = ["warm", "direct", "strategic"].indexOf(style) >= 0 ? style : "warm";
      styleSelect.addEventListener("change", function () {
        writeStorage(STYLE_KEY, styleSelect.value || "warm");
      });
    }

    function setStatus(text) {
      if (!status) return;
      status.innerHTML = 'Status: <strong>' + escapeHtml(text) + "</strong>";
    }

    function addMessage(text, cls, answerForCopy) {
      var node = document.createElement("div");
      node.className = "viki-assistant-msg" + (cls ? " " + cls : "");
      node.textContent = text;

      if (answerForCopy) {
        var t = UI[lang];
        var copyBtn = document.createElement("button");
        copyBtn.type = "button";
        copyBtn.className = "viki-assistant-copy";
        copyBtn.textContent = t.copy;
        copyBtn.addEventListener("click", async function () {
          var ok = await writeClipboard(answerForCopy);
          copyBtn.textContent = ok ? t.copied : t.copyFail;
          setTimeout(function () {
            copyBtn.textContent = t.copy;
          }, 1400);
        });
        node.appendChild(copyBtn);
      }

      messages.appendChild(node);
      messages.scrollTop = messages.scrollHeight;
      return node;
    }

    async function ask(question) {
      var q = String(question || "").trim();
      if (!q) return;

      var t = UI[lang];
      addMessage(q, "user");
      textarea.value = "";
      setStatus(t.requesting);
      var loading = addMessage(t.requesting, "loading");

      try {
        var reqPayload = buildRequestPayload(q, lang, styleSelect ? styleSelect.value || "warm" : "warm");
        var resp = await fetch(config.endpoint, {
          method: String(config.method || "POST").toUpperCase(),
          headers: buildHeaders(),
          body: JSON.stringify(reqPayload)
        });

        var data = null;
        var answer = "";
        if (config.stream) {
          answer = await readSseText(resp);
          if (answer) data = { answer: answer, source: "llm" };
        }
        if (!answer) {
          try {
            data = await resp.json();
          } catch (error) {
            data = null;
          }
          answer = extractAnswer(data);
        }

        loading.remove();

        if (resp.ok && answer) {
          addMessage(answer, "", answer);
          var source = String((data && data.source) || "").toLowerCase();
          if (source === "llm") {
            setStatus(t.sourceLLM + " (" + config.provider.toUpperCase() + "/" + config.model + ")");
          } else if (source === "local") {
            setStatus(t.sourceLocal);
          } else {
            setStatus(t.done);
          }
        } else {
          addMessage(t.empty, "error");
          setStatus(t.failed);
        }
      } catch (error) {
        loading.remove();
        addMessage(t.network, "error");
        setStatus(t.network);
      }
    }

    launcher.addEventListener("click", function () {
      root.classList.remove("is-closed");
      writeStorage(STATE_KEY, "open");
    });

    closeBtn.addEventListener("click", function () {
      root.classList.add("is-closed");
      writeStorage(STATE_KEY, "closed");
    });

    minBtn.addEventListener("click", function () {
      var hidden = body.hasAttribute("hidden");
      if (hidden) {
        body.removeAttribute("hidden");
        minBtn.textContent = "-";
        minBtn.setAttribute("aria-label", UI[lang].minimize);
      } else {
        body.setAttribute("hidden", "");
        minBtn.textContent = "+";
        minBtn.setAttribute("aria-label", UI[lang].expand);
      }
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      ask(textarea.value);
    });

    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        ask(chip.textContent || "");
      });
    });

    langButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var next = btn.getAttribute("data-lang") === "zh" ? "zh" : "en";
        if (next === lang) return;
        writeStorage(LANG_KEY, next);
        root.remove();
        mount();
      });
    });

    setStatus(UI[lang].waiting);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
