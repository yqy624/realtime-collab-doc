<template>
  <section class="chat-card">
    <header class="chat-header">
      <div>
        <h3>实时聊天</h3>
        <p>消息与当前文档绑定</p>
      </div>
      <span v-if="unreadMentions > 0" class="mention-badge">{{ unreadMentions }} 条提及</span>
    </header>
    <div ref="messageBox" class="messages">
      <article
        v-for="message in sortedMessages"
        :key="message.id ?? message.createdAt"
        class="message"
        :class="{ 'is-mentioned': isMentionedMessage(message.message, message.senderName) }"
      >
        <img v-if="message.senderAvatar" :src="message.senderAvatar" :alt="message.senderName" class="avatar image-avatar" />
        <div v-else class="avatar">{{ (message.senderName || "?").slice(0, 1).toUpperCase() }}</div>
        <div class="bubble">
          <div class="bubble-head">
            <strong>{{ message.senderName }}</strong>
            <span v-if="isMentionedMessage(message.message, message.senderName)" class="mentioned-you">提到了你</span>
          </div>
          <p v-html="renderMessage(message.message)"></p>
        </div>
      </article>
    </div>
    <form class="chat-form" @submit.prevent="submit">
      <div class="composer">
        <textarea
          ref="composerRef"
          v-model="draft"
          rows="3"
          placeholder="输入消息，支持 @用户 提醒"
          @input="handleDraftInput"
          @keydown="handleKeydown"
          @focus="handleFocus"
        />
        <div v-if="mentionState.open" class="mention-menu">
          <button
            v-for="(user, index) in filteredMentionUsers"
            :key="user"
            type="button"
            class="mention-option"
            :class="{ active: index === mentionState.activeIndex }"
            @mousedown.prevent="applyMention(user)"
          >
            <span class="mention-option-name">@{{ user }}</span>
            <span class="mention-option-meta">在线成员</span>
          </button>
          <div v-if="filteredMentionUsers.length === 0" class="mention-empty">没有匹配的在线成员</div>
        </div>
      </div>
      <button class="send" type="submit">发送</button>
    </form>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";

interface ChatMessageItem {
  id?: number;
  senderName: string;
  senderAvatar?: string;
  message: string;
  createdAt?: string;
}

const props = defineProps<{
  messages: ChatMessageItem[];
  onlineUsers: string[];
  currentUsername?: string;
  unreadMentions?: number;
}>();

const emit = defineEmits<{
  (e: "send", value: string): void;
  (e: "chat-focus"): void;
}>();

const draft = ref("");
const messageBox = ref<HTMLDivElement | null>(null);
const composerRef = ref<HTMLTextAreaElement | null>(null);
const mentionState = ref({
  open: false,
  query: "",
  start: -1,
  end: -1,
  activeIndex: 0
});

const sortedMessages = computed(() => [...props.messages].sort((left, right) => {
  const leftTime = left.createdAt ? new Date(left.createdAt).getTime() : 0;
  const rightTime = right.createdAt ? new Date(right.createdAt).getTime() : 0;
  return leftTime - rightTime;
}));

const availableMentionUsers = computed(() => {
  const current = (props.currentUsername || "").trim().toLowerCase();
  return props.onlineUsers.filter((user) => user.trim().toLowerCase() !== current);
});

const filteredMentionUsers = computed(() => {
  if (!mentionState.value.query) {
    return availableMentionUsers.value;
  }
  const query = mentionState.value.query.toLowerCase();
  return availableMentionUsers.value.filter((user) => user.toLowerCase().startsWith(query));
});

const submit = () => {
  const value = draft.value.trim();
  if (!value) {
    return;
  }
  emit("send", value);
  draft.value = "";
  closeMentionMenu();
};

const escapeHtml = (value: string) => value
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#39;");

const renderMessage = (value: string) => escapeHtml(value).replace(/(^|\s)(@[\w一-龥-]+)/g, '$1<span class="mention">$2</span>');

const buildMentionPattern = () => {
  const username = (props.currentUsername || "").trim();
  if (!username) return null;
  return new RegExp(`(^|\\s)@${username.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?=$|\\s|[，。！？,.!?])`, "i");
};

const isMentionedMessage = (value: string, senderName: string) => {
  if (!props.currentUsername || senderName === props.currentUsername) {
    return false;
  }
  const pattern = buildMentionPattern();
  return pattern ? pattern.test(value) : false;
};

