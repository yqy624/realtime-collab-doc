<template>
  <aside class="list-card">
    <div class="list-header">
      <div>
        <h3>文档列表</h3>
        <p>选择已有文档或创建新文档</p>
      </div>
      <button class="primary" @click="$emit('create')">新建</button>
    </div>
    <div class="items">
      <article v-for="doc in documents" :key="doc.id" class="doc-item">
        <button class="doc-main" @click="$emit('select', doc)">
          <strong>{{ doc.title }}</strong>
          <span>版本 {{ doc.revision }} · {{ doc.isPublic ? "公开" : "私有" }}</span>
        </button>
        <button v-if="doc.canDelete" class="danger" @click="$emit('delete', doc)">删除</button>
      </article>
    </div>
  </aside>
</template>

<script setup lang="ts">
defineProps<{
  documents: Array<{ id: number; title: string; revision: number; isPublic?: boolean; canDelete?: boolean }>;
}>();

defineEmits<{
  (e: "select", doc: { id: number; title: string; revision: number; isPublic?: boolean; canDelete?: boolean }): void;
  (e: "create"): void;
  (e: "delete", doc: { id: number; title: string }): void;
}>();
</script>

<style scoped>
.list-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 24px;
  padding: 20px;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.05);
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.list-header h3 {
  margin: 0;
}

.list-header p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.items {
  display: grid;
  gap: 10px;
  overflow: auto;
}

.doc-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
}

.doc-main,
.primary,
.danger {
  border: 1px solid var(--line);
  border-radius: 16px;
  background: white;
  padding: 14px;
  text-align: left;
  cursor: pointer;
}

.doc-main {
  min-width: 0;
}

.primary {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
  font-weight: 600;
  text-align: center;
}

.danger {
  padding: 12px 14px;
  color: #b42318;
  border-color: #fecdca;
  background: #fff5f4;
}

.doc-main strong,
.doc-main span {
  display: block;
}

.doc-main span {
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
}
</style>
