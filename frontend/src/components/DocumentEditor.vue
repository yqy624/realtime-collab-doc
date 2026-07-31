<template>
  <section class="editor-card">
    <header class="editor-header">
      <input v-model="localTitle" class="title-input" :readonly="readonly" @change="emitTitle" />
      <div class="meta">
        <span v-if="!readonly">{{ onlineUsers.length }} 人在线</span>
        <span>版本 {{ revision }}</span>
      </div>
    </header>

    <div class="editor-toolbar">
      <div class="toolbar-left">
        <span class="save-indicator" :class="saveStatusClass">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
          </svg>
          <span v-if="readonly">历史版本只读</span>
          <span v-else-if="saveStatus === 'saved'">已保存</span>
          <span v-else-if="saveStatus === 'unsaved'">未保存的更改</span>
          <span v-else>正在保存...</span>
        </span>
        <button v-if="!readonly" class="tool-btn submit-btn" @click="$emit('submit-version')" :disabled="saveStatus === 'saving'">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 3v12"/>
            <path d="m17 8-5-5-5 5"/>
            <path d="M5 21h14"/>
          </svg>
          <span>提交版本</span>
        </button>
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
      :class="{ readonly: readonly }"
      :contenteditable="readonly ? 'false' : 'true'"
      :data-empty="isEditorEmpty ? 'true' : 'false'"
      data-placeholder="请输入内容..."
      @input="handleInput"
      @keyup="emitCursor"
      @mouseup="emitCursor"
    ></div>
    <footer v-if="remoteCursors.length && !readonly" class="cursor-bar">
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

const props = withDefaults(defineProps<{
  title: string;
  content: string;
  revision: number;
  saveStatus: "saved" | "saving" | "unsaved";
  onlineUsers: string[];
  remoteCursors: RemoteCursor[];
  readonly?: boolean;
}>(), {
  readonly: false
});

const emit = defineEmits<{
  (e: "title-change", value: string): void;
  (e: "content-change", payload: TextOperation): void;
  (e: "cursor-change", position: number): void;
  (e: "submit-version"): void;
}>();

const editor = ref<HTMLDivElement>(null!);
const isEditorEmpty = ref(true);
const readEditorText = () => {
  const text = editor.value?.innerText ?? "";
  return text.trim().length === 0 ? "" : text;
};
const getSelectionInfo = () => {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0 || !editor.value) return null;
  const range = selection.getRangeAt(0);
  if (!editor.value.contains(range.startContainer) || !editor.value.contains(range.endContainer)) {
    return null;
  }

  const startRange = range.cloneRange();
  startRange.selectNodeContents(editor.value);
  startRange.setEnd(range.startContainer, range.startOffset);
  const endRange = range.cloneRange();
  endRange.selectNodeContents(editor.value);
  endRange.setEnd(range.endContainer, range.endOffset);

  return {
    text: range.toString(),
    start: startRange.toString().length,
    end: endRange.toString().length
  };
};
defineExpose({ getText: readEditorText, getSelectionInfo });
const localTitle = ref(props.title);
let lastContent = props.content ?? "";
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
    editor.value.innerText = props.content ?? "";
    isEditorEmpty.value = readEditorText() === "";
  }
});

watch(
  () => props.content,
  (value) => {
    if (editor.value && editor.value.innerText !== value) {
      editor.value.innerText = value ?? "";
    }
    lastContent = value ?? "";
    isEditorEmpty.value = lastContent.trim().length === 0;
  }
);

watch(
  () => props.title,
  (value) => {
    localTitle.value = value;
  }
);

const emitTitle = () => {
  if (props.readonly) return;
  emit("title-change", localTitle.value);
};

const handleInput = () => {
  if (!editor.value || props.readonly) return;
  isEditorEmpty.value = readEditorText() === "";
  if (debounceTimer) window.clearTimeout(debounceTimer);
  debounceTimer = window.setTimeout(() => {
    const currentText = readEditorText();
    const payload = createOperation(lastContent, currentText, props.revision);
    lastContent = currentText;
    emit("content-change", payload);
  }, 300);
  emitCursor();
};

const emitCursor = () => {
  if (!editor.value || props.readonly) return;
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
.title-input:read-only {
  color: var(--ink);
  cursor: default;
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
.submit-btn {
  color: var(--accent);
  border-color: rgba(37, 99, 235, 0.25);
}
.save-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--muted);
  padding: 6px 10px;
  border-radius: 999px;
  background: #fff;
  border: 1px solid var(--line);
}
.save-indicator.save-status-saved {
  color: #12b76a;
  border-color: rgba(18, 183, 106, 0.25);
  background: #f0fdf4;
}
.save-indicator.save-status-saving {
  color: #f59e0b;
  border-color: rgba(245, 158, 11, 0.25);
  background: #fffbeb;
}
.save-indicator.save-status-unsaved {
  color: var(--accent);
  border-color: rgba(37, 99, 235, 0.25);
  background: #eff6ff;
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
.editor.readonly {
  background: #fcfcfd;
  cursor: default;
}
.editor:empty::before,
.editor[data-empty="true"]::before {
  content: attr(data-placeholder);
  color: var(--muted);
  pointer-events: none;
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
