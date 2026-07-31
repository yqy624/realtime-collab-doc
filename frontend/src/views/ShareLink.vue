<template>
  <main class="share-page">
    <div class="share-card">
      <div class="card-icon">📄</div>
      <h2>{{ doc?.title || "加载中..." }}</h2>
      <p class="muted" v-if="doc">
        由 {{ doc.creatorName || "用户" }} 分享 · 最后修改 {{ fmtTime(doc.updatedAt) }}
      </p>
      <p class="muted" v-if="!loading && !doc">链接无效或文档已被删除</p>

      <div class="actions">
        <button v-if="!userStore.token" class="btn primary" @click="goLogin">登录后查看</button>
        <button v-if="userStore.token && doc" class="btn primary" @click="openDoc">打开文档</button>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { accessShareToken } from "../api/document";
import { useUserStore } from "../store";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const doc = ref<any>(null);
const loading = ref(true);

onMounted(async () => {
  const token = String(route.params.token || "");
  if (!token) {
    loading.value = false;
    return;
  }
  try {
    const { data } = await accessShareToken(token);
    doc.value = data.data;
  } catch {
    doc.value = null;
  }
  loading.value = false;
});

const openDoc = () => {
  if (doc.value) router.push(`/editor/${doc.value.id}`);
};

const goLogin = () => {
  router.push(`/login?redirect=/share/${route.params.token}`);
};

const fmtTime = (t?: string) => {
  if (!t) return "";
  return String(t).replace("T", " ").slice(0, 16);
};
</script>

<style scoped>
.share-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 50%, #ecfdf5 100%);
  padding: 20px;
}
.share-card {
  background: #fff;
  border-radius: 24px;
  padding: 48px 56px;
  text-align: center;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.12);
  max-width: 420px;
}
.card-icon { font-size: 48px; margin-bottom: 12px; }
h2 { margin: 0 0 8px; color: #0f172a; }
.muted { color: #8a94a6; font-size: 13px; margin: 4px 0 24px; }
.actions { margin-top: 20px; }
.btn {
  border: none;
  border-radius: 12px;
  padding: 12px 32px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}
.btn.primary {
  background: linear-gradient(135deg, #2563eb, #4f46e5);
  color: #fff;
}
.btn.primary:hover { transform: translateY(-1px); }
</style>
