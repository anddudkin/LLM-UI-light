<script setup>
import { nextTick, watch, ref } from "vue";
import ToolIndicator from "./ToolIndicator.vue";
import { renderMarkdown } from "../utils/markdown";

const props = defineProps({
  conversationId: { type: [String, Number], default: null },
  messages: { type: Array, required: true },
  streaming: { type: Boolean, default: false },
  streamingText: { type: String, default: "" },
  toolStatus: { type: Object, default: null },
  error: { type: String, default: null },
});

const BOTTOM_THRESHOLD = 120;

const emit = defineEmits(["edit-message"]);

const container = ref(null);
const editingIndex = ref(-1);
const editingText = ref("");
const copiedIndex = ref(-1);
let copiedTimeout = null;

function copyWithExecCommand(text) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  }
  document.body.removeChild(textarea);
  return ok;
}

async function copyMessage(text, index) {
  let ok = false;
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      ok = true;
    } catch {
      ok = false;
    }
  }
  if (!ok) ok = copyWithExecCommand(text);
  if (!ok) return;
  copiedIndex.value = index;
  clearTimeout(copiedTimeout);
  copiedTimeout = setTimeout(() => {
    copiedIndex.value = -1;
  }, 1500);
}

const isNearBottom = ref(true);

function onScroll() {
  const el = container.value;
  if (!el) return;
  isNearBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < BOTTOM_THRESHOLD;
}

function scrollToBottom() {
  if (container.value) container.value.scrollTop = container.value.scrollHeight;
}

watch(
  () => [props.messages.length, props.streamingText, props.error],
  async () => {
    const shouldStick = isNearBottom.value;
    await nextTick();
    if (shouldStick) scrollToBottom();
  },
  { deep: false }
);

watch(
  () => props.conversationId,
  async () => {
    isNearBottom.value = true;
    await nextTick();
    scrollToBottom();
  }
);

function startEdit(index) {
  if (props.streaming) return;
  editingIndex.value = index;
  editingText.value = props.messages[index].content;
}

function cancelEdit() {
  editingIndex.value = -1;
  editingText.value = "";
}

function submitEdit(message) {
  const value = editingText.value.trim();
  if (!value || !message.id) {
    cancelEdit();
    return;
  }
  emit("edit-message", { id: message.id, content: value });
  cancelEdit();
}

function onEditKeydown(event, message) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    submitEdit(message);
  } else if (event.key === "Escape") {
    cancelEdit();
  }
}
</script>

<template>
  <div ref="container" class="messages" @scroll="onScroll">
    <div class="column">
      <div v-for="(message, i) in messages" :key="message.id ?? i" class="row" :class="message.role">
        <div v-if="message.role === 'assistant'" class="avatar">✦</div>
        <div v-if="message.role === 'assistant'" class="assistant-wrap">
          <div class="bubble markdown-body" v-html="renderMarkdown(message.content)" />
          <button
            class="copy-btn"
            type="button"
            :title="copiedIndex === i ? 'Скопировано' : 'Скопировать'"
            @click="copyMessage(message.content, i)"
          >
            <svg v-if="copiedIndex !== i" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="9" y="9" width="12" height="12" rx="2" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
            <svg v-else viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 6L9 17l-5-5" />
            </svg>
          </button>
        </div>
        <div v-else-if="editingIndex === i" class="edit-wrap">
          <textarea
            v-model="editingText"
            class="edit-textarea"
            rows="2"
            @keydown="onEditKeydown($event, message)"
          />
          <div class="edit-actions">
            <button class="edit-cancel" @click="cancelEdit">Отмена</button>
            <button class="edit-save" @click="submitEdit(message)">Отправить</button>
          </div>
        </div>
        <div v-else class="user-wrap">
          <div class="bubble">{{ message.content }}</div>
          <button
            v-if="!streaming && message.id"
            class="edit-btn"
            type="button"
            title="Редактировать сообщение"
            @click="startEdit(i)"
          >
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 20h9" />
              <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
            </svg>
          </button>
        </div>
      </div>

      <div v-if="streaming && (streamingText || !toolStatus)" class="row assistant">
        <div class="avatar">✦</div>
        <div class="bubble">
          <span v-if="streamingText" class="markdown-body" v-html="renderMarkdown(streamingText)" />
          <span v-else class="cursor" />
        </div>
      </div>

      <div v-if="toolStatus" class="row assistant">
        <div class="avatar">✦</div>
        <ToolIndicator :tool-status="toolStatus" />
      </div>

      <div v-if="error" class="row assistant">
        <div class="avatar">✦</div>
        <div class="bubble error">{{ error }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem 1.5rem 0.5rem;
}

.column {
  max-width: 46rem;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}

.row {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
}

.row.user {
  justify-content: flex-end;
}

.avatar {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--accent);
  color: var(--accent-text);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  margin-top: 0.1rem;
}

.bubble {
  max-width: 70%;
  padding: 0.65rem 0.95rem;
  border-radius: 16px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
  font-size: 0.87rem;
}

.row.user .bubble {
  background: var(--user-bubble-bg);
  color: var(--user-bubble-text);
  border-bottom-right-radius: 4px;
}

