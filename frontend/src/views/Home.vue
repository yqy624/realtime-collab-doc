<template>
  <main class="home-page">
    <!-- 顶部导航 -->
    <header class="top-nav">
      <div class="brand">
        <span class="brand-logo">✍️</span>
        <span class="brand-name">音go实时协作网</span>
      </div>
      <div class="nav-right">
        <div class="user-chip" @click="showUserMenu = !showUserMenu">
          <img :src="userStore.avatarUrl || placeholderAvatar" class="nav-avatar" alt="" />
          <span>{{ userStore.username }}</span>
          <span class="chev">▾</span>
        </div>
        <div v-if="showUserMenu" class="user-menu">
          <div class="menu-item" @click="logout">🚪 退出登录</div>
        </div>
      </div>
    </header>

    <!-- Hero -->
    <section class="hero">
      <div class="hero-text">
        <span class="tag">✦ 实时协作空间</span>
        <h1>一起创作，<br />实时同步</h1>
        <p>创建文档、邀请协作者、在文档内实时交流——所有编辑即时同步。</p>
        <div class="hero-actions">
          <button class="btn primary-big" @click="createNew">＋ 新建文档</button>
          <button class="btn ghost-big" @click="goPublic">🌐 浏览公开文档</button>
        </div>
      </div>
      <div class="hero-stats">
        <div class="stat-card">
          <span class="stat-num">{{ documentStore.documents.length }}</span>
          <span class="stat-label">我的文档</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ ownedCount }}</span>
          <span class="stat-label">我创建的</span>
        </div>
        <div class="stat-card">
          <span class="stat-num">{{ sharedCount }}</span>
          <span class="stat-label">分享给我的</span>
        </div>
      </div>
    </section>

    <!-- 文档区域 -->
    <section class="knowledge-search">
      <div class="search-heading">
        <div>
          <span class="tag">RAG KNOWLEDGE SEARCH</span>
          <h2>从可访问文档中找答案依据</h2>
          <p>按关键词检索文档片段，结果会显示来源文档和命中位置。</p>
        </div>
        <form class="knowledge-form" @submit.prevent="runKnowledgeSearch">
          <input
            v-model="knowledgeQuery"
            placeholder="输入关键词，例如：协作、风险、版本历史"
            aria-label="知识库关键词"
          />
          <button type="submit" :disabled="searching || !knowledgeQuery.trim()">
            {{ searching ? "检索中..." : "检索" }}
          </button>
        </form>
      </div>
      <div v-if="knowledgeSearched" class="knowledge-results">
        <div class="results-meta">
          <span>共命中 {{ knowledgeResults.length }} 个片段</span>
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
            <span>片段 {{ item.chunkIndex + 1 }} · {{ Math.round(item.score * 100) }}%</span>
          </div>
          <p>{{ item.content }}</p>
          <small>命中：{{ item.matchedTerms.join("、") }}</small>
        </article>
        <div v-if="knowledgeResults.length === 0" class="no-results">
          没有在当前可访问文档中找到相关片段。
        </div>
      </div>
    </section>

    <section class="docs-area">
      <DocumentList
        :documents="displayDocuments"
        @select="goEditor"
        @create="createNew"
        @delete="removeDocument"
        @share="openShare"
      />
    </section>

    <!-- 新建文档弹窗 -->
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

    <!-- 分享弹窗 -->
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
import { searchKnowledge, type KnowledgeSearchHit } from "../api/ai";
import { createDocument, deleteDocument, listDocuments } from "../api/document";
import { useDocumentStore, useUserStore } from "../store";

const router = useRouter();
const userStore = useUserStore();
const documentStore = useDocumentStore();

const placeholderAvatar = "https://ui-avatars.com/api/?name=?&background=6366f1&color=fff";
const showUserMenu = ref(false);
const shareDoc = ref<{ id: number; title: string } | null>(null);
const showCreate = ref(false);
const createTitle = ref("");
const createPublic = ref(false);
const knowledgeQuery = ref("");
const knowledgeResults = ref<KnowledgeSearchHit[]>([]);
const knowledgeSearched = ref(false);
const searching = ref(false);

const displayDocuments = computed(() =>
  documentStore.documents.map((doc: any) => ({
    ...doc,
    canDelete: doc.creatorId === userStore.userId
  }))
);

const ownedCount = computed(
  () => documentStore.documents.filter((d: any) => d.permission === "owner").length
);
const sharedCount = computed(
  () => documentStore.documents.filter((d: any) => d.permission && d.permission !== "owner").length
);

const load = async () => {
  const { data } = await listDocuments();
  documentStore.setDocuments(data.data || []);
};

onMounted(load);

const createNew = () => {
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
    isPublic: createPublic.value
  });
  ElMessage.success(createPublic.value ? "公开文档已创建" : "文档已创建");
  await load();
  showCreate.value = false;
  router.push(`/editor/${data.data.id}`);
};

const goEditor = (doc: { id: number }) => router.push(`/editor/${doc.id}`);

const runKnowledgeSearch = async () => {
  if (!knowledgeQuery.value.trim()) return;
  searching.value = true;
  knowledgeSearched.value = true;
  try {
    const { data } = await searchKnowledge(knowledgeQuery.value.trim());
    knowledgeResults.value = data.data?.results || [];
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || error?.message || "知识库检索失败");
    knowledgeResults.value = [];
  } finally {
    searching.value = false;
  }
};

