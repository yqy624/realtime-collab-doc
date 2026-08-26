<template>
  <main class="home-page">
    <header class="top-nav">
      <div class="brand">
        <span class="brand-mark">D</span>
        <span class="brand-name">音go实时协作网</span>
      </div>
      <div class="nav-right">
        <div class="user-chip" @click="showUserMenu = !showUserMenu">
          <img :src="userStore.avatarUrl || placeholderAvatar" class="nav-avatar" alt="" />
          <span>{{ userStore.username }}</span>
          <span class="chev">v</span>
        </div>
        <div v-if="showUserMenu" class="user-menu">
          <button class="menu-item" type="button" @click="logout">退出登录</button>
        </div>
      </div>
    </header>

    <section class="app-shell">
      <aside class="workspace-sidebar">
        <div class="sidebar-section">
          <div class="section-title">
            <span>空间</span>
            <button type="button" @click="showWorkspaceCreate = true">新建</button>
          </div>
          <button
            class="workspace-item"
            :class="{ active: activeWorkspaceId === null }"
            type="button"
            @click="selectAllDocuments"
          >
            <span class="workspace-dot all"></span>
            <span>全部可访问文档</span>
          </button>
          <button
            v-for="workspace in workspaces"
            :key="workspace.id"
            class="workspace-item"
            :class="{ active: activeWorkspaceId === workspace.id }"
            type="button"
            @click="selectWorkspace(workspace.id)"
          >
            <span class="workspace-dot"></span>
            <span>{{ workspace.name }}</span>
            <small>{{ roleLabel(workspace.role) }}</small>
          </button>
        </div>

        <div v-if="activeWorkspace" class="sidebar-section">
          <div class="section-title">
            <span>文件夹</span>
            <button v-if="canCreateInWorkspace" type="button" @click="showFolderCreate = true">
              新建
            </button>
          </div>
          <button
            class="folder-item"
            :class="{ active: activeFolderId === null }"
            type="button"
            @click="selectFolder(null)"
          >
            全部文档
          </button>
          <button
            v-for="folder in folders"
            :key="folder.id"
            class="folder-item"
            :class="{ active: activeFolderId === folder.id }"
            type="button"
            @click="selectFolder(folder.id)"
          >
            {{ folder.name }}
          </button>
          <p v-if="folders.length === 0" class="sidebar-empty">暂无文件夹</p>
        </div>

        <div class="sidebar-section">
          <div class="section-title">
            <span>治理</span>
          </div>
          <button
            class="folder-item"
            :class="{ active: isTrashView }"
            type="button"
            @click="openTrash"
          >
            回收站
          </button>
          <button
            v-if="canManageWorkspace"
            class="folder-item"
            :class="{ active: isAuditView }"
            type="button"
            @click="openAuditLogs"
          >
            治理日志
          </button>
          <button
            class="folder-item"
            :class="{ active: isAgentCenterView }"
            type="button"
            @click="openAgentCenter"
          >
            Agent Center
          </button>
          <button
            class="folder-item"
            :class="{ active: isKnowledgeView }"
            type="button"
            @click="openKnowledgeBase"
          >
            知识库
          </button>
        </div>
      </aside>

      <section class="workspace-main">
        <section class="summary-strip">
          <div>
            <span class="eyebrow">{{ summaryEyebrow }}</span>
            <h1>{{ summaryTitle }}</h1>
            <p>{{ summaryDescription }}</p>
          </div>
          <div v-if="!isTrashView && !isAuditView && !isAgentCenterView && !isKnowledgeView" class="summary-actions">
            <button class="primary-action" type="button" :disabled="!canCreateInWorkspace" @click="createNew">
              新建文档
            </button>
          </div>
          <div class="summary-stats">
            <div>
              <strong>{{ summaryCount }}</strong>
              <span>当前列表</span>
            </div>
            <div>
              <strong>{{ ownedCount }}</strong>
              <span>我创建的</span>
            </div>
            <div>
              <strong>{{ sharedCount }}</strong>
              <span>协作文档</span>
            </div>
          </div>
        </section>

        <section v-if="!isTrashView && !isAuditView && !isAgentCenterView && !isKnowledgeView" class="knowledge-search">
          <div class="search-heading">
            <div>
              <span class="eyebrow">RAG</span>
              <h2>知识检索</h2>
            </div>
            <form class="knowledge-form" @submit.prevent="runKnowledgeSearch">
              <input
                v-model="knowledgeQuery"
                placeholder="搜索可访问文档内容"
                aria-label="知识库关键词"
              />
              <button type="submit" :disabled="searching || !knowledgeQuery.trim()">
                {{ searching ? "检索中" : "检索" }}
              </button>
            </form>
          </div>
          <div v-if="knowledgeSearched" class="knowledge-results">
            <div class="results-meta">
              <span>命中 {{ knowledgeResults.length }} 个片段</span>
              <button type="button" @click="clearKnowledgeSearch">清空</button>
            </div>
            <article
              v-for="item in knowledgeResults"
              :key="`${item.documentId}-${item.chunkIndex}`"
              class="knowledge-result"
              @click="goEditor({ id: item.documentId })"
            >
              <div class="result-top">
                <strong>{{ item.title }}</strong>
                <span>{{ citationLabel(item) }} · {{ Math.round(item.score * 100) }}%</span>
              </div>
              <p>{{ item.content }}</p>
              <small>命中：{{ item.matchedTerms.join("、") }}</small>
            </article>
            <div v-if="knowledgeResults.length === 0" class="no-results">
              没有找到相关片段。
            </div>
          </div>
        </section>

        <section v-if="isKnowledgeView" class="knowledge-base-panel">
          <div class="knowledge-grid">
            <section class="knowledge-card upload-card">
              <div class="section-heading">
                <span>资料导入</span>
                <span class="muted">PDF / DOCX / Markdown / TXT</span>
              </div>
              <label class="upload-drop">
                <input type="file" accept=".pdf,.docx,.md,.markdown,.txt" @change="handleKnowledgeFile" />
                <span>{{ pendingKnowledgeFile?.name || "选择资料文件" }}</span>
              </label>
              <button
                class="primary-action"
                type="button"
                :disabled="uploadingKnowledge || !pendingKnowledgeFile"
                @click="uploadKnowledge"
              >
                {{ uploadingKnowledge ? "索引中" : "上传并索引" }}
              </button>
            </section>
            <section class="knowledge-card stats-card">
              <div class="section-heading">
                <span>知识覆盖</span>
                <span class="muted">{{ knowledgeStats.vectorBackend || "local_hash" }}</span>
              </div>
              <div class="knowledge-stats">
                <div>
                  <strong>{{ knowledgeStats.sourceCount }}</strong>
                  <span>来源</span>
                </div>
                <div>
                  <strong>{{ knowledgeStats.chunkCount }}</strong>
                  <span>片段</span>
                </div>
                <div>
                  <strong>{{ Math.round(knowledgeStats.coverageRate * 100) }}%</strong>
                  <span>完成率</span>
                </div>
                <div>
                  <strong>{{ knowledgeStats.failedJobCount }}</strong>
                  <span>失败</span>
                </div>
              </div>
            </section>
          </div>

          <section class="knowledge-card">
            <div class="search-heading">
              <div class="section-heading inline">
                <span>混合检索</span>
                <span class="muted">关键词 + 本地向量 + 权限过滤 + rerank</span>
              </div>
              <form class="knowledge-form" @submit.prevent="runKnowledgeSearch">
                <input
                  v-model="knowledgeQuery"
                  placeholder="搜索当前空间知识库"
                  aria-label="知识库混合检索"
                />
                <button type="submit" :disabled="searching || !knowledgeQuery.trim()">
                  {{ searching ? "检索中" : "检索" }}
                </button>
              </form>
            </div>
            <div v-if="knowledgeSearched" class="knowledge-results">
              <article
                v-for="item in knowledgeResults"
                :key="`${item.sourceId}-${item.chunkIndex}`"
                class="knowledge-result"
                @click="openCitation(item)"
              >
                <div class="result-top">
                  <strong>{{ item.title }}</strong>
                  <span>{{ citationLabel(item) }} · {{ Math.round(item.score * 100) }}%</span>
                </div>
                <p>{{ item.content }}</p>
                <small>{{ sourceLabel(item.sourceType || "document") }} · 命中：{{ item.matchedTerms.join("、") || "-" }}</small>
              </article>
              <div v-if="knowledgeResults.length === 0" class="no-results">
                当前可访问知识源中没有足够依据。
              </div>
            </div>
          </section>

          <section class="knowledge-card">
            <div class="section-heading">
              <span>来源管理</span>
              <span class="muted">{{ knowledgeSources.length }}</span>
            </div>
            <article v-for="source in knowledgeSources" :key="source.id" class="source-row">
              <div>
                <strong>{{ source.title }}</strong>
                <span>
                  {{ sourceLabel(source.sourceType) }} · {{ statusLabel(source.status) }}
                  · {{ source.chunkCount }} chunks
                  <template v-if="source.indexedAt"> · {{ fmtTime(source.indexedAt) }}</template>
                </span>
              </div>
              <button type="button" @click="reindexSource(source.id)">重建索引</button>
            </article>
            <div v-if="knowledgeSources.length === 0" class="empty-trash">
              暂无知识源。
            </div>
          </section>

          <section class="knowledge-card">
            <div class="section-heading">
              <span>索引任务</span>
              <span class="muted">{{ knowledgeJobs.length }}</span>
            </div>
            <article v-for="job in knowledgeJobs" :key="job.id" class="job-row">
              <span>#{{ job.id }} · Source #{{ job.sourceId }} · {{ statusLabel(job.status) }}</span>
              <time>{{ fmtTime(job.completedAt || job.startedAt || job.createdAt) }}</time>
            </article>
            <div v-if="knowledgeJobs.length === 0" class="empty-trash">
              暂无索引任务。
            </div>
          </section>
        </section>

        <section v-if="!isTrashView && !isAuditView && !isAgentCenterView && !isKnowledgeView" class="docs-area">
          <DocumentList
            :documents="displayDocuments"
            @select="goEditor"
            @create="createNew"
            @delete="removeDocument"
            @share="openShare"
            @move="openMove"
          />
        </section>
        <section v-else-if="isTrashView" class="trash-panel">
          <article v-for="doc in trashDocuments" :key="doc.id" class="trash-row">
            <div>
              <strong>{{ doc.title }}</strong>
              <span>
                删除时间：{{ fmtTime(doc.deletedAt) }}
                <template v-if="doc.deleteReason"> · {{ doc.deleteReason }}</template>
              </span>
            </div>
            <div class="trash-actions">
              <button type="button" @click="restoreDocument(doc)">恢复</button>
              <button class="danger-action" type="button" @click="permanentDelete(doc)">
                彻底删除
              </button>
            </div>
          </article>
          <div v-if="trashDocuments.length === 0" class="empty-trash">
            回收站为空。
          </div>
        </section>
        <section v-else-if="isAuditView" class="audit-panel">
          <article v-for="log in auditLogs" :key="log.id" class="audit-row">
            <div>
              <strong>{{ actionLabel(log.action) }}</strong>
              <span>
                {{ fmtTime(log.createdAt) }} · 操作人 #{{ log.actorId }}
                <template v-if="log.documentId"> · 文档 #{{ log.documentId }}</template>
                <template v-if="log.targetId"> · 目标 #{{ log.targetId }}</template>
              </span>
            </div>
            <code>{{ compactAudit(log) }}</code>
          </article>
          <div v-if="auditLogs.length === 0" class="empty-trash">
            暂无治理日志。
          </div>
        </section>
        <section v-else-if="isAgentCenterView" class="agent-center-panel">
          <div class="agent-center-grid">
            <section class="agent-center-block">
              <div class="section-heading">
                <span>Skills</span>
                <span class="muted">{{ agentSkills.length }}</span>
              </div>
              <article v-for="skill in agentSkills" :key="skill.id" class="agent-center-row">
                <strong>{{ skill.name }}</strong>
                <p>{{ skill.description }}</p>
                <span>{{ skill.tools.length }} tools · v{{ skill.version || 1 }}</span>
              </article>
            </section>
            <section class="agent-center-block">
              <div class="section-heading">
                <span>Tools</span>
                <span class="muted">{{ agentTools.length }}</span>
              </div>
              <article v-for="tool in agentTools" :key="tool.name" class="agent-center-row compact">
                <strong>{{ toolLabel(tool.name) }}</strong>
                <span>{{ tool.toolType || "builtin" }} · {{ tool.requiresApproval ? "需审批" : "免审批" }}</span>
              </article>
            </section>
          </div>
          <section class="agent-center-block">
            <div class="section-heading">
              <span>最近任务</span>
              <span class="muted">{{ agentRuns.length }}</span>
            </div>
            <article v-for="run in agentRuns" :key="run.runId" class="agent-run-row">
              <div>
                <strong>{{ run.goal }}</strong>
                <span>
                  {{ agentStatusLabel(run.status) }} · {{ run.executionMode || "inline" }}
                  <template v-if="run.documentId"> · 文档 #{{ run.documentId }}</template>
                </span>
              </div>
              <time>{{ fmtTime(run.updatedAt || run.createdAt) }}</time>
            </article>
            <div v-if="agentRuns.length === 0" class="empty-trash">
              暂无 Agent 任务。
            </div>
          </section>
        </section>
      </section>
    </section>

    <el-dialog v-model="showCreate" title="新建文档" width="420px">
      <div class="create-form">
        <el-input
          v-model="createTitle"
          placeholder="请输入文档名称"
          maxlength="50"
          @keyup.enter="confirmCreate"
        />
        <div class="create-public">
          <div class="create-public-text">
            <span class="create-public-title">公开文档</span>
            <span class="create-public-desc">公开后所有登录用户都能看到并访问</span>
          </div>
          <el-switch v-model="createPublic" />
        </div>
      </div>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="confirmCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showWorkspaceCreate" title="新建空间" width="420px">
      <div class="create-form">
        <el-input v-model="workspaceName" placeholder="空间名称" maxlength="40" />
        <el-input
          v-model="workspaceDescription"
          type="textarea"
          :rows="3"
          placeholder="空间说明"
          maxlength="200"
        />
      </div>
      <template #footer>
        <el-button @click="showWorkspaceCreate = false">取消</el-button>
        <el-button type="primary" @click="confirmWorkspaceCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showFolderCreate" title="新建文件夹" width="380px">
      <el-input v-model="folderName" placeholder="文件夹名称" maxlength="40" />
      <template #footer>
        <el-button @click="showFolderCreate = false">取消</el-button>
        <el-button type="primary" @click="confirmFolderCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showMoveDialog" title="移动文档" width="440px">
      <div class="move-form">
        <div v-if="moveDoc" class="move-doc-title">{{ moveDoc.title }}</div>
        <label>
          <span>目标空间</span>
          <select v-model="moveWorkspaceValue" @change="handleMoveWorkspaceChange">
            <option value="">不归属空间</option>
            <option
              v-for="workspace in writableWorkspaces"
              :key="workspace.id"
              :value="String(workspace.id)"
            >
              {{ workspace.name }}
            </option>
          </select>
        </label>
        <label>
          <span>目标文件夹</span>
          <select v-model="moveFolderValue" :disabled="!moveWorkspaceValue">
            <option value="">空间根目录</option>
            <option
              v-for="folder in moveFolders"
              :key="folder.id"
              :value="String(folder.id)"
            >
              {{ folder.name }}
            </option>
          </select>
        </label>
      </div>
      <template #footer>
        <el-button @click="showMoveDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmMove">移动</el-button>
      </template>
    </el-dialog>

    <ShareDialog
      v-if="shareDoc"
      :document-id="shareDoc.id"
      :title="shareDoc.title"
      @close="shareDoc = null"
      @public-change="updateDocumentVisibility(shareDoc.id, $event)"
    />
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import DocumentList from "../components/DocumentList.vue";
import ShareDialog from "../components/ShareDialog.vue";
import {
  getKnowledgeJobs,
  getKnowledgeSources,
  getKnowledgeStats,
  getAgentRuns,
  getAgentSkills,
  getAgentTools,
  reindexKnowledgeSource,
  searchKnowledge,
  uploadKnowledgeSource,
  type EmbeddingJob,
  type AgentRun,
  type AgentSkill,
  type AgentToolSpec,
  type KnowledgeSearchHit,
  type KnowledgeSource,
  type KnowledgeStats
} from "../api/ai";
import {
  createDocument,
  deleteDocument,
  listDocuments,
  listTrashDocuments,
  restoreDeletedDocument,
  updateDocument
} from "../api/document";
import {
  createFolder,
  createWorkspace,
  listWorkspaceAuditLogs,
  listFolders,
  listWorkspaces,
  type AuditLogItem,
  type FolderItem,
  type WorkspaceItem
} from "../api/platform";
import { useDocumentStore, useUserStore } from "../store";

