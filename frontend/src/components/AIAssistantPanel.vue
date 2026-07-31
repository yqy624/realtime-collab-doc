<template>
  <section class="ai-card">
    <header class="ai-header">
      <div>
        <h3>AI 助手</h3>
        <p>本地 Ollama · {{ modelName || "granite4.1:8b" }}</p>
      </div>
      <span v-if="busy" class="status-dot">生成中</span>
    </header>

    <div class="ai-content">
      <div class="selection-row">
        <div>
          <span class="field-label">选中文本</span>
          <span class="selection-count">{{ selectedText.length }} 字</span>
        </div>
        <button class="secondary-btn" type="button" @click="readSelection">读取选区</button>
      </div>
      <textarea
        v-model="selectedText"
        class="selection-input"
        rows="4"
        placeholder="在编辑器中选择文本，或直接粘贴到这里"
      />

      <div class="action-grid">
        <button class="action-btn primary" type="button" :disabled="busy" @click="runSummary">
          总结全文
        </button>
        <button
          v-for="item in rewriteModes"
          :key="item.value"
          class="action-btn"
          type="button"
          :disabled="busy || !selectedText.trim()"
          @click="runRewrite(item.value)"
        >
          {{ item.label }}
        </button>
      </div>

      <form class="ask-form" @submit.prevent="runAsk">
        <textarea
          v-model="question"
          rows="3"
          placeholder="询问文档内容，例如：提炼这篇文档的三个风险点"
        />
        <button class="ask-btn" type="submit" :disabled="busy || !question.trim()">发送问题</button>
      </form>

      <div class="result-header">
        <span class="field-label">生成结果</span>
        <span v-if="elapsedMs > 0" class="result-meta">{{ elapsedMs }} ms</span>
      </div>
      <div class="result-box" :class="{ empty: !result }">
        {{ result || "AI 结果会显示在这里，不会自动修改文档" }}
      </div>
      <div v-if="result" class="result-actions">
        <button class="secondary-btn" type="button" @click="copyResult">复制</button>
        <button class="secondary-btn" type="button" @click="appendResult">插入文末</button>
        <button
          v-if="lastAction === 'rewrite' && selectionRange"
          class="apply-btn"
          type="button"
          @click="replaceSelection"
        >
          替换选区
        </button>
      </div>

      <div class="history-header">
        <span class="field-label">最近记录</span>
        <button class="text-btn" type="button" @click="loadHistory">刷新</button>
      </div>
      <div v-if="history.length === 0" class="history-empty">暂无 AI 记录</div>
      <div v-else class="history-list">
        <article v-for="item in history.slice(-6).reverse()" :key="item.id" class="history-item">
          <div class="history-meta">
            <strong>{{ item.role === "user" ? "我" : "AI" }}</strong>
            <span>{{ actionLabel(item.action) }}</span>
          </div>
          <p>{{ item.content }}</p>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  getAIHistory,
  streamAI,
  type AIHistoryItem,
  type RewriteMode
} from "../api/ai";

interface SelectionInfo {
  text: string;
  start: number;
  end: number;
}

const props = defineProps<{
  documentId: number;
  getSelection: () => SelectionInfo | null;
  appendToDocument: (content: string) => void;
  replaceDocumentSelection: (content: string, selection: SelectionInfo) => void;
}>();

const rewriteModes: Array<{ label: string; value: RewriteMode }> = [
  { label: "润色选区", value: "polish" },
  { label: "扩写选区", value: "expand" },
  { label: "翻译选区", value: "translate" }
];

const selectedText = ref("");
const question = ref("");
const result = ref("");
const busy = ref(false);
const elapsedMs = ref(0);
const modelName = ref("");
const lastAction = ref<"ask" | "summary" | "rewrite" | "">("");
const selectionRange = ref<SelectionInfo | null>(null);
const history = ref<AIHistoryItem[]>([]);

const readSelection = () => {
  const selection = props.getSelection();
  if (!selection?.text.trim()) {
    ElMessage.warning("请先在文档中选择一段文字");
    return;
  }
  selectedText.value = selection.text;
  selectionRange.value = selection;
};

