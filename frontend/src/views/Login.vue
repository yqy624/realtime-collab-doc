<template>
  <main class="auth-page">
    <section class="auth-shell">
      <aside class="brand-panel">
        <div class="brand-header">
          <div class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 48 48" fill="none">
              <path d="M14 27.5V20a10 10 0 0 1 20 0v7.5" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" />
              <path d="M10 25.5v5a4 4 0 0 0 4 4h2.5v-11H14a4 4 0 0 0-4 4ZM38 25.5v5a4 4 0 0 1-4 4h-2.5v-11H34a4 4 0 0 1 4 4Z" fill="currentColor" />
              <path d="M25 37h4" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" />
            </svg>
          </div>
          <span>音go实时协作网</span>
        </div>

        <div class="brand-copy">
          <span class="section-kicker">REAL-TIME CREATIVE SPACE</span>
          <h1>让每一次灵感，<br /><em>都能一起完成。</em></h1>
          <p>把文档、讨论和灵感放在同一个空间里，让团队在同一段声音和文字里保持同步。</p>
        </div>

        <div class="waveform" aria-hidden="true">
          <i v-for="bar in waveformBars" :key="bar" :style="{ height: `${bar}%` }"></i>
        </div>

        <div class="brand-features">
          <div class="feature">
            <span class="feature-icon">01</span>
            <div>
              <strong>实时同步</strong>
              <span>每一次编辑都能即时抵达</span>
            </div>
          </div>
          <div class="feature">
            <span class="feature-icon">02</span>
            <div>
              <strong>一起讨论</strong>
              <span>在文档里直接交流想法</span>
            </div>
          </div>
        </div>

        <span class="panel-note">WRITE TOGETHER · MOVE FURTHER</span>
      </aside>

      <section class="login-panel">
        <div class="login-topline">
          <span class="mobile-brand">音go实时协作网</span>
          <span class="secure-note">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M7 10V8a5 5 0 0 1 10 0v2M6 10h12v10H6V10Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
            </svg>
            安全登录
          </span>
        </div>

        <div class="login-heading">
          <span class="section-kicker">WELCOME BACK</span>
          <h2>欢迎回来</h2>
          <p>登录你的协作空间，继续完成正在进行的创作。</p>
        </div>

        <form class="auth-form" @submit.prevent="submit">
          <label class="field">
            <span>用户名</span>
            <div class="input-wrap">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle cx="12" cy="8" r="3.5" stroke="currentColor" stroke-width="1.8" />
                <path d="M5.5 19c.8-3 3-4.5 6.5-4.5s5.7 1.5 6.5 4.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
              </svg>
              <input
                v-model="form.username"
                autocomplete="username"
                placeholder="输入用户名"
                required
              />
            </div>
          </label>

          <label class="field">
            <span>密码</span>
            <div class="input-wrap">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <rect x="5" y="10" width="14" height="10" rx="2" stroke="currentColor" stroke-width="1.8" />
                <path d="M8 10V7.5a4 4 0 0 1 8 0V10" stroke="currentColor" stroke-width="1.8" />
              </svg>
              <input
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="输入密码"
                required
              />
              <button
                class="password-toggle"
                type="button"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword"
              >
                <svg v-if="showPassword" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M3 3l18 18M10.6 10.6a2 2 0 0 0 2.8 2.8M9.9 5.2A11.3 11.3 0 0 1 12 5c5.2 0 8.5 4.2 9.5 7-.3 1-1.1 2.4-2.3 3.7M6.2 6.2C4.6 7.3 3.5 9 2.5 12c1 2.8 4.3 7 9.5 7 1.1 0 2.1-.2 3-.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M2.5 12s3.5-7 9.5-7 9.5 7 9.5 7-3.5 7-9.5 7-9.5-7-9.5-7Z" stroke="currentColor" stroke-width="1.8" />
                  <circle cx="12" cy="12" r="2.8" stroke="currentColor" stroke-width="1.8" />
                </svg>
              </button>
            </div>
          </label>

          <div class="form-options">
            <span class="demo-hint">演示账号：admin / password123</span>
          </div>

          <button class="submit-button" type="submit" :disabled="isSubmitting">
            <span>{{ isSubmitting ? "正在进入..." : "进入协作空间" }}</span>
            <svg v-if="!isSubmitting" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M5 12h13M13 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span v-else class="loading-spinner" aria-hidden="true"></span>
          </button>

          <p class="register-prompt">
            还没有账号？
            <router-link to="/register">创建一个新账号</router-link>
          </p>
        </form>

        <p class="copyright">© 2026 音go实时协作网 · Create in sync</p>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { loginApi } from "../api/auth";
