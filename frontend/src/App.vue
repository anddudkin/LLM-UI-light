<script setup>
import { onMounted } from "vue";
import { useAuthStore } from "./stores/auth";
import LoginForm from "./components/LoginForm.vue";

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
    <LoginForm />
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
