<template>
  <section class="agent-card">
    <header class="agent-header">
      <div>
        <p class="eyebrow">MODEL / PLAN / TOOLS / MEMORY</p>
        <h3>Agent 工作台</h3>
        <p class="subtext">{{ scopeLabel }}</p>
      </div>
      <span class="status" :class="statusClass">{{ statusLabel }}</span>
    </header>

    <div class="agent-content">
      <form class="query-form" @submit.prevent="runAgent">
        <label class="skill-picker">
          <span>Skill</span>
          <select v-model="selectedSkillId">
            <option value="">自动选择</option>
            <option v-for="skill in skills" :key="skill.id" :value="String(skill.id)">
              {{ skill.name }}
            </option>
          </select>
        </label>
        <div v-if="activeSkill" class="skill-card">
          <strong>{{ activeSkill.name }}</strong>
          <p>{{ activeSkill.description }}</p>
          <div class="skill-tools">
            <span v-for="tool in activeSkill.tools" :key="tool">{{ toolLabel(tool) }}</span>
          </div>
        </div>
        <textarea
          v-model="goal"
          rows="3"
          placeholder="输入一个需要多步完成的目标，例如：总结当前文档并指出风险"
        />
        <button class="agent-btn" type="submit" :disabled="busy || !goal.trim()">
          <span>{{ busy ? "执行中..." : "运行 Agent" }}</span>
          <span aria-hidden="true">→</span>
        </button>
      </form>

      <div v-if="run" class="run-meta">
        <span>Run #{{ run.runId }}</span>
        <span v-if="activeRunSkill">{{ activeRunSkill.name }}</span>
        <span>{{ run.executionMode || "inline" }}</span>
        <span>{{ run.model || "model" }}</span>
        <span v-if="run.updatedAt">{{ formatTime(run.updatedAt) }}</span>
      </div>

      <section v-if="run" class="section">
        <div class="section-heading">
          <span>执行计划</span>
          <span class="meta">{{ completedSteps }}/{{ run.plan.length }} 步</span>
        </div>
        <div class="plan-list">
          <article v-for="step in run.plan" :key="step.id" class="plan-step">
            <div class="step-index">{{ stepIndex(step) }}</div>
            <div class="step-body">
              <strong>{{ toolLabel(step.tool) }}</strong>
              <span>{{ step.reason || "执行 Agent 步骤" }}</span>
            </div>
            <span class="step-status" :class="step.status">{{ stepStatusLabel(step.status) }}</span>
          </article>
        </div>
      </section>

      <section v-if="run?.pendingApproval" class="approval-box">
        <div>
          <strong>需要确认写入</strong>
          <p>{{ toolLabel(run.pendingApproval.tool) }} 将改变文档状态。</p>
          <pre v-if="approvalPreview">{{ approvalPreview }}</pre>
        </div>
        <div class="approval-actions">
          <button class="approve-btn" type="button" :disabled="busy" @click="approve(true)">
            批准执行
          </button>
          <button class="reject-btn" type="button" :disabled="busy" @click="approve(false)">
            拒绝
          </button>
        </div>
      </section>

      <section v-if="run?.result" class="section">
        <div class="section-heading">
          <span>Agent 输出</span>
          <button class="copy-btn" type="button" @click="copyResult">复制</button>
        </div>
        <div class="answer-box">{{ run.result }}</div>
      </section>

      <section v-if="run?.trace.length" class="section">
        <div class="section-heading">
          <span>执行轨迹</span>
          <span class="meta">{{ run.trace.length }} 个事件</span>
        </div>
        <div class="trace-list">
          <div v-for="event in run.trace" :key="`${event.stepId}-${event.status}`" class="trace-event">
            <span class="trace-dot" :class="event.status"></span>
            <span>{{ toolLabel(event.tool || event.kind) }}</span>
            <span class="meta">{{ event.durationMs }} ms</span>
          </div>
        </div>
      </section>

      <section v-if="invocations.length" class="section">
        <div class="section-heading">
          <span>工具调用</span>
          <span class="meta">{{ invocations.length }} 条</span>
        </div>
        <div class="invocation-list">
          <article v-for="item in invocations" :key="item.id" class="invocation-row">
            <div>
              <strong>{{ toolLabel(item.toolName) }}</strong>
              <span>{{ item.toolType }} · {{ invocationStatusLabel(item.status) }} · {{ approvalLabel(item.approvalStatus) }}</span>
            </div>
            <code>{{ item.durationMs }} ms</code>
          </article>
        </div>
      </section>

      <section v-if="run?.memories.length" class="section">
        <div class="section-heading">
          <span>召回记忆</span>
          <span class="meta">{{ run.memories.length }} 条</span>
        </div>
        <div class="memory-list">
          <p v-for="memory in run.memories" :key="String(memory.id)">
            {{ String(memory.content || "") }}
          </p>
        </div>
      </section>

      <p v-if="run?.error" class="error-box">{{ run.error }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import {
  approveAgentRun,
  getAgentRunInvocations,
  getAgentSkills,
  runAgent as startAgent,
  type AgentSkill,
  type AgentPlanStep,
  type AgentRun,
  type ToolInvocation
} from "../api/ai";

const props = defineProps<{ scopeDocumentId?: number; workspaceId?: number | null }>();

const emit = defineEmits<{
  (e: "history-change"): void;
}>();

const goal = ref("");
const run = ref<AgentRun | null>(null);
const skills = ref<AgentSkill[]>([]);
const invocations = ref<ToolInvocation[]>([]);
const selectedSkillId = ref("");
const busy = ref(false);

const scopeLabel = computed(() =>
  props.scopeDocumentId ? "当前文档范围 · 权限过滤" : "全部可访问文档 · 权限过滤"
);

const statusLabel = computed(() => {
  if (!run.value) return "待命";
  const labels: Record<string, string> = {
    planning: "规划中",
    executing: "执行中",
    awaiting_approval: "待确认",
    completed: "已完成",
    failed: "失败",
    cancelled: "已取消"
  };
  return labels[run.value.status] || run.value.status;
});

const statusClass = computed(() => run.value?.status || "idle");
const completedSteps = computed(
  () => run.value?.plan.filter((step) => step.status === "completed").length || 0
);
const activeSkill = computed(
  () => skills.value.find((item) => String(item.id) === selectedSkillId.value) || null
);
const activeRunSkill = computed(
  () => skills.value.find((item) => item.id === run.value?.skillId) || null
);
const approvalPreview = computed(() => {
  const output = run.value?.pendingApproval?.output || {};
  const diff = output.diff || output.proposedContent || output.message;
  return diff ? String(diff).slice(0, 1200) : "";
});

const loadSkills = async () => {
  try {
    const { data } = await getAgentSkills(props.workspaceId);
    skills.value = data.data || [];
    if (!selectedSkillId.value && skills.value.length) {
      const matched = props.scopeDocumentId
        ? skills.value.find((item) => item.slug === "summary")
        : skills.value.find((item) => item.slug === "knowledge_qa");
      selectedSkillId.value = matched ? String(matched.id) : "";
    }
  } catch {
    skills.value = [];
  }
};

onMounted(loadSkills);

watch(
  () => props.workspaceId,
  async () => {
    selectedSkillId.value = "";
    await loadSkills();
  }
);

const loadInvocations = async () => {
  if (!run.value) {
    invocations.value = [];
    return;
  }
  const { data } = await getAgentRunInvocations(run.value.runId);
  invocations.value = data.data || [];
};

const runAgent = async () => {
  if (!goal.value.trim()) return;
  busy.value = true;
  try {
    const skillId = selectedSkillId.value ? Number(selectedSkillId.value) : null;
    const { data } = await startAgent(goal.value.trim(), props.scopeDocumentId, { skillId });
    run.value = data.data;
    await loadInvocations();
    emit("history-change");
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || error?.message || "Agent 执行失败");
  } finally {
    busy.value = false;
  }
};

