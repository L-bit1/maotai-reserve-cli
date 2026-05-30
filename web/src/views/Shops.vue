<template>
  <div>
    <h2 class="page-title">门店排行</h2>
    <el-form :inline="true" class="filter">
      <el-form-item label="账号">
        <el-select v-model="accountId" placeholder="选择已登录账号" style="width: 200px">
          <el-option
            v-for="a in accounts"
            :key="a.id"
            :label="a.mobile"
            :value="a.id"
            :disabled="!a.has_token"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="商品编码">
        <el-input v-model="itemCode" placeholder="10941" style="width: 120px" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="loadRank">查询排行</el-button>
        <el-button @click="syncShops">同步门店</el-button>
      </el-form-item>
    </el-form>
    <el-alert v-if="sessionId" :title="`场次 sessionId: ${sessionId}`" type="info" show-icon style="margin-bottom: 12px" />
    <el-table :data="rankList" stripe>
      <el-table-column type="index" width="50" />
      <el-table-column prop="name" label="门店" />
      <el-table-column prop="city" label="城市" width="100" />
      <el-table-column prop="inventory" label="库存" width="90" sortable />
      <el-table-column prop="shop_id" label="门店ID" width="160" class-name="hide-mobile" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { accountsApi, shopsApi, type AccountItem, type ShopRankItem } from "@/api";

const accounts = ref<AccountItem[]>([]);
const accountId = ref<number | undefined>();
const itemCode = ref("10941");
const rankList = ref<ShopRankItem[]>([]);
const sessionId = ref("");
const loading = ref(false);

onMounted(async () => {
  const res = await accountsApi.list(1, 100);
  accounts.value = res.items;
  const logged = res.items.find((a) => a.has_token);
  if (logged?.id) accountId.value = logged.id;
});

async function loadRank() {
  if (!accountId.value) {
    ElMessage.warning("请选择已登录账号");
    return;
  }
  loading.value = true;
  try {
    const data = await shopsApi.rank(accountId.value, itemCode.value);
    sessionId.value = data.session_id;
    rankList.value = data.items;
  } finally {
    loading.value = false;
  }
}

async function syncShops() {
  if (!accountId.value) return;
  const r = await shopsApi.sync(accountId.value);
  ElMessage.success(`已同步 ${r.shops} 家门店`);
}
</script>