const router = useRouter();
const userStore = useUserStore();
const documentStore = useDocumentStore();

const placeholderAvatar = "https://ui-avatars.com/api/?name=?&background=6366f1&color=fff";
const showUserMenu = ref(false);
const shareDoc = ref<{ id: number; title: string } | null>(null);
const showCreate = ref(false);
const showWorkspaceCreate = ref(false);
const showFolderCreate = ref(false);
const showMoveDialog = ref(false);
const isTrashView = ref(false);
const isAuditView = ref(false);
const isAgentCenterView = ref(false);
const isKnowledgeView = ref(false);
const createTitle = ref("");
const createPublic = ref(false);
const workspaceName = ref("");
const workspaceDescription = ref("");
const folderName = ref("");
const workspaces = ref<WorkspaceItem[]>([]);
const folders = ref<FolderItem[]>([]);
const moveFolders = ref<FolderItem[]>([]);
const activeWorkspaceId = ref<number | null>(null);
const activeFolderId = ref<number | null>(null);
const moveDoc = ref<any | null>(null);
const moveWorkspaceValue = ref("");
const moveFolderValue = ref("");
const trashDocuments = ref<any[]>([]);
const auditLogs = ref<AuditLogItem[]>([]);
const agentSkills = ref<AgentSkill[]>([]);
const agentTools = ref<AgentToolSpec[]>([]);
const agentRuns = ref<AgentRun[]>([]);
const knowledgeSources = ref<KnowledgeSource[]>([]);
const knowledgeJobs = ref<EmbeddingJob[]>([]);
const knowledgeStats = ref<KnowledgeStats>({
  sourceCount: 0,
  indexedSourceCount: 0,
  chunkCount: 0,
  failedJobCount: 0,
  coverageRate: 0,
  vectorBackend: "local_hash"
});
const pendingKnowledgeFile = ref<File | null>(null);
const uploadingKnowledge = ref(false);
const knowledgeQuery = ref("");
const knowledgeResults = ref<KnowledgeSearchHit[]>([]);
const knowledgeSearched = ref(false);
const searching = ref(false);

