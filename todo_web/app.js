const API_BASE = "/api/todos";
const STATUS_ORDER = ["pending", "doing", "done"];
const STATUS_LABEL = {
  pending: "Pending",
  doing: "Doing",
  done: "Done",
};
const PRIORITY_LABEL = {
  high: "High",
  medium: "Medium",
  low: "Low",
};
const TOKEN_KEY = "todo_auth_token";
const USER_KEY = "todo_auth_user";

const boardEl = document.getElementById("board");
const formEl = document.getElementById("todo-form");
const todoTemplate = document.getElementById("todo-template");
const filterForm = document.getElementById("filter-form");

const editDialog = document.getElementById("edit-dialog");
const editForm = document.getElementById("edit-form");
const editCancel = document.getElementById("edit-cancel");

const editId = document.getElementById("edit-id");
const editTitle = document.getElementById("edit-title");
const editDescription = document.getElementById("edit-description");
const editStatus = document.getElementById("edit-status");
const editDueDate = document.getElementById("edit-due-date");
const editPriority = document.getElementById("edit-priority");

const authStatus = document.getElementById("auth-status");
const authUsername = document.getElementById("auth-username");
const authPassword = document.getElementById("auth-password");
const btnLogin = document.getElementById("btn-login");
const btnRegister = document.getElementById("btn-register");
const btnLogout = document.getElementById("btn-logout");

const btnClearFilters = document.getElementById("btn-clear-filters");
const btnExportJson = document.getElementById("btn-export-json");
const btnExportCsv = document.getElementById("btn-export-csv");

let todos = [];
let token = localStorage.getItem(TOKEN_KEY) || "";
let username = localStorage.getItem(USER_KEY) || "";
let currentFilters = {};

function setAuth(nextToken, nextUsername) {
  token = nextToken || "";
  username = nextUsername || "";
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, username);
    authStatus.textContent = `Signed in as ${username}`;
  } else {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    authStatus.textContent = "Not signed in";
  }
}

function requireAuth() {
  if (!token) {
    alert("Please login or register first.");
    return false;
  }
  return true;
}

async function request(url, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(url, {
    headers,
    ...options,
  });

  const isJson = (res.headers.get("content-type") || "").includes("application/json");
  const body = isJson ? await res.json() : null;

  if (!res.ok) {
    const msg = body && body.error ? body.error : `Request failed with ${res.status}`;
    if (res.status === 401) {
      setAuth("", "");
      boardEl.innerHTML = `<p class="error">Please sign in again.</p>`;
    }
    throw new Error(msg);
  }

  return body;
}

function fmtDate(text) {
  if (!text) return "";
  const value = text.includes("T") ? text : text.replace(" ", "T") + "Z";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return text;
  return d.toLocaleString();
}

function groupByStatus(items) {
  return STATUS_ORDER.reduce((acc, status) => {
    acc[status] = items.filter((item) => item.status === status);
    return acc;
  }, {});
}

function todoCard(todo) {
  const card = todoTemplate.content.firstElementChild.cloneNode(true);

  card.dataset.id = String(todo.id);
  card.querySelector(".todo-title").textContent = todo.title;
  card.querySelector(".todo-desc").textContent = todo.description || "No description";
  const tags = card.querySelector(".todo-tags");
  tags.innerHTML = `
    <span class="tag tag-priority-${todo.priority}">Priority: ${PRIORITY_LABEL[todo.priority] || todo.priority}</span>
    <span class="tag">Due: ${todo.due_date || "No date"}</span>
  `;
  card.querySelector(".todo-meta").textContent = `Created: ${fmtDate(todo.created_at)} | Updated: ${fmtDate(todo.updated_at)}`;

  const check = card.querySelector(".done-toggle");
  check.checked = todo.status === "done";

  const statusSelect = card.querySelector(".status-select");
  statusSelect.value = todo.status;

  if (todo.status === "done") {
    card.classList.add("is-done");
  }

  check.addEventListener("change", async () => {
    const next = check.checked ? "done" : "pending";
    await updateTodo(todo.id, { status: next });
  });

  statusSelect.addEventListener("change", async (event) => {
    await updateTodo(todo.id, { status: event.target.value });
  });

  card.querySelector(".btn-delete").addEventListener("click", async () => {
    const ok = window.confirm(`Delete todo: ${todo.title}?`);
    if (!ok) return;
    await request(`${API_BASE}/${todo.id}`, { method: "DELETE" });
    await refresh();
  });

  card.querySelector(".btn-edit").addEventListener("click", () => {
    editId.value = String(todo.id);
    editTitle.value = todo.title;
    editDescription.value = todo.description || "";
    editStatus.value = todo.status;
    editDueDate.value = todo.due_date || "";
    editPriority.value = todo.priority || "medium";
    editDialog.showModal();
  });

  return card;
}

