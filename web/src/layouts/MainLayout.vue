<template>
  <el-container class="layout">
    <el-aside :width="collapsed ? '64px' : '220px'" class="aside">
      <div class="logo">
        <span v-if="!collapsed">茅台抢单</span>
        <span v-else>茅</span>
      </div>
      <el-menu
        :default-active="route.name as string"
        router
        background-color="#1a1d24"
        text-color="#bfcbd9"
        active-text-color="#fff"
        :collapse="collapsed"
      >
        <el-menu-item index="dashboard" :route="{ name: 'dashboard' }">
          <el-icon><Odometer /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="accounts" :route="{ name: 'accounts' }">
          <el-icon><User /></el-icon>
          <span>账号管理</span>
        </el-menu-item>
        <el-menu-item index="products" :route="{ name: 'products' }">
          <el-icon><Goods /></el-icon>
          <span>商品管理</span>
        </el-menu-item>
        <el-menu-item index="shops" :route="{ name: 'shops' }">
          <el-icon><Shop /></el-icon>
          <span>门店排行</span>
        </el-menu-item>
        <el-menu-item index="jobs" :route="{ name: 'jobs' }">
          <el-icon><Timer /></el-icon>
          <span>任务中心</span>
        </el-menu-item>
        <el-menu-item index="records" :route="{ name: 'records' }">
          <el-icon><Document /></el-icon>
          <span>预约记录</span>
        </el-menu-item>
        <el-menu-item index="lottery" :route="{ name: 'lottery' }">
          <el-icon><Trophy /></el-icon>
          <span>中签与付款</span>
        </el-menu-item>
        <el-menu-item index="settings" :route="{ name: 'settings' }">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <el-button text class="hide-mobile" @click="collapsed = !collapsed">
          <el-icon><Fold /></el-icon>
        </el-button>
        <span class="header-title">{{ titleMap[route.name as string] || "" }}</span>
        <div class="header-right">
          <span class="user">{{ auth.username }}</span>
          <el-button type="danger" link @click="onLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const collapsed = ref(false);

const titleMap: Record<string, string> = {
  dashboard: "仪表盘",
  accounts: "账号管理",
  products: "商品管理",
  shops: "门店排行",
  jobs: "任务中心",
  records: "预约记录",
  lottery: "中签与付款",
  settings: "系统设置",
};

function onLogout() {
  auth.logout();
  router.push({ name: "login" });
}
</script>

<style scoped>
.layout {
  min-height: 100vh;
}
.aside {
  background: var(--mt-sidebar);
  transition: width 0.2s;
}
.logo {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 18px;
  border-bottom: 1px solid #2d3139;
}
.header {
  display: flex;
  align-items: center;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.header-title {
  flex: 1;
  font-weight: 600;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.user {
  color: #606266;
  font-size: 14px;
}
.main {
  padding: 16px;
}
@media (max-width: 768px) {
  .aside {
    position: fixed;
    z-index: 100;
    height: 100%;
  }
  .main {
    padding: 12px;
  }
}
</style>
