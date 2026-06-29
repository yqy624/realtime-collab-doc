<template>
  <section class="chat-card">
    <header>
      <h3>实时聊天</h3>
      <p>消息与当前文档绑定</p>
    </header>
    <div ref="messageBox" class="messages">
      <article v-for="message in sortedMessages" :key="message.id ?? message.createdAt" class="message">
        <img v-if="message.senderAvatar" :src="message.senderAvatar" :alt="message.senderName" class="avatar image-avatar" />
        <div v-else class="avatar">{{ (message.senderName || "?").slice(0, 1).toUpperCase() }}</div>
        <div class="bubble">
          <strong>{{ message.senderName }}</strong>
          <p v-html="renderMessage(message.message)"></p>
        </div>
      </article>
    </div>
    <form class="chat-form" @submit.prevent="submit">
      <textarea
        v-model="draft"
        rows="3"
        placeholder="输入消息，支持 @用户 提醒"
      />
      <button class="send" type="submit">发送</button>
    </form>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";

const props = defineProps<{
  messages: Array<{ id?: number; senderName: string; senderAvatar?: string; message: string; createdAt?: string }>;
}>();

const emit = defineEmits<{
  (e: "send", value: string): void;
}>();

const draft = ref("");
const messageBox = ref<HTMLDivElement | null>(null);

const sortedMessages = computed(() => [...props.messages].sort((left, right) => {
  const leftTime = left.createdAt ? new Date(left.createdAt).getTime() : 0;
  const rightTime = right.createdAt ? new Date(right.createdAt).getTime() : 0;
  return leftTime - rightTime;
}));

const submit = () => {
  const value = draft.value.trim();
  if (!value) {
    return;
  }
  emit("send", value);
  draft.value = "";
};

const escapeHtml = (value: string) => value
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#39;");

const renderMessage = (value: string) => escapeHtml(value).replace(/(^|\s)(@[\w一-龥-]+)/g, '$1<span class="mention">$2</span>');

watch(
  () => sortedMessages.value.length,
  async () => {
    await nextTick();
    const el = messageBox.value;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }
);
</script>

<style scoped>
.chat-card {
  display: grid;
  grid-template-rows: auto 1fr auto;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 24px;
  padding: 20px;
  min-height: 0;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.05);
}

header h3 {
  margin: 0;
}

header p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.messages {
  overflow: auto;
  display: grid;
  gap: 12px;
  padding: 18px 0;
}

.message {
  display: grid;
  grid-template-columns: 40px 1fr;
  gap: 12px;
  align-items: start;
}

.avatar {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 700;
}

.image-avatar {
  object-fit: cover;
  background: #fff;
}

.bubble {
  background: #f8fafc;
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 12px 14px;
}

.bubble strong {
  font-size: 13px;
}

.bubble p {
  margin: 6px 0 0;
  white-space: pre-wrap;
}

.bubble :deep(.mention) {
  color: #7c3aed;
  font-weight: 700;
  background: #f3e8ff;
  padding: 0 4px;
  border-radius: 999px;
}

.chat-form {
  display: grid;
  gap: 10px;
}

textarea {
  width: 100%;
  border-radius: 16px;
  border: 1px solid var(--line);
  padding: 12px 14px;
  resize: vertical;
}

.send {
  justify-self: end;
  border: none;
  border-radius: 999px;
  padding: 10px 18px;
  background: var(--accent);
  color: white;
  cursor: pointer;
}
</style>
