<template>
  <div>
    <div class="toolbar">
      <h2 class="page-title">账号管理</h2>
      <div class="toolbar-actions">
        <el-input
          v-model="search"
          placeholder="搜索手机号/城市/备注"
          clearable
          style="width: 220px"
          @keyup.enter="onSearch"
        />
        <el-button @click="onSearch">搜索</el-button>
        <el-upload :show-file-list="false" accept=".csv" :http-request="onImport">
          <el-button>导入 CSV</el-button>
        </el-upload>
        <el-button @click="syncCreds">同步凭证文件</el-button>
        <el-button type="primary" @click="showCreate = true">新增账号</el-button>
      </div>
    </div>
    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="mobile" label="手机号" width="130" />
      <el-table-column prop="city" label="城市" width="100" />
      <el-table-column prop="egress_group" label="出口组" width="90" />
      <el-table-column label="登录" width="90">
        <template #default="{ row }">
          <el-tag :type="row.has_token ? 'success' : 'info'" size="small">
            {{ row.has_token ? "已登" : "未登" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="enabled" label="启用" width="70">
        <template #default="{ row }">{{ row.enabled ? "是" : "否" }}</template>
      </el-table-column>
      <el-table-column label="操作" min-width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="sendCode(row)">发码</el-button>
          <el-button size="small" type="primary" @click="openLogin(row)">登录</el-button>
          <el-button size="small" @click="checkToken(row)">校验</el-button>
          <el-button size="small" type="danger" link @click="remove(row)">删</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[20, 50, 100, 200]"
      layout="total, sizes, prev, pager, next"
      style="margin-top: 12px"
      @change="load"
    />

    <el-dialog v-model="showCreate" title="新增账号" width="90%" style="max-width: 480px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="手机号"><el-input v-model="form.mobile" maxlength="11" /></el-form-item>
        <el-form-item label="省份"><el-input v-model="form.province" /></el-form-item>
        <el-form-item label="城市"><el-input v-model="form.city" /></el-form-item>
        <el-form-item label="出口组"><el-input v-model="form.egress_group" placeholder="ip001" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="create">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showLogin" title="短信登录" width="90%" style="max-width: 400px">
      <p>账号：{{ current?.mobile }}</p>
      <el-input v-model="vcode" placeholder="4-6 位验证码" maxlength="6" />
      <template #footer>
        <el-button @click="showLogin = false">取消</el-button>
        <el-button type="primary" :loading="loginLoading" @click="doLogin">确认登录</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadRequestOptions } from "element-plus";
import { accountsApi, type AccountItem } from "@/api";

const list = ref<AccountItem[]>([]);
const loading = ref(false);
const showCreate = ref(false);
const showLogin = ref(false);
const current = ref<AccountItem | null>(null);
const vcode = ref("");
const loginLoading = ref(false);
const search = ref("");
const page = ref(1);
const pageSize = ref(50);
const total = ref(0);
const form = reactive({
  mobile: "",
  province: "",
  city: "",
  egress_group: "",
});

async function load() {
  loading.value = true;
  try {
    const res = await accountsApi.list(page.value, pageSize.value, search.value || undefined);
    list.value = res.items;
    total.value = res.total;
  } finally {
    loading.value = false;
  }
}

function onSearch() {
  page.value = 1;
  load();
}

async function onImport(opt: UploadRequestOptions) {
  const file = opt.file as File;
  try {
    const r = await accountsApi.importCsv(file);
    ElMessage.success(`导入完成：新增 ${r.created}，更新 ${r.updated}`);
    load();
  } catch (e) {
    ElMessage.error(String(e));
  }
}

async function syncCreds() {
  const r = await accountsApi.syncCredentials();
  ElMessage.success(`已同步 ${r.synced} 个账号`);
}

async function create() {
  await accountsApi.create(form);
  ElMessage.success("已创建");
  showCreate.value = false;
  load();
}

async function sendCode(row: AccountItem) {
  await accountsApi.sendVcode(row.id!);
  ElMessage.success("验证码已发送");
  current.value = row;
}

function openLogin(row: AccountItem) {
  current.value = row;
  vcode.value = "";
  showLogin.value = true;
}

async function doLogin() {
  if (!current.value?.id) return;
  loginLoading.value = true;
  try {
    await accountsApi.login(current.value.id, vcode.value);
    ElMessage.success("登录成功");
    showLogin.value = false;
    load();
  } finally {
    loginLoading.value = false;
  }
}

async function checkToken(row: AccountItem) {
  const res = await accountsApi.validate(row.id!);
  ElMessage.info(res.message);
}

async function remove(row: AccountItem) {
  await ElMessageBox.confirm("确定删除该账号？", "提示");
  await accountsApi.remove(row.id!);
  load();
}

onMounted(load);
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
</style>
