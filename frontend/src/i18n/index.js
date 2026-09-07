import { ref, watch } from "vue";
import en from "./locales/en";
import ru from "./locales/ru";

const messages = { en, ru };
const STORAGE_KEY = "app_llm_locale";
const DEFAULT_LOCALE = "en";

function detectInitialLocale() {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored && messages[stored] ? stored : DEFAULT_LOCALE;
}

export const locale = ref(detectInitialLocale());

function applyDocumentLocale(next) {
  document.documentElement.lang = next;
  document.title = t("chat.brand");
}

export function setLocale(next) {
  if (!messages[next]) return;
  locale.value = next;
  localStorage.setItem(STORAGE_KEY, next);
}

watch(locale, applyDocumentLocale, { immediate: true });

function resolve(dict, path) {
  return path.split(".").reduce((node, key) => (node == null ? undefined : node[key]), dict);
}

export function t(key, vars) {
  let str = resolve(messages[locale.value], key);
  if (str === undefined) str = resolve(messages[DEFAULT_LOCALE], key);
  if (str === undefined) return key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      str = str.replace(new RegExp(`\\{${name}\\}`, "g"), value);
    }
  }
  return str;
}