const activeWorkspace = computed(
  () => workspaces.value.find((item) => item.id === activeWorkspaceId.value) || null
);
const canCreateInWorkspace = computed(
  () => !activeWorkspace.value || ["owner", "admin", "member"].includes(activeWorkspace.value.role)
);
const canManageWorkspace = computed(
  () => !!activeWorkspace.value && ["owner", "admin"].includes(activeWorkspace.value.role)
);
const writableWorkspaces = computed(() =>
  workspaces.value.filter((item) => ["owner", "admin", "member"].includes(item.role))
);
const summaryEyebrow = computed(() => {
  if (isTrashView.value) return "GOVERNANCE";
  if (isAuditView.value) return "AUDIT";
  if (isAgentCenterView.value) return "AGENT";
  if (isKnowledgeView.value) return "KNOWLEDGE";
  return "WORKSPACE";
});
const summaryTitle = computed(() => {
  if (isTrashView.value) return "回收站";
  if (isAuditView.value) return "治理日志";
  if (isAgentCenterView.value) return "Agent Center";
  if (isKnowledgeView.value) return "知识库";
  return activeWorkspace.value?.name || "全部可访问文档";
});
const summaryDescription = computed(() => {
  if (isTrashView.value) return "已删除文档会先进入回收站，可恢复或彻底删除。";
  if (isAuditView.value) return "空间成员、权限、目录和文档关键变更会记录在这里。";
  if (isAgentCenterView.value) return "统一查看 Skill、工具注册表和最近 Agent 任务。";
  if (isKnowledgeView.value) return "上传资料、刷新索引，并用带引用的混合检索跨资料查证。";
  return activeWorkspace.value?.description || "跨个人空间、分享文档和公开文档统一查看。";
});
const summaryCount = computed(() => {
  if (isTrashView.value) return trashDocuments.value.length;
  if (isAuditView.value) return auditLogs.value.length;
  if (isAgentCenterView.value) return agentRuns.value.length;
  if (isKnowledgeView.value) return knowledgeStats.value.sourceCount;
  return displayDocuments.value.length;
});

