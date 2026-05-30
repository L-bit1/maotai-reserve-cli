import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/Login.vue"),
      meta: { public: true },
    },
    {
      path: "/",
      component: () => import("@/layouts/MainLayout.vue"),
      children: [
        { path: "", name: "dashboard", component: () => import("@/views/Dashboard.vue") },
        { path: "accounts", name: "accounts", component: () => import("@/views/Accounts.vue") },
        { path: "products", name: "products", component: () => import("@/views/Products.vue") },
        { path: "shops", name: "shops", component: () => import("@/views/Shops.vue") },
        { path: "jobs", name: "jobs", component: () => import("@/views/Jobs.vue") },
        { path: "records", name: "records", component: () => import("@/views/Records.vue") },
        { path: "lottery", name: "lottery", component: () => import("@/views/Lottery.vue") },
        { path: "settings", name: "settings", component: () => import("@/views/Settings.vue") },
      ],
    },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (!to.meta.public && !auth.token) {
    return { name: "login" };
  }
  if (auth.token && !auth.username && to.name !== "login") {
    await auth.fetchMe();
  }
  return true;
});

export default router;
