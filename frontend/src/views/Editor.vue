<template>
  <main class="editor-page">
    <header class="topbar">
      <button class="back" @click="$router.push('/home')">返回文档列表</button>
      <div class="title-wrap">
        <span class="eyebrow">音go实时协作网 · 实时工作区</span>
        <h1>{{ documentStore.currentDocument?.title || "协作文档" }}</h1>
      </div>
      <div class="topbar-actions">
        <button class="header-btn" @click="toggleInfo">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          <span>文档信息</span>
        </button>
        <button class="header-btn" @click="toggleHistory">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          <span>版本历史</span>
        </button>
        <button
          v-if="canShare"
          class="header-btn share-header-btn"
          @click="showShare = true"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
            <polyline points="16 6 12 2 8 6" />
            <line x1="12" y1="2" x2="12" y2="15" />
          </svg>
          <span>分享</span>
        </button>
      </div>
    </header>

    <section v-if="documentStore.currentDocument" class="workspace">
      <div class="left-rail">
        <UserList :users="onlineUsers" />
        <section class="history-card">
          <div class="history-card-header">
            <h3>用户聊天历史</h3>
            <span>{{ userHistoryRecords.length }}</span>
          </div>
          <p v-if="userHistoryRecords.length === 0" class="history-empty">暂无用户聊天记录</p>
          <button
            v-for="record in userHistoryRecords"
            :key="record.id"
            class="history-record"
            :class="{ active: activeHistory?.selectedId === record.id }"
            type="button"
            @click="openUserHistory(record.id)"
          >
            <strong>{{ record.title }}</strong>
            <span>{{ record.preview }}</span>
            <time v-if="record.createdAt">{{ formatShortDate(record.createdAt) }}</time>
          </button>
        </section>
        <section class="history-card">
          <div class="history-card-header">
            <h3>AI / Agent 历史</h3>
            <span>{{ aiAgentHistoryRecords.length }}</span>
          </div>
          <p v-if="aiAgentHistoryRecords.length === 0" class="history-empty">暂无 AI 或 Agent 记录</p>
          <button
            v-for="record in aiAgentHistoryRecords"
            :key="record.id"
            class="history-record"
            :class="{ active: activeHistory?.selectedId === record.id }"
            type="button"
            @click="openAIAgentHistory(record.id)"
          >
            <strong>{{ record.title }}</strong>
            <span>{{ record.preview }}</span>
            <time v-if="record.createdAt">{{ formatShortDate(record.createdAt) }}</time>
          </button>
        </section>
      </div>
      <DocumentEditor
        v-if="!activeHistory"
        ref="editorRef"
        :title="documentStore.currentDocument.title"
        :content="documentStore.currentDocument.content"
        :revision="documentStore.currentDocument.revision"
        :save-status="saveStatus"
        :online-users="onlineUsers"
        :remote-cursors="remoteCursors"
        @title-change="updateTitle"
        @content-change="handleContentChange"
        @cursor-change="sendCursor"
        @save="handleSave"
        @submit-version="handleSubmitVersion"
      />
      <ChatHistoryViewer
        v-else
        :kind="activeHistory.kind"
        :title="activeHistory.title"
        :subtitle="activeHistory.subtitle"
        :selected-id="activeHistory.selectedId"
        :items="activeHistory.items"
        @back="closeHistoryView"
      />
      <div class="right-panel">
        <nav class="right-tabs" aria-label="协作工具">
          <button
            class="right-tab"
            :class="{ active: activeRightPanel === 'chat' }"
            type="button"
            @click="activeRightPanel = 'chat'"
          >
            聊天
          </button>
          <button
            class="right-tab"
            :class="{ active: activeRightPanel === 'ai' }"
            type="button"
            @click="activeRightPanel = 'ai'"
          >
            AI 助手
          </button>
          <button
            class="right-tab"
            :class="{ active: activeRightPanel === 'agent' }"
            type="button"
            @click="activeRightPanel = 'agent'"
          >
            知识 Agent
          </button>
        </nav>
        <ChatPanel
          v-if="activeRightPanel === 'chat'"
          ref="chatPanelRef"
          :messages="messages"
          :online-users="onlineUsers"
          :current-username="userStore.username"
          :unread-mentions="unreadMentions"
          @send="sendChat"
          @chat-focus="clearUnreadMentions"
        />
        <AIAssistantPanel
          v-else-if="activeRightPanel === 'ai'"
          :document-id="documentId"
          :get-selection="getEditorSelection"
          :append-to-document="appendAIResult"
          :replace-document-selection="replaceAISelection"
          @history-change="loadAssistantHistories"
        />
        <KnowledgeAgentPanel
          v-else
          :scope-document-id="documentId"
          :workspace-id="documentStore.currentDocument.workspaceId"
          @history-change="loadAssistantHistories"
        />
      </div>
    </section>

    <div v-if="showInfo" class="overlay" @click.self="showInfo = false">
      <aside class="slide-panel">
        <header class="panel-header">
          <h2>文档信息</h2>
          <button class="close-btn" @click="showInfo = false">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </header>
        <div class="panel-body" v-if="documentStore.currentDocument">
          <div class="info-row">
            <span class="info-label">文档名称</span>
            <span class="info-value">{{ documentStore.currentDocument.title }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">创建时间</span>
            <span class="info-value">{{ formatDate(documentStore.currentDocument.createdAt) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">最后修改</span>
            <span class="info-value">{{ formatDate(documentStore.currentDocument.updatedAt) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">当前版本</span>
            <span class="info-value">#{{ documentStore.currentDocument.revision }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">权限</span>
            <span class="info-value">{{ documentStore.currentDocument.isPublic ? "公开" : "私有" }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">在线成员</span>
            <span class="info-value">{{ onlineUsers.length }} 人</span>
          </div>
        </div>
      </aside>
    </div>

    <div v-if="showHistory" class="overlay" @click.self="showHistory = false">
      <aside class="slide-panel">
        <header class="panel-header">
          <h2>版本历史</h2>
          <button class="close-btn" @click="showHistory = false">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </header>
        <div class="panel-body">
          <p v-if="loadingHistory" class="loading-text">加载中...</p>
          <p v-else-if="snapshots.length === 0" class="loading-text">暂无历史版本。点击“提交版本”创建记录。</p>
          <div v-else class="snapshot-list">
            <article v-for="snap in snapshots" :key="snap.id" class="snapshot-item" :class="{ 'is-current': snap.revision === documentStore.currentDocument?.revision }">
              <div class="snapshot-meta">
                <strong>版本 #{{ snap.revision }}</strong>
                <span>{{ formatDate(snap.createdAt) }}</span>
                <span class="snapshot-user">由 {{ snap.userName }} 提交</span>
              </div>
              <p class="snapshot-title">{{ snap.title }}</p>
              <div class="snapshot-actions">
                <button class="view-btn" @click="openSnapshot(snap)">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                  <span>查看</span>
                </button>
                <button v-if="snap.revision !== documentStore.currentDocument?.revision" class="restore-btn" @click="handleRestore(snap.id)">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="1 4 1 10 7 10" />
                    <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
                  </svg>
                  <span>恢复</span>
                </button>
                <span v-else class="current-badge">当前版本</span>
              </div>
            </article>
          </div>
        </div>
      </aside>
    </div>

    <div v-if="activeSnapshot" class="overlay snapshot-overlay" @click.self="closeSnapshot">
      <aside class="snapshot-panel">
        <header class="panel-header">
          <div>
            <h2>历史版本</h2>
            <p class="snapshot-caption">{{ formatDate(activeSnapshot.createdAt) }} · 由 {{ activeSnapshot.userName }} 提交</p>
          </div>
          <button class="close-btn" @click="closeSnapshot">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </header>
        <div class="snapshot-view-body">
          <DocumentEditor
            :title="activeSnapshot.title"
            :content="activeSnapshot.content || ''"
            :revision="activeSnapshot.revision"
            :save-status="'saved'"
            :online-users="[]"
            :remote-cursors="[]"
            :readonly="true"
          />
        </div>
      </aside>
    </div>
    <ShareDialog
      v-if="showShare && documentStore.currentDocument"
      :document-id="documentStore.currentDocument.id"
      :title="documentStore.currentDocument.title"
      @close="showShare = false"
      @public-change="updateDocumentVisibility"
    />
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage, ElMessageBox, ElNotification } from "element-plus";
import ChatPanel from "../components/ChatPanel.vue";
import AIAssistantPanel from "../components/AIAssistantPanel.vue";
import KnowledgeAgentPanel from "../components/KnowledgeAgentPanel.vue";
import DocumentEditor from "../components/DocumentEditor.vue";
import ChatHistoryViewer from "../components/ChatHistoryViewer.vue";
import UserList from "../components/UserList.vue";
import ShareDialog from "../components/ShareDialog.vue";
import { fetchMessages, getDocument, getSnapshots, persistDocument, restoreSnapshot, saveDocument, updateDocument } from "../api/document";
import {
  getAgentRuns,
  getAIHistory,
  type AgentRun,
  type AIHistoryItem
} from "../api/ai";
import { CollabSocket } from "../api/websocket";
import { useDocumentStore, useUserStore } from "../store";
import type { TextOperation } from "../utils/ot";

interface SnapshotItem {
  id: number;
  documentId: number;
  title: string;
  content?: string;
  revision: number;
  userId: number;
  userName: string;
  createdAt: string;
}

interface MentionNotificationPayload {
  documentId: number;
  senderName: string;
  senderAvatar?: string;
  message: string;
  createdAt?: string;
}

interface ChatMessageItem {
  id?: number;
  senderName: string;
  senderAvatar?: string;
  message: string;
  createdAt?: string;
}

interface HistoryListRecord {
  id: string;
  title: string;
  preview: string;
  createdAt?: string;
}

interface HistoryViewerItem {
  id: string;
  actor: string;
  role: "user" | "assistant" | "agent" | "system";
  label: string;
  content: string;
  createdAt?: string;
}

interface HistorySelection {
  kind: "user" | "ai";
  title: string;
  subtitle: string;
  selectedId: string;
  items: HistoryViewerItem[];
}

const route = useRoute();
const documentStore = useDocumentStore();
const userStore = useUserStore();
const onlineUsers = ref<string[]>([]);
const remoteCursors = ref<Array<{ userId: number; username: string; cursorPosition: number }>>([]);
const messages = ref<ChatMessageItem[]>([]);
const aiHistory = ref<AIHistoryItem[]>([]);
const agentRuns = ref<AgentRun[]>([]);
const socket = new CollabSocket();

const saveStatus = ref<"saved" | "saving" | "unsaved">("saved");
const showInfo = ref(false);
const showHistory = ref(false);
const showShare = ref(false);
const canShare = computed(
  () => ["owner", "manage"].includes(documentStore.currentDocument?.permission || "")
);
const snapshots = ref<SnapshotItem[]>([]);
const loadingHistory = ref(false);
const activeSnapshot = ref<SnapshotItem | null>(null);
const unreadMentions = ref(0);
const activeRightPanel = ref<"chat" | "ai" | "agent">("chat");
const editorRef = ref<InstanceType<typeof DocumentEditor> | null>(null);
const chatPanelRef = ref<InstanceType<typeof ChatPanel> | null>(null);
const activeHistory = ref<HistorySelection | null>(null);
const pendingEditRequestIds = new Set<string>();

const documentId = Number(route.params.id);

const clip = (value: string, limit = 52) => {
  const normalized = value.replace(/\s+/g, " ").trim();
  return normalized.length > limit ? `${normalized.slice(0, limit)}...` : normalized;
};

const actionLabel = (action: string) => {
  if (action === "summary") return "文档总结";
  if (action === "rewrite") return "选区改写";
  if (action === "agent_query") return "Agent 问答";
  return "AI 提问";
};

const userHistoryRecords = computed<HistoryListRecord[]>(() =>
  [...messages.value]
    .filter((message) => message.id !== undefined)
    .sort((left, right) => {
      const leftTime = left.createdAt ? new Date(left.createdAt).getTime() : 0;
      const rightTime = right.createdAt ? new Date(right.createdAt).getTime() : 0;
      return rightTime - leftTime;
    })
    .slice(0, 12)
    .map((message) => ({
      id: `user-${message.id}`,
      title: message.senderName,
      preview: clip(message.message),
      createdAt: message.createdAt
    }))
);

const aiConversationRecords = computed(() => {
  const rows = [...aiHistory.value].sort((left, right) => left.id - right.id);
  const records: Array<HistoryListRecord & { questionId: number; answer?: AIHistoryItem }> = [];

  rows.forEach((row, index) => {
    if (row.role !== "user") return;
    const answer = rows[index + 1]?.role === "assistant"
      && rows[index + 1]?.action === row.action
      ? rows[index + 1]
      : undefined;
    records.push({
      id: `ai-${row.id}`,
      title: actionLabel(row.action),
      preview: clip(row.content),
      createdAt: row.createdAt,
      questionId: row.id,
      answer
    });
  });
  return records;
});

const aiAgentHistoryRecords = computed<HistoryListRecord[]>(() => [
  ...aiConversationRecords.value.map((record) => ({
    id: record.id,
    title: record.title,
    preview: record.preview,
    createdAt: record.createdAt
  })),
  ...agentRuns.value.map((run) => ({
    id: `agent-${run.runId}`,
    title: "Agent 任务",
    preview: clip(run.goal),
    createdAt: run.updatedAt || run.createdAt
  }))
].sort((left, right) => {
  const leftTime = left.createdAt ? new Date(left.createdAt).getTime() : 0;
  const rightTime = right.createdAt ? new Date(right.createdAt).getTime() : 0;
  return rightTime - leftTime;
}).slice(0, 16));

const loadDocument = async () => {
  const { data: docResp } = await getDocument(documentId);
  documentStore.setCurrentDocument(docResp.data);
  saveStatus.value = "saved";
  try {
    const { data: msgResp } = await fetchMessages(documentId);
    messages.value = msgResp.data;
  } catch {
    messages.value = [];
  }
  await loadAssistantHistories();
};

const loadAssistantHistories = async () => {
  const [aiResult, agentResult] = await Promise.allSettled([
    getAIHistory(documentId),
    getAgentRuns(documentId)
  ]);
  aiHistory.value = aiResult.status === "fulfilled" ? aiResult.value.data.data || [] : [];
  agentRuns.value = agentResult.status === "fulfilled" ? agentResult.value.data.data || [] : [];
};

const focusChatComposer = async () => {
  await chatPanelRef.value?.scrollToLatest();
  chatPanelRef.value?.focusComposer();
};

const clearUnreadMentions = () => {
  unreadMentions.value = 0;
};

const handleMentionNotification = async (payload: unknown) => {
  const mention = payload as MentionNotificationPayload;
  if (mention.documentId !== documentId) {
    return;
  }

  unreadMentions.value += 1;
  ElNotification({
    title: "有人提到了你",
    message: `${mention.senderName}：${mention.message}`,
    type: "warning",
    duration: 5000,
    onClick: async () => {
      clearUnreadMentions();
      await focusChatComposer();
    }
  });
};

const connectSocket = () => {
  socket.connect(documentId, {
    onConnect: () => {
      // JOIN is sent automatically by CollabSocket
    },
    onDisconnect: () => {},
    onDocumentMessage: (payload) => {
      const message = payload as {
        type: string;
        userId?: number;
        username?: string;
        content?: string;
        revision?: number;
        requestId?: string;
        cursorPosition?: number;
        chatMessage?: string;
      };
      if (!documentStore.currentDocument) return;
      if (message.type === "SYNC" || message.type === "EDIT") {
        if (message.type === "EDIT" && message.userId === userStore.userId && message.requestId) {
          pendingEditRequestIds.delete(message.requestId);
        }
        documentStore.setCurrentDocument({
          ...documentStore.currentDocument,
          content: message.content ?? documentStore.currentDocument.content,
          revision: message.revision ?? documentStore.currentDocument.revision
        });
        if (message.type === "SYNC" || (message.userId !== userStore.userId && saveStatus.value !== "unsaved")) {
          saveStatus.value = "saved";
        }
      }
      if (message.type === "CURSOR" && message.userId && message.userId !== userStore.userId) {
        remoteCursors.value = [
          ...remoteCursors.value.filter((cursor) => cursor.userId !== message.userId),
          {
            userId: message.userId,
            username: message.username ?? "未知用户",
            cursorPosition: message.cursorPosition ?? 0
          }
        ];
      }
      if (message.type === "ERROR" && message.username === userStore.username) {
        ElMessage.error(message.chatMessage || "协作同步失败");
      }
    },
    onPresenceMessage: (payload) => {
      const message = payload as { onlineUsers?: string[] };
      onlineUsers.value = message.onlineUsers ?? [];
      remoteCursors.value = remoteCursors.value.filter((cursor) => onlineUsers.value.includes(cursor.username));
    },
    onChatMessage: (payload) => {
      messages.value = [...messages.value, payload as ChatMessageItem];
    },
    onMentionMessage: handleMentionNotification,
    onErrorMessage: (payload) => {
      const message = payload as { message?: string };
      ElMessage.error(message.message || "协作连接异常");
    },
    onWebSocketError: () => {
      ElMessage.error("协作连接异常");
    }
  });
};

onMounted(async () => {
  try {
    await loadDocument();
    connectSocket();
  } catch (error) {
    ElMessage.error((error as Error)?.message || "加载文档失败");
  }
});

onBeforeUnmount(() => {
  socket.disconnect();
});

const handleContentChange = (operation: TextOperation) => {
  const requestId = crypto.randomUUID();
  pendingEditRequestIds.add(requestId);
  saveStatus.value = "unsaved";
  socket.send({
    type: "EDIT",
    documentId,
    userId: userStore.userId,
    operation: {
      ...operation,
      clientId: `${userStore.userId ?? "guest"}`,
      requestId
    }
  });
};

const waitForPendingEdits = async () => {
  const startedAt = Date.now();
  while (pendingEditRequestIds.size > 0) {
    if (Date.now() - startedAt > 5000) {
      return false;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 100));
  }
  return true;
};

const handleSave = async () => {
  if (!documentStore.currentDocument || saveStatus.value !== "unsaved") return;

  saveStatus.value = "saving";
  try {
    const synced = await waitForPendingEdits();
    if (!synced) {
      throw new Error("保存失败，请检查协作连接后重试");
    }
    const { data } = await persistDocument(documentId);
    if (data.success === false) {
      throw new Error(data.message || "保存失败");
    }
    documentStore.setCurrentDocument(data.data);
    saveStatus.value = "saved";
    ElMessage.success("已保存");
  } catch (error: any) {
    saveStatus.value = "unsaved";
    ElMessage.error(error?.response?.data?.message || error?.message || "保存失败");
  }
};

const handleSubmitVersion = async () => {
  if (!documentStore.currentDocument) return;

  const latestContent = editorRef.value?.getText() ?? documentStore.currentDocument.content;
  const defaultTitle = documentStore.currentDocument.title || `文档-${Date.now()}`;
  let title = defaultTitle;

  try {
    const { value } = await ElMessageBox.prompt("请输入提交到历史版本的文档名称", "提交版本", {
      confirmButtonText: "提交",
      cancelButtonText: "取消",
      inputValue: defaultTitle,
      inputPlaceholder: "请输入提交文档名称"
    });
    title = (value || defaultTitle).trim() || defaultTitle;
  } catch {
    return;
  }

  saveStatus.value = "saving";
  try {
    const { data } = await saveDocument(documentId, {
      title,
      content: latestContent
    });
    saveStatus.value = "saved";
    ElMessage.success(`已提交版本 #${data.data.revision}`);
    await loadDocument();
    await loadSnapshots();
    showHistory.value = true;
  } catch (error: any) {
    saveStatus.value = "unsaved";
    ElMessage.error(error?.response?.data?.message || "提交版本失败");
  }
};

const updateTitle = async (title: string) => {
  if (!documentStore.currentDocument) return;
  const { data } = await updateDocument(documentId, {
    ...documentStore.currentDocument,
    title
  });
  documentStore.setCurrentDocument(data.data);
};

const sendCursor = (cursorPosition: number) => {
  socket.send({ type: "CURSOR", documentId, userId: userStore.userId, cursorPosition });
};

const sendChat = (message: string) => {
  socket.send({ type: "CHAT", documentId, userId: userStore.userId, chatMessage: message });
};

const openUserHistory = (selectedId: string) => {
  activeHistory.value = {
    kind: "user",
    title: "用户协作聊天",
    subtitle: "当前文档的用户之间历史消息",
    selectedId,
    items: [...messages.value]
      .sort((left, right) => {
        const leftTime = left.createdAt ? new Date(left.createdAt).getTime() : 0;
        const rightTime = right.createdAt ? new Date(right.createdAt).getTime() : 0;
        return leftTime - rightTime;
      })
      .map((message) => ({
        id: `user-${message.id ?? message.createdAt ?? message.message}`,
        actor: message.senderName,
        role: "user" as const,
        label: "协作消息",
        content: message.message,
        createdAt: message.createdAt
      }))
  };
};

const openAIAgentHistory = (selectedId: string) => {
  if (selectedId.startsWith("ai-")) {
    const questionId = Number(selectedId.slice(3));
    const question = aiHistory.value.find((item) => item.id === questionId);
    if (!question) return;
    const answer = aiHistory.value.find(
      (item) => item.id > question.id && item.role === "assistant" && item.action === question.action
    );
    activeHistory.value = {
      kind: "ai",
      title: actionLabel(question.action),
      subtitle: "AI 助手或知识 Agent 的一次问答记录",
      selectedId,
      items: [
        {
          id: selectedId,
          actor: "我",
          role: "user",
          label: actionLabel(question.action),
          content: question.content,
          createdAt: question.createdAt
        },
        ...(answer
          ? [{
              id: `ai-answer-${answer.id}`,
              actor: question.action === "agent_query" ? "知识 Agent" : "AI 助手",
              role: "assistant" as const,
              label: answer.model || "本地模型",
              content: answer.content,
              createdAt: answer.createdAt
            }]
          : [])
      ]
    };
    return;
  }

  const run = agentRuns.value.find((item) => `agent-${item.runId}` === selectedId);
  if (!run) return;
  const planSummary = run.plan.length
    ? run.plan.map((step, index) => `${index + 1}. ${step.tool} - ${step.status}`).join("\n")
    : "暂无执行计划";
  activeHistory.value = {
    kind: "ai",
    title: "Agent 任务",
    subtitle: `状态：${run.status} · 模型：${run.model || "本地模型"}`,
    selectedId,
    items: [
      {
        id: selectedId,
        actor: "我",
        role: "user",
        label: "任务目标",
        content: run.goal,
        createdAt: run.createdAt
      },
      {
        id: `agent-plan-${run.runId}`,
        actor: "Agent",
        role: "agent",
        label: "执行计划",
        content: planSummary,
        createdAt: run.updatedAt || run.createdAt
      },
      {
        id: `agent-result-${run.runId}`,
        actor: "Agent",
        role: "assistant",
        label: run.error ? "执行失败" : "执行结果",
        content: run.result || run.error || "暂无输出",
        createdAt: run.updatedAt || run.createdAt
      }
    ]
  };
};

const closeHistoryView = () => {
  activeHistory.value = null;
};

type SelectionInfo = { text: string; start: number; end: number };

const getEditorSelection = (): SelectionInfo | null => {
  return editorRef.value?.getSelectionInfo?.() ?? null;
};

const sendFullSync = (content: string) => {
  if (!documentStore.currentDocument) return;
  const requestId = crypto.randomUUID();
  pendingEditRequestIds.add(requestId);
  documentStore.setCurrentDocument({
    ...documentStore.currentDocument,
    content
  });
  saveStatus.value = "unsaved";
  socket.send({
    type: "EDIT",
    documentId,
    userId: userStore.userId,
    operation: {
      type: "FULL_SYNC",
      position: 0,
      content,
      revision: documentStore.currentDocument.revision,
      clientId: `${userStore.userId ?? "guest"}-ai`,
      requestId
    }
  });
};

const appendAIResult = (content: string) => {
  if (!content.trim() || !documentStore.currentDocument) return;
  const current = editorRef.value?.getText() ?? documentStore.currentDocument.content ?? "";
  const separator = current.trim() ? "\n\n" : "";
  sendFullSync(`${current}${separator}${content.trim()}`);
};

const replaceAISelection = (content: string, selection: SelectionInfo) => {
  if (!content.trim() || !documentStore.currentDocument) return;
  const current = editorRef.value?.getText() ?? documentStore.currentDocument.content ?? "";
  const start = Math.max(0, Math.min(selection.start, current.length));
  const end = Math.max(start, Math.min(selection.end, current.length));
  sendFullSync(`${current.slice(0, start)}${content.trim()}${current.slice(end)}`);
};

const updateDocumentVisibility = (isPublic: boolean) => {
  if (!documentStore.currentDocument) return;
  documentStore.setCurrentDocument({
    ...documentStore.currentDocument,
    isPublic
  });
};

const toggleInfo = () => {
  showHistory.value = false;
  showInfo.value = !showInfo.value;
};

const toggleHistory = async () => {
  showInfo.value = false;
  showHistory.value = !showHistory.value;
  if (showHistory.value) {
    await loadSnapshots();
  }
};

const loadSnapshots = async () => {
  loadingHistory.value = true;
  try {
    const { data } = await getSnapshots(documentId);
    snapshots.value = data.data || [];
  } catch {
    snapshots.value = [];
  } finally {
    loadingHistory.value = false;
  }
};

const openSnapshot = (snapshot: SnapshotItem) => {
  activeSnapshot.value = snapshot;
};

const closeSnapshot = () => {
  activeSnapshot.value = null;
};

const handleRestore = async (snapshotId: number) => {
  try {
    await ElMessageBox.confirm(
      "恢复后将使用该历史版本覆盖当前文档内容，是否继续？",
      "恢复历史版本",
      { confirmButtonText: "恢复", cancelButtonText: "取消", type: "warning" }
    );
    await restoreSnapshot(documentId, snapshotId);
    ElMessage.success("已恢复到所选历史版本");
    activeSnapshot.value = null;
    await loadDocument();
    await loadSnapshots();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error?.response?.data?.message || "恢复历史版本失败");
    }
  }
};

const formatDate = (dateStr?: string) => {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
};

const formatShortDate = (dateStr?: string) => {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
};
</script>

<style scoped>
.editor-page {
  padding: 24px;
  max-width: 1600px;
  margin: 0 auto;
}
.topbar {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 22px;
}
.back {
  border: 1px solid var(--line);
  background: white;
  border-radius: 999px;
  padding: 10px 14px;
  cursor: pointer;
}
.title-wrap {
  flex: 1;
}
.title-wrap h1 {
  margin: 8px 0 0;
  font-size: clamp(26px, 4vw, 40px);
}
.eyebrow {
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
}
.topbar-actions {
  display: flex;
  gap: 8px;
}
.header-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: white;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
}
.header-btn:hover {
  background: #f0f4ff;
  border-color: var(--accent);
  color: var(--accent);
}
.workspace {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 360px;
  gap: 20px;
  align-items: start;
}
.right-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 8px;
  min-height: 620px;
}
.right-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 4px;
  padding: 4px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #f8fafc;
}
.right-tab {
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  padding: 8px 10px;
  font-size: 13px;
}
.right-tab.active {
  background: #fff;
  color: var(--accent);
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.08);
}
.left-rail {
  display: grid;
  gap: 20px;
}
.history-card {
  display: grid;
  gap: 10px;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--panel);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.04);
}
.history-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.history-card-header h3 {
  margin: 0;
  font-size: 15px;
}
.history-card-header span {
  min-width: 24px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  text-align: center;
  font-size: 12px;
  font-weight: 700;
  padding: 3px 7px;
}
.history-empty {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
}
.history-record {
  display: grid;
  gap: 4px;
  width: 100%;
  border: 1px solid transparent;
  border-radius: 10px;
  background: #f8fafc;
  color: var(--ink);
  cursor: pointer;
  padding: 10px 12px;
  text-align: left;
}
.history-record:hover,
.history-record.active {
  border-color: var(--accent);
  background: #eff6ff;
}
.history-record strong {
  overflow: hidden;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.history-record span {
  overflow: hidden;
  color: var(--muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.history-record time {
  color: var(--muted);
  font-size: 11px;
}
.overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  justify-content: flex-end;
}
.slide-panel,
.snapshot-panel {
  background: #fff;
  height: 100%;
  overflow-y: auto;
  box-shadow: -8px 0 30px rgba(0, 0, 0, 0.1);
  animation: slideIn 0.2s ease;
}
.slide-panel {
  width: min(420px, 90vw);
}
.snapshot-panel {
  width: min(1100px, 100vw);
}
@keyframes slideIn {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--line);
}
.panel-header h2 {
  margin: 0;
  font-size: 18px;
}
.snapshot-caption {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 12px;
}
.close-btn {
  border: none;
  background: none;
  cursor: pointer;
  padding: 4px;
  border-radius: 8px;
  color: var(--muted);
}
.close-btn:hover {
  background: #f5f5f5;
  color: var(--ink);
}
.panel-body {
  padding: 20px 24px;
}
.snapshot-view-body {
  padding: 20px 24px 28px;
}
.loading-text {
  color: var(--muted);
  text-align: center;
  padding: 40px 0;
}
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}
.info-label {
  font-size: 13px;
  color: var(--muted);
}
.info-value {
  font-size: 14px;
  font-weight: 500;
}
.snapshot-list {
  display: grid;
  gap: 12px;
}
.snapshot-item {
  padding: 14px 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fafbfc;
}
.snapshot-item.is-current {
  border-color: var(--accent);
  background: #f0f4ff;
}
.snapshot-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 6px;
}
.snapshot-meta strong {
  color: var(--ink);
}
.snapshot-user {
  margin-left: auto;
}
.snapshot-title {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 500;
}
.snapshot-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.view-btn,
.restore-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.15s;
}
.view-btn {
  border: 1px solid rgba(37, 99, 235, 0.2);
  background: #eff6ff;
  color: var(--accent);
}
.view-btn:hover {
  background: #dbeafe;
}
.restore-btn {
  border: 1px solid #f59e0b;
  background: #fffbeb;
  color: #b45309;
}
.restore-btn:hover {
  background: #fef3c7;
}
.current-badge {
  font-size: 12px;
  color: var(--accent);
  font-weight: 600;
}
@media (max-width: 1200px) {
  .workspace {
    grid-template-columns: 1fr;
  }
}
</style>
