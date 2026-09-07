<script setup>
import { ref, nextTick } from "vue";
import { useChatStore } from "../stores/chat";
import FileUpload from "./FileUpload.vue";

const chat = useChatStore();
const text = ref("");
const files = ref([]);
const textarea = ref(null);
const isDraggingOver = ref(false);
const webSearchEnabled = ref(false);
let dragDepth = 0;

async function resize() {
  await nextTick();
  if (!textarea.value) return;
  textarea.value.style.height = "auto";
  textarea.value.style.height = `${Math.min(textarea.value.scrollHeight, 200)}px`;
}

function removeFile(index) {
  files.value.splice(index, 1);
}

async function send() {
  const value = text.value.trim();
  if (!value && files.value.length === 0) return;
  if (chat.streaming) return;

  const pendingFiles = files.value;
  text.value = "";
  files.value = [];
  resize();

  if (pendingFiles.length > 0) {
    await chat.sendMessageWithFiles(value, pendingFiles, webSearchEnabled.value);
  } else {
    await chat.sendMessage(value, webSearchEnabled.value);
  }
}

function onKeydown(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    send();
  }
}

function onDragEnter() {
  dragDepth++;
  isDraggingOver.value = true;
}

function onDragLeave() {
  dragDepth = Math.max(0, dragDepth - 1);
  if (dragDepth === 0) isDraggingOver.value = false;
}

function onDrop(event) {
  dragDepth = 0;
  isDraggingOver.value = false;
  const dropped = Array.from(event.dataTransfer?.files || []);
  if (dropped.length) {
    files.value = [...files.value, ...dropped];
  }
}
</script>

<template>
  <div class="input-bar">
    <div class="column">
      <div
        class="composer"
        :class="{ dragging: isDraggingOver }"
        @dragenter.prevent="onDragEnter"
        @dragover.prevent
        @dragleave.prevent="onDragLeave"
        @drop.prevent="onDrop"
      >
        <div v-if="isDraggingOver" class="drop-hint">Отпустите файлы, чтобы прикрепить</div>
        <div v-if="files.length" class="file-chips">
          <span v-for="(file, i) in files" :key="i" class="chip">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" />
              <path d="M14 2v6h6" />
            </svg>
            {{ file.name }}
            <button type="button" @click="removeFile(i)">×</button>
          </span>
        </div>
        <div class="row">
          <FileUpload :files="files" @update:files="(v) => (files = v)" />
          <textarea
            ref="textarea"
            v-model="text"
            placeholder="Напишите сообщение..."
            rows="1"
            :disabled="chat.streaming"
            @input="resize"
            @keydown="onKeydown"
          />
          <button class="send" :disabled="chat.streaming || (!text.trim() && files.length === 0)" @click="send">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          </button>
        </div>
      </div>
      <div class="below-composer">
        <button
          type="button"
          class="web-search-toggle"
          :class="{ active: webSearchEnabled }"
          :aria-pressed="webSearchEnabled"
          @click="webSearchEnabled = !webSearchEnabled"
        >
          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="2" y1="12" x2="22" y2="12" />
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
          </svg>
          Поиск в интернете
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.input-bar {
  padding: 0.75rem 1.5rem 1.25rem;
}

.column {
  max-width: 46rem;
  margin: 0 auto;
}

.composer {
  position: relative;
  background: var(--input-bg);
  border: 1px solid var(--border);
  border-radius: 22px;
  box-shadow: var(--shadow-md);
  padding: 0.5rem 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  transition: border-color 0.15s, background 0.15s;
}

.composer.dragging {
  border-color: var(--accent);
  border-style: dashed;
  background: var(--bg-tertiary);
}

.drop-hint {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 22px;
  background: var(--input-bg);
  color: var(--accent);
  font-size: 0.85rem;
  font-weight: 500;
  pointer-events: none;
  z-index: 1;
}

.file-chips {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
  padding: 0.3rem 0.4rem 0;
}

.chip {
  background: var(--bg-tertiary);
  color: var(--text);
  border-radius: 10px;
  padding: 0.3rem 0.55rem;
  font-size: 0.78rem;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  max-width: 12rem;
}

.chip svg {
  flex-shrink: 0;
  color: var(--text-secondary);
}

.chip button {
  border: none;
  background: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  padding: 0;
}

.row {
  display: flex;
  align-items: flex-end;
  gap: 0.35rem;
}

textarea {
  flex: 1;
  resize: none;
  border: none;
  background: transparent;
  color: var(--text);
  padding: 0.45rem 0.1rem;
  font-family: inherit;
  font-size: 0.95rem;
  line-height: 1.4;
  max-height: 200px;
}

textarea:focus {
  outline: none;
}

textarea::placeholder {
  color: var(--text-secondary);
}

.send {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: none;
  background: var(--accent);
  color: var(--accent-text);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}

.send:hover:not(:disabled) {
  background: var(--accent-hover);
}

.send:disabled {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  cursor: not-allowed;
}

.below-composer {
  display: flex;
  padding: 0.45rem 0.2rem 0;
}

.web-search-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.8rem;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.web-search-toggle:hover {
  background: var(--bg-tertiary);
}

.web-search-toggle.active {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--accent-text);
}
</style>
