<template>
  <section class="agent-card">
    <header class="agent-header">
      <div>
        <p class="eyebrow">RAG + LangGraph</p>
        <h3>知识库 Agent</h3>
        <p class="subtext">{{ scopeLabel }}</p>
      </div>
      <span v-if="busy" class="running">运行中</span>
    </header>

    <div class="agent-content">
      <form class="query-form" @submit.prevent="runAgent">
        <textarea
          v-model="question"
          rows="3"
          :placeholder="scopeDocumentId ? '询问当前文档，例如：这份文档的关键风险是什么？' : '询问可访问文档，例如：哪些文档提到了项目风险？'"
        />
        <button class="agent-btn" type="submit" :disabled="busy || !question.trim()">
          <span>运行 Agent</span>
          <span aria-hidden="true">→</span>
        </button>
      </form>

      <div v-if="answer" class="answer-section">
        <div class="section-heading">
          <span>回答</span>
          <span class="meta">{{ elapsedMs }} ms · {{ model }}</span>
        </div>
        <div class="answer-box" :class="{ refusal }">{{ answer }}</div>
        <button class="copy-btn" type="button" @click="copyAnswer">复制回答</button>
      </div>

      <div class="trace-line" v-if="traceChunks >= 0">
        <span class="trace-dot"></span>
        <span>检索 {{ traceChunks }} 个片段</span>
        <span class="trace-arrow">→</span>
        <span>证据判断</span>
        <span class="trace-arrow">→</span>
        <span>生成回答</span>
      </div>

      <div class="citation-section">
        <div class="section-heading">
          <span>引用依据</span>
          <span class="meta">{{ citations.length }} 条</span>
        </div>
        <div v-if="citations.length === 0" class="empty-citations">
          Agent 检索到的文档片段会显示在这里
        </div>
        <article v-for="item in citations" :key="`${item.documentId}-${item.chunkIndex}`" class="citation">
          <div class="citation-meta">
            <strong>{{ item.title }}</strong>
            <span>片段 {{ item.chunkIndex + 1 }} · {{ Math.round(item.score * 100) }}%</span>
          </div>
          <p>{{ item.content }}</p>
          <small v-if="item.matchedTerms.length">命中：{{ item.matchedTerms.join("、") }}</small>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import { queryKnowledgeAgent, type KnowledgeSearchHit } from "../api/ai";

const props = defineProps<{ scopeDocumentId?: number }>();

const question = ref("");
const answer = ref("");
const citations = ref<KnowledgeSearchHit[]>([]);
const busy = ref(false);
const refusal = ref(false);
const elapsedMs = ref(0);
const model = ref("");
const traceChunks = ref(-1);

const scopeLabel = computed(() =>
  props.scopeDocumentId ? "当前文档范围 · 权限过滤后检索" : "全部可访问文档 · 权限过滤后检索"
);

const runAgent = async () => {
  if (!question.value.trim()) return;
  busy.value = true;
  answer.value = "";
  citations.value = [];
  traceChunks.value = -1;
  try {
    const { data } = await queryKnowledgeAgent(question.value.trim(), {
      documentId: props.scopeDocumentId
    });
    const result = data.data;
    answer.value = result.answer || "";
    citations.value = result.citations || [];
    refusal.value = Boolean(result.refusal);
    elapsedMs.value = Number(result.elapsedMs || 0);
    model.value = String(result.model || "");
    traceChunks.value = Number(result.trace?.retrievedChunks ?? 0);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || error?.message || "Agent 请求失败");
  } finally {
    busy.value = false;
  }
};

const copyAnswer = async () => {
  await navigator.clipboard.writeText(answer.value);
  ElMessage.success("回答已复制");
};
</script>

<style scoped>
.agent-card {
  display: grid;
  grid-template-rows: auto 1fr;
  min-height: 0;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.05);
}
.agent-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 20px;
  border-bottom: 1px solid var(--line);
}
.agent-header h3 { margin: 4px 0 0; }
.eyebrow {
  margin: 0;
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.subtext, .meta { color: var(--muted); font-size: 11px; }
.subtext { margin: 6px 0 0; }
.running { color: #b45309; font-size: 12px; }
.agent-content { overflow: auto; padding: 16px 20px 20px; }
.query-form { display: grid; gap: 8px; }
.query-form textarea {
  width: 100%;
  box-sizing: border-box;
  resize: vertical;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 10px 12px;
  font: inherit;
  font-size: 12px;
}
.agent-btn {
  display: inline-flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid var(--accent);
  border-radius: 8px;
  background: var(--accent);
  color: #fff;
  cursor: pointer;
  padding: 9px 12px;
  font-size: 12px;
}
.agent-btn:disabled { cursor: not-allowed; opacity: 0.5; }
.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  margin-top: 16px;
  font-size: 12px;
  font-weight: 700;
}
.answer-box {
  margin-top: 8px;
  padding: 12px;
  min-height: 100px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #f8fafc;
  white-space: pre-wrap;
  line-height: 1.65;
  font-size: 12px;
}
.answer-box.refusal { border-color: #f5c26b; background: #fffbeb; }
.copy-btn {
  margin-top: 8px;
  border: none;
  background: transparent;
  color: var(--accent);
  cursor: pointer;
  padding: 2px 0;
  font-size: 12px;
}
.trace-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 14px;
  color: var(--muted);
  font-size: 11px;
}
.trace-dot { width: 6px; height: 6px; border-radius: 50%; background: #16a34a; }
.trace-arrow { color: #cbd5e1; }
.empty-citations {
  margin-top: 8px;
  padding: 12px;
  border: 1px dashed var(--line);
  border-radius: 10px;
  color: var(--muted);
  font-size: 11px;
}
.citation {
  margin-top: 8px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
}
.citation-meta { display: flex; justify-content: space-between; gap: 8px; font-size: 11px; }
.citation-meta span, .citation small { color: var(--muted); }
.citation p { margin: 6px 0; white-space: pre-wrap; line-height: 1.5; font-size: 11px; }
.citation small { font-size: 10px; }
</style>
