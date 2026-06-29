<template>
  <main class="auth-page">
    <section class="auth-card">
      <div class="copy">
        <span class="eyebrow">创建账号</span>
        <h1>开始你的协作空间</h1>
        <p>注册后即可创建文档、邀请同学协作，并使用实时聊天进行讨论。</p>
      </div>
      <form class="auth-form" @submit.prevent="submit">
        <input v-model="form.username" placeholder="用户名" />
        <input v-model="form.email" type="email" placeholder="邮箱" />
        <input v-model="form.password" type="password" placeholder="密码" />
        <button type="submit">注册</button>
        <router-link to="/login">已有账号？去登录</router-link>
      </form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { registerApi } from "../api/auth";

const router = useRouter();
const form = reactive({
  username: "",
  email: "",
  password: ""
});

const submit = async () => {
  try {
    await registerApi(form);
    ElMessage.success("注册成功，请登录");
    router.push("/login");
  } catch (error) {
    ElMessage.error("注册失败，请检查输入信息");
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
  grid-template-columns: 1.05fr 0.95fr;
  gap: 26px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(18px);
  border-radius: 34px;
  padding: 32px;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.12);
}

.copy {
  background: linear-gradient(135deg, #ecfff5, #edf4ff);
  border-radius: 28px;
  padding: 32px;
}

.eyebrow {
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  background: white;
  color: #127c56;
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
  background: #127c56;
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
