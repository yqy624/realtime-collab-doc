import { defineStore } from "pinia";

export interface UserState {
  userId: number | null;
  username: string;
  email: string;
  avatarUrl: string;
  token: string;
}

const emptyState = (): UserState => ({
  userId: null,
  username: "",
  email: "",
  avatarUrl: "",
  token: ""
});

export const useUserStore = defineStore("user", {
  state: (): UserState => {
    const raw = sessionStorage.getItem("collab-user");
    return raw ? JSON.parse(raw) as UserState : emptyState();
  },
  getters: {
    isLoggedIn: (state) => Boolean(state.token)
  },
  actions: {
    setUser(payload: UserState) {
      Object.assign(this, payload);
      sessionStorage.setItem("token", payload.token);
      sessionStorage.setItem("collab-user", JSON.stringify(payload));
    },
    logout() {
      Object.assign(this, emptyState());
      sessionStorage.removeItem("token");
      sessionStorage.removeItem("collab-user");
    }
  }
});
