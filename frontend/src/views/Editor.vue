<template>
  <main class="editor-page">
    <header class="topbar">
      <button class="back" @click="$router.push('/home')">返回文档列表</button>
      <div class="title-wrap">
        <span class="eyebrow">Realtime Workspace</span>
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
      </div>
    </header>

    <section v-if="documentStore.currentDocument" class="workspace">
      <div class="left-rail">
        <UserList :users="onlineUsers" />
      </div>
      <DocumentEditor
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
        @submit-version="handleSubmitVersion"
      />
      <ChatPanel
        ref="chatPanelRef"
        :messages="messages"
        :online-users="onlineUsers"
        :current-username="userStore.username"
        :unread-mentions="unreadMentions"
        @send="sendChat"
        @chat-focus="clearUnreadMentions"
      />
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
  </main>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage, ElMessageBox, ElNotification } from "element-plus";
import ChatPanel from "../components/ChatPanel.vue";
import DocumentEditor from "../components/DocumentEditor.vue";
import UserList from "../components/UserList.vue";
import { fetchMessages, getDocument, getSnapshots, restoreSnapshot, saveDocument, updateDocument } from "../api/document";
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

const route = useRoute();
const documentStore = useDocumentStore();
const userStore = useUserStore();
const onlineUsers = ref<string[]>([]);
const remoteCursors = ref<Array<{ userId: number; username: string; cursorPosition: number }>>([]);
const messages = ref<Array<{ id?: number; senderName: string; senderAvatar?: string; message: string; createdAt?: string }>>([]);
const socket = new CollabSocket();

const saveStatus = ref<"saved" | "saving" | "unsaved">("saved");
const showInfo = ref(false);
const showHistory = ref(false);
const snapshots = ref<SnapshotItem[]>([]);
const loadingHistory = ref(false);
const activeSnapshot = ref<SnapshotItem | null>(null);
const unreadMentions = ref(0);
const editorRef = ref<InstanceType<typeof DocumentEditor> | null>(null);
const chatPanelRef = ref<InstanceType<typeof ChatPanel> | null>(null);

const documentId = Number(route.params.id);

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
        cursorPosition?: number;
        chatMessage?: string;
      };
      if (!documentStore.currentDocument) return;
      if (message.type === "SYNC" || message.type === "EDIT") {
        documentStore.setCurrentDocument({
          ...documentStore.currentDocument,
          content: message.content ?? documentStore.currentDocument.content,
          revision: message.revision ?? documentStore.currentDocument.revision
        });
        saveStatus.value = "saved";
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
      messages.value = [...messages.value, payload as { senderName: string; senderAvatar?: string; message: string; createdAt?: string }];
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
  saveStatus.value = "unsaved";
  socket.send({
    type: "EDIT",
    documentId,
    userId: userStore.userId,
    operation: { ...operation, clientId: `${userStore.userId ?? "guest"}` }
  });
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
.left-rail {
  display: grid;
  gap: 20px;
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