function render(items) {
  const grouped = groupByStatus(items);
  boardEl.innerHTML = "";

  STATUS_ORDER.forEach((status) => {
    const col = document.createElement("section");
    col.className = `lane lane-${status}`;

    const list = grouped[status];

    const head = document.createElement("header");
    head.className = "lane-head";
    head.innerHTML = `<h2>${STATUS_LABEL[status]}</h2><span>${list.length}</span>`;

    const body = document.createElement("div");
    body.className = "lane-body";

    if (list.length === 0) {
      const empty = document.createElement("p");
      empty.className = "lane-empty";
      empty.textContent = "No tasks";
      body.appendChild(empty);
    } else {
      list.forEach((todo) => body.appendChild(todoCard(todo)));
    }

    col.appendChild(head);
    col.appendChild(body);
    boardEl.appendChild(col);
  });
}

async function refresh() {
  if (!token) {
    boardEl.innerHTML = `<p class="error">Sign in to view your todos.</p>`;
    return;
  }

  const params = new URLSearchParams();
  Object.entries(currentFilters).forEach(([k, v]) => {
    if (v) params.set(k, v);
  });
  const url = params.toString() ? `${API_BASE}?${params.toString()}` : API_BASE;
  todos = await request(url);
  render(todos);
}

async function updateTodo(id, patch) {
  await request(`${API_BASE}/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
  await refresh();
}

formEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!requireAuth()) return;

  const title = document.getElementById("title").value.trim();
  const description = document.getElementById("description").value.trim();
  const status = document.getElementById("status").value;
  const due_date = document.getElementById("due_date").value;
  const priority = document.getElementById("priority").value;

  if (!title) {
    alert("Title is required");
    return;
  }

  await request(API_BASE, {
    method: "POST",
    body: JSON.stringify({ title, description, status, due_date, priority }),
  });

  formEl.reset();
  await refresh();
});

editCancel.addEventListener("click", () => editDialog.close());

editForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const id = Number(editId.value);
  await updateTodo(id, {
    title: editTitle.value.trim(),
    description: editDescription.value.trim(),
    status: editStatus.value,
    due_date: editDueDate.value,
    priority: editPriority.value,
  });
  editDialog.close();
});

btnLogin.addEventListener("click", async () => {
  const u = authUsername.value.trim().toLowerCase();
  const p = authPassword.value;
  if (!u || !p) return alert("Please enter username and password");

  try {
    const data = await request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: u, password: p }),
      headers: {},
    });
    setAuth(data.token, data.username);
    await refresh();
  } catch (err) {
    alert(err.message);
  }
});

btnRegister.addEventListener("click", async () => {
  const u = authUsername.value.trim().toLowerCase();
  const p = authPassword.value;
  if (!u || !p) return alert("Please enter username and password");

  try {
    const data = await request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ username: u, password: p }),
      headers: {},
    });
    setAuth(data.token, data.username);
    await refresh();
  } catch (err) {
    alert(err.message);
  }
});

btnLogout.addEventListener("click", async () => {
  if (!token) return;
  try {
    await request("/api/auth/logout", { method: "POST" });
  } catch (_err) {
    // Ignore backend logout errors when token is stale.
  }
  setAuth("", "");
  boardEl.innerHTML = `<p class="error">Signed out.</p>`;
});

filterForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  currentFilters = {
    q: document.getElementById("filter-q").value.trim(),
    status: document.getElementById("filter-status").value,
    priority: document.getElementById("filter-priority").value,
    due_after: document.getElementById("filter-due-after").value,
    due_before: document.getElementById("filter-due-before").value,
  };
  await refresh();
});

btnClearFilters.addEventListener("click", async () => {
  filterForm.reset();
  currentFilters = {};
  await refresh();
});

async function exportData(format) {
  if (!requireAuth()) return;
  const params = new URLSearchParams({ format });
  Object.entries(currentFilters).forEach(([k, v]) => {
    if (v) params.set(k, v);
  });
  const res = await fetch(`/api/export?${params.toString()}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || "Export failed");
  }
  const blob = await res.blob();
  const cd = res.headers.get("content-disposition") || "";
  const match = /filename=([^;]+)/i.exec(cd);
  const filename = match ? match[1].trim() : `todos.${format}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

btnExportJson.addEventListener("click", async () => {
  try {
    await exportData("json");
  } catch (err) {
    alert(err.message);
  }
});

btnExportCsv.addEventListener("click", async () => {
  try {
    await exportData("csv");
  } catch (err) {
    alert(err.message);
  }
});

if (token && username) {
  authStatus.textContent = `Signed in as ${username}`;
  refresh().catch((err) => {
    console.error(err);
    boardEl.innerHTML = `<p class="error">Failed to load todos: ${err.message}</p>`;
  });
} else {
  authStatus.textContent = "Not signed in";
  boardEl.innerHTML = `<p class="error">Sign in to view your todos.</p>`;
}
