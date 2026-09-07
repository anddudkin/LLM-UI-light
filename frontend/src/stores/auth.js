import { defineStore } from "pinia";
import { login } from "../api/client";

const STORAGE_KEY = "app_llm_user";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    userId: null,
    email: null,
    ready: false,
    error: null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.email,
  },
  actions: {
    loadFromStorage() {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const { userId, email } = JSON.parse(raw);
        this.userId = userId;
        this.email = email;
      }
    },
    persist() {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ userId: this.userId, email: this.email }));
    },
    // Called once on app bootstrap. If the URL carries ?user_info=... (the
    // encrypted email from the company platform's /api/sso redirect), exchange
    // it for a user via /api/login. Otherwise fall back to a previously stored
    // login.
    async initAuth() {
      const params = new URLSearchParams(window.location.search);
      const userInfo = params.get("user_info");

      if (userInfo) {
        try {
          const { user_id, email } = await login(userInfo);
          this.userId = user_id;
          this.email = email;
          this.persist();
        } catch (e) {
          this.error = e?.message || "Не удалось выполнить вход.";
        } finally {
          // Strip user_info even on failure — otherwise a reload resubmits the
          // same broken token and reproduces the same error indefinitely.
          params.delete("user_info");
          const newSearch = params.toString();
          const newUrl = window.location.pathname + (newSearch ? `?${newSearch}` : "") + window.location.hash;
          window.history.replaceState({}, "", newUrl);
        }
      } else {
        this.loadFromStorage();
      }

      this.ready = true;
    },
  },
});
