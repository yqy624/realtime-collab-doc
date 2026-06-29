<template>
  <main class="auth-page">
    <section class="auth-card">
      <div class="copy">
        <span class="eyebrow">RealTimeCollabDoc</span>
        <h1>登录协作文档系统</h1>
        <p>使用你的账号进入实时协作空间，继续编辑、讨论和同步文档。</p>
      </div>
      <form class="auth-form" @submit.prevent="submit">
        <input v-model="form.username" placeholder="用户名" />
        <input v-model="form.password" type="password" placeholder="密码" />
        <button type="submit">登录</button>
        <router-link to="/register">没有账号？去注册</router-link>
      </form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { loginApi } from "../api/auth";
import { useUserStore } from "../store";

const router = useRouter();
const userStore = useUserStore();
const form = reactive({
  username: "admin",
  password: "password123"
});

const submit = async () => {
  try {
    const { data } = await loginApi(form);
    userStore.setUser(data.data);
    ElMessage.success(`登录成功：${data.data.username}`);
    router.push("/home");
  } catch (error: any) {
    const detail = error?.response?.data?.message || error?.message || "登录失败";
    ElMessage.error(detail);
  }
};
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
}

.auth-card {
  width: min(960px, 100%);
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 26px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(18px);
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 34px;
  padding: 32px;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.12);
}

.copy {
  background: linear-gradient(135deg, #fff9ec, #ebf6ff);
  border-radius: 28px;
  padding: 32px;
}

.eyebrow {
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  background: white;
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
}

h1 {
  margin: 18px 0 10px;
  font-size: clamp(34px, 5vw, 52px);
  line-height: 1.05;
}

p {
  color: var(--muted);
  line-height: 1.7;
}

.auth-form {
  display: grid;
  gap: 14px;
  align-content: center;
}

input,
button {
  border-radius: 18px;
  border: 1px solid var(--line);
  padding: 15px 16px;
}

button {
  border: none;
  background: var(--accent);
  color: white;
  font-weight: 700;
  cursor: pointer;
}

@media (max-width: 840px) {
  .auth-card {
    grid-template-columns: 1fr;
  }
}
</style>
