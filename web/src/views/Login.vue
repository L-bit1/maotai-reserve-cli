<template>
  <div class="login-page">
    <el-card class="login-card">
      <h1>茅台抢单管理</h1>
      <p class="sub">Web 管理端 · 后期可扩展手机 App</p>
      <el-form @submit.prevent="onSubmit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="admin" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">
          登录
        </el-button>
      </el-form>
      <el-alert
        v-if="apiDown"
        title="后端未启动：请先运行 ./scripts/start-api.sh，或双击「启动Web+API.command」"
        type="warning"
        show-icon
        :closable="false"
        style="margin-bottom: 12px"
      />
      <p class="hint">默认 admin / admin123 · 须同时启动后端(8000)与前端(5173)</p>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import http from "@/api/http";

const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const apiDown = ref(false);
const form = reactive({ username: "admin", password: "admin123" });

onMounted(async () => {
  try {
    await http.get("/ping", { timeout: 3000 });
    apiDown.value = false;
  } catch {
    apiDown.value = true;
  }
});

async function onSubmit() {
  loading.value = true;
  try {
    await auth.login(form.username, form.password);
    router.push({ name: "dashboard" });
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1d24 0%, #3d1519 50%, #c41e3a 100%);
  padding: 16px;
}
.login-card {
  width: 100%;
  max-width: 400px;
  border-radius: 16px;
}
.login-card h1 {
  margin: 0 0 8px;
  text-align: center;
  color: var(--mt-primary);
}
.sub {
  text-align: center;
  color: #909399;
  font-size: 13px;
  margin-bottom: 24px;
}
.hint {
  font-size: 12px;
  color: #909399;
  margin-top: 16px;
  text-align: center;
}
</style>
