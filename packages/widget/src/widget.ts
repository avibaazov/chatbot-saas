/**
 * Embeddable chat widget. Ships as a single, dependency-free <script> tag:
 *
 *   <script src=".../widget.js" data-bot-key="sk_pub_..." data-api-base="https://api.example.com" async></script>
 *
 * Renders inside a Shadow DOM so the host page's CSS can never leak in (or the widget's
 * out) — the one thing an embeddable UI running on someone else's site has to get right.
 * Talks only to the public /widget/{site_key} routes (services/api/app/routes/widget.py) —
 * no cookies, no Clerk token, just the site key baked into this tag at embed time.
 */

interface WidgetConfig {
  display_name: string;
  primary_color: string;
}

type Message = { role: "user" | "assistant"; content: string };

function getScriptConfig(): { siteKey: string; apiBase: string } {
  const script = document.currentScript as HTMLScriptElement | null;
  const siteKey = script?.dataset.botKey;
  const apiBase = script?.dataset.apiBase;

  if (!siteKey || !apiBase) {
    throw new Error(
      "[chatbot-widget] Missing data-bot-key or data-api-base on the <script> tag.",
    );
  }
  return { siteKey, apiBase: apiBase.replace(/\/$/, "") };
}

async function fetchConfig(apiBase: string, siteKey: string): Promise<WidgetConfig> {
  const res = await fetch(`${apiBase}/widget/${siteKey}/config`);
  if (!res.ok) {
    throw new Error(`[chatbot-widget] Failed to load config (${res.status})`);
  }
  return res.json();
}

async function askBot(apiBase: string, siteKey: string, question: string): Promise<string> {
  const res = await fetch(`${apiBase}/widget/${siteKey}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    if (res.status === 429) throw new Error("Too many messages — try again in a moment.");
    throw new Error(`Request failed (${res.status})`);
  }
  const body = (await res.json()) as { answer: string };
  return body.answer;
}

function buildStyles(primaryColor: string): string {
  return `
    :host { all: initial; }
    * { box-sizing: border-box; font-family: system-ui, -apple-system, sans-serif; }
    .bubble {
      position: fixed; bottom: 20px; right: 20px; width: 56px; height: 56px;
      border-radius: 999px; background: ${primaryColor}; color: white; border: none;
      cursor: pointer; box-shadow: 0 4px 12px rgba(0,0,0,0.2); font-size: 24px;
      display: flex; align-items: center; justify-content: center; z-index: 2147483000;
    }
    .panel {
      position: fixed; bottom: 88px; right: 20px; width: 320px; height: 440px;
      background: white; border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.25);
      display: flex; flex-direction: column; overflow: hidden; z-index: 2147483000;
    }
    .panel[hidden] { display: none; }
    .header { background: ${primaryColor}; color: white; padding: 12px 16px; font-weight: 600; }
    .messages { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px; }
    .msg { max-width: 85%; padding: 8px 12px; border-radius: 10px; font-size: 14px; line-height: 1.4; }
    .msg.user { align-self: flex-end; background: ${primaryColor}; color: white; }
    .msg.assistant { align-self: flex-start; background: #f1f1f1; color: #111; }
    .msg.error { align-self: center; color: #b00020; font-size: 12px; }
    form { display: flex; border-top: 1px solid #eee; }
    input { flex: 1; border: none; padding: 10px 12px; font-size: 14px; outline: none; }
    button.send { border: none; background: none; color: ${primaryColor}; font-weight: 600; padding: 0 14px; cursor: pointer; }
    button.send:disabled { opacity: 0.5; cursor: default; }
  `;
}

async function mount() {
  const { siteKey, apiBase } = getScriptConfig();

  let config: WidgetConfig;
  try {
    config = await fetchConfig(apiBase, siteKey);
  } catch (err) {
    console.error(err);
    return; // don't render a broken widget on a misconfigured/blocked origin
  }

  const host = document.createElement("div");
  document.body.appendChild(host);
  const shadow = host.attachShadow({ mode: "open" });

  const style = document.createElement("style");
  style.textContent = buildStyles(config.primary_color);
  shadow.appendChild(style);

  const bubble = document.createElement("button");
  bubble.className = "bubble";
  bubble.setAttribute("aria-label", `Chat with ${config.display_name}`);
  bubble.textContent = "💬";
  shadow.appendChild(bubble);

  const panel = document.createElement("div");
  panel.className = "panel";
  panel.hidden = true;
  panel.innerHTML = `
    <div class="header">${escapeHtml(config.display_name)}</div>
    <div class="messages"></div>
    <form>
      <input type="text" placeholder="Ask a question…" autocomplete="off" />
      <button class="send" type="submit">Send</button>
    </form>
  `;
  shadow.appendChild(panel);

  const messagesEl = panel.querySelector<HTMLDivElement>(".messages")!;
  const form = panel.querySelector<HTMLFormElement>("form")!;
  const input = panel.querySelector<HTMLInputElement>("input")!;
  const sendButton = panel.querySelector<HTMLButtonElement>("button.send")!;

  const history: Message[] = [];

  function render() {
    messagesEl.innerHTML = "";
    for (const m of history) {
      const el = document.createElement("div");
      el.className = `msg ${m.role}`;
      el.textContent = m.content;
      messagesEl.appendChild(el);
    }
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  bubble.addEventListener("click", () => {
    panel.hidden = !panel.hidden;
    if (!panel.hidden) input.focus();
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) return;

    history.push({ role: "user", content: question });
    render();
    input.value = "";
    input.disabled = true;
    sendButton.disabled = true;

    try {
      const answer = await askBot(apiBase, siteKey, question);
      history.push({ role: "assistant", content: answer });
    } catch (err) {
      const el = document.createElement("div");
      el.className = "msg error";
      el.textContent = err instanceof Error ? err.message : "Something went wrong.";
      messagesEl.appendChild(el);
    } finally {
      input.disabled = false;
      sendButton.disabled = false;
      input.focus();
      render();
    }
  });
}

function escapeHtml(s: string): string {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

mount();
