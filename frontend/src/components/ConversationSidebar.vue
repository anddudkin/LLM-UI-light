<script setup>
import { onMounted } from "vue";
import { useChatStore } from "../stores/chat";
import { t, locale, setLocale } from "../i18n";

const chat = useChatStore();

onMounted(() => {
  chat.fetchConversations();
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

    <div class="lang-switch" role="group">
      <button
        type="button"
        :class="{ active: locale === 'en' }"
        :aria-pressed="locale === 'en'"
        @click="setLocale('en')"
      >
        EN
      </button>
      <button
        type="button"
        :class="{ active: locale === 'ru' }"
        :aria-pressed="locale === 'ru'"
        @click="setLocale('ru')"
      >
        RU
      </button>
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
  display: flex;
  gap: 0.25rem;
  padding: 0.5rem 0.4rem 0.15rem;
  margin-top: auto;
  border-top: 1px solid var(--border);
}

.lang-switch button {
  flex: 1;
  padding: 0.35rem 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.lang-switch button:hover {
  background: var(--bg-tertiary);
}

.lang-switch button.active {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--accent-text);
}
</style>