const displayDocuments = computed(() =>
  documentStore.documents.map((doc: any) => ({
    ...doc,
    canDelete: doc.permission === "owner" || doc.permission === "manage"
  }))
);
const ownedCount = computed(
  () => documentStore.documents.filter((d: any) => d.permission === "owner").length
);
const sharedCount = computed(
  () => documentStore.documents.filter((d: any) => d.permission && d.permission !== "owner").length
);

const loadWorkspaces = async () => {
  const { data } = await listWorkspaces();
  workspaces.value = data.data || [];
};

const loadFoldersForActiveWorkspace = async () => {
  if (!activeWorkspaceId.value) {
    folders.value = [];
    return;
  }
  const { data } = await listFolders(activeWorkspaceId.value);
  folders.value = data.data || [];
};

const loadDocumentsForCurrentScope = async () => {
  const { data } = await listDocuments({
    workspaceId: activeWorkspaceId.value || undefined,
    folderId: activeFolderId.value
  });
  documentStore.setDocuments(data.data || []);
};

const loadTrashDocuments = async () => {
  const { data } = await listTrashDocuments();
  trashDocuments.value = data.data || [];
};

const load = async () => {
  await loadWorkspaces();
  await loadFoldersForActiveWorkspace();
  await loadDocumentsForCurrentScope();
};

onMounted(load);

const selectAllDocuments = async () => {
  isTrashView.value = false;
  isAuditView.value = false;
  isAgentCenterView.value = false;
  isKnowledgeView.value = false;
  activeWorkspaceId.value = null;
  activeFolderId.value = null;
  folders.value = [];
  await loadDocumentsForCurrentScope();
};

