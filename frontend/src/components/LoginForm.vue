<script setup>
import { ref } from "vue";
import { useAuthStore } from "../stores/auth";
import { t } from "../i18n";

const auth = useAuthStore();

const mode = ref("login"); // "login" | "register"
const email = ref("");
const password = ref("");
const submitting = ref(false);
const localError = ref(null);

function toggleMode() {
  mode.value = mode.value === "login" ? "register" : "login";
  localError.value = null;
}

async function onSubmit() {
  localError.value = null;
  submitting.value = true;
  try {
    if (mode.value === "login") {
      await auth.loginWithPassword(email.value, password.value);
    } else {
      await auth.register(email.value, password.value);
    }
  } catch (e) {
    localError.value = e?.message || t("errors.loginFailed");
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="card">
    <div class="logo">✦</div>
    <h1>{{ mode === "login" ? t("auth.loginTitle") : t("auth.registerTitle") }}</h1>
    <p v-if="auth.error" class="ssoError">{{ auth.error }}</p>

    <form @submit.prevent="onSubmit">
      <input
        v-model="email"
        type="email"
        autocomplete="email"
        :placeholder="t('auth.emailPlaceholder')"
        required
      />
      <input
        v-model="password"
        type="password"
        :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
        :placeholder="t('auth.passwordPlaceholder')"
        minlength="8"
        required
      />
      <p v-if="localError" class="error">{{ localError }}</p>
      <button type="submit" :disabled="submitting">
        {{ submitting ? t("auth.submitting") : mode === "login" ? t("auth.loginButton") : t("auth.registerButton") }}
      </button>
    </form>

    <button type="button" class="switchMode" @click="toggleMode">
      {{ mode === "login" ? t("auth.switchToRegister") : t("auth.switchToLogin") }}
    </button>
  </div>
</template>

<style scoped>
.card {
  text-align: center;
  max-width: 22rem;
  width: 100%;
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
  margin: 0 0 1rem;
  color: var(--text);
}

.ssoError {
  margin: 0 0 1rem;
  color: var(--text-secondary);
  font-size: 0.85rem;
  line-height: 1.5;
}

form {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

input {
  width: 100%;
  padding: 0.65rem 0.85rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-secondary);
  color: var(--text);
  font-size: 0.9rem;
  box-sizing: border-box;
}

input:focus {
  outline: none;
  border-color: var(--accent);
}

.error {
  margin: 0;
  color: #d33;
  font-size: 0.85rem;
  text-align: left;
}

button[type="submit"] {
  margin-top: 0.25rem;
  padding: 0.65rem;
  border: none;
  border-radius: var(--radius);
  background: var(--accent);
  color: var(--accent-text);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
}

button[type="submit"]:disabled {
  opacity: 0.6;
  cursor: default;
}

.switchMode {
  margin-top: 1rem;
  border: none;
  background: none;
  color: var(--accent);
  font-size: 0.85rem;
  cursor: pointer;
  padding: 0;
}
</style>
