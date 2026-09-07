<script setup>
import { onMounted } from "vue";
import { useAuthStore } from "./stores/auth";
import { t } from "./i18n";

const auth = useAuthStore();

onMounted(() => {
  auth.initAuth();
});
</script>

<template>
  <div v-if="!auth.ready" class="centered">
    <div class="spinner" />
  </div>
  <div v-else-if="!auth.isAuthenticated" class="centered">
    <div class="card">
      <div class="logo">✦</div>
      <h1>{{ auth.error ? t("app.loginFailedTitle") : t("app.welcomeTitle") }}</h1>
      <p>{{ auth.error || t("app.welcomeBody") }}</p>
    </div>
  </div>
  <router-view v-else />
</template>

<style scoped>
.centered {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 2rem;
  background: var(--bg-secondary);
}

.card {
  text-align: center;
  max-width: 22rem;
  padding: 2.5rem 2rem;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-md);
}

.logo {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--accent);
  color: var(--accent-text);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  margin: 0 auto 1.25rem;
}

.card h1 {
  font-size: 1.15rem;
  margin: 0 0 0.5rem;
  color: var(--text);
}

.card p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.5;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