const startStream = async (
  action: "ask" | "summary" | "rewrite",
  payload: { question?: string; selectedText?: string; mode?: RewriteMode }
) => {
  busy.value = true;
  result.value = "";
  elapsedMs.value = 0;
  lastAction.value = action;

  try {
    await streamAI(props.documentId, { action, ...payload }, (event) => {
      if (event.event === "meta") {
        modelName.value = String(event.data.model || "");
      } else if (event.event === "chunk") {
        result.value += String(event.data.content || "");
      } else if (event.event === "done") {
        elapsedMs.value = Number(event.data.elapsedMs || 0);
        modelName.value = String(event.data.model || modelName.value);
      } else if (event.event === "error") {
        throw new Error(String(event.data.message || "AI 请求失败"));
      }
    });
    await loadHistory();
  } catch (error: any) {
    result.value = "";
    ElMessage.error(error?.message || error?.response?.data?.message || "AI 请求失败");
  } finally {
    busy.value = false;
  }
};

const runSummary = () => startStream("summary", {});

const runAsk = () => {
  if (!question.value.trim()) return;
  return startStream("ask", { question: question.value.trim() });
};

const runRewrite = (mode: RewriteMode) => {
  if (!selectedText.value.trim()) return;
  if (!selectionRange.value) {
    const selection = props.getSelection();
    if (selection) selectionRange.value = selection;
  }
  return startStream("rewrite", {
    selectedText: selectedText.value,
    mode
  });
};

const copyResult = async () => {
  await navigator.clipboard.writeText(result.value);
  ElMessage.success("已复制 AI 结果");
};

const appendResult = () => {
  props.appendToDocument(result.value);
  ElMessage.success("已插入文末");
};

const replaceSelection = () => {
  if (!selectionRange.value) return;
  props.replaceDocumentSelection(result.value, selectionRange.value);
  ElMessage.success("已替换选区");
};

const loadHistory = async () => {
  try {
    const { data } = await getAIHistory(props.documentId);
    history.value = data.data || [];
  } catch {
    history.value = [];
  }
};

const actionLabel = (action: string) => {
  if (action === "summary") return "总结";
  if (action === "rewrite") return "改写";
  return "提问";
};

onMounted(loadHistory);
</script>

<style scoped>
.ai-card {
  display: grid;
  grid-template-rows: auto 1fr;
  min-height: 0;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.05);
}

.ai-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 20px;
  border-bottom: 1px solid var(--line);
}

.ai-header h3 {
  margin: 0;
}

.ai-header p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.status-dot {
  align-self: start;
  color: #b45309;
  font-size: 12px;
}

.ai-content {
  overflow: auto;
  padding: 16px 20px 20px;
}

.selection-row,
.result-header,
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.field-label {
  color: var(--ink);
  font-size: 12px;
  font-weight: 700;
}

.selection-count,
.result-meta {
  margin-left: 8px;
  color: var(--muted);
  font-size: 11px;
}

.selection-input,
.ask-form textarea {
  width: 100%;
  box-sizing: border-box;
  margin-top: 8px;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 10px 12px;
  resize: vertical;
  font: inherit;
  font-size: 12px;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.action-btn,
.ask-btn,
.apply-btn,
.secondary-btn,
.text-btn {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  color: var(--ink);
  cursor: pointer;
  font-size: 12px;
  padding: 8px 10px;
}

.action-btn.primary,
.ask-btn,
.apply-btn {
  border-color: var(--accent);
  background: var(--accent);
  color: #fff;
}

.action-btn:disabled,
.ask-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.secondary-btn:hover,
.action-btn:hover:not(:disabled) {
  border-color: var(--accent);
  background: #eff6ff;
}

.ask-form {
  display: grid;
  gap: 8px;
  margin-top: 14px;
}

.ask-btn {
  justify-self: end;
}

.result-header {
  margin-top: 16px;
}

.result-box {
  min-height: 120px;
  margin-top: 8px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #f8fafc;
  white-space: pre-wrap;
  line-height: 1.6;
  font-size: 12px;
}

.result-box.empty {
  color: var(--muted);
}

.result-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.history-header {
  margin-top: 18px;
}

.text-btn {
  border: none;
  padding: 2px 0;
  color: var(--accent);
}

.history-empty {
  padding: 12px 0;
  color: var(--muted);
  font-size: 12px;
}

.history-list {
  display: grid;
  gap: 8px;
  margin-top: 8px;
}

.history-item {
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fafbfc;
}

.history-meta {
  display: flex;
  gap: 8px;
  color: var(--muted);
  font-size: 11px;
}

.history-item p {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 6px 0 0;
  white-space: pre-wrap;
  font-size: 12px;
  line-height: 1.5;
}
</style>