import { useUserStore } from "../store";

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const showPassword = ref(false);
const isSubmitting = ref(false);
const waveformBars = [34, 52, 76, 48, 92, 58, 38, 70, 100, 62, 44, 80, 54, 36, 66, 88, 46, 72, 40, 60, 84, 50, 32, 68];
const form = reactive({
  username: "admin",
  password: "password123"
});

const submit = async () => {
  if (isSubmitting.value) return;
  isSubmitting.value = true;
  try {
    const { data } = await loginApi(form);
    userStore.setUser(data.data);
    ElMessage.success(`登录成功：${data.data.username}`);
    const redirect = route.query.redirect as string | undefined;
    router.push(redirect || "/home");
  } catch (error: any) {
    const detail = error?.response?.data?.message || error?.message || "登录失败";
    ElMessage.error(detail);
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 28px;
  background: #edf1f6;
}

.auth-shell {
  width: min(1120px, 100%);
  min-height: 680px;
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(390px, 0.92fr);
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.75);
  border-radius: 28px;
  background: #fff;
  box-shadow: 0 30px 80px rgba(29, 42, 68, 0.16);
}

.brand-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 680px;
  overflow: hidden;
  padding: 42px 46px 34px;
  color: #f7fbff;
  background: #101b35;
}

.brand-panel::before,
.brand-panel::after {
  position: absolute;
  content: "";
  border: 1px solid rgba(145, 221, 255, 0.2);
  border-radius: 50%;
  pointer-events: none;
}

.brand-panel::before {
  width: 430px;
  height: 430px;
  right: -190px;
  top: -150px;
}

.brand-panel::after {
  width: 540px;
  height: 540px;
  right: -250px;
  top: -210px;
  border-color: rgba(145, 221, 255, 0.1);
}

.brand-header {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 17px;
  font-weight: 800;
  letter-spacing: 0;
}

.brand-mark {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border: 1px solid rgba(174, 231, 255, 0.55);
  border-radius: 13px;
  color: #9de7ff;
  background: rgba(124, 216, 255, 0.1);
}

.brand-mark svg {
  width: 29px;
  height: 29px;
}

.brand-copy {
  position: relative;
  z-index: 1;
  max-width: 550px;
  margin-top: auto;
}

.section-kicker {
  color: #5da5c4;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.16em;
}

.brand-copy h1 {
  margin: 16px 0 18px;
  color: #fff;
  font-size: clamp(36px, 5vw, 62px);
  line-height: 1.08;
  letter-spacing: 0;
}

.brand-copy h1 em {
  color: #9de7ff;
  font-style: normal;
}

.brand-copy p {
  max-width: 440px;
  margin: 0;
  color: #a9b8d0;
  font-size: 15px;
  line-height: 1.8;
}

.waveform {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  height: 92px;
  margin: 30px 0 28px;
}

.waveform i {
  width: 5px;
  min-height: 14px;
  border-radius: 999px;
  background: #86dfff;
  opacity: 0.84;
}

.waveform i:nth-child(3n) {
  background: #ffd27f;
}

.brand-features {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 14px;
}

.feature {
  display: flex;
  align-items: center;
  gap: 13px;
}

.feature-icon {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border: 1px solid rgba(157, 231, 255, 0.28);
  border-radius: 10px;
  color: #9de7ff;
  font-size: 10px;
  font-weight: 800;
}

.feature strong,
.feature span {
  display: block;
}

.feature strong {
  color: #f5f8ff;
  font-size: 13px;
}

.feature div span {
  margin-top: 3px;
  color: #8495b0;
  font-size: 12px;
}

.panel-note {
  position: relative;
  z-index: 1;
  margin-top: auto;
  padding-top: 34px;
  color: #627896;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.18em;
}

.login-panel {
  display: flex;
  flex-direction: column;
  padding: 48px 58px 30px;
  background: #fff;
}

.login-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 28px;
}

.mobile-brand {
  display: none;
  color: #15223d;
  font-size: 15px;
  font-weight: 800;
}

.secure-note {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #8290a6;
  font-size: 11px;
}

.secure-note svg {
  width: 15px;
  height: 15px;
  color: #24a47b;
}

.login-heading {
  margin: auto 0 34px;
}