const selectWorkspace = async (workspaceId: number) => {
  isTrashView.value = false;
  isAuditView.value = false;
  isAgentCenterView.value = false;
  isKnowledgeView.value = false;
  activeWorkspaceId.value = workspaceId;
  activeFolderId.value = null;
  await loadFoldersForActiveWorkspace();
  await loadDocumentsForCurrentScope();
};

const selectFolder = async (folderId: number | null) => {
  isTrashView.value = false;
  isAuditView.value = false;
  isAgentCenterView.value = false;
  isKnowledgeView.value = false;
  activeFolderId.value = folderId;
  await loadDocumentsForCurrentScope();
};

const openTrash = async () => {
  isTrashView.value = true;
  isAuditView.value = false;
  isAgentCenterView.value = false;
  isKnowledgeView.value = false;
  activeFolderId.value = null;
  await loadTrashDocuments();
};

const openAuditLogs = async () => {
  if (!activeWorkspaceId.value) return;
  isTrashView.value = false;
  isAuditView.value = true;
  isAgentCenterView.value = false;
  isKnowledgeView.value = false;
  activeFolderId.value = null;
  const { data } = await listWorkspaceAuditLogs(activeWorkspaceId.value);
  auditLogs.value = data.data || [];
};

const openAgentCenter = async () => {
  isTrashView.value = false;
  isAuditView.value = false;
  isAgentCenterView.value = true;
  isKnowledgeView.value = false;
  activeFolderId.value = null;
  const workspaceId = activeWorkspaceId.value || undefined;
  const [skillsResult, toolsResult, runsResult] = await Promise.allSettled([
    getAgentSkills(workspaceId),
    getAgentTools(),
    getAgentRuns()
  ]);
  agentSkills.value = skillsResult.status === "fulfilled" ? skillsResult.value.data.data || [] : [];
  agentTools.value = toolsResult.status === "fulfilled" ? toolsResult.value.data.data || [] : [];
  agentRuns.value = runsResult.status === "fulfilled" ? runsResult.value.data.data || [] : [];
};

const loadKnowledgeBase = async () => {
  const workspaceId = activeWorkspaceId.value || undefined;
  const [sourcesResult, jobsResult, statsResult] = await Promise.allSettled([
    getKnowledgeSources(workspaceId),
    getKnowledgeJobs(workspaceId),
    getKnowledgeStats(workspaceId)
  ]);
  knowledgeSources.value =
    sourcesResult.status === "fulfilled" ? sourcesResult.value.data.data || [] : [];
  knowledgeJobs.value = jobsResult.status === "fulfilled" ? jobsResult.value.data.data || [] : [];
  knowledgeStats.value =
    statsResult.status === "fulfilled"
      ? statsResult.value.data.data || knowledgeStats.value
      : knowledgeStats.value;
};

const openKnowledgeBase = async () => {
  isTrashView.value = false;
  isAuditView.value = false;
  isAgentCenterView.value = false;
  isKnowledgeView.value = true;
  activeFolderId.value = null;
  knowledgeSearched.value = false;
  knowledgeResults.value = [];
  await loadKnowledgeBase();
};

const handleKnowledgeFile = (event: Event) => {
  const input = event.target as HTMLInputElement;
  pendingKnowledgeFile.value = input.files?.[0] || null;
};

const uploadKnowledge = async () => {
  if (!pendingKnowledgeFile.value) return;
  uploadingKnowledge.value = true;
  try {
    const { data } = await uploadKnowledgeSource(pendingKnowledgeFile.value, {
      workspaceId: activeWorkspaceId.value || undefined
    });
    if (data.success === false) {
      throw new Error(data.message || "知识源上传失败");
    }
    pendingKnowledgeFile.value = null;
    ElMessage.success("知识源已上传并完成索引");
    await loadKnowledgeBase();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || error?.message || "知识源上传失败");
  } finally {
    uploadingKnowledge.value = false;
  }
};

const reindexSource = async (sourceId: number) => {
  try {
    const { data } = await reindexKnowledgeSource(sourceId);
    if (data.success === false) {
      throw new Error(data.message || "重建索引失败");
    }
    ElMessage.success("索引已刷新");
    await loadKnowledgeBase();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || error?.message || "重建索引失败");
  }
};

const createNew = () => {
  if (!canCreateInWorkspace.value) {
    ElMessage.warning("当前空间没有创建权限");
    return;
  }
  createTitle.value = "";
  createPublic.value = false;
  showCreate.value = true;
};

const confirmCreate = async () => {
  const title = createTitle.value.trim();
  if (!title) {
    ElMessage.warning("请输入文档名称");
    return;
  }
  const { data } = await createDocument({
    title,
    content: "",
    isPublic: createPublic.value,
    workspaceId: activeWorkspaceId.value,
    folderId: activeFolderId.value,
    contentFormat: "plain_text"
  });
  ElMessage.success("文档已创建");
  await loadWorkspaces();
  await loadDocumentsForCurrentScope();
  showCreate.value = false;
  router.push(`/editor/${data.data.id}`);
};

const confirmWorkspaceCreate = async () => {
  const name = workspaceName.value.trim();
  if (!name) {
    ElMessage.warning("请输入空间名称");
    return;
  }
  const { data } = await createWorkspace({
    name,
    description: workspaceDescription.value.trim()
  });
  activeWorkspaceId.value = data.data.id;
  activeFolderId.value = null;
  workspaceName.value = "";
  workspaceDescription.value = "";
  showWorkspaceCreate.value = false;
  await load();
  ElMessage.success("空间已创建");
};

