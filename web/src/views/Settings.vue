<template>
  <div>
    <h2 class="page-title">系统设置</h2>
    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <el-card header="预约参数">
          <el-form v-if="form" label-width="120px">
            <el-form-item label="申购时间">
              <el-input v-model="form.schedule_target_time" placeholder="09:00:00" />
            </el-form-item>
            <el-form-item label="提前秒数">
              <el-input-number v-model="form.schedule_advance_seconds" :min="0" :max="30" />
            </el-form-item>
            <el-form-item label="默认选店">
              <el-select v-model="form.shop_strategy_default" style="width: 100%">
                <el-option label="库存最大" value="max_inventory" />
                <el-option label="低竞争" value="min_competition" />
                <el-option label="距离最近" value="nearest" />
              </el-select>
            </el-form-item>
            <el-form-item label="重试次数">
              <el-input-number v-model="form.retry_count" :min="1" :max="10" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="save">保存到 config.yaml</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card header="健康检查">
          <el-button @click="loadHealth" :loading="healthLoading">刷新</el-button>
          <ul class="health-list">
            <li v-for="(item, i) in healthItems" :key="i" :class="item.level">
              [{{ item.category }}] {{ item.message }}
            </li>
          </ul>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { settingsApi } from "@/api";

const form = ref<Record<string, unknown> | null>(null);
const saving = ref(false);
const healthItems = ref<{ level: string; category: string; message: string }[]>([]);
const healthLoading = ref(false);

async function load() {
  form.value = await settingsApi.get();
}

async function save() {
  if (!form.value) return;
  saving.value = true;
  try {
    await settingsApi.put(form.value);
    ElMessage.success("已保存");
  } finally {
    saving.value = false;
  }
}

async function loadHealth() {
  healthLoading.value = true;
  try {
    const res = await settingsApi.health();
    healthItems.value = res.items;
  } finally {
    healthLoading.value = false;
  }
}

onMounted(() => {
  load();
  loadHealth();
});
</script>

<style scoped>
.health-list {
  list-style: none;
  padding: 0;
  margin-top: 12px;
  font-size: 13px;
}
.health-list .ok {
  color: #67c23a;
}
.health-list .warn {
  color: #e6a23c;
}
.health-list .fail {
  color: #f56c6c;
}
</style>
