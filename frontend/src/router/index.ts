import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/Home.vue";
import LoginView from "../views/Login.vue";
import RegisterView from "../views/Register.vue";
import EditorView from "../views/Editor.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/home" },
    { path: "/login", component: LoginView },
    { path: "/register", component: RegisterView },
    { path: "/home", component: HomeView, meta: { requiresAuth: true } },
    { path: "/editor/:id", component: EditorView, meta: { requiresAuth: true } }
  ]
});

router.beforeEach((to) => {
  const token = sessionStorage.getItem("token");
  if (to.meta.requiresAuth && !token) {
    return "/login";
  }
  if ((to.path === "/login" || to.path === "/register") && token) {
    return "/home";
  }
  return true;
});

export default router;