const closeMentionMenu = () => {
  mentionState.value = {
    open: false,
    query: "",
    start: -1,
    end: -1,
    activeIndex: 0
  };
};

const updateMentionState = () => {
  const textarea = composerRef.value;
  if (!textarea) return;

  const cursor = textarea.selectionStart ?? draft.value.length;
  const beforeCursor = draft.value.slice(0, cursor);
  const mentionMatch = beforeCursor.match(/(?:^|\s)@([\w一-龥-]*)$/);
  if (!mentionMatch) {
    closeMentionMenu();
    return;
  }

  const fullMatch = mentionMatch[0];
  const query = mentionMatch[1] || "";
  const atIndex = cursor - fullMatch.length + fullMatch.lastIndexOf("@");
  mentionState.value = {
    open: true,
    query,
    start: atIndex,
    end: cursor,
    activeIndex: 0
  };
};

const applyMention = (username: string) => {
  const textarea = composerRef.value;
  if (!textarea || mentionState.value.start < 0 || mentionState.value.end < 0) {
    return;
  }

  const before = draft.value.slice(0, mentionState.value.start);
  const after = draft.value.slice(mentionState.value.end);
  draft.value = `${before}@${username} ${after}`;
  closeMentionMenu();

  nextTick(() => {
    if (!textarea) return;
    const nextCursor = before.length + username.length + 2;
    textarea.focus();
    textarea.setSelectionRange(nextCursor, nextCursor);
  });
};

const handleDraftInput = () => {
  updateMentionState();
};

const handleKeydown = (event: KeyboardEvent) => {
  if (!mentionState.value.open) {
    return;
  }

  if (event.key === "ArrowDown") {
    event.preventDefault();
    if (filteredMentionUsers.value.length === 0) return;
    mentionState.value.activeIndex = (mentionState.value.activeIndex + 1) % filteredMentionUsers.value.length;
    return;
  }

  if (event.key === "ArrowUp") {
    event.preventDefault();
    if (filteredMentionUsers.value.length === 0) return;
    mentionState.value.activeIndex = (mentionState.value.activeIndex - 1 + filteredMentionUsers.value.length) % filteredMentionUsers.value.length;
    return;
  }

  if (event.key === "Enter" || event.key === "Tab") {
    if (filteredMentionUsers.value.length === 0) {
      return;
    }
    event.preventDefault();
    applyMention(filteredMentionUsers.value[mentionState.value.activeIndex]);
    return;
  }

  if (event.key === "Escape") {
    event.preventDefault();
    closeMentionMenu();
  }
};

const handleFocus = async () => {
  emit("chat-focus");
  await nextTick();
  const el = messageBox.value;
  if (el) {
    el.scrollTop = el.scrollHeight;
  }
};

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

defineExpose({
  focusComposer: () => {
    composerRef.value?.focus();
  },
  scrollToLatest: async () => {
    await nextTick();
    const el = messageBox.value;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }
});
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

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

header h3 {
  margin: 0;
}

header p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.mention-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 6px 10px;
  background: #fef3c7;
  color: #92400e;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
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

.message.is-mentioned .bubble {
  border-color: rgba(124, 58, 237, 0.35);
  background: linear-gradient(180deg, #faf5ff 0%, #f8fafc 100%);
  box-shadow: inset 0 0 0 1px rgba(124, 58, 237, 0.08);
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

.bubble-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bubble strong {
  font-size: 13px;
}

.mentioned-you {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 2px 8px;
  background: #ede9fe;
  color: #6d28d9;
  font-size: 11px;
  font-weight: 700;
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

.composer {
  position: relative;
}

textarea {
  width: 100%;
  border-radius: 16px;
  border: 1px solid var(--line);
  padding: 12px 14px;
  resize: vertical;
}

.mention-menu {
  position: absolute;
  left: 0;
  right: 0;
  bottom: calc(100% + 8px);
  display: grid;
  gap: 4px;
  padding: 8px;
  border-radius: 16px;
  border: 1px solid var(--line);
  background: #fff;
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.12);
  z-index: 10;
}

.mention-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: none;
  border-radius: 12px;
  background: transparent;
  padding: 10px 12px;
  cursor: pointer;
  text-align: left;
}

.mention-option:hover,
.mention-option.active {
  background: #eff6ff;
}

.mention-option-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
}

.mention-option-meta,
.mention-empty {
  font-size: 12px;
  color: var(--muted);
}

.mention-empty {
  padding: 10px 12px;
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
