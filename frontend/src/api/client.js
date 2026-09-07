const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8010";

function authHeaders() {
  const raw = localStorage.getItem("app_llm_user");
  if (!raw) return {};
  const { email } = JSON.parse(raw);
  return email ? { "X-User-Email": email } : {};
}

function parseErrorMessage(text) {
  try {
    const data = JSON.parse(text);
    const detail = data.message || data.detail;
    if (Array.isArray(detail)) {
      // FastAPI/Pydantic validation errors: detail is a list of {loc, msg, type}.
      return detail.map((d) => d.msg || JSON.stringify(d)).join("; ") || text;
    }
    return detail || text;
  } catch {
    return text;
  }
}

async function readNdjsonStream(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let newlineIndex;
    while ((newlineIndex = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, newlineIndex).trim();
      buffer = buffer.slice(newlineIndex + 1);
      if (line) onEvent(JSON.parse(line));
    }
  }
  if (buffer.trim()) onEvent(JSON.parse(buffer.trim()));
}

export async function login(userInfo) {
  const body = new URLSearchParams({ user_info: userInfo });
  const res = await fetch(`${BASE_URL}/api/login`, { method: "POST", body });
  if (!res.ok) throw new Error(parseErrorMessage(await res.text()));
  return res.json();
}

export async function listConversations() {
  const res = await fetch(`${BASE_URL}/api/v1/conversations`, { headers: authHeaders() });
  if (!res.ok) throw new Error(parseErrorMessage(await res.text()));
  return res.json();
}

export async function createConversation() {
  const res = await fetch(`${BASE_URL}/api/v1/conversations`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(parseErrorMessage(await res.text()));
  return res.json();
}

export async function getMessages(conversationId) {
  const res = await fetch(`${BASE_URL}/api/v1/conversations/${conversationId}/messages`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(parseErrorMessage(await res.text()));
  return res.json();
}

export async function streamChat({ conversationId, message, forceWebSearch, onEvent }) {
  const res = await fetch(`${BASE_URL}/api/v1/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ conversation_id: conversationId, message, force_web_search: !!forceWebSearch }),
  });

  if (!res.ok) {
    const text = await res.text();
    return { ok: false, status: res.status, message: parseErrorMessage(text) };
  }

  await readNdjsonStream(res, onEvent);
  return { ok: true };
}

export async function editMessage({ conversationId, messageId, message, onEvent }) {
  const res = await fetch(`${BASE_URL}/api/v1/conversations/${conversationId}/messages/${messageId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ message }),
  });

  if (!res.ok) {
    const text = await res.text();
    return { ok: false, status: res.status, message: parseErrorMessage(text) };
  }

  await readNdjsonStream(res, onEvent);
  return { ok: true };
}

export async function streamChatWithFiles({ conversationId, message, files, forceWebSearch, onEvent }) {
  const formData = new FormData();
  formData.append("conversation_id", conversationId);
  formData.append("message", message);
  formData.append("force_web_search", forceWebSearch ? "true" : "false");
  for (const file of files) formData.append("files", file);

  const res = await fetch(`${BASE_URL}/api/v1/chat/completions_files`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    return { ok: false, status: res.status, message: parseErrorMessage(text) };
  }

  await readNdjsonStream(res, onEvent);
  return { ok: true };
}
