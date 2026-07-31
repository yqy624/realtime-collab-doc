<template>
  <div class="share-overlay" @click.self="close">
    <div class="share-dialog">
      <header class="share-header">
        <div>
          <h3>分享文档</h3>
          <p class="muted">{{ title }}</p>
        </div>
        <button class="icon-btn" @click="close">✕</button>
      </header>

      <div class="share-body">
        <!-- 链接分享 -->
        <section class="share-section">
          <div class="section-title">
            <span class="dot blue"></span>
            <h4>链接分享</h4>
          </div>

          <div v-if="linkMode === 'off'" class="link-off">
            <p class="muted">关闭状态下，只有你和指定用户能访问</p>
            <button class="btn primary" @click="enableLink">开启链接分享</button>
          </div>

          <div v-else class="link-on">
            <div class="link-row">
              <input class="link-input" :value="shareUrl" readonly @focus="selectAll" />
              <button class="btn copy" @click="copyLink">复制</button>
            </div>
            <div class="perm-row">
              <span class="muted">拥有链接的人：</span>
              <div class="seg">
                <button :class="['seg-btn', linkPermission === 'view' && 'on']" @click="setLinkPerm('view')">可查看</button>
                <button :class="['seg-btn', linkPermission === 'edit' && 'on']" @click="setLinkPerm('edit')">可编辑</button>
              </div>
            </div>
          </div>
        </section>

        <!-- 指定人 -->
        <section class="share-section">
          <div class="section-title">
            <span class="dot green"></span>
            <h4>指定用户</h4>
          </div>

          <div class="add-row">
            <input
              v-model="username"
              class="link-input"
              placeholder="输入用户名添加协作者"
              @keyup.enter="addUser"
            />
            <select v-model="newPerm" class="perm-select">
              <option value="view">可查看</option>
              <option value="edit">可编辑</option>
            </select>
            <button class="btn primary" :disabled="!username.trim()" @click="addUser">添加</button>
          </div>

          <div v-if="users.length" class="user-list">
            <div v-for="u in users" :key="u.id" class="user-row">
              <img class="avatar" :src="u.avatarUrl || placeholderAvatar" alt="" />
              <span class="user-name">{{ u.username }}</span>
              <select v-model="u.permission" class="perm-select small" @change="changeUserPerm(u)">
                <option value="view">可查看</option>
                <option value="edit">可编辑</option>
              </select>
              <button class="icon-btn danger" title="移除" @click="removeUser(u)">✕</button>
            </div>
          </div>
          <p v-else class="muted empty">还没有指定用户</p>
        </section>

        <!-- 公开访问 -->
        <section class="share-section">
          <div class="section-title">
            <span class="dot yellow"></span>
            <h4>公开访问</h4>
            <el-switch
              v-model="isPublic"
              size="small"
              :loading="isUpdatingPublic"
              @change="togglePublic"
            />
          </div>
          <p class="muted">公开后，所有登录用户都能在文档列表看到并访问</p>
        </section>
      </div>

      <footer class="share-footer">
        <button class="btn ghost" @click="close">完成</button>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { ElMessage } from "element-plus";
import {
  createShareLink, getShareInfo, revokeShare, updateSharePermission,
  shareToUser, removeShareUser, updateDocument
} from "../api/document";

const props = defineProps<{
  documentId: number;
  title: string;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "public-change", value: boolean): void;
}>();

const placeholderAvatar = "https://ui-avatars.com/api/?name=?&background=ccc&color=fff";

const linkMode = ref<"off" | "on">("off");
const linkPermission = ref<"view" | "edit">("view");
const shareToken = ref("");
const isPublic = ref(false);
const isUpdatingPublic = ref(false);
const users = ref<Array<{ id: number; username: string; avatarUrl: string; permission: string }>>([]);
const username = ref("");
const newPerm = ref<"view" | "edit">("view");

const shareUrl = computed(() => {
  const base = `${window.location.origin}/new`;
  return shareToken.value ? `${base}/share/${shareToken.value}` : "";
});

const load = async () => {
  try {
    const { data } = await getShareInfo(props.documentId);
    const info = data.data;
    shareToken.value = info.shareToken || "";
    linkMode.value = info.shareToken ? "on" : "off";
    linkPermission.value = info.sharePermission || "view";
    isPublic.value = !!info.isPublic;
    users.value = info.users || [];
  } catch (e) {
    // 非所有者查看分享信息会失败，忽略
  }
};

onMounted(load);

const enableLink = async () => {
  const { data } = await createShareLink(props.documentId);
  shareToken.value = data.data.shareToken;
  linkMode.value = "on";
  linkPermission.value = data.data.sharePermission || "view";
  ElMessage.success("链接已开启");
};

