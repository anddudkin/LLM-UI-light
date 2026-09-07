<script setup>
import { useChatStore } from "../stores/chat";
import ConversationSidebar from "../components/ConversationSidebar.vue";
import MessageList from "../components/MessageList.vue";
import MessageInput from "../components/MessageInput.vue";
import { t } from "../i18n";

const chat = useChatStore();
</script>

<template>
  <div class="layout">
    <ConversationSidebar />
    <div class="main">
      <div v-if="chat.messages.length === 0" class="welcome">
        <div class="welcome-inner">
          <div class="welcome-logo">✦</div>
          <h1>{{ t("chat.greeting") }}</h1>
          <div class="welcome-input">
            <MessageInput />
          </div>
        </div>
      </div>
      <template v-else>
        <MessageList
          :conversation-id="chat.currentConversationId"
          :messages="chat.messages"
          :streaming="chat.streaming"
          :streaming-text="chat.streamingText"
          :tool-status="chat.toolStatus"
          :error="chat.error"
          @edit-message="({ id, content }) => chat.editMessage(id, content)"
        />
        <MessageInput />
      </template>
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  background: var(--bg);
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.welcome {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 1.5rem;
}

.welcome-inner {
  width: 100%;
  max-width: 44rem;
  text-align: center;
}

.welcome-logo {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: var(--accent);
  color: var(--accent-text);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
  margin: 0 auto 1.25rem;
}

.welcome-inner h1 {
  font-size: 1.6rem;
  font-weight: 600;
  color: var(--text);
  margin: 0 0 1.75rem;
}

.welcome-input :deep(.input-bar) {
  border-top: none;
  padding: 0;
}
</style>
