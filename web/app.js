"use strict";

const $ = (id) => document.getElementById(id);
const state = {project: localStorage.getItem("memory-project") || "Challenge A", bootstrap: null, chat: null, busy: false, pending: null, memoryTab: "active"};
const labels = {language: "Ngôn ngữ", database: "Cơ sở dữ liệu", authentication: "Xác thực", api_style: "Quy ước API"};
let toastTimer;

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method: "POST", headers: {"Content-Type": "application/json", "X-Memory-Chat": "1"}, body: JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Chưa xử lý được yêu cầu. Hãy thử lại.");
  return data;
}

function toast(message) {
  $("toast").textContent = message;
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $("toast").hidden = true; }, 5500);
}

function time(value) {
  return new Date(value).toLocaleTimeString("vi-VN", {hour: "2-digit", minute: "2-digit"});
}

function date(value) {
  return new Date(value).toLocaleString("vi-VN", {day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit"});
}

function uuid() { return crypto.randomUUID().replaceAll("-", ""); }

function inline(text, parent) {
  // Build DOM text nodes. Never interpret assistant/user text as HTML.
  const matcher = /(\*\*([^*\n]+)\*\*|`([^`\n]+)`)/g;
  let start = 0;
  for (const match of text.matchAll(matcher)) {
    parent.append(document.createTextNode(text.slice(start, match.index)));
    parent.append(node(match[2] ? "strong" : "code", "", match[2] || match[3]));
    start = match.index + match[0].length;
  }
  parent.append(document.createTextNode(text.slice(start)));
}

function markdown(text) {
  const container = node("div", "message-content");
  const parts = text.split(/```[^\n]*\n([\s\S]*?)(?:```|$)/g);
  parts.forEach((part, index) => {
    if (index % 2) {
      const pre = node("pre");
      pre.append(node("code", "", part.trimEnd()));
      const copy = node("button", "copy-code", "Sao chép");
      copy.type = "button";
      copy.addEventListener("click", () => navigator.clipboard.writeText(part.trimEnd()).then(() => toast("Đã sao chép đoạn code.")).catch(() => toast("Bạn có thể chọn và sao chép đoạn code.")));
      pre.append(copy);
      container.append(pre);
      return;
    }
    let list = null;
    for (const line of part.split("\n")) {
      if (!line.trim()) { list = null; continue; }
      if (/^\s*[-*]\s/.test(line) || /^\s*\d+\.\s/.test(line)) {
        if (!list) { list = node("ul"); container.append(list); }
        const li = node("li");
        inline(line.replace(/^\s*(?:[-*]|\d+\.)\s/, ""), li);
        list.append(li);
      } else {
        list = null;
        const p = node(/^#{1,4}\s/.test(line) ? "h3" : "p");
        inline(line.replace(/^#{1,4}\s/, ""), p);
        container.append(p);
      }
    }
  });
  return container;
}

function renderConfig() {
  const config = state.bootstrap.config;
  const ai = config.provider === "openai";
  $("modeBadge").textContent = ai ? "OpenAI · " + config.model : "Demo · không dùng LLM";
  $("modeBadge").classList.toggle("ai", ai);
  $("sidebarMode").textContent = ai ? "AI" : "DEMO";
  $("demoBanner").hidden = ai;
}

function renderChats() {
  $("projectTitle").textContent = state.project;
  $("composerProject").textContent = state.project;
  const select = $("projectSelect");
  select.replaceChildren();
  for (const project of state.bootstrap.projects) {
    const option = node("option", "", project);
    option.value = project;
    option.selected = project === state.project;
    select.append(option);
  }
  const list = $("chatList");
  list.replaceChildren();
  if (!state.bootstrap.chats.length) list.append(node("div", "empty-chats", "Chưa có cuộc trò chuyện.\nBắt đầu bằng một tin nhắn bên cạnh."));
  for (const chat of state.bootstrap.chats) {
    const button = node("button", "chat-entry" + (state.chat?.id === chat.id ? " active" : ""));
    button.type = "button";
    button.title = chat.title;
    button.append(node("span", "chat-entry-icon", "◷"), node("span", "", chat.title));
    button.addEventListener("click", () => guarded(() => loadChat(chat.id)));
    button.disabled = state.busy;
    list.append(button);
  }
}

function renderMemory() {
  const memory = state.bootstrap.memory;
  $("memoryCount").textContent = String(memory.active.length);
  $("activeCount").textContent = String(memory.active.length);
  $("activeTab").setAttribute("aria-selected", String(state.memoryTab === "active"));
  $("historyTab").setAttribute("aria-selected", String(state.memoryTab === "history"));
  const target = $("memoryItems");
  target.replaceChildren();
  const items = state.memoryTab === "active" ? memory.active : [...memory.history].sort((a, b) => b.created_at.localeCompare(a.created_at) || b.id - a.id);
  if (!items.length) {
    const empty = node("div", "memory-empty");
    empty.append(node("span", "empty-memory-symbol", "◈"), node("strong", "", "Một khởi đầu mới"), node("p", "", "Chưa có quy ước nào được lưu. Hãy nói những quyết định bạn muốn mình nhớ về dự án."));
    target.append(empty);
  }
  for (const item of items) {
    const card = node("article", "memory-card" + (item.status === "superseded" ? " superseded" : ""));
    const head = node("div", "memory-card-head");
    head.append(node("span", "memory-card-label", labels[item.key] || item.key), node("span", "version", "v" + item.version + (item.status === "superseded" ? " · Đã thay thế" : "")));
    card.append(head, node("div", "memory-card-value", item.value), node("div", "memory-card-meta", (item.status === "active" ? "Đã nhớ · " : "Thay thế · ") + date(item.superseded_at || item.created_at)));
    if (state.memoryTab === "history") {
      const details = node("details", "memory-card-source");
      details.append(node("summary", "", "Nguồn quyết định"), node("p", "", item.source), node("span", "", "Chat/session: " + item.created_session));
      card.append(details);
    }
    target.append(card);
  }
}

function showTrace(turn) {
  if (!turn?.request) {
    $("traceDescription").textContent = "Cuộc trò chuyện này chưa có lượt trả lời. Gửi một tin nhắn để xem memory thực sự được nạp vào context.";
    $("traceContent").textContent = "Chưa có request. Bộ nhớ hiện hành ở bảng bên phải sẽ được retrieve khi bạn gửi tin nhắn.";
  } else {
    $("traceDescription").textContent = "Đây là request thực tế của lượt chat này. Chat mới chỉ có memory và tin nhắn mới; các lượt tiếp theo có thêm history của riêng cuộc trò chuyện đó.";
    $("traceContent").textContent = JSON.stringify({chat_id: state.chat.id, turn_id: turn.id, memory_changes: turn.changes, request: turn.request}, null, 2);
  }
  $("traceDialog").showModal();
}

function userMessage(text) {
  const row = node("article", "message user");
  row.append(node("div", "message-body", text));
  return row;
}

function botMessage(turn) {
  const row = node("article", "message assistant");
  row.append(node("div", "avatar", "✳"));
  const body = node("div", "message-body");
  body.append(node("div", "message-name", "Memory"), markdown(turn.assistant_text));
  const tools = node("div", "message-tools");
  tools.append(node("span", "message-time", time(turn.updated_at)));
  const changes = (turn.changes || []).filter((change) => change.action !== "unchanged");
  if (changes.length) {
    const memory = node("button", "memory-change", "✓ Đã nhớ " + changes.length + " quy ước");
    memory.addEventListener("click", () => { state.memoryTab = "active"; renderMemory(); openMemory(); });
    tools.append(memory);
  }
  const trace = node("button", "message-trace", "Xem ngữ cảnh ↗");
  trace.addEventListener("click", () => showTrace(turn));
  tools.append(trace);
  body.append(tools);
  row.append(body);
  return row;
}

function renderMessages(scroll = false) {
  const target = $("messages");
  target.replaceChildren();
  const turns = state.chat?.turns || [];
  $("welcome").hidden = turns.length > 0 || Boolean(state.pending);
  for (const turn of turns) {
    target.append(userMessage(turn.user_text));
    if (turn.status === "completed") target.append(botMessage(turn));
    else if (turn.status === "failed" || !state.busy) {
      const error = node("div", "message-error", turn.error || "Lượt chat bị gián đoạn khi server khởi động lại.");
      const retry = node("button", "", "Thử lại tin nhắn");
      retry.disabled = state.busy;
      retry.addEventListener("click", () => send(turn.user_text, turn.id));
      error.append(retry);
      target.append(error);
    }
  }
  if (state.pending) {
    if (!turns.some((turn) => turn.id === state.pending.id)) target.append(userMessage(state.pending.text));
    const row = node("div", "message assistant");
    row.append(node("div", "avatar", "✳"));
    const body = node("div", "message-body");
    body.append(node("div", "message-name", "Memory đang trả lời"));
    const typing = node("div", "typing");
    typing.append(node("span"), node("span"), node("span"));
    body.append(typing);
    row.append(body);
    target.append(row);
  }
  if (scroll) requestAnimationFrame(() => { $("messagesScroll").scrollTop = $("messagesScroll").scrollHeight; });
}

function setBusy(value) {
  state.busy = value;
  $("sendButton").disabled = value || !$("messageInput").value.trim();
  $("messageInput").disabled = value;
  for (const id of ["newChat", "addProject", "projectSelect", "modeBadge", "openSettings", "bannerSettings"]) $(id).disabled = value;
  renderChats();
}

async function bootstrap(pickChat = true) {
  state.bootstrap = await api("/api/bootstrap?project=" + encodeURIComponent(state.project));
  renderConfig(); renderMemory();
  if (pickChat) {
    const stored = localStorage.getItem("memory-chat:" + state.project);
    const chat = state.bootstrap.chats.find((c) => c.id === stored) || state.bootstrap.chats[0];
    state.chat = chat ? await api("/api/chats/" + chat.id) : null;
    renderMessages();
  }
  renderChats();
}

async function loadChat(id) {
  state.chat = await api("/api/chats/" + id);
  localStorage.setItem("memory-chat:" + state.project, id);
  $("messageInput").value = "";
  renderChats(); renderMessages(true);
  closeSidebar();
  $("messageInput").focus();
}

async function newChat() {
  state.chat = await api("/api/chats", {project: state.project});
  localStorage.setItem("memory-chat:" + state.project, state.chat.id);
  $("messageInput").value = "";
  await bootstrap(false);
  renderMessages();
  closeSidebar();
  toast("Đã mở chat mới. Bộ nhớ dự án được giữ lại.");
  $("messageInput").focus();
}

async function send(text, retryId) {
  if (state.busy || !text.trim()) return;
  text = text.trim();
  setBusy(true);
  const turnId = retryId || uuid();
  try {
    if (!state.chat) {
      state.chat = await api("/api/chats", {project: state.project});
      localStorage.setItem("memory-chat:" + state.project, state.chat.id);
    }
    state.pending = {id: turnId, text};
    $("messageInput").value = "";
    $("messageInput").rows = 2;
    renderMessages(true);
    const result = await api("/api/chat", {chat_id: state.chat.id, text, turn_id: turnId});
    state.bootstrap.memory = result.memory;
    state.chat = await api("/api/chats/" + state.chat.id);
    await bootstrap(false);
  } catch (error) {
    toast(error.message || "Không kết nối được server. Kiểm tra server rồi thử lại.");
    try {
      if (state.chat) state.chat = await api("/api/chats/" + state.chat.id);
      await bootstrap(false);
    } catch { /* Keep the draft when the server is unavailable. */ }
    if (!state.chat?.turns.some((turn) => turn.id === turnId)) $("messageInput").value = text;
  } finally {
    state.pending = null;
    setBusy(false);
    renderMessages(true);
    $("messageInput").focus();
  }
}

function closeSidebar() { $("sidebar").classList.remove("mobile-open"); $("mobileShade").hidden = true; }
function openMemory() { document.body.classList.remove("memory-hidden"); $("memoryPanel").classList.add("mobile-open"); }

function openSettings() {
  $("providerInput").value = state.bootstrap.config.provider;
  $("modelInput").value = state.bootstrap.config.model;
  $("apiKeyInput").value = "";
  $("apiKeyInput").placeholder = state.bootstrap.config.has_api_key ? "Đã có key ở server · để trống để giữ lại" : "sk-…";
  $("settingsError").hidden = true;
  settingsFields();
  $("settingsDialog").showModal();
}

function settingsFields() {
  const ai = $("providerInput").value === "openai";
  $("apiFields").hidden = !ai;
  $("saveSettings").textContent = ai ? "Kiểm tra kết nối & lưu" : "Dùng chế độ demo";
}

async function guarded(action) {
  if (state.busy) return;
  try { await action(); } catch (error) { toast(error.message); }
}

$("chatForm").addEventListener("submit", (event) => { event.preventDefault(); send($("messageInput").value); });
$("messageInput").addEventListener("input", () => { $("sendButton").disabled = state.busy || !$("messageInput").value.trim(); $("messageInput").rows = Math.min(5, Math.max(2, $("messageInput").value.split("\n").length)); });
$("messageInput").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); send($("messageInput").value); }
});
$("newChat").addEventListener("click", () => guarded(newChat));
$("projectSelect").addEventListener("change", () => guarded(async () => {
  state.project = $("projectSelect").value;
  localStorage.setItem("memory-project", state.project);
  await bootstrap(); closeSidebar();
}));
$("addProject").addEventListener("click", () => { $("projectInput").value = ""; $("projectDialog").showModal(); });
$("projectForm").addEventListener("submit", (event) => { event.preventDefault(); guarded(async () => {
  const name = $("projectInput").value.trim();
  if (!name) return;
  await api("/api/chats", {project: name});
  state.project = name;
  localStorage.setItem("memory-project", name);
  $("projectDialog").close();
  await bootstrap(); closeSidebar();
}); });
for (const button of document.querySelectorAll("[data-prompt]")) button.addEventListener("click", () => { if (state.busy) return; $("messageInput").value = button.dataset.prompt; $("sendButton").disabled = false; $("messageInput").focus(); });
for (const id of ["openSettings", "bannerSettings", "modeBadge"]) $(id).addEventListener("click", openSettings);
$("providerInput").addEventListener("change", settingsFields);
$("settingsForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("saveSettings").disabled = true;
  $("saveSettings").textContent = "Đang kiểm tra…";
  $("settingsError").hidden = true;
  try {
    const config = await api("/api/settings", {provider: $("providerInput").value, model: $("modelInput").value.trim() || "gpt-5-mini", api_key: $("apiKeyInput").value, test_connection: $("providerInput").value === "openai"});
    $("apiKeyInput").value = "";
    state.bootstrap.config = config;
    renderConfig();
    $("settingsDialog").close();
    toast(config.provider === "openai" ? "Đã kết nối AI. Bạn có thể trò chuyện bình thường." : "Đã chuyển sang demo. Bộ nhớ dự án được giữ lại.");
  } catch (error) {
    $("apiKeyInput").value = "";
    $("settingsError").textContent = error.message;
    $("settingsError").hidden = false;
  } finally { $("saveSettings").disabled = false; settingsFields(); }
});
for (const button of document.querySelectorAll("[data-close]")) button.addEventListener("click", () => { if (button.dataset.close === "settingsDialog") $("apiKeyInput").value = ""; $(button.dataset.close).close(); });
$("settingsDialog").addEventListener("close", () => { $("apiKeyInput").value = ""; });
$("activeTab").addEventListener("click", () => { state.memoryTab = "active"; renderMemory(); });
$("historyTab").addEventListener("click", () => { state.memoryTab = "history"; renderMemory(); });
$("openTrace").addEventListener("click", () => showTrace([...(state.chat?.turns || [])].reverse().find((t) => t.request)));
$("toggleMemory").addEventListener("click", () => {
  if (window.matchMedia("(max-width:1000px)").matches) $("memoryPanel").classList.toggle("mobile-open");
  else document.body.classList.toggle("memory-hidden");
});
$("closeMemory").addEventListener("click", () => $("memoryPanel").classList.remove("mobile-open"));
$("toggleSidebar").addEventListener("click", () => { $("sidebar").classList.toggle("mobile-open"); $("mobileShade").hidden = !$("sidebar").classList.contains("mobile-open"); });
$("mobileShade").addEventListener("click", closeSidebar);
$("exportEvidence").addEventListener("click", () => guarded(async () => {
  const data = await api("/api/export?project=" + encodeURIComponent(state.project));
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: "application/json"}));
  const anchor = node("a"); anchor.href = url; anchor.download = "challenge-a-evidence-" + new Date().toISOString().slice(0, 10) + ".json"; document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast("Đã xuất memory, lịch sử và ngữ cảnh để kiểm chứng.");
}));

$("sendButton").disabled = true;
bootstrap().catch((error) => toast("Không tải được ứng dụng: " + error.message));
