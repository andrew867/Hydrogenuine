const API_KEY = localStorage.getItem("hg_api_key") || "oss-demo-key";
const API_BASE = localStorage.getItem("hg_api_base") || "http://127.0.0.1:8000/v1";

const routes = [
  ["chat", "Chat"],
  ["workflows", "Workflows"],
  ["research", "Research"],
  ["documents", "Documents"],
  ["memory", "Memory"],
  ["approvals", "Approvals"],
  ["receipts", "Receipts"],
  ["settings-models", "Models"],
  ["settings-tools", "Tools"],
  ["settings-data", "Data"],
  ["onboarding", "Onboarding"],
  ["diagnostics", "Diagnostics"],
];

const state = {
  chats: [],
  currentChatId: null,
  messages: [],
  plans: [],
  workflows: [],
  receipts: [],
  memory: [],
  documents: [],
  leases: [],
  diagnostics: null,
  models: [],
};

function el(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char]);
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "content-type": "application/json",
      "x-api-key": API_KEY,
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    const detail = data.detail || data.reason || response.statusText;
    throw new Error(detail);
  }
  return data;
}

async function refreshBase() {
  try {
    state.diagnostics = await api("/diagnostics");
    state.models = (await api("/models")).providers;
    state.receipts = (await api("/receipts")).receipts;
    state.memory = (await api("/memory")).memory;
    state.documents = (await api("/documents")).documents;
    state.leases = (await api("/leases")).leases;
    state.plans = (await api("/plans")).plans;
    state.workflows = (await api("/workflows")).workflows;
    const chats = await api("/chats");
    state.chats = chats.chats || [];
    document.querySelector(".status-dot").className = "status-dot ok";
    el("api-status").textContent = "API connected";
  } catch (error) {
    document.querySelector(".status-dot").className = "status-dot bad";
    el("api-status").textContent = "API offline";
  }
}

async function loadMessages(chatId) {
  if (!chatId) {
    state.messages = [];
    return;
  }
  try {
    state.messages = (await api(`/chats/${chatId}/messages`)).messages || [];
  } catch {
    state.messages = [];
  }
}

function renderNav() {
  const current = currentRoute();
  el("nav").innerHTML = routes.map(([id, label]) => (
    `<a href="#/${id}" class="${id === current ? "active" : ""}">${label}</a>`
  )).join("");
}

