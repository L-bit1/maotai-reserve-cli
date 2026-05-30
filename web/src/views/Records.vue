<template>
  <div>
    <h2 class="page-title">预约记录</h2>
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="8">
        <el-statistic title="总尝试" :value="stats?.total_attempts ?? 0" />
      </el-col>
      <el-col :span="8">
        <el-statistic title="成功" :value="stats?.submit_success ?? 0" />
      </el-col>
      <el-col :span="8">
        <el-statistic title="成功率" :value="ratePct" suffix="%" />
      </el-col>
    </el-row>
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="account_id" label="账号ID" width="80" />
      <el-table-column prop="item_name" label="商品" />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="message" label="结果" show-overflow-tooltip />
      <el-table-column prop="reserved_at" label="时间" width="170" class-name="hide-mobile" />
    </el-table>
    <el-pagination
      v-model:current-page="page"
      :page-size="20"
      :total="total"
      layout="prev, pager, next"
      style="margin-top: 16px"
      @current-change="load"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { recordsApi, type RecordItem, type StatsData } from "@/api";

const list = ref<RecordItem[]>([]);
const stats = ref<StatsData | null>(null);
const page = ref(1);
const total = ref(0);

const ratePct = computed(() =>
  ((stats.value?.submit_success_rate ?? 0) * 100).toFixed(1)
);

async function load() {
  const [s, r] = await Promise.all([
    recordsApi.stats(),
    recordsApi.list({ page: page.value }),
  ]);
  stats.value = s;
  list.value = r.items;
  total.value = r.total;
}

onMounted(load);
</script>