const setLinkPerm = async (perm: "view" | "edit") => {
  linkPermission.value = perm;
  await updateSharePermission(props.documentId, perm);
  ElMessage.success(`链接权限已改为${perm === "edit" ? "可编辑" : "可查看"}`);
};

const copyLink = async () => {
  try {
    await navigator.clipboard.writeText(shareUrl.value);
    ElMessage.success("链接已复制");
  } catch {
    ElMessage.warning("复制失败，请手动复制");
  }
};

const selectAll = (e: Event) => {
  (e.target as HTMLInputElement).select();
};

const addUser = async () => {
  const name = username.value.trim();
  if (!name) return;
  try {
    const { data } = await shareToUser(props.documentId, name, newPerm.value);
    users.value = data.data.users || [];
    username.value = "";
    ElMessage.success(`已添加 ${name}`);
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || "添加失败");
  }
};

const changeUserPerm = async (u: { username: string; permission: string }) => {
  try {
    const { data } = await shareToUser(props.documentId, u.username, u.permission);
    users.value = data.data.users || [];
    ElMessage.success("权限已更新");
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || "更新失败");
  }
};

const removeUser = async (u: { id: number }) => {
  try {
    const { data } = await removeShareUser(props.documentId, u.id);
    users.value = data.data.users || [];
    ElMessage.success("已移除");
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || "移除失败");
  }
};

const togglePublic = async (value: boolean | string | number) => {
  const previousValue = isPublic.value;
  const nextValue = value === true;
  isPublic.value = nextValue;
  isUpdatingPublic.value = true;

  try {
    const { data } = await updateDocument(props.documentId, { isPublic: nextValue });
    const savedValue = data.data?.isPublic === true;
    isPublic.value = savedValue;
    emit("public-change", savedValue);
    ElMessage.success(savedValue ? "文档已公开" : "文档已设为私有");
  } catch (e: any) {
    isPublic.value = previousValue;
    ElMessage.error(e.response?.data?.message || "操作失败");
  } finally {
    isUpdatingPublic.value = false;
  }
};

const close = () => emit("close");
</script>

<style scoped>
.share-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}

.share-dialog {
  width: min(520px, 100%);
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.2);
  overflow: hidden;
}

.share-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px 24px 14px;
  border-bottom: 1px solid #eef0f4;
}

.share-header h3 { margin: 0; font-size: 18px; }
.muted { color: #8a94a6; font-size: 13px; margin: 4px 0 0; }

.share-body {
  padding: 16px 24px;
  overflow-y: auto;
  flex: 1;
}

.share-section { margin-bottom: 22px; }
.section-title { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.section-title h4 { margin: 0; font-size: 14px; }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot.blue { background: #3b82f6; }
.dot.green { background: #10b981; }
.dot.yellow { background: #f59e0b; }

.link-off { display: flex; align-items: center; gap: 14px; }
.link-off p { margin: 0; flex: 1; }

.link-row { display: flex; gap: 8px; margin-bottom: 10px; }
.link-input {
  flex: 1;
  padding: 9px 12px;
  border: 1px solid #dfe3ea;
  border-radius: 10px;
  font-size: 13px;
  color: #334155;
  background: #f8fafc;
  min-width: 0;
}
.link-input:focus { outline: none; border-color: #3b82f6; }

.perm-row { display: flex; align-items: center; gap: 10px; }
.seg { display: flex; border: 1px solid #dfe3ea; border-radius: 10px; overflow: hidden; }
.seg-btn {
  padding: 6px 14px;
  border: none;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
  color: #64748b;
}
.seg-btn.on { background: #eff6ff; color: #2563eb; font-weight: 600; }

.add-row { display: flex; gap: 8px; margin-bottom: 12px; }
.perm-select {
  padding: 8px 10px;
  border: 1px solid #dfe3ea;
  border-radius: 10px;
  font-size: 13px;
  background: #fff;
}
.perm-select.small { padding: 4px 6px; font-size: 12px; }

.user-list { display: flex; flex-direction: column; gap: 8px; }
.user-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid #eef0f4;
  border-radius: 12px;
}
.avatar { width: 28px; height: 28px; border-radius: 50%; }
.user-name { flex: 1; font-size: 14px; }
.empty { margin: 0; }

.btn {
  padding: 9px 16px;
  border-radius: 10px;
  border: 1px solid transparent;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.btn.primary { background: #2563eb; color: #fff; }
.btn.primary:disabled { background: #b3c9f5; cursor: not-allowed; }
.btn.copy { background: #f1f5f9; color: #334155; }
.btn.ghost { background: #f8fafc; color: #334155; border-color: #dfe3ea; }

.icon-btn {
  border: none;
  background: transparent;
  font-size: 16px;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px 8px;
}
.icon-btn.danger { color: #ef4444; }

.share-footer {
  padding: 14px 24px;
  border-top: 1px solid #eef0f4;
  display: flex;
  justify-content: flex-end;
}
</style>