.login-heading h2 {
  margin: 13px 0 8px;
  color: #15223d;
  font-size: 35px;
  letter-spacing: 0;
}

.login-heading p {
  max-width: 320px;
  margin: 0;
  color: #8995a8;
  font-size: 13px;
  line-height: 1.7;
}

.auth-form {
  display: grid;
  gap: 19px;
}

.field {
  display: grid;
  gap: 8px;
}

.field > span {
  color: #33415c;
  font-size: 12px;
  font-weight: 700;
}

.input-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 52px;
  border: 1px solid #dce3ec;
  border-radius: 12px;
  padding: 0 14px;
  background: #fbfcfe;
  transition: border-color 0.18s, box-shadow 0.18s, background 0.18s;
}

.input-wrap:focus-within {
  border-color: #48b9d3;
  background: #fff;
  box-shadow: 0 0 0 4px rgba(72, 185, 211, 0.12);
}

.input-wrap > svg {
  flex: 0 0 auto;
  width: 19px;
  height: 19px;
  color: #91a0b5;
}

.input-wrap input {
  width: 100%;
  min-width: 0;
  border: none;
  outline: none;
  color: #1b2a45;
  background: transparent;
  font-size: 14px;
}

.input-wrap input::placeholder {
  color: #aab4c2;
}

.password-toggle {
  display: grid;
  flex: 0 0 auto;
  width: 28px;
  height: 28px;
  place-items: center;
  border: none;
  border-radius: 7px;
  color: #91a0b5;
  background: transparent;
  cursor: pointer;
}

.password-toggle:hover {
  color: #2b8fae;
  background: #edf8fb;
}

.password-toggle svg {
  width: 17px;
  height: 17px;
}

.form-options {
  display: flex;
  justify-content: flex-end;
  margin-top: -4px;
}

.demo-hint {
  color: #98a4b5;
  font-size: 11px;
}

.submit-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 52px;
  border: none;
  border-radius: 12px;
  color: #10213f;
  background: #ffd27f;
  box-shadow: 0 10px 22px rgba(236, 177, 76, 0.24);
  cursor: pointer;
  font-size: 14px;
  font-weight: 800;
  transition: transform 0.18s, box-shadow 0.18s, background 0.18s;
}

.submit-button:hover:not(:disabled) {
  background: #ffca68;
  box-shadow: 0 13px 26px rgba(236, 177, 76, 0.32);
  transform: translateY(-1px);
}

.submit-button:disabled {
  cursor: wait;
  opacity: 0.72;
}

.submit-button svg {
  width: 18px;
  height: 18px;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(16, 33, 63, 0.25);
  border-top-color: #10213f;
  border-radius: 50%;
  animation: spin 0.75s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.register-prompt {
  margin: 0;
  color: #8b98aa;
  font-size: 12px;
  text-align: center;
}

.register-prompt a {
  color: #2b8fae;
  font-weight: 800;
}

.register-prompt a:hover {
  text-decoration: underline;
}

.copyright {
  margin: auto 0 0;
  padding-top: 34px;
  color: #b0bac7;
  font-size: 10px;
  text-align: center;
}

@media (max-width: 820px) {
  .auth-page {
    padding: 16px;
  }

  .auth-shell {
    min-height: auto;
    grid-template-columns: 1fr;
  }

  .brand-panel {
    min-height: 390px;
    padding: 28px 28px 24px;
  }

  .brand-copy {
    margin-top: 56px;
  }

  .brand-copy h1 {
    margin-top: 12px;
    font-size: 38px;
  }

  .waveform {
    height: 52px;
    margin: 22px 0;
  }

  .brand-features {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .panel-note {
    display: none;
  }

  .login-panel {
    padding: 30px 28px 26px;
  }

  .mobile-brand {
    display: inline;
  }

  .login-heading {
    margin: 46px 0 28px;
  }
}

@media (max-width: 480px) {
  .auth-page {
    display: block;
    padding: 0;
  }

  .auth-shell {
    border: none;
    border-radius: 0;
  }

  .brand-panel {
    min-height: 350px;
    border-radius: 0;
  }

  .brand-copy {
    margin-top: 42px;
  }

  .brand-copy h1 {
    font-size: 34px;
  }

  .brand-copy p {
    font-size: 13px;
  }

  .brand-features {
    display: none;
  }

  .login-panel {
    padding: 28px 22px 24px;
  }
}
</style>