const approve = async (approved: boolean) => {
  if (!run.value) return;
  busy.value = true;
  try {
    const { data } = await approveAgentRun(run.value.runId, approved);
    run.value = data.data;
    await loadInvocations();
    emit("history-change");
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || error?.message || "审批失败");
  } finally {
    busy.value = false;
  }
};

const copyResult = async () => {
  if (!run.value?.result) return;
  await navigator.clipboard.writeText(run.value.result);
  ElMessage.success("已复制");
};

const toolLabel = (tool: string) => {
  const labels: Record<string, string> = {
    recall_memory: "召回记忆",
    search_knowledge: "检索知识库",
    web_search: "联网搜索",
    weather_query: "天气查询",
    get_current_document: "读取当前文档",
    list_snapshots: "读取历史版本",
    model_generate: "模型生成",
    generate_diff: "生成文档差异",
    remember: "写入记忆",
    create_snapshot: "创建快照",
    apply_document_content: "写回文档"
  };
  if (tool.startsWith("mcp:")) {
    return tool.split(":").slice(-1)[0] || tool;
  }
  return labels[tool] || tool;
};

const stepStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    pending: "等待",
    completed: "完成",
    waiting_approval: "待确认",
    failed: "失败",
    rejected: "拒绝"
  };
  return labels[status] || status;
};

const stepIndex = (step: AgentPlanStep) =>
  run.value ? run.value.plan.findIndex((item) => item.id === step.id) + 1 : 0;

const formatTime = (value: string) =>
  new Date(value).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });

const invocationStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    running: "执行中",
    waiting_approval: "待确认",
    completed: "完成",
    failed: "失败"
  };
  return labels[status] || status;
};

const approvalLabel = (status: string) => {
  const labels: Record<string, string> = {
    not_required: "无需审批",
    pending: "待审批",
    approved: "已批准",
    rejected: "已拒绝"
  };
  return labels[status] || status;
};
</script>

