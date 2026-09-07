<script setup>
import { t } from "../i18n";

defineProps({
  toolStatus: { type: Object, default: null },
});

function toolLabel(tool) {
  const key = `tool.${tool}`;
  const label = t(key);
  return label === key ? t("tool.calling", { tool }) : label;
}
</script>

<template>
  <div v-if="toolStatus" class="pill">
    <span class="dot" />
    {{ toolLabel(toolStatus.tool) }}
  </div>
</template>

<style scoped>
.pill {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.8rem;
  border-radius: 999px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: 0.82rem;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  animation: pulse 1.1s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 0.35;
    transform: scale(0.85);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}
</style>
