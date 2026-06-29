<template>
  <main class="home-page">
    <header class="hero">
      <div>
        <span class="tag">MVP workspace</span>
        <h1>欢迎回来，{{ userStore.username }}</h1>
        <p>创建文档、进入实时协作，或和团队直接在文档侧边栏里交流。</p>
      </div>
      <button class="ghost" @click="logout">退出登录</button>
    </header>

    <section class="home-grid">
      <DocumentList
        :documents="displayDocuments"
        @select="goEditor"
        @create="createNew"
        @delete="removeDocument"
      />
      <div class="summary-card">
        <h3>当前 MVP 能力</h3>
        <ul>
          <li>JWT 登录认证</li>
          <li>文档 CRUD</li>
          <li>WebSocket 实时协作</li>
          <li>在线用户状态</li>
          <li>文档内聊天</li>
          <li>远端光标提示</li>
        </ul>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import DocumentList from "../components/DocumentList.vue";
import { createDocument, deleteDocument, listDocuments } from "../api/document";
import { useDocumentStore, useUserStore } from "../store";

const router = useRouter();
const userStore = useUserStore();
const documentStore = useDocumentStore();

const displayDocuments = computed(() =>
  documentStore.documents.map((doc) => ({
    ...doc,
    canDelete: doc.creatorId === userStore.userId
  }))
);

const load = async () => {
  const { data } = await listDocuments();
  documentStore.setDocuments(data.data);
};

onMounted(load);

const createNew = async () => {
  const defaultTitle = `新建协作文档-${Date.now()}`;
  let title = defaultTitle;

  try {
    const { value } = await ElMessageBox.prompt("请输入文档名称", "新建文档", {
      confirmButtonText: "创建",
      cancelButtonText: "取消",
      inputValue: defaultTitle,
      inputPlaceholder: "请输入文档名称"
    });
    title = (value || defaultTitle).trim() || defaultTitle;
  } catch {
    return;
  }

  const { data } = await createDocument({
    title,
    content: "在这里开始输入内容...",
    isPublic: true
  });
  ElMessage.success("文档已创建");
  await load();
  router.push(`/editor/${data.data.id}`);
};

const goEditor = (doc: { id: number }) => {
  router.push(`/editor/${doc.id}`);
};

const removeDocument = async (doc: { id: number; title: string }) => {
  await ElMessageBox.confirm(`确定删除“${doc.title}”吗？`, "删除文档", {
    type: "warning",
    confirmButtonText: "删除",
    cancelButtonText: "取消"
  });
  await deleteDocument(doc.id);
  ElMessage.success("文档已删除");
  await load();
};

const logout = () => {
  userStore.logout();
  router.push("/login");
};
</script>

<style scoped>
.home-page {
  padding: 28px;
  max-width: 1400px;
  margin: 0 auto;
}

.hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  margin-bottom: 24px;
}

.tag {
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  background: #fff;
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
}

h1 {
  margin: 14px 0 10px;
  font-size: clamp(32px, 5vw, 56px);
  line-height: 1;
}

p {
  margin: 0;
  color: var(--muted);
  max-width: 720px;
  line-height: 1.7;
}

.home-grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 22px;
}

.summary-card,
.ghost {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 24px;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.05);
}

.summary-card {
  padding: 24px;
}

.summary-card h3 {
  margin: 0 0 14px;
}

.summary-card ul {
  margin: 0;
  padding-left: 18px;
  color: var(--muted);
  line-height: 1.8;
}

.ghost {
  padding: 12px 16px;
  cursor: pointer;
}

@media (max-width: 900px) {
  .home-grid {
    grid-template-columns: 1fr;
  }

  .hero {
    flex-direction: column;
  }
}
</style>
