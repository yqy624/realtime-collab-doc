<template>
  <section class="editor-card">
    <header class="editor-header">
      <input v-model="localTitle" class="title-input" @change="emitTitle" />
      <div class="meta">
        <span>{{ onlineUsers.length }} 人在线</span>
        <span>版本 {{ revision }}</span>
      </div>
    </header>

    <div class="editor-toolbar">
      <div class="toolbar-left">
        <button class="tool-btn save-btn" :class="saveStatusClass" @click="$emit('save')" :disabled="saveStatus === 'saving'">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
          </svg>
          <span v-if="saveStatus === 'saved'">已保存</span>
          <span v-else-if="saveStatus === 'saving'">保存中...</span>
          <span v-else>保存</span>
        </button>
        <span class="save-indicator" :class="saveStatusClass">
          <span v-if="saveStatus === 'saved'">已保存</span>
          <span v-else-if="saveStatus === 'unsaved'">未保存的改变</span>
          <span v-else>正在保存...</span>
        </span>
      </div>
      <div class="toolbar-right">
        <span class="word-count">{{ wordCount }} 字</span>
        <span class="char-count">{{ charCount }} 字符</span>
        <button class="tool-btn export-btn" @click="exportText" title="导出为.txt">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          <span>导出</span>
        </button>
      </div>
    </div>

    <div
      ref="editor"
      class="editor"
      contenteditable="true"
      @input="handleInput"
      @keyup="emitCursor"
      @mouseup="emitCursor"
    ></div>
    <footer v-if="remoteCursors.length" class="cursor-bar">
      <span v-for="cursor in remoteCursors" :key="cursor.userId" class="cursor-chip">
        {{ cursor.username }} 光标在{{ cursor.cursorPosition }}
      </span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import type { TextOperation } from "../utils/ot";

interface RemoteCursor {
  userId: number;
  username: string;
  cursorPosition: number;
}

const props = defineProps<{
  title: string;
  content: string;
  revision: number;
  saveStatus: "saved" | "saving" | "unsaved";
  onlineUsers: string[];
  remoteCursors: RemoteCursor[];
}>();

const emit = defineEmits<{
  (e: "title-change", value: string): void;
  (e: "content-change", payload: TextOperation): void;
  (e: "cursor-change", position: number): void;
  (e: "save"): void;
}>();

const editor = ref<HTMLDivElement | null>(null);
const localTitle = ref(props.title);
let lastContent = props.content;
let debounceTimer: number | null = null;

const wordCount = computed(() => {
  const text = editor.value?.innerText || props.content || "";
  const trimmed = text.trim();
  if (!trimmed) return 0;
  return trimmed.split(/\s+/).length;
});

const charCount = computed(() => {
  const text = editor.value?.innerText || props.content || "";
  return text.length;
});

const saveStatusClass = computed(() => "save-status-" + props.saveStatus);

const exportText = () => {
  const text = editor.value?.innerText || props.content || "";
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${localTitle.value || "document"}.txt`;
  a.click();
  URL.revokeObjectURL(url);
};

onMounted(() => {
  if (editor.value) {
    editor.value.innerText = props.content;
  }
});

watch(
  () => props.content,
  (value) => {
    if (editor.value && editor.value.innerText !== value) {
      editor.value.innerText = value;
    }
    lastContent = value;
  }
);

watch(
  () => props.title,
  (value) => {
    localTitle.value = value;
  }
);

const emitTitle = () => emit("title-change", localTitle.value);

const handleInput = () => {
  if (!editor.value) return;
  const current = editor.value.innerText;
  if (debounceTimer) window.clearTimeout(debounceTimer);
  debounceTimer = window.setTimeout(() => {
    const payload = createOperation(lastContent, current, props.revision);
    lastContent = current;
    emit("content-change", payload);
  }, 300);
  emitCursor();
};

const emitCursor = () => {
  if (!editor.value) return;
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0) return;
  const range = selection.getRangeAt(0);
  if (!editor.value.contains(range.startContainer)) return;
  const prefix = range.cloneRange();
  prefix.selectNodeContents(editor.value);
  prefix.setEnd(range.startContainer, range.startOffset);
  emit("cursor-change", prefix.toString().length);
};

const createOperation = (previous: string, current: string, revision: number): TextOperation => {
  if (current.length >= previous.length) {
    let position = 0;
    while (position < previous.length && previous[position] === current[position]) position++;
    return { type: "INSERT", position, content: current.slice(position, current.length - (previous.length - position)), revision };
  }
  let position = 0;
  while (position < current.length && previous[position] === current[position]) position++;
  return { type: "DELETE", position, length: previous.length - current.length, revision };
};
</script>

<style scoped>
.editor-card {
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 26px;
  min-height: 620px;
  overflow: hidden;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.05);
}
.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 22px;
  border-bottom: 1px solid var(--line);
  background: linear-gradient(180deg, #fffdf7 0%, #ffffff 100%);
}
.title-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 24px;
  font-weight: 700;
}
.meta {
  display: flex;
  gap: 14px;
  color: var(--muted);
  font-size: 13px;
}
.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 22px;
  border-bottom: 1px solid var(--line);
  background: #fafcff;
}
.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.tool-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
}
.tool-btn:hover {
  background: #f0f4ff;
  border-color: var(--accent);
}
.tool-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.save-btn.save-status-saved {
  border-color: #12b76a;
  color: #12b76a;
}
.save-btn.save-status-saved:hover {
  background: #f0fdf4;
}
.save-btn.save-status-saving {
  border-color: #f59e0b;
  color: #f59e0b;
}
.save-btn.save-status-unsaved {
  border-color: var(--accent);
  color: var(--accent);
}
.save-indicator {
  font-size: 12px;
  color: var(--muted);
}
.save-indicator.save-status-saved {
  color: #12b76a;
}
.save-indicator.save-status-saving {
  color: #f59e0b;
}
.save-indicator.save-status-unsaved {
  color: var(--accent);
}
.word-count,
.char-count {
  font-size: 12px;
  color: var(--muted);
}
.export-btn {
  color: var(--muted);
}
.export-btn:hover {
  color: var(--accent);
}
.editor {
  padding: 28px;
  outline: none;
  line-height: 1.7;
  white-space: pre-wrap;
  overflow: auto;
}
.cursor-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 22px 18px;
  border-top: 1px solid var(--line);
  background: #fffbeb;
}
.cursor-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  background: #fff;
  border: 1px solid #fde68a;
  padding: 6px 10px;
  font-size: 12px;
  color: #92400e;
}
</style>
