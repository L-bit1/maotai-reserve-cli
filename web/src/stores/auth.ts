import { defineStore } from "pinia";
import { ref } from "vue";
import { authApi } from "@/api";

const TOKEN_KEY = "mt_admin_token";

export const useAuthStore = defineStore("auth", () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || "");
  const username = ref("");

  async function login(user: string, pass: string) {
    const data = await authApi.login(user, pass);
    token.value = data.access_token;
    localStorage.setItem(TOKEN_KEY, data.access_token);
    const me = await authApi.me();
    username.value = me.username;
  }

  async function fetchMe() {
    if (!token.value) return;
    try {
      const me = await authApi.me();
      username.value = me.username;
    } catch {
      logout();
    }
  }

  function logout() {
    token.value = "";
    username.value = "";
    localStorage.removeItem(TOKEN_KEY);
  }

  return { token, username, login, logout, fetchMe };
});