function currentRoute() {
  return (location.hash.replace(/^#\/?/, "") || "chat").split("/")[0];
}

function setTitle(label) {
  el("page-title").textContent = label;
}

function panel(title, body, span = 6) {
  return `<section class="panel span-${span}"><h2>${title}</h2>${body}</section>`;
}

function renderList(items, empty, render) {
  if (!items || items.length === 0) return `<div class="empty">${empty}</div>`;
  return items.map(render).join("");
}

async function renderChat() {
  setTitle("Chat");
  el("route").innerHTML = `<div class="loading">Loading chat workspace...</div>`;
  if (!state.currentChatId && state.chats[0]) state.currentChatId = state.chats[0].chat_id;
  await loadMessages(state.currentChatId);
  el("route").innerHTML = `
    <div class="chat-layout">
      <section class="panel chat-list">
        <h2>Conversations</h2>
        <div class="actions">
          <button class="button primary" data-action="new-chat">New chat</button>
          <button class="button" data-action="branch-chat">Branch</button>
          <button class="button" data-action="retry-chat">Retry</button>
        </div>
        ${renderList(state.chats, "No conversations yet.", (chat) => `
          <button class="item button ${chat.chat_id === state.currentChatId ? "primary" : ""}" data-chat="${chat.chat_id}">
            <span>${escapeHtml(chat.title || "Chat")}</span>
            <span class="mono">${escapeHtml((chat.updated_at || "").slice(11, 19))}</span>
          </button>
        `)}
      </section>
      <section class="panel messages">
        <div class="message-log">
          ${renderList(state.messages, "Start with a governed local request.", (message) => `
            <article class="bubble ${escapeHtml(message.role)}">
              <p class="mono muted">${escapeHtml(message.role)} ${escapeHtml(message.message_id || "")}</p>
              <div>${escapeHtml(message.content)}</div>
            </article>
          `)}
        </div>
        <form class="composer" data-form="send-message">
          <div class="pill-row">
            <span class="pill">model: stub</span>
            <span class="pill">authority: none</span>
            <span class="pill">receipts: ${state.receipts.length}</span>
          </div>
          <div class="field">
            <label for="message">Message</label>
            <textarea id="message" name="message">Plan a local research task and show the approval boundary.</textarea>
          </div>
          <div class="actions">
            <button class="button primary" type="submit">Send</button>
            <button class="button" type="button" data-action="attach">Attach note</button>
            <button class="button danger" type="button" data-action="stop">Stop</button>
          </div>
        </form>
      </section>
      <aside class="side-stack">
        ${panel("Plan", renderList(state.plans.slice(0, 2), "No plans yet.", (plan) => `
          <div class="item"><span>${escapeHtml(plan.request)}</span><span class="pending">${escapeHtml(plan.status)}</span></div>
        `), 12)}
        ${panel("Sources", `<div class="item"><span>Research sources appear here with claim boundaries.</span><span class="evidence">cited</span></div>`, 12)}
        ${panel("Receipts", renderList(state.receipts.slice(-3), "No receipts yet.", (receipt) => `
          <div class="timeline-row"><span>${escapeHtml(receipt.kind)}</span><span class="mono evidence">${escapeHtml(receipt.receipt_hash.slice(0, 8))}</span></div>
        `), 12)}
      </aside>
    </div>
  `;
}

function renderWorkflows() {
  setTitle("Workflows");
  el("route").innerHTML = `<div class="grid">
    ${panel("Plan Builder", `
      <form data-form="create-plan">
        <div class="field"><label for="plan-request">Request</label><textarea id="plan-request" name="request">Create a cited local model setup checklist with receipts.</textarea></div>
        <button class="button primary" type="submit">Create plan</button>
      </form>
    `, 5)}
    ${panel("Plans", renderList(state.plans, "No plans yet.", (plan) => `
      <div class="item">
        <div><strong>${escapeHtml(plan.request)}</strong><p class="muted">${plan.steps.length} steps · revision ${plan.revision}</p></div>
        <div class="actions"><button class="button" data-approve-plan="${plan.plan_id}">Approve</button><button class="button primary" data-workflow-plan="${plan.plan_id}">Run</button></div>
      </div>
    `), 7)}
    ${panel("Workflow Runs", renderList(state.workflows, "No workflow runs yet.", (workflow) => `
      <div class="item">
        <div><strong>${escapeHtml(workflow.workflow_id)}</strong><p class="muted">${workflow.steps.length} steps · ${workflow.artifacts.length} artifacts</p></div>
        <span class="${workflow.status === "completed" ? "allowed" : "pending"}">${escapeHtml(workflow.status)}</span>
      </div>
    `), 12)}
  </div>`;
}

function renderResearch() {
  setTitle("Research");
  el("route").innerHTML = `<div class="grid">
    ${panel("Source-Aware Research", `
      <form data-form="research">
        <div class="field"><label for="research-query">Query</label><textarea id="research-query" name="query">How should a local-first AI tool disclose source boundaries?</textarea></div>
        <button class="button primary" type="submit">Create cited report</button>
      </form>
    `, 5)}
    ${panel("Claim Boundaries", `
      <div id="research-output" class="empty">Run fixture research to show sources, confidence and claim boundaries.</div>
    `, 7)}
  </div>`;
}

function renderDocuments() {
  setTitle("Documents");
  el("route").innerHTML = `<div class="grid">
    ${panel("Ingest", `
      <form data-form="document">
        <div class="field"><label for="doc-name">Name</label><input id="doc-name" name="name" value="demo.md"></div>
        <div class="field"><label for="doc-content">Content</label><textarea id="doc-content" name="content">Hydrogenuine stores local document citations. Receipts stay local.</textarea></div>
        <button class="button primary" type="submit">Ingest document</button>
      </form>
    `, 5)}
    ${panel("Library", renderList(state.documents, "No documents ingested.", (doc) => `
      <div class="item"><span>${escapeHtml(doc.name)}</span><span class="mono evidence">${escapeHtml(doc.sha256.slice(0, 10))}</span></div>
    `), 7)}
  </div>`;
}

function renderMemory() {
  setTitle("Memory");
  el("route").innerHTML = `<div class="grid">
    ${panel("Candidate Memory", `
      <form data-form="memory">
        <div class="field"><label for="memory-text">Fact</label><textarea id="memory-text" name="text">The workspace uses deterministic fixtures for release evidence.</textarea></div>
        <button class="button primary" type="submit">Record candidate</button>
      </form>
    `, 5)}
    ${panel("Inspector", renderList(state.memory, "No memory recorded.", (memory) => `
      <div class="item">
        <div><strong>${escapeHtml(memory.text)}</strong><p class="muted">authority ${escapeHtml(memory.authority)} · revisions ${memory.revisions.length}</p></div>
        <button class="button" data-accept-memory="${memory.memory_id}">Accept</button>
      </div>
    `), 7)}
  </div>`;
}

function renderApprovals() {
  setTitle("Approvals");
  el("route").innerHTML = `<div class="grid">
    ${panel("Capability Leases", `
      <form data-form="lease">
        <div class="field"><label for="capability">Capability</label><select id="capability" name="capability"><option>simulated.echo</option><option>tools.run</option><option>artifact.write</option></select></div>
        <button class="button primary" type="submit">Request lease</button>
      </form>
    `, 5)}
    ${panel("Review Queue", renderList(state.leases, "No lease requests.", (lease) => `
      <div class="item">
        <div><strong>${escapeHtml(lease.capability)}</strong><p class="muted">${escapeHtml(lease.lease_id)}</p></div>
        <div class="actions"><button class="button primary" data-lease-approve="${lease.lease_id}">Approve</button><button class="button danger" data-lease-revoke="${lease.lease_id}">Revoke</button></div>
      </div>
    `), 7)}
  </div>`;
}

function renderReceipts() {
  setTitle("Receipts");
  el("route").innerHTML = `<div class="grid">
    ${panel("Receipt Chain", renderList(state.receipts, "No receipts recorded.", (receipt) => `
      <div class="timeline-row">
        <span>${escapeHtml(receipt.kind)} <span class="muted">${escapeHtml(receipt.decision)}</span></span>
        <span class="mono evidence">${escapeHtml(receipt.receipt_hash.slice(0, 16))}</span>
      </div>
    `), 12)}
  </div>`;
}

function renderSettings(kind) {
  const label = kind === "settings-models" ? "Model Settings" : kind === "settings-tools" ? "Tool Settings" : "Data Settings";
  setTitle(label);
  const body = kind === "settings-models"
    ? renderList(state.models, "No model providers.", (provider) => `<div class="item"><span>${escapeHtml(provider.label)}</span><span class="${provider.configured ? "allowed" : "pending"}">${provider.configured ? "configured" : "optional"}</span></div>`)
    : kind === "settings-tools"
      ? `<div class="item"><span>Default tool policy</span><span class="denied">deny unless lease active</span></div><div class="item"><span>Allowed roots</span><span class="pending">configure locally</span></div>`
      : `<div class="item"><span>Data directory</span><span class="mono">${escapeHtml((state.diagnostics || {}).data_dir || ".hg_community")}</span></div><div class="item"><span>Telemetry</span><span class="allowed">off</span></div>`;
  el("route").innerHTML = `<div class="grid">${panel(label, body, 12)}</div>`;
}

function renderOnboarding() {
  setTitle("Onboarding");
  el("route").innerHTML = `<div class="grid">
    ${panel("First Run", `
      <div class="metric-row"><span>1. Data directory</span><span class="allowed">local</span></div>
      <div class="metric-row"><span>2. Model</span><span class="allowed">deterministic stub ready</span></div>
      <div class="metric-row"><span>3. Tool roots</span><span class="pending">empty by default</span></div>
      <div class="metric-row"><span>4. Telemetry</span><span class="allowed">off</span></div>
      <div class="actions"><a class="button primary" href="#/chat">Open chat</a><a class="button" href="#/settings-models">Configure models</a></div>
    `, 12)}
  </div>`;
}

function renderDiagnostics() {
  setTitle("Diagnostics");
  const diag = state.diagnostics || {};
  el("route").innerHTML = `<div class="grid">
    ${panel("Local Runtime", `
      <div class="metric-row"><span>API</span><span class="${diag.ok ? "allowed" : "denied"}">${diag.ok ? "healthy" : "offline"}</span></div>
      <div class="metric-row"><span>Data</span><span class="mono">${escapeHtml(diag.data_dir || "unknown")}</span></div>
      <div class="metric-row"><span>Telemetry</span><span class="allowed">${escapeHtml(diag.telemetry || "off")}</span></div>
      <div class="metric-row"><span>Network</span><span class="pending">${escapeHtml(diag.network || "configurable")}</span></div>
    `, 6)}
    ${panel("Stores", Object.entries(diag.stores || {}).map(([key, value]) => `<div class="metric-row"><span>${escapeHtml(key)}</span><span class="mono">${value}</span></div>`).join("") || `<div class="empty">No diagnostics yet.</div>`, 6)}
  </div>`;
}

async function renderRoute() {
  await refreshBase();
  renderNav();
  const route = currentRoute();
  if (route === "chat") return renderChat();
  if (route === "workflows") return renderWorkflows();
  if (route === "research") return renderResearch();
  if (route === "documents") return renderDocuments();
  if (route === "memory") return renderMemory();
  if (route === "approvals") return renderApprovals();
  if (route === "receipts") return renderReceipts();
  if (route.startsWith("settings")) return renderSettings(route);
  if (route === "onboarding") return renderOnboarding();
  if (route === "diagnostics") return renderDiagnostics();
  location.hash = "#/chat";
}

document.addEventListener("click", async (event) => {
  const target = event.target.closest("[data-chat], [data-action], [data-approve-plan], [data-workflow-plan], [data-accept-memory], [data-lease-approve], [data-lease-revoke]");
  if (!target) return;
  try {
    if (target.dataset.chat) state.currentChatId = target.dataset.chat;
    if (target.dataset.action === "new-chat") {
      const chat = await api("/chats", { method: "POST", body: JSON.stringify({ title: "New governed chat" }) });
      state.currentChatId = chat.chat_id;
    }
    if (target.dataset.action === "branch-chat" && state.currentChatId) await api(`/chats/${state.currentChatId}/branch`, { method: "POST", body: "{}" });
    if (target.dataset.action === "retry-chat" && state.currentChatId) await api(`/chats/${state.currentChatId}/retry`, { method: "POST", body: "{}" });
    if (target.dataset.action === "attach" && state.currentChatId) await api(`/chats/${state.currentChatId}/attachments`, { method: "POST", body: JSON.stringify({ name: "note.md", content: "fixture attachment" }) });
    if (target.dataset.action === "stop") window.alert("Current deterministic run has no active stream to stop.");
    if (target.dataset.approvePlan) await api(`/plans/${target.dataset.approvePlan}/approve`, { method: "POST", body: "{}" });
    if (target.dataset.workflowPlan) {
      const workflow = await api("/workflows", { method: "POST", body: JSON.stringify({ plan_id: target.dataset.workflowPlan }) });
      await api(`/workflows/${workflow.workflow.workflow_id}/run`, { method: "POST", body: "{}" });
    }
    if (target.dataset.acceptMemory) await api(`/memory/${target.dataset.acceptMemory}`, { method: "PATCH", body: JSON.stringify({ status: "accepted" }) });
    if (target.dataset.leaseApprove) await api(`/leases/${target.dataset.leaseApprove}/approve`, { method: "POST", body: "{}" });
    if (target.dataset.leaseRevoke) await api(`/leases/${target.dataset.leaseRevoke}/revoke`, { method: "POST", body: "{}" });
    await renderRoute();
  } catch (error) {
    el("route").insertAdjacentHTML("afterbegin", `<div class="error">${escapeHtml(error.message)}</div>`);
  }
});

document.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const formData = Object.fromEntries(new FormData(form).entries());
  try {
    if (form.dataset.form === "send-message") {
      if (!state.currentChatId) {
        const chat = await api("/chats", { method: "POST", body: JSON.stringify({ title: "New governed chat" }) });
        state.currentChatId = chat.chat_id;
      }
      await api(`/chats/${state.currentChatId}/messages`, { method: "POST", body: JSON.stringify({ content: formData.message, provider: "stub" }) });
    }
    if (form.dataset.form === "create-plan") await api("/plans", { method: "POST", body: JSON.stringify({ request: formData.request }) });
    if (form.dataset.form === "research") {
      const result = await api("/research", { method: "POST", body: JSON.stringify({ query: formData.query }) });
      document.getElementById("research-output").innerHTML = result.research.sources.map((source) => `<div class="item"><span>${escapeHtml(source.title)}</span><span class="evidence">${escapeHtml(source.claim_boundary)}</span></div>`).join("");
      return;
    }
    if (form.dataset.form === "document") await api("/documents", { method: "POST", body: JSON.stringify({ name: formData.name, content: formData.content }) });
    if (form.dataset.form === "memory") await api("/memory", { method: "POST", body: JSON.stringify({ text: formData.text }) });
    if (form.dataset.form === "lease") await api("/leases", { method: "POST", body: JSON.stringify({ capability: formData.capability, scope: { local: true } }) });
    await renderRoute();
  } catch (error) {
    el("route").insertAdjacentHTML("afterbegin", `<div class="error">${escapeHtml(error.message)}</div>`);
  }
});

el("refresh").addEventListener("click", renderRoute);
el("theme-toggle").addEventListener("click", () => document.documentElement.classList.toggle("light"));
window.addEventListener("hashchange", renderRoute);

renderRoute();