<style scoped>
.agent-card {
  display: grid;
  grid-template-rows: auto 1fr;
  min-height: 0;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.05);
}
.agent-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--line);
}
.agent-header h3 {
  margin: 4px 0 0;
  font-size: 18px;
}
.eyebrow {
  margin: 0;
  color: var(--accent);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.subtext,
.meta {
  color: var(--muted);
  font-size: 11px;
}
.subtext {
  margin: 6px 0 0;
}
.status {
  align-self: flex-start;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 5px 8px;
  color: var(--muted);
  font-size: 11px;
}
.status.executing,
.status.planning {
  color: #1d4ed8;
  border-color: #93c5fd;
  background: #eff6ff;
}
.status.awaiting_approval {
  color: #b45309;
  border-color: #f5c26b;
  background: #fffbeb;
}
.status.completed {
  color: #15803d;
  border-color: #86efac;
  background: #f0fdf4;
}
.status.failed,
.status.cancelled {
  color: #b91c1c;
  border-color: #fca5a5;
  background: #fef2f2;
}
.agent-content {
  overflow: auto;
  padding: 16px 20px 20px;
}
.query-form {
  display: grid;
  gap: 8px;
}
.skill-picker {
  display: grid;
  gap: 5px;
  color: var(--muted);
  font-size: 11px;
}
.skill-picker select {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  color: var(--ink);
  font: inherit;
  font-size: 12px;
  padding: 8px 10px;
}
.skill-card {
  display: grid;
  gap: 6px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #eff6ff;
  padding: 10px;
}
.skill-card strong {
  color: #1e3a8a;
  font-size: 12px;
}
.skill-card p {
  margin: 0;
  color: #475569;
  font-size: 11px;
  line-height: 1.5;
}
.skill-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.skill-tools span {
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  background: #fff;
  color: #1d4ed8;
  font-size: 10px;
  padding: 3px 6px;
}
.query-form textarea {
  width: 100%;
  box-sizing: border-box;
  resize: vertical;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 10px 12px;
  font: inherit;
  font-size: 12px;
}
.agent-btn,
.approve-btn,
.reject-btn {
  border-radius: 8px;
  cursor: pointer;
  padding: 9px 12px;
  font-size: 12px;
}
.agent-btn {
  display: inline-flex;
  justify-content: space-between;
  border: 1px solid var(--accent);
  background: var(--accent);
  color: #fff;
}
.agent-btn:disabled,
.approve-btn:disabled,
.reject-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.run-meta {
  display: flex;
  gap: 10px;
  margin-top: 12px;
  color: var(--muted);
  font-size: 10px;
}
.section {
  margin-top: 16px;
}
.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;
}
.plan-list,
.trace-list,
.memory-list {
  display: grid;
  gap: 6px;
  margin-top: 8px;
}
.plan-step {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}
.step-index {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #eff6ff;
  color: var(--accent);
  font-size: 10px;
  font-weight: 700;
}
.step-body {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.step-body strong {
  font-size: 11px;
}
.step-body span {
  overflow: hidden;
  color: var(--muted);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.step-status {
  color: var(--muted);
  font-size: 10px;
}
.step-status.completed {
  color: #15803d;
}
.step-status.waiting_approval {
  color: #b45309;
}
.step-status.failed,
.step-status.rejected {
  color: #b91c1c;
}
.approval-box {
  display: grid;
  gap: 10px;
  margin-top: 16px;
  padding: 12px;
  border: 1px solid #f5c26b;
  border-radius: 10px;
  background: #fffbeb;
}
.approval-box strong {
  font-size: 12px;
}
.approval-box p {
  margin: 4px 0 0;
  color: #92400e;
  font-size: 11px;
}
.approval-box pre {
  overflow: auto;
  max-height: 180px;
  margin: 8px 0 0;
  border-radius: 8px;
  background: #fff;
  color: #78350f;
  font-size: 10px;
  line-height: 1.5;
  padding: 8px;
  white-space: pre-wrap;
}
.approval-actions {
  display: flex;
  gap: 8px;
}
.approve-btn {
  border: 1px solid #b45309;
  background: #b45309;
  color: #fff;
}
.reject-btn {
  border: 1px solid #f5c26b;
  background: #fff;
  color: #92400e;
}
.answer-box {
  margin-top: 8px;
  padding: 12px;
  min-height: 80px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #f8fafc;
  white-space: pre-wrap;
  line-height: 1.65;
  font-size: 12px;
}
.copy-btn {
  border: none;
  background: transparent;
  color: var(--accent);
  cursor: pointer;
  padding: 0;
  font-size: 11px;
}
.trace-event {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--ink);
  font-size: 11px;
}
.invocation-list {
  display: grid;
  gap: 6px;
  margin-top: 8px;
}
.invocation-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  padding: 8px;
}
.invocation-row div {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.invocation-row strong {
  overflow: hidden;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.invocation-row span,
.invocation-row code {
  color: var(--muted);
  font-size: 10px;
}
.trace-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #16a34a;
}
.trace-dot.waiting_approval {
  background: #d97706;
}
.trace-dot.failed {
  background: #dc2626;
}
.memory-list p {
  margin: 0;
  padding: 8px;
  border-left: 2px solid var(--accent);
  background: #f8fafc;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.5;
}
.error-box {
  margin: 14px 0 0;
  padding: 10px;
  border: 1px solid #fca5a5;
  border-radius: 8px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 11px;
}
</style>
