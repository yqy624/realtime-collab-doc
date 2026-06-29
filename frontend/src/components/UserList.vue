<template>
  <section class="user-card">
    <h3>在线成员</h3>
    <div class="users">
      <div v-for="user in users" :key="user" class="user-chip">
        <span class="dot"></span>
        {{ user }}
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  users: string[];
}>();
</script>

<style scoped>
.user-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 24px;
  padding: 20px;
}

h3 {
  margin: 0 0 14px;
}

.users {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--accent-soft);
  color: var(--accent);
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #12b76a;
}
</style>