.user-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.25rem;
  max-width: 70%;
}

.user-wrap .bubble {
  max-width: 100%;
}

.edit-btn {
  flex-shrink: 0;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.15s, background 0.15s, color 0.15s;
}

.row.user:hover .edit-btn {
  opacity: 1;
}

.edit-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text);
}

.edit-wrap {
  width: 100%;
  max-width: 70%;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  background: var(--input-bg);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 0.6rem 0.7rem;
}

.edit-textarea {
  resize: vertical;
  border: none;
  background: transparent;
  color: var(--text);
  font-family: inherit;
  font-size: 0.87rem;
  line-height: 1.5;
  min-height: 2.6em;
}

.edit-textarea:focus {
  outline: none;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.edit-actions button {
  border: none;
  border-radius: 10px;
  padding: 0.35rem 0.75rem;
  font-size: 0.8rem;
  cursor: pointer;
}

.edit-cancel {
  background: transparent;
  color: var(--text-secondary);
}

.edit-cancel:hover {
  background: var(--bg-tertiary);
}

.edit-save {
  background: var(--accent);
  color: var(--accent-text);
}

.edit-save:hover {
  background: var(--accent-hover);
}

.row.assistant .bubble {
  background: transparent;
  color: var(--text);
  padding: 0.15rem 0;
  max-width: 100%;
}

.assistant-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  max-width: 100%;
  min-width: 0;
  flex: 1;
}

.copy-btn {
  flex-shrink: 0;
  width: 26px;
  height: 26px;
  margin-top: 0.1rem;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 1;
  transition: background 0.15s, color 0.15s;
}

.copy-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text);
}

.markdown-body {
  /* Rendered HTML has its own block-level spacing (p/li/table margins) — pre-wrap here would
     also make the whitespace markdown-it puts between tags render as extra blank lines.
     Applies directly (not via inheritance) so it covers both the message bubble and the
     streaming-text span, which only carries the markdown-body class. */
  white-space: normal;
}

.bubble.error {
  background: var(--danger-bg);
  color: var(--danger-text);
  border: 1px solid var(--danger-border);
  border-radius: 12px;
  padding: 0.6rem 0.9rem;
}

.cursor {
  display: inline-block;
  width: 8px;
  height: 1.1em;
  background: var(--text-secondary);
  border-radius: 2px;
  vertical-align: text-bottom;
  animation: blink 1s step-start infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}
</style>

<!--
  Unscoped on purpose: this content comes from v-html (renderMarkdown), so it never goes
  through Vue's template compiler and never gets the scoped data-v-* attribute that
  `<style scoped>` selectors rely on to match. Rules here must stay global.
-->
<style>
.markdown-body :first-child {
  margin-top: 0;
}

.markdown-body :last-child {
  margin-bottom: 0;
}

.markdown-body p {
  margin: 0.5em 0;
}

.markdown-body ul,
.markdown-body ol {
  margin: 0.5em 0;
  padding-left: 1.4em;
}

.markdown-body li {
  margin: 0.2em 0;
}

.markdown-body li > p {
  margin: 0.2em 0;
}

.markdown-body h1,
.markdown-body h2,
.markdown-body h3,
.markdown-body h4 {
  margin: 0.8em 0 0.4em;
  line-height: 1.3;
  font-weight: 600;
}

.markdown-body h1 {
  font-size: 1.4em;
}

.markdown-body h2 {
  font-size: 1.25em;
}

.markdown-body h3 {
  font-size: 1.1em;
}

.markdown-body a {
  color: var(--accent);
}

.markdown-body strong {
  font-weight: 600;
}

.markdown-body blockquote {
  margin: 0.5em 0;
  padding: 0.1em 0.9em;
  border-left: 3px solid var(--border);
  color: var(--text-secondary);
}

.markdown-body code {
  background: var(--bg-tertiary);
  border-radius: 4px;
  padding: 0.15em 0.4em;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  font-size: 0.88em;
}

.markdown-body pre {
  background: var(--bg-tertiary);
  border-radius: 10px;
  padding: 0.8em 1em;
  overflow-x: auto;
  margin: 0.6em 0;
}

.markdown-body pre code {
  background: none;
  padding: 0;
  border-radius: 0;
  font-size: 0.85em;
  line-height: 1.5;
  white-space: pre;
}

.markdown-body table {
  border-collapse: collapse;
  margin: 0.6em 0;
  font-size: 0.92em;
  display: block;
  overflow-x: auto;
}

.markdown-body th,
.markdown-body td {
  border: 1px solid var(--border);
  padding: 0.4em 0.7em;
  text-align: left;
}

.markdown-body th {
  background: var(--bg-tertiary);
  font-weight: 600;
}

.markdown-body hr {
  border: none;
  border-top: 1px solid var(--border);
  margin: 0.8em 0;
}

.markdown-body img {
  max-width: 100%;
  border-radius: 8px;
}

.markdown-body .katex-display {
  overflow-x: auto;
  overflow-y: hidden;
  padding: 0.2em 0;
}
</style>