const confirmFolderCreate = async () => {
  if (!activeWorkspaceId.value) return;
  const name = folderName.value.trim();
  if (!name) {
    ElMessage.warning("请输入文件夹名称");
    return;
  }
  const { data } = await createFolder(activeWorkspaceId.value, { name });
  activeFolderId.value = data.data.id;
  folderName.value = "";
  showFolderCreate.value = false;
  await loadFoldersForActiveWorkspace();
  await loadDocumentsForCurrentScope();
  ElMessage.success("文件夹已创建");
};

const goEditor = (doc: { id: number }) => router.push(`/editor/${doc.id}`);

const runKnowledgeSearch = async () => {
  if (!knowledgeQuery.value.trim()) return;
  searching.value = true;
  knowledgeSearched.value = true;
  try {
    const { data } = await searchKnowledge(knowledgeQuery.value.trim(), {
      workspaceId: activeWorkspaceId.value || undefined
    });
    knowledgeResults.value = data.data?.results || [];
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || error?.message || "知识库检索失败");
    knowledgeResults.value = [];
  } finally {
    searching.value = false;
  }
};

const openCitation = (item: KnowledgeSearchHit) => {
  if (item.documentId) {
    router.push(`/editor/${item.documentId}`);
    return;
  }
  ElMessage.info("上传资料来源当前仅支持查看引用片段");
};

const clearKnowledgeSearch = () => {
  knowledgeQuery.value = "";
  knowledgeResults.value = [];
  knowledgeSearched.value = false;
};

const openShare = (doc: { id: number; title: string }) => {
  shareDoc.value = doc;
};

const openMove = async (doc: any) => {
  moveDoc.value = doc;
  moveWorkspaceValue.value = doc.workspaceId ? String(doc.workspaceId) : "";
  moveFolderValue.value = doc.folderId ? String(doc.folderId) : "";
  moveFolders.value = [];
  if (moveWorkspaceValue.value) {
    const { data } = await listFolders(Number(moveWorkspaceValue.value));
    moveFolders.value = data.data || [];
  }
  showMoveDialog.value = true;
};

const handleMoveWorkspaceChange = async () => {
  moveFolderValue.value = "";
  moveFolders.value = [];
  if (!moveWorkspaceValue.value) return;
  const { data } = await listFolders(Number(moveWorkspaceValue.value));
  moveFolders.value = data.data || [];
};

const confirmMove = async () => {
  if (!moveDoc.value) return;
  const workspaceId = moveWorkspaceValue.value ? Number(moveWorkspaceValue.value) : null;
  const folderId = moveFolderValue.value ? Number(moveFolderValue.value) : null;
  try {
    await updateDocument(moveDoc.value.id, { workspaceId, folderId });
    showMoveDialog.value = false;
    moveDoc.value = null;
    ElMessage.success("文档位置已更新");
    await loadWorkspaces();
    await loadFoldersForActiveWorkspace();
    await loadDocumentsForCurrentScope();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || error?.message || "移动文档失败");
  }
};

const updateDocumentVisibility = (documentId: number, isPublic: boolean) => {
  documentStore.documents = documentStore.documents.map((doc) =>
    doc.id === documentId ? { ...doc, isPublic } : doc
  );
};

const removeDocument = async (doc: { id: number; title: string }) => {
  await ElMessageBox.confirm(`确定删除"${doc.title}"吗？`, "删除文档", {
    type: "warning",
    confirmButtonText: "删除",
    cancelButtonText: "取消"
  });
  await deleteDocument(doc.id);
  ElMessage.success("文档已移入回收站");
  await loadWorkspaces();
  await loadDocumentsForCurrentScope();
};

const restoreDocument = async (doc: { id: number; title: string }) => {
  await restoreDeletedDocument(doc.id);
  ElMessage.success(`已恢复"${doc.title}"`);
  await loadWorkspaces();
  await loadTrashDocuments();
  await loadDocumentsForCurrentScope();
};

const permanentDelete = async (doc: { id: number; title: string }) => {
  await ElMessageBox.confirm(`彻底删除"${doc.title}"后无法恢复，是否继续？`, "彻底删除", {
    type: "warning",
    confirmButtonText: "彻底删除",
    cancelButtonText: "取消"
  });
  await deleteDocument(doc.id, { permanent: true });
  ElMessage.success("文档已彻底删除");
  await loadWorkspaces();
  await loadTrashDocuments();
};

const roleLabel = (role: string) => {
  const labels: Record<string, string> = {
    owner: "所有者",
    admin: "管理员",
    member: "成员",
    viewer: "访客"
  };
  return labels[role] || role;
};

const sourceLabel = (sourceType: string) => {
  const labels: Record<string, string> = {
    document: "协作文档",
    upload_pdf: "PDF",
    upload_docx: "DOCX",
    upload_markdown: "Markdown",
    upload_text: "TXT"
  };
  return labels[sourceType] || sourceType;
};

const statusLabel = (status: string) => {
  const labels: Record<string, string> = {
    pending: "待索引",
    indexing: "索引中",
    ready: "已索引",
    completed: "已完成",
    running: "运行中",
    failed: "失败"
  };
  return labels[status] || status;
};

const citationLabel = (item: KnowledgeSearchHit) => {
  if (item.pageNumber) return `第 ${item.pageNumber} 页`;
  if (item.locationLabel) return item.locationLabel;
  return `片段 ${item.chunkIndex + 1}`;
};

const logout = () => {
  userStore.logout();
  router.push("/login");
};

const fmtTime = (value?: string | null) => {
  if (!value) return "-";
  return String(value).replace("T", " ").slice(0, 16);
};

