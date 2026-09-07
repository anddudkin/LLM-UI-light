<script setup>
const props = defineProps({
  files: { type: Array, required: true },
});

const emit = defineEmits(["update:files"]);

function onChange(event) {
  emit("update:files", [...props.files, ...event.target.files]);
  event.target.value = "";
}
</script>

<template>
  <label class="attach-btn" title="Прикрепить файл">
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21.44 11.05 12.25 20.24a5 5 0 0 1-7.07-7.07l9.19-9.19a3.5 3.5 0 0 1 4.95 4.95L9.88 18.36a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    </svg>
    <input type="file" multiple accept=".pdf,.docx" @change="onChange" hidden />
  </label>
</template>

<style scoped>
.attach-btn {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 0.15s;
}

.attach-btn:hover {
  background: var(--bg-tertiary);
}
</style>
