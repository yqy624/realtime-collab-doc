<template>
  <section class="history-viewer">
    <header class="viewer-header">
      <div>
        <p class="eyebrow">{{ kindLabel }}</p>
        <h2>{{ title }}</h2>
        <p class="subtext">{{ subtitle }}</p>
      </div>
      <button class="back-btn" type="button" @click="$emit('back')">返回文档</button>
    </header>

    <div v-if="items.length === 0" class="empty-state">暂无聊天记录</div>
    <div v-else class="timeline">
      <article
        v-for="item in items"
        :key="item.id"
        class="timeline-item"
        :class="{ selected: item.id === selectedId, assistant: item.role !== 'user' }"
      >
        <div class="avatar">{{ item.actor.slice(0, 1).toUpperCase() }}</div>
        <div class="bubble">
          <div class="bubble-head">
            <strong>{{ item.actor }}</strong>
            <span>{{ item.label }}</span>
            <time v-if="item.createdAt">{{ formatDate(item.createdAt) }}</time>
          </div>
          <p>{{ item.content }}</p>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

interface HistoryViewerItem {
  id: string;
  actor: string;
  role: "user" | "assistant" | "agent" | "system";
  label: string;
  content: string;
  createdAt?: string;
}

const props = defineProps<{
  title: string;
  subtitle: string;
  kind: "user" | "ai";
  selectedId?: string;
  items: HistoryViewerItem[];
}>();

defineEmits<{
  (e: "back"): void;
}>();

const kindLabel = computed(() =>
  props.kind === "user" ? "用户之间历史聊天记录" : "AI 助手 / Agent 历史聊天记录"
);

const formatDate = (dateStr: string) =>
  new Date(dateStr).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
</script>

<style scoped>
.history-viewer {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 620px;
  border: 1px solid var(--line);
  border-radius: 24px;
  background: var(--panel);
  overflow: hidden;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.05);
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 22px 24px;
  border-bottom: 1px solid var(--line);
}

.viewer-header h2 {
  margin: 4px 0 0;
  font-size: 22px;
}

.eyebrow {
  margin: 0;
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
}

.subtext {
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.back-btn {
  align-self: start;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  padding: 8px 12px;
  font-size: 13px;
}

.back-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.empty-state {
  display: grid;
  place-items: center;
  color: var(--muted);
  min-height: 360px;
}

.timeline {
  display: grid;
  align-content: start;
  gap: 12px;
  overflow: auto;
  padding: 24px;
}

.timeline-item {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}

.avatar {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 700;
}

.bubble {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #f8fafc;
  padding: 12px 14px;
}

.timeline-item.assistant .bubble {
  background: #f0fdf4;
}

.timeline-item.selected .bubble {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}

.bubble-head {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 12px;
}

.bubble-head strong {
  color: var(--ink);
  font-size: 13px;
}

.bubble-head time {
  margin-left: auto;
}

.bubble p {
  margin: 8px 0 0;
  white-space: pre-wrap;
  line-height: 1.65;
}
</style>
