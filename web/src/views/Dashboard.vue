<template>
  <div>
    <h2 class="page-title">仪表盘</h2>
    <el-row :gutter="16">
      <el-col :xs="24" :sm="8">
        <el-card class="stat-card" shadow="hover">
          <div class="label">预约尝试</div>
          <div class="value">{{ stats?.total_attempts ?? 0 }}</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card class="stat-card" shadow="hover">
          <div class="label">提交成功</div>
          <div class="value">{{ stats?.submit_success ?? 0 }}</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card class="stat-card" shadow="hover">
          <div class="label">成功率</div>
          <div class="value">{{ rateText }}</div>
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="24">
        <el-card header="服务器定时任务">
          <template v-if="scheduler?.running">
            <p v-for="j in scheduler.jobs" :key="j.id" class="sched-line">
              {{ j.id }}：下次 {{ j.next_run || "—" }}
            </p>
          </template>
          <p v-else class="sched-line">定时任务未运行或已关闭</p>
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="24">
        <el-card header="最近任务">
          <el-table :data="jobs" size="small" stripe>
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="status" label="状态" width="100" />
            <el-table-column prop="progress" label="进度" width="80">
              <template #default="{ row }">{{ row.progress }}%</template>
            </el-table-column>
            <el-table-column prop="dry_run" label="试跑" width="70">
              <template #default="{ row }">{{ row.dry_run ? "是" : "否" }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { jobsApi, recordsApi, settingsApi, type JobItem, type StatsData } from "@/api";

const stats = ref<StatsData | null>(null);
const jobs = ref<JobItem[]>([]);
const scheduler = ref<{ running: boolean; jobs: { id: string; next_run: string | null }[] } | null>(
  null
);

const rateText = computed(() => {
  const r = stats.value?.submit_success_rate ?? 0;
  return `${(r * 100).toFixed(1)}%`;
});

onMounted(async () => {
  stats.value = await recordsApi.stats();
  jobs.value = (await jobsApi.list()).slice(0, 5);
  try {
    scheduler.value = await settingsApi.scheduler();
  } catch {
    scheduler.value = null;
  }
});
</script>

<style scoped>
.label {
  color: #909399;
  font-size: 13px;
}
.sched-line {
  font-size: 13px;
  margin: 4px 0;
}
</style>
