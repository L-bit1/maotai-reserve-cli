<template>
  <div>
    <div class="toolbar">
      <h2 class="page-title">中签与付款</h2>
      <el-button type="primary" @click="sync">同步中签结果</el-button>
      <el-button @click="weekend">周末欢乐购</el-button>
      <el-button @click="travel">小茅运旅行</el-button>
      <el-button type="warning" @click="notify">推送待付款</el-button>
      <el-button @click="exportCsv">导出待付款 CSV</el-button>
    </div>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="mb"
      title="统一付款说明"
      description="i茅台中签后须在官方 App 内 24 小时内支付。本页汇总待付款订单并支持提醒，无法代扣。"
    />

    <el-tabs v-model="tab">
      <el-tab-pane label="全部记录" name="all">
        <el-table :data="results" stripe v-loading="loading">
          <el-table-column prop="mobile" label="手机号" width="120" />
          <el-table-column prop="item_name" label="商品" />
          <el-table-column prop="session_name" label="场次" width="120" />
          <el-table-column prop="status" label="申购状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="payment_status" label="付款" width="100">
            <template #default="{ row }">
              <el-tag :type="payTag(row.payment_status)" size="small">{{ payLabel(row.payment_status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="order_id" label="订单号" width="140" />
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="待付款" name="pending">
        <el-table :data="pending" stripe>
          <el-table-column prop="mobile" label="手机号" width="120" />
          <el-table-column prop="item_name" label="商品" />
          <el-table-column prop="order_id" label="订单号" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" type="success" @click="markPaid(row.id)">标记已付</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { lotteryApi, paymentsApi, type LotteryRow } from "@/api";

const tab = ref("pending");
const loading = ref(false);
const results = ref<LotteryRow[]>([]);
const pending = ref<LotteryRow[]>([]);

function statusLabel(s: string) {
  return { waiting: "待公布", failed: "未中签", won: "中签" }[s] || s;
}
function statusTag(s: string) {
  return s === "won" ? "success" : s === "failed" ? "info" : "warning";
}
function payLabel(s: string) {
  return { pending: "待付款", paid: "已付", expired: "已过期", none: "-" }[s] || s;
}
function payTag(s: string) {
  return s === "pending" ? "danger" : s === "paid" ? "success" : "info";
}

async function load() {
  loading.value = true;
  try {
    const [all, pend] = await Promise.all([
      lotteryApi.results(),
      paymentsApi.pending(),
    ]);
    results.value = all.items;
    pending.value = pend.items;
  } finally {
    loading.value = false;
  }
}

async function sync() {
  const r = await lotteryApi.sync(true);
  ElMessage.success(`已同步 ${r.synced} 条${r.errors?.length ? `，${r.errors.length} 个账号失败` : ""}`);
  await load();
}

async function weekend() {
  await lotteryApi.weekendReserve();
  ElMessage.success("周末欢乐购已在后台执行");
}

async function travel() {
  await lotteryApi.travel();
  ElMessage.success("旅行任务已在后台执行");
}

async function notify() {
  const r = await paymentsApi.notify();
  ElMessage.success(r.message || "已推送");
}

async function exportCsv() {
  const blob = await paymentsApi.exportBlob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "pending_payments.csv";
  a.click();
  URL.revokeObjectURL(url);
}

async function markPaid(id: number) {
  await paymentsApi.markPaid(id);
  ElMessage.success("已标记为已付款");
  await load();
}

onMounted(load);
</script>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 16px;
}
.page-title {
  margin: 0;
  flex: 1;
  min-width: 120px;
}
.mb {
  margin-bottom: 16px;
}
</style>