const clearKnowledgeSearch = () => {
  knowledgeQuery.value = "";
  knowledgeResults.value = [];
  knowledgeSearched.value = false;
};

const goPublic = () => {
  // 触发筛选公开文档
  window.dispatchEvent(new CustomEvent("filter-public"));
};

const openShare = (doc: { id: number; title: string }) => {
  shareDoc.value = doc;
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
  ElMessage.success("文档已删除");
  await load();
};

const logout = () => {
  userStore.logout();
  router.push("/login");
};
</script>

<style scoped>
.home-page { min-height: 100vh; background: #f8fafc; }

/* 顶部导航 */
.top-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 32px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid #eef0f4;
}
.brand { display: flex; align-items: center; gap: 10px; }
.brand-logo { font-size: 22px; }
.brand-name { font-weight: 800; font-size: 17px; color: #1e293b; }

.nav-right { position: relative; }
.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 999px;
  cursor: pointer;
  background: #f1f5f9;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}
.nav-avatar { width: 26px; height: 26px; border-radius: 50%; }
.chev { font-size: 10px; color: #94a3b8; }

.user-menu {
  position: absolute;
  right: 0;
  top: 44px;
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.12);
  padding: 6px;
  min-width: 140px;
  z-index: 200;
}
.menu-item {
  padding: 9px 12px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  color: #334155;
}
.menu-item:hover { background: #f8fafc; }

/* Hero */
.hero {
  max-width: 1200px;
  margin: 0 auto;
  padding: 48px 32px 32px;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 32px;
  flex-wrap: wrap;
}
.tag {
  display: inline-block;
  padding: 5px 12px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}
.hero h1 {
  font-size: clamp(34px, 5vw, 56px);
  line-height: 1.12;
  margin: 16px 0 12px;
  color: #0f172a;
  letter-spacing: -0.5px;
}
.hero p { color: #64748b; font-size: 15px; max-width: 460px; line-height: 1.7; margin: 0 0 24px; }

.hero-actions { display: flex; gap: 12px; }
.btn { border: none; border-radius: 14px; cursor: pointer; font-weight: 700; font-size: 14px; }
.primary-big {
  background: linear-gradient(135deg, #2563eb, #4f46e5);
  color: #fff;
  padding: 13px 26px;
  box-shadow: 0 8px 24px rgba(79, 70, 229, 0.35);
}
.primary-big:hover { transform: translateY(-2px); }
.ghost-big {
  background: #fff;
  color: #334155;
  padding: 13px 26px;
  border: 1px solid #e2e8f0;
}
.ghost-big:hover { border-color: #3b82f6; color: #2563eb; }

.hero-stats { display: flex; gap: 14px; }
.stat-card {
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 16px;
  padding: 16px 22px;
  text-align: center;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
  min-width: 90px;
}
.stat-num { display: block; font-size: 26px; font-weight: 800; color: #4f46e5; }
.stat-label { font-size: 12px; color: #94a3b8; }

/* 文档区 */
.docs-area { max-width: 1200px; margin: 0 auto; padding: 0 32px 48px; }

.knowledge-search {
  max-width: 1200px;
  margin: 0 auto 28px;
  padding: 0 32px;
}
.search-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
  padding: 24px;
  background: #fff;
  border: 1px solid #dbe4f0;
  border-radius: 16px;
}
.search-heading h2 { margin: 12px 0 6px; color: #0f172a; font-size: 22px; }
.search-heading p { margin: 0; color: #64748b; font-size: 13px; }
.knowledge-form { display: flex; gap: 8px; min-width: min(460px, 100%); }
.knowledge-form input {
  min-width: 0;
  flex: 1;
  border: 1px solid #dbe4f0;
  border-radius: 9px;
  padding: 11px 12px;
  outline: none;
  font-size: 13px;
}
.knowledge-form input:focus { border-color: #3b82f6; }
.knowledge-form button {
  border: 1px solid #2563eb;
  border-radius: 9px;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
  padding: 0 18px;
  font-size: 13px;
}
.knowledge-form button:disabled { cursor: not-allowed; opacity: .5; }
.knowledge-results { display: grid; gap: 8px; margin-top: 10px; }
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
  font-size: 12px;
}
.knowledge-result {
  padding: 14px 16px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  cursor: pointer;
}
.knowledge-result:hover { border-color: #93c5fd; }
.result-top { display: flex; justify-content: space-between; gap: 12px; font-size: 13px; }
.result-top span, .knowledge-result small { color: #64748b; font-size: 11px; }
.knowledge-result p { margin: 7px 0; color: #334155; font-size: 12px; line-height: 1.6; white-space: pre-wrap; }
.no-results { padding: 22px; color: #64748b; text-align: center; font-size: 12px; }

/* 新建文档弹窗 */
.create-form { display: flex; flex-direction: column; gap: 16px; }
.create-public {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px solid #eef0f4;
  border-radius: 12px;
}
.create-public-title { display: block; font-size: 14px; font-weight: 600; color: #1e293b; }
.create-public-desc { display: block; font-size: 12px; color: #94a3b8; margin-top: 2px; }

@media (max-width: 768px) {
  .top-nav { padding: 12px 16px; }
  .hero { padding: 32px 16px 24px; }
  .docs-area { padding: 0 16px 32px; }
  .knowledge-search { padding: 0 16px; }
  .search-heading { align-items: stretch; flex-direction: column; padding: 18px; }
  .knowledge-form { min-width: 0; }
  .hero-stats { width: 100%; }
  .stat-card { flex: 1; }
}
</style>
