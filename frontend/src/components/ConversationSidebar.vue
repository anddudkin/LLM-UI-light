<script setup>
import { onMounted, onBeforeUnmount, ref } from "vue";
import { useChatStore } from "../stores/chat";
import { t, locale, setLocale } from "../i18n";

const chat = useChatStore();

const localeOptions = [
  { code: "en", label: "English" },
  { code: "ru", label: "Русский" },
];

const langMenuOpen = ref(false);
const langSwitchEl = ref(null);

function toggleLangMenu() {
  langMenuOpen.value = !langMenuOpen.value;
}

function selectLocale(code) {
  setLocale(code);
  langMenuOpen.value = false;
}

function onDocumentClick(event) {
  if (langSwitchEl.value && !langSwitchEl.value.contains(event.target)) {
    langMenuOpen.value = false;
  }
}

onMounted(() => {
  chat.fetchConversations();
  document.addEventListener("click", onDocumentClick);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", onDocumentClick);
});
</script>

<template>
  <aside class="sidebar">
    <div class="brand">
      <span class="logo">✦</span>
      <span class="brand-name">{{ t("chat.brand") }}</span>
    </div>

    <button class="new-chat" @click="chat.newConversation()">
      <svg class="new-chat-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <path d="M12 5v14M5 12h14" />
      </svg>
      <span class="new-chat-label">{{ t("chat.newChat") }}</span>
    </button>

    <div class="list-label" v-if="chat.conversations.length">{{ t("chat.chats") }}</div>
    <ul class="list">
      <li
        v-for="conversation in chat.conversations"
        :key="conversation.id"
        :class="{ active: conversation.id === chat.currentConversationId }"
        :title="conversation.title"
        @click="chat.selectConversation(conversation.id)"
      >
        {{ conversation.title }}
      </li>
    </ul>

    <div class="lang-switch" ref="langSwitchEl">
      <button
        type="button"
        class="lang-trigger"
        :aria-expanded="langMenuOpen"
        :title="t('chat.language')"
        @click="toggleLangMenu"
      >
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10" />
          <path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20" />
        </svg>
      </button>
      <ul v-if="langMenuOpen" class="lang-menu" role="menu">
        <li v-for="option in localeOptions" :key="option.code">
          <button
            type="button"
            :class="{ active: locale === option.code }"
            :aria-pressed="locale === option.code"
            @click="selectLocale(option.code)"
          >
            {{ option.label }}
          </button>
        </li>
      </ul>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 260px;
  flex-shrink: 0;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 0.75rem;
  gap: 0.5rem;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.4rem 0.6rem;
  color: var(--text);
  font-weight: 600;
  font-size: 0.95rem;
}

.brand .logo {
  width: 24px;
  height: 24px;
  border-radius: 7px;
  background: var(--accent);
  color: var(--accent-text);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
}

.new-chat {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--bg);
  color: var(--text);
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  box-shadow: var(--shadow-sm);
  transition: background 0.15s, box-shadow 0.15s, transform 0.15s;
}

.new-chat-icon {
  position: absolute;
  left: 0.75rem;
}

.new-chat:hover {
  background: var(--bg-tertiary);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.list-label {
  color: var(--text-secondary);
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.75rem 0.5rem 0.15rem;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
  scrollbar-color: transparent transparent;
}

.sidebar:hover .list {
  scrollbar-color: var(--border) transparent;
}

.list::-webkit-scrollbar {
  width: 8px;
}

.list::-webkit-scrollbar-track {
  background: transparent;
}

.list::-webkit-scrollbar-thumb {
  background-color: transparent;
  border-radius: 8px;
}

.sidebar:hover .list::-webkit-scrollbar-thumb {
  background-color: var(--border);
}

.list li {
  display: flex;
  align-items: center;
  min-height: 2.1rem;
  padding: 0 0.6rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.85rem;
  line-height: 1.3;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: background 0.15s;
}

.list li:hover {
  background: var(--bg-tertiary);
}

.list li.active {
  background: var(--bg-tertiary);
  font-weight: 600;
}

.lang-switch {
  position: relative;
  padding: 0.5rem 0.4rem 0.15rem;
  margin-top: auto;
  border-top: 1px solid var(--border);
}

.lang-trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--bg);
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.lang-trigger:hover,
.lang-trigger[aria-expanded="true"] {
  background: var(--bg-tertiary);
  color: var(--text);
}

.lang-menu {
  position: absolute;
  bottom: calc(100% + 0.35rem);
  left: 0.4rem;
  min-width: 9rem;
  list-style: none;
  margin: 0;
  padding: 0.3rem;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: var(--shadow-md);
  z-index: 10;
}

.lang-menu button {
  display: block;
  width: 100%;
  padding: 0.4rem 0.55rem;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text);
  font-size: 0.82rem;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s;
}

.lang-menu button:hover {
  background: var(--bg-tertiary);
}

.lang-menu button.active {
  background: var(--accent);
  color: var(--accent-text);
}
</style>
