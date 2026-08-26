<template>
  <div class="doc-list">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <h3>{{ activeFilter === "public" ? "公开文档" : "我的文档" }}</h3>
        <span class="count">{{ documents.length }} 份</span>
      </div>
      <div class="toolbar-right">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input v-model="keyword" placeholder="搜索文档..." class="search-input" />
        </div>
        <button class="btn create-btn" @click="$emit('create')">＋ 新建文档</button>
      </div>
    </div>

    <!-- 筛选标签 -->
    <div class="filters">
      <button
        v-for="f in filterTabs"
        :key="f.key"
        :class="['filter-btn', activeFilter === f.key && 'on']"
        @click="activeFilter = f.key"
      >
        {{ f.label }}
      </button>
    </div>

    <!-- 文档卡片网格 -->
    <div v-if="filtered.length" class="card-grid">
      <article
        v-for="doc in filtered"
        :key="doc.id"
        class="doc-card"
        @click="$emit('select', doc)"
      >
        <div class="card-top">
          <span :class="['perm-badge', permClass(doc.permission)]">{{ permLabel(doc) }}</span>
          <span v-if="doc.canDelete" class="del-btn" title="删除" @click.stop="$emit('delete', doc)">🗑</span>
        </div>
        <div class="card-icon">{{ iconOf(doc) }}</div>
        <h4 class="card-title">{{ doc.title }}</h4>
        <p class="card-meta">
          {{ doc.creatorName || "未知" }} · {{ fmtTime(doc.updatedAt) }}
        </p>
        <div class="card-foot">
          <span class="revision">v{{ doc.revision }}</span>
          <div class="card-actions">
            <button
              v-if="doc.permission === 'owner' || doc.permission === 'manage'"
              class="action-btn"
              @click.stop="$emit('move', doc)"
            >移动</button>
            <button
              v-if="doc.permission === 'owner' || doc.permission === 'manage'"
              class="action-btn"
              @click.stop="$emit('share', doc)"
            >分享</button>
          </div>
        </div>
      </article>
    </div>

    <div v-else class="empty-box">
      <div class="empty-icon">📄</div>
      <p v-if="activeFilter === 'public'">暂无公开文档</p>
      <p v-else>还没有文档，点击"新建文档"开始协作</p>
      <button v-if="activeFilter !== 'public'" class="btn create-btn" @click="$emit('create')">＋ 新建文档</button>
      <button v-else class="btn create-btn" @click="activeFilter = 'all'">查看我的文档</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from "vue";

interface Doc {
  id: number;
  title: string;
  revision: number;
  isPublic?: boolean;
  permission?: string;
  creatorName?: string;
  workspaceId?: number | null;
  folderId?: number | null;
  updatedAt?: string;
  canDelete?: boolean;
}

const props = defineProps<{ documents: Doc[] }>();

defineEmits<{
  (e: "select", doc: Doc): void;
  (e: "create"): void;
  (e: "delete", doc: Doc): void;
  (e: "share", doc: Doc): void;
  (e: "move", doc: Doc): void;
}>();

const keyword = ref("");
const activeFilter = ref<"all" | "mine" | "shared" | "public">("all");

// 首页"浏览公开文档"按钮 → 切换到公开文档筛选
const onFilterPublic = () => {
  activeFilter.value = "public";
};
onMounted(() => window.addEventListener("filter-public", onFilterPublic));
onBeforeUnmount(() => window.removeEventListener("filter-public", onFilterPublic));

const filterTabs = [
  { key: "all", label: "全部" },
  { key: "mine", label: "我创建的" },
  { key: "shared", label: "分享给我的" },
  { key: "public", label: "公开的" }
];

const filtered = computed(() => {
  let list = props.documents;
  if (activeFilter.value === "mine") list = list.filter((d) => d.permission === "owner");
  if (activeFilter.value === "shared") list = list.filter((d) => d.permission && d.permission !== "owner");
  if (activeFilter.value === "public") list = list.filter((d) => d.isPublic);
  if (keyword.value.trim()) {
    const kw = keyword.value.trim().toLowerCase();
    list = list.filter((d) => d.title.toLowerCase().includes(kw));
  }
  return list;
});

const permClass = (p?: string) => {
  if (p === "owner" || p === "manage") return "owner";
  if (p === "edit" || p === "comment") return "edit";
  return "view";
};

const permLabel = (doc: Doc) => {
  if (doc.permission === "owner") return "我创建的";
  if (doc.permission === "manage") return "可管理";
  if (doc.permission === "edit") return "可编辑";
  if (doc.permission === "comment") return "可评论";
  if (doc.isPublic) return "公开";
  return "可查看";
};

const iconOf = (doc: Doc) => {
  if (doc.title.includes("欢迎")) return "🎉";
  const colors = ["📘", "📗", "📙", "📕", "📓", "📒"];
  return colors[doc.id % colors.length];
};

const fmtTime = (t?: string) => {
  if (!t) return "";
  return String(t).replace("T", " ").slice(5, 16);
};
</script>

<style scoped>
.doc-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.toolbar-left { display: flex; align-items: baseline; gap: 10px; }
.toolbar-left h3 { margin: 0; font-size: 18px; }
.count { font-size: 12px; color: #8a94a6; }
.toolbar-right { display: flex; gap: 10px; align-items: center; }

.search-box {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f1f5f9;
  border-radius: 12px;
  padding: 0 12px;
}
.search-icon { font-size: 13px; }
.search-input {
  border: none;
  background: transparent;
  padding: 9px 0;
  font-size: 13px;
  width: 160px;
  outline: none;
}

.btn { border: none; border-radius: 12px; cursor: pointer; font-weight: 600; }
.create-btn {
  background: linear-gradient(135deg, #2563eb, #4f46e5);
  color: #fff;
  padding: 10px 18px;
  font-size: 13px;
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.3);
}
.create-btn:hover { transform: translateY(-1px); }

.filters { display: flex; gap: 8px; }
.filter-btn {
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #fff;
  font-size: 12px;
  color: #64748b;
  cursor: pointer;
}
.filter-btn.on { background: #eff6ff; border-color: #3b82f6; color: #2563eb; font-weight: 600; }

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.doc-card {
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 18px;
  padding: 18px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 8px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}
.doc-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.1);
  border-color: #c7d2fe;
}

.card-top { display: flex; justify-content: space-between; align-items: center; }
.perm-badge {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 999px;
  font-weight: 600;
}
.perm-badge.owner { background: #eff6ff; color: #2563eb; }
.perm-badge.edit { background: #ecfdf5; color: #059669; }
.perm-badge.view { background: #f8fafc; color: #64748b; }

.del-btn { font-size: 13px; opacity: 0.5; cursor: pointer; }
.del-btn:hover { opacity: 1; }

.card-icon { font-size: 34px; }
.card-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-meta { margin: 0; font-size: 12px; color: #8a94a6; }

.card-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px dashed #eef0f4;
}
.revision { font-size: 11px; color: #b0b8c4; }
.card-actions {
  display: flex;
  gap: 6px;
}
.action-btn {
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  padding: 4px 10px;
  font-size: 12px;
  color: #475569;
  cursor: pointer;
}
.action-btn:hover { border-color: #3b82f6; color: #2563eb; }

.empty-box {
  text-align: center;
  padding: 60px 20px;
  border: 2px dashed #e2e8f0;
  border-radius: 20px;
  color: #8a94a6;
}
.empty-icon { font-size: 40px; margin-bottom: 10px; }
.empty-box p { margin: 0 0 16px; }
</style>