const actionLabel = (action: string) => {
  const labels: Record<string, string> = {
    "workspace.create": "创建空间",
    "workspace.update": "更新空间",
    "workspace.member.upsert": "新增或更新成员",
    "workspace.member.remove": "移除成员",
    "folder.create": "创建文件夹",
    "document.create": "创建文档",
    "document.update": "更新文档",
    "document.soft_delete": "移入回收站",
    "document.restore": "恢复文档",
    "document.hard_delete": "彻底删除",
    "document.permission.upsert": "新增或更新文档权限",
    "document.permission.remove": "移除文档权限",
    "document.share_link.create": "创建分享链接",
    "document.share_link.update": "更新分享链接",
    "document.share_link.revoke": "关闭分享链接",
    "document.share_user.upsert": "指定用户分享",
    "document.share_user.remove": "移除指定分享"
  };
  return labels[action] || action;
};

const compactAudit = (log: AuditLogItem) => {
  const payload = Object.keys(log.after || {}).length ? log.after : log.metadata;
  return JSON.stringify(payload);
};

const toolLabel = (tool: string) => {
  const labels: Record<string, string> = {
    recall_memory: "召回记忆",
    search_knowledge: "检索知识库",
    web_search: "联网搜索",
    weather_query: "天气查询",
    get_current_document: "读取文档",
    list_snapshots: "历史版本",
    generate_diff: "生成差异",
    remember: "写入记忆",
    create_snapshot: "创建快照",
    apply_document_content: "写回文档"
  };
  return labels[tool] || tool;
};

const agentStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    queued: "排队中",
    running: "运行中",
    executing: "运行中",
    awaiting_approval: "待审批",
    completed: "已完成",
    failed: "失败",
    cancelled: "已取消"
  };
  return labels[status] || status;
};
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: #f6f7f9;
  color: #172033;
}
.top-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 24px;
  border-bottom: 1px solid #e2e7ef;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(10px);
}
.brand,
.user-chip {
  display: flex;
  align-items: center;
}
.brand {
  gap: 10px;
}
.brand-mark {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 7px;
  background: #2563eb;
  color: #fff;
  font-weight: 800;
}
.brand-name {
  font-size: 15px;
  font-weight: 800;
}
.nav-right {
  position: relative;
}
.user-chip {
  gap: 8px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: #fff;
  padding: 6px 10px;
  cursor: pointer;
  font-size: 13px;
}
.nav-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
}
.chev {
  color: #7a8699;
  font-size: 10px;
}
.user-menu {
  position: absolute;
  top: 40px;
  right: 0;
  min-width: 132px;
  padding: 6px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);
}
.menu-item {
  width: 100%;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #334155;
  cursor: pointer;
  padding: 8px 10px;
  text-align: left;
}
.menu-item:hover {
  background: #f1f5f9;
}
.app-shell {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  min-height: calc(100vh - 56px);
}
.workspace-sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
  border-right: 1px solid #e2e7ef;
  background: #fff;
  padding: 18px 14px;
}
.sidebar-section {
  display: grid;
  gap: 8px;
}
.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}
.section-title button {
  border: none;
  background: transparent;
  color: #2563eb;
  cursor: pointer;
  font-size: 12px;
}
.workspace-item,
.folder-item {
  align-items: center;
  width: 100%;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: #334155;
  cursor: pointer;
  padding: 9px 10px;
  text-align: left;
}
.workspace-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 8px;
}
.workspace-item span:nth-child(2),
.folder-item {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.workspace-item small {
  color: #94a3b8;
  font-size: 11px;
}
.workspace-item:hover,
.workspace-item.active,
.folder-item:hover,
.folder-item.active {
  border-color: #bfdbfe;
  background: #eff6ff;
}
.workspace-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2563eb;
}
.workspace-dot.all {
  background: #16a34a;
}
.folder-item {
  display: block;
  padding-left: 14px;
}
.sidebar-empty {
  margin: 2px 10px 0;
  color: #94a3b8;
  font-size: 12px;
}
.workspace-main {
  min-width: 0;
  padding: 24px;
}
.summary-strip {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 24px;
  align-items: center;
  margin-bottom: 18px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: #fff;
  padding: 18px 20px;
}
.eyebrow {
  color: #2563eb;
  font-size: 11px;
  font-weight: 800;
}
.summary-strip h1,
.search-heading h2 {
  margin: 6px 0 0;
}
.summary-strip h1 {
  font-size: 26px;
}
.summary-strip p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 13px;
}
.primary-action {
  border: 1px solid #2563eb;
  border-radius: 8px;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
  padding: 10px 16px;
  font-weight: 700;
}
.primary-action:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}
.summary-stats {
  display: grid;
  grid-template-columns: repeat(3, 76px);
  gap: 8px;
}
.summary-stats div {
  border-left: 1px solid #e2e8f0;
  padding-left: 12px;
}
.summary-stats strong,
.summary-stats span {
  display: block;
}
.summary-stats strong {
  font-size: 20px;
}
.summary-stats span {
  color: #64748b;
  font-size: 11px;
}
.knowledge-search,
.docs-area {
  margin-bottom: 18px;
}
.knowledge-base-panel {
  display: grid;
  gap: 14px;
}
.knowledge-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 0.75fr);
  gap: 14px;
}
.knowledge-card {
  display: grid;
  gap: 12px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: #fff;
  padding: 14px;
}
.upload-card,
.stats-card {
  align-content: start;
}
.upload-drop {
  display: grid;
  place-items: center;
  min-height: 96px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
  cursor: pointer;
  font-size: 13px;
  padding: 14px;
  text-align: center;
}
.upload-drop input {
  display: none;
}
.knowledge-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.knowledge-stats div {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  padding: 10px;
}
.knowledge-stats strong,
.knowledge-stats span {
  display: block;
}
.knowledge-stats strong {
  color: #172033;
  font-size: 20px;
}
.knowledge-stats span {
  color: #64748b;
  font-size: 11px;
}
.section-heading.inline {
  align-items: baseline;
}
.knowledge-search {
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: #fff;
  padding: 16px;
}
.search-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.knowledge-form {
  display: flex;
  gap: 8px;
  min-width: min(440px, 100%);
}
.knowledge-form input {
  min-width: 0;
  flex: 1;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  outline: none;
  padding: 10px 12px;
}
.knowledge-form input:focus {
  border-color: #2563eb;
}
.knowledge-form button {
  border: 1px solid #2563eb;
  border-radius: 8px;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
  padding: 0 16px;
}
.knowledge-form button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.knowledge-results {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}
.results-meta {
  display: flex;
  justify-content: space-between;
  color: #64748b;
  font-size: 12px;
}
.results-meta button {
  border: none;
  background: transparent;
  color: #2563eb;
  cursor: pointer;
}
.knowledge-result {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  padding: 12px 14px;
}
.knowledge-result:hover {
  border-color: #93c5fd;
}
.result-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
}
.result-top span,
.knowledge-result small {
  color: #64748b;
  font-size: 11px;
}
.knowledge-result p {
  margin: 7px 0;
  color: #334155;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
}
.no-results {
  color: #64748b;
  font-size: 12px;
  padding: 12px 0;
  text-align: center;
}
.trash-panel {
  display: grid;
  gap: 10px;
}
.audit-panel {
  display: grid;
  gap: 10px;
}
.agent-center-panel {
  display: grid;
  gap: 14px;
}
.agent-center-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
  gap: 14px;
}
.agent-center-block {
  display: grid;
  gap: 10px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: #fff;
  padding: 14px;
}
.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #172033;
  font-size: 13px;
  font-weight: 800;
}
.muted {
  color: #64748b;
  font-weight: 600;
}
.agent-center-row,
.agent-run-row {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  padding: 11px 12px;
}
.agent-center-row {
  display: grid;
  gap: 5px;
}
.agent-center-row.compact {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
}
.agent-center-row strong,
.agent-run-row strong {
  overflow: hidden;
  color: #172033;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.agent-center-row p {
  margin: 0;
  color: #475569;
  font-size: 12px;
  line-height: 1.5;
}
.agent-center-row span,
.agent-run-row span,
.agent-run-row time {
  color: #64748b;
  font-size: 11px;
}
.agent-run-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}
.agent-run-row div {
  display: grid;
  gap: 4px;
  min-width: 0;
}
.source-row,
.job-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  padding: 11px 12px;
}
.source-row div {
  display: grid;
  gap: 4px;
  min-width: 0;
}
.source-row strong {
  overflow: hidden;
  color: #172033;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.source-row span,
.job-row span,
.job-row time {
  color: #64748b;
  font-size: 11px;
}
.source-row button {
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  background: #eff6ff;
  color: #1d4ed8;
  cursor: pointer;
  padding: 7px 10px;
  font-size: 12px;
}
.trash-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: #fff;
  padding: 14px 16px;
}
.audit-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(180px, 38%);
  gap: 14px;
  align-items: center;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: #fff;
  padding: 14px 16px;
}
.audit-row strong,
.audit-row span {
  display: block;
}
.audit-row strong {
  color: #172033;
  font-size: 14px;
}
.audit-row span {
  color: #64748b;
  font-size: 12px;
  margin-top: 4px;
}
.audit-row code {
  overflow: hidden;
  border-radius: 6px;
  background: #f8fafc;
  color: #475569;
  font-size: 11px;
  padding: 8px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.trash-row strong,
.trash-row span {
  display: block;
}
.trash-row strong {
  color: #172033;
  font-size: 14px;
}
.trash-row span {
  color: #64748b;
  font-size: 12px;
  margin-top: 4px;
}
.trash-actions {
  display: flex;
  gap: 8px;
}
.trash-actions button {
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: #fff;
  color: #334155;
  cursor: pointer;
  padding: 8px 11px;
}
.trash-actions button:hover {
  border-color: #2563eb;
  color: #2563eb;
}
.trash-actions .danger-action {
  border-color: #fecaca;
  color: #b91c1c;
}
.trash-actions .danger-action:hover {
  border-color: #dc2626;
  background: #fef2f2;
  color: #991b1b;
}
.empty-trash {
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  color: #64748b;
  font-size: 13px;
  padding: 40px 16px;
  text-align: center;
}
.create-form {
  display: grid;
  gap: 14px;
}
.move-form {
  display: grid;
  gap: 14px;
}
.move-doc-title {
  overflow: hidden;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  color: #334155;
  font-size: 13px;
  padding: 10px 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.move-form label {
  display: grid;
  gap: 6px;
  color: #64748b;
  font-size: 12px;
}
.move-form select {
  width: 100%;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: #fff;
  color: #172033;
  padding: 9px 10px;
}
.create-public {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  padding: 12px 14px;
}
.create-public-title,
.create-public-desc {
  display: block;
}
.create-public-title {
  color: #1e293b;
  font-size: 14px;
  font-weight: 700;
}
.create-public-desc {
  color: #64748b;
  font-size: 12px;
  margin-top: 2px;
}
@media (max-width: 960px) {
  .app-shell {
    grid-template-columns: 1fr;
  }
  .workspace-sidebar {
    border-right: none;
    border-bottom: 1px solid #e2e7ef;
  }
  .summary-strip {
    grid-template-columns: 1fr;
  }
  .summary-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .search-heading {
    align-items: stretch;
    flex-direction: column;
  }
  .knowledge-form {
    min-width: 0;
  }
  .agent-center-grid,
  .agent-run-row,
  .agent-center-row.compact,
  .knowledge-grid,
  .source-row,
  .job-row {
    grid-template-columns: 1fr;
  }
  .audit-row {
    grid-template-columns: 1fr;
  }
}
</style>
