<template>
  <div>
    <div class="toolbar">
      <h2 class="page-title">商品管理</h2>
      <el-button type="primary" @click="openEdit()">新增商品</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="item_code" label="编码" width="100" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="sort_order" label="排序" width="80" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
            {{ row.enabled ? "是" : "否" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" link @click="remove(row)">删</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" :title="form.id ? '编辑' : '新增'" width="90%" style="max-width: 420px">
      <el-form label-width="80px">
        <el-form-item label="编码"><el-input v-model="form.item_code" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort_order" :min="0" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.enabled" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { productsApi, type ProductItem } from "@/api";

const list = ref<ProductItem[]>([]);
const visible = ref(false);
const form = reactive<ProductItem>({
  item_code: "10941",
  name: "飞天茅台500ml",
  enabled: true,
  sort_order: 0,
});

async function load() {
  list.value = await productsApi.list();
}

function openEdit(row?: ProductItem) {
  Object.assign(form, row || { item_code: "", name: "", enabled: true, sort_order: 0, id: undefined });
  visible.value = true;
}

async function save() {
  if (form.id) {
    await productsApi.update(form.id, form);
  } else {
    await productsApi.create(form);
  }
  ElMessage.success("已保存");
  visible.value = false;
  load();
}

async function remove(row: ProductItem) {
  await productsApi.remove(row.id!);
  load();
}

onMounted(load);
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}
</style>
