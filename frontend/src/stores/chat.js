import { defineStore } from "pinia";
import {
  listConversations,
  createConversation,
  getMessages,
  streamChat,
  streamChatWithFiles,
  editMessage as editMessageRequest,
} from "../api/client";

export const useChatStore = defineStore("chat", {
  state: () => ({
    conversations: [],
    currentConversationId: null,
    messages: [],
    streaming: false,
    streamingText: "",
    toolStatus: null,
    error: null,
    _creatingConversation: null,
  }),
  actions: {
    async fetchConversations() {
      this.conversations = await listConversations();
    },

    async newConversation() {
      if (this.currentConversationId && this.messages.length === 0) {
        return this.conversations.find((c) => c.id === this.currentConversationId);
      }
      if (this._creatingConversation) return this._creatingConversation;

      const reusable = this.conversations.find((c) => c.title === "Новый чат");
      if (reusable) {
        await this.selectConversation(reusable.id);
        return reusable;
      }

      this._creatingConversation = (async () => {
        const conversation = await createConversation();
        this.conversations.unshift(conversation);
        await this.selectConversation(conversation.id);
        return conversation;
      })();

      try {
        return await this._creatingConversation;
      } finally {
        this._creatingConversation = null;
      }
    },

    async selectConversation(id) {
      this.currentConversationId = id;
      this.messages = await getMessages(id);
      this.error = null;
    },

    async _ensureConversation() {
      if (this.currentConversationId) return this.currentConversationId;
      const conversation = await this.newConversation();
      return conversation.id;
    },

    _handleEvent(event) {
      if (event.type === "token") {
        this.streamingText += event.content;
      } else if (event.type === "tool_call_start") {
        this.streamingText = "";
        this.toolStatus = { tool: event.tool, query: event.query };
      } else if (event.type === "tool_result") {
        this.toolStatus = null;
      } else if (event.type === "error") {
        this.error = event.message;
      } else if (event.type === "title") {
        const conversation = this.conversations.find((c) => c.id === this.currentConversationId);
        if (conversation) conversation.title = event.title;
      }
    },

    async sendMessage(text, forceWebSearch = false) {
      const conversationId = await this._ensureConversation();

      this.messages.push({ role: "user", content: text });
      this.streaming = true;
      this.streamingText = "";
      this.toolStatus = null;
      this.error = null;

      let result;
      try {
        result = await streamChat({
          conversationId,
          message: text,
          forceWebSearch,
          onEvent: (event) => this._handleEvent(event),
        });
      } catch (e) {
        result = { ok: false, message: e?.message || "Не удалось связаться с сервером." };
      }

      await this._finishStream(result);
    },

    async editMessage(messageId, newText) {
      const conversationId = this.currentConversationId;
      if (!conversationId || this.streaming) return;

      const index = this.messages.findIndex((m) => m.id === messageId);
      if (index === -1) return;

      this.messages = this.messages.slice(0, index);
      this.messages.push({ id: messageId, role: "user", content: newText });
      this.streaming = true;
      this.streamingText = "";
      this.toolStatus = null;
      this.error = null;

      let result;
      try {
        result = await editMessageRequest({
          conversationId,
          messageId,
          message: newText,
          onEvent: (event) => this._handleEvent(event),
        });
      } catch (e) {
        result = { ok: false, message: e?.message || "Не удалось связаться с сервером." };
      }

      await this._finishStream(result);
    },

    async sendMessageWithFiles(text, files, forceWebSearch = false) {
      const conversationId = await this._ensureConversation();

      this.messages.push({ role: "user", content: text || `[Отправлено ${files.length} файл(ов)]` });
      this.streaming = true;
      this.streamingText = "";
      this.toolStatus = null;
      this.error = null;

      let result;
      try {
        result = await streamChatWithFiles({
          conversationId,
          message: text,
          files,
          forceWebSearch,
          onEvent: (event) => this._handleEvent(event),
        });
      } catch (e) {
        result = { ok: false, message: e?.message || "Не удалось связаться с сервером." };
      }

      await this._finishStream(result);
    },

    async _finishStream(result) {
      if (!result.ok) {
        this.error = result.message || `Ошибка запроса (${result.status})`;
      } else if (this.currentConversationId) {
        // Re-fetch so locally-added messages (pushed without an id) pick up the
        // server-assigned ids that editing a message later needs to target.
        try {
          this.messages = await getMessages(this.currentConversationId);
        } catch (e) {
          // Keep the optimistically accumulated messages if the refresh fails.
        }
      }
      this.streaming = false;
      this.streamingText = "";
      this.toolStatus = null;
    },
  },
});
