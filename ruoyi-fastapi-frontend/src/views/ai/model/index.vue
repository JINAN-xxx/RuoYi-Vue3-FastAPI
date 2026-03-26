<template>
  <div class="app-container page-shell model-page">
    <section class="page-hero">
      <div class="page-hero__row">
        <div>
          <div class="page-hero__eyebrow">模型配置中心</div>
          <h1 class="page-hero__title">模型管理</h1>
          <p class="page-hero__subtitle">
            统一维护模型接入配置、供应商参数与可用能力。这里的配置会直接影响对话、推理、视觉和知识库场景的调用体验。
          </p>
        </div>
        <div class="page-hero__actions">
          <el-button type="primary" icon="Plus" @click="handleAdd" v-hasPermi="['ai:model:add']">新增模型</el-button>
          <el-button icon="Refresh" @click="getList">刷新列表</el-button>
        </div>
      </div>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-card__label">模型总数</div>
          <div class="stat-card__value">{{ modelStats.total }}</div>
          <div class="stat-card__desc">当前页已加载模型数量</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">启用模型</div>
          <div class="stat-card__value">{{ modelStats.active }}</div>
          <div class="stat-card__desc">状态为正常，可用于实际调用</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">支持推理</div>
          <div class="stat-card__value">{{ modelStats.reasoning }}</div>
          <div class="stat-card__desc">可开启深度思考能力的模型</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">支持图片</div>
          <div class="stat-card__value">{{ modelStats.vision }}</div>
          <div class="stat-card__desc">具备视觉输入能力的模型</div>
        </div>
      </div>
    </section>

    <section class="toolbar-shell">
      <el-form
        :model="queryParams"
        ref="queryRef"
        :inline="true"
        v-show="showSearch"
        class="compact-filters"
      >
        <el-form-item label="模型编码" prop="modelCode">
          <el-input
            v-model="queryParams.modelCode"
            placeholder="搜索模型编码"
            clearable
            style="width: 220px"
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item label="提供商" prop="provider">
          <el-select
            v-model="queryParams.provider"
            placeholder="全部提供商"
            clearable
            style="width: 200px"
            @keyup.enter="handleQuery"
          >
            <el-option
              v-for="dict in ai_provider_type"
              :key="dict.value"
              :label="dict.label"
              :value="dict.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select
            v-model="queryParams.status"
            placeholder="全部状态"
            clearable
            style="width: 180px"
          >
            <el-option
              v-for="dict in sys_normal_disable"
              :key="dict.value"
              :label="dict.label"
              :value="dict.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="handleQuery">筛选</el-button>
          <el-button icon="RefreshLeft" @click="resetQuery">重置</el-button>
        </el-form-item>
        <el-form-item>
          <el-button
            type="success"
            plain
            icon="Edit"
            :disabled="single"
            @click="handleUpdate"
            v-hasPermi="['ai:model:edit']"
          >
            修改
          </el-button>
        </el-form-item>
        <el-form-item>
          <el-button
            type="danger"
            plain
            icon="Delete"
            :disabled="multiple"
            @click="handleDelete"
            v-hasPermi="['ai:model:remove']"
          >
            删除
          </el-button>
        </el-form-item>
        <el-form-item class="toolbar-tail">
          <right-toolbar
            v-model:showSearch="showSearch"
            @queryTable="getList"
          ></right-toolbar>
        </el-form-item>
      </el-form>
    </section>

    <section class="table-shell">
      <el-table
        v-loading="loading"
        :data="modelList"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="模型信息" min-width="260">
          <template #default="scope">
            <div class="model-main">
              <div class="model-code">{{ scope.row.modelCode }}</div>
              <div class="model-name">{{ scope.row.modelName || "未命名模型" }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="提供商" align="center" prop="provider" min-width="140">
          <template #default="scope">
            <dict-tag class="provider-tag" :options="ai_provider_type" :value="scope.row.provider" />
          </template>
        </el-table-column>
        <el-table-column label="能力" align="center" min-width="180">
          <template #default="scope">
            <div class="capability-tags">
              <el-tag size="small" effect="light" :type="scope.row.supportReasoning === 'Y' ? 'success' : 'info'">
                {{ scope.row.supportReasoning === "Y" ? "推理" : "标准" }}
              </el-tag>
              <el-tag size="small" effect="light" :type="scope.row.supportImages === 'Y' ? 'primary' : 'info'">
                {{ scope.row.supportImages === "Y" ? "视觉" : "文本" }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" align="center" prop="status" width="120">
          <template #default="scope">
            <dict-tag :options="sys_normal_disable" :value="scope.row.status" />
          </template>
        </el-table-column>
        <el-table-column label="温度" align="center" prop="temperature" width="100" />
        <el-table-column label="最大输出" align="center" prop="maxTokens" width="120" />
        <el-table-column
          label="创建时间"
          align="center"
          prop="createTime"
          width="180"
        >
          <template #default="scope">
            <span>{{ parseTime(scope.row.createTime) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="180"
          align="center"
          class-name="small-padding fixed-width"
        >
          <template #default="scope">
            <el-button
              link
              type="primary"
              icon="Edit"
              @click="handleUpdate(scope.row)"
              v-hasPermi="['ai:model:edit']"
            >修改</el-button>
            <el-button
              link
              type="danger"
              icon="Delete"
              @click="handleDelete(scope.row)"
              v-hasPermi="['ai:model:remove']"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <pagination
          v-show="total > 0"
          :total="total"
          v-model:page="queryParams.pageNum"
          v-model:limit="queryParams.pageSize"
          @pagination="getList"
        />
      </div>
    </section>

    <!-- 添加或修改对话框 -->
    <el-dialog :title="title" v-model="open" width="700px" append-to-body class="model-dialog">
      <el-form ref="modelRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="10">
          <el-col :span="12">
            <el-form-item label="模型编码" prop="modelCode">
              <el-input
                v-model="form.modelCode"
                placeholder="请输入模型编码（如 deepseek-r1）"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="模型名称" prop="modelName">
              <el-input v-model="form.modelName" placeholder="请输入模型名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="提供商" prop="provider">
              <el-select
                v-model="form.provider"
                placeholder="请选择提供商"
                style="width: 100%"
              >
                <el-option
                  v-for="dict in ai_provider_type"
                  :key="dict.value"
                  :label="dict.label"
                  :value="dict.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="模型排序" prop="modelSort">
              <el-input-number
                v-model="form.modelSort"
                :min="0"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="接口密钥" prop="apiKey">
              <el-input
                v-model="form.apiKey"
                placeholder="请输入接口密钥"
                type="password"
              />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="接口地址" prop="baseUrl">
              <el-input v-model="form.baseUrl" placeholder="请输入接口地址" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最大输出" prop="maxTokens">
              <el-input-number
                v-model="form.maxTokens"
                :min="0"
                style="width: 100%"
                placeholder="最大输出"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="默认温度" prop="temperature">
              <el-input-number
                v-model="form.temperature"
                :min="0"
                :max="2"
                :step="0.1"
                placeholder="默认温度"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="支持推理" prop="supportReasoning">
              <el-radio-group v-model="form.supportReasoning">
                <el-radio
                  v-for="dict in sys_yes_no"
                  :key="dict.value"
                  :value="dict.value"
                  >{{ dict.label }}</el-radio
                >
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="支持图片" prop="supportImages">
              <el-radio-group v-model="form.supportImages">
                <el-radio
                  v-for="dict in sys_yes_no"
                  :key="dict.value"
                  :value="dict.value"
                  >{{ dict.label }}</el-radio
                >
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="模型类型" prop="modelType">
              <el-input
                v-model="form.modelType"
                placeholder="请输入模型类型（可选）"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态" prop="status">
              <el-radio-group v-model="form.status">
                <el-radio
                  v-for="dict in sys_normal_disable"
                  :key="dict.value"
                  :value="dict.value"
                  >{{ dict.label }}</el-radio
                >
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注" prop="remark">
              <el-input
                v-model="form.remark"
                type="textarea"
                placeholder="请输入内容"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" @click="submitForm">确 定</el-button>
          <el-button @click="cancel">取 消</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="AiModel">
import {
  listModel,
  addModel,
  delModel,
  getModel,
  updateModel,
} from "@/api/ai/model";

const { proxy } = getCurrentInstance();
const { ai_provider_type, sys_normal_disable, sys_yes_no } = proxy.useDict(
  "ai_provider_type",
  "sys_normal_disable",
  "sys_yes_no",
);

const modelList = ref([]);
const open = ref(false);
const loading = ref(true);
const showSearch = ref(true);
const ids = ref([]);
const single = ref(true);
const multiple = ref(true);
const total = ref(0);
const title = ref("");

const modelStats = computed(() => ({
  total: modelList.value.length,
  active: modelList.value.filter((item) => item.status === "0").length,
  reasoning: modelList.value.filter((item) => item.supportReasoning === "Y").length,
  vision: modelList.value.filter((item) => item.supportImages === "Y").length,
}));

const data = reactive({
  form: {},
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    modelCode: undefined,
    provider: undefined,
    status: undefined,
  },
  rules: {
    modelCode: [
      { required: true, message: "模型编码不能为空", trigger: "blur" },
    ],
    provider: [
      { required: true, message: "提供商不能为空", trigger: "change" },
    ],
    modelSort: [
      { required: true, message: "模型排序不能为空", trigger: "blur" },
    ],
  },
});

const { queryParams, form, rules } = toRefs(data);

/** 查询列表 */
function getList() {
  loading.value = true;
  listModel(queryParams.value).then((response) => {
    modelList.value = response.rows;
    total.value = response.total;
    loading.value = false;
  });
}

/** 取消按钮 */
function cancel() {
  open.value = false;
  reset();
}

/** 表单重置 */
function reset() {
  form.value = {
    modelId: undefined,
    modelCode: undefined,
    modelName: undefined,
    provider: undefined,
    modelSort: 0,
    apiKey: undefined,
    baseUrl: undefined,
    maxTokens: undefined,
    temperature: undefined,
    supportReasoning: "N",
    supportImages: "N",
    modelType: undefined,
    status: "0",
    remark: undefined,
  };
  proxy.resetForm("modelRef");
}

/** 搜索按钮操作 */
function handleQuery() {
  queryParams.value.pageNum = 1;
  getList();
}

/** 重置按钮操作 */
function resetQuery() {
  proxy.resetForm("queryRef");
  handleQuery();
}

/** 多选框选中数据 */
function handleSelectionChange(selection) {
  ids.value = selection.map((item) => item.modelId);
  single.value = selection.length != 1;
  multiple.value = !selection.length;
}

/** 新增按钮操作 */
function handleAdd() {
  reset();
  open.value = true;
  title.value = "添加模型";
}

/** 修改按钮操作 */
function handleUpdate(row) {
  reset();
  const modelId = row.modelId || ids.value;
  getModel(modelId).then((response) => {
    form.value = response.data;
    open.value = true;
    title.value = "修改模型";
  });
}

/** 提交按钮 */
function submitForm() {
  proxy.$refs["modelRef"].validate((valid) => {
    if (valid) {
      if (form.value.modelId != undefined) {
        updateModel(form.value).then((response) => {
          proxy.$modal.msgSuccess("修改成功");
          open.value = false;
          getList();
        });
      } else {
        addModel(form.value).then((response) => {
          proxy.$modal.msgSuccess("新增成功");
          open.value = false;
          getList();
        });
      }
    }
  });
}

/** 删除按钮操作 */
function handleDelete(row) {
  const modelIds = row.modelId || ids.value;
  proxy.$modal
    .confirm('是否确认删除模型编号为"' + modelIds + '"的数据项？')
    .then(function () {
      return delModel(modelIds);
    })
    .then(() => {
      getList();
      proxy.$modal.msgSuccess("删除成功");
    })
    .catch(() => {});
}

getList();
</script>

<style scoped lang="scss">
.model-page {
  .toolbar-tail {
    margin-left: auto;
    margin-right: 0;
  }

  .table-shell {
    padding: 8px 8px 0;
  }

  .pagination-wrap {
    display: flex;
    justify-content: flex-end;
    padding: 12px 12px 18px;
  }
}

.model-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.model-code {
  font-weight: 700;
  color: var(--app-text-primary);
}

.model-name {
  font-size: 12px;
  color: var(--app-text-secondary);
}

.capability-tags {
  display: inline-flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}

.provider-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  max-width: 100%;
  white-space: normal;
  word-break: break-word;
  line-height: 1.4;
  text-align: center;
}

.model-dialog {
  :deep(.el-dialog__body) {
    padding-top: 12px;
  }
}
</style>
