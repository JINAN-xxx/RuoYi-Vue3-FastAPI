<template>
  <div class="app-container page-shell knowledge-page">
    <section class="page-hero">
      <div class="page-hero__row">
        <div>
          <div class="page-hero__eyebrow">知识资产中心</div>
          <h1 class="page-hero__title">知识库</h1>
          <p class="page-hero__subtitle">
            统一管理企业、部门和个人知识资产。文档上传后会自动解析、切片并建立向量索引，为后续检索和对话提供基础。
          </p>
        </div>
        <div class="page-hero__actions">
          <el-button
            type="primary"
            icon="Upload"
            @click="openUploadDialog"
            v-hasPermi="['ai:knowledge:upload']"
          >
            上传文档
          </el-button>
          <el-button icon="Refresh" @click="getList">刷新列表</el-button>
        </div>
      </div>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-card__label">当前页文档</div>
          <div class="stat-card__value">{{ documentStats.total }}</div>
          <div class="stat-card__desc">已加载到当前视图的知识文档数量</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">可检索文档</div>
          <div class="stat-card__value">{{ documentStats.ready }}</div>
          <div class="stat-card__desc">索引完成后可用于检索与问答</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">建立索引中</div>
          <div class="stat-card__value">{{ documentStats.indexing }}</div>
          <div class="stat-card__desc">系统会自动轮询最新处理状态</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">异常文档</div>
          <div class="stat-card__value">{{ documentStats.error }}</div>
          <div class="stat-card__desc">优先检查依赖、配置或源文件内容</div>
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
        <el-form-item label="文档名称" prop="originName">
          <el-input
            v-model="queryParams.originName"
            placeholder="搜索文档名称"
            clearable
            style="width: 240px"
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item label="知识范围" prop="scope">
          <el-select v-model="queryParams.scope" placeholder="全部范围" clearable style="width: 180px">
            <el-option label="企业知识" value="enterprise" />
            <el-option label="部门知识" value="department" />
            <el-option label="个人知识" value="personal" />
          </el-select>
        </el-form-item>
        <el-form-item label="索引状态" prop="status">
          <el-select v-model="queryParams.status" placeholder="全部状态" clearable style="width: 180px">
            <el-option label="索引中" value="indexing" />
            <el-option label="已就绪" value="ready" />
            <el-option label="异常" value="error" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="handleQuery">筛选</el-button>
          <el-button icon="RefreshLeft" @click="resetQuery">重置</el-button>
        </el-form-item>
        <el-form-item class="toolbar-tail">
          <right-toolbar v-model:showSearch="showSearch" @queryTable="getList"></right-toolbar>
        </el-form-item>
      </el-form>
    </section>

    <section class="table-shell">
      <el-table v-loading="loading" :data="documentList">
        <el-table-column label="文档信息" prop="originName" min-width="260" show-overflow-tooltip>
          <template #default="scope">
            <div class="doc-main">
              <a
                v-if="scope.row.documentUrl"
                :href="baseApi + scope.row.documentUrl"
                class="doc-link"
                target="_blank"
                rel="noreferrer"
              >
                {{ scope.row.originName }}
              </a>
              <span class="doc-meta">{{ formatSize(scope.row.fileSize) }} · {{ scope.row.fileExt || "-" }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="范围" align="center" width="120">
          <template #default="scope">
            <el-tag :type="scopeTagType(scope.row.scope)" effect="light">
              {{ scopeLabel(scope.row.scope) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" align="center" width="120">
          <template #default="scope">
            <el-tag :type="statusTagType(scope.row.status)" effect="light">
              {{ statusLabel(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="切片" align="center" prop="chunkCount" width="100" />
        <el-table-column label="创建人" align="center" prop="createBy" width="120" />
        <el-table-column label="创建时间" align="center" prop="createTime" width="180">
          <template #default="scope">
            <span>{{ parseTime(scope.row.createTime) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="索引预览" min-width="320" show-overflow-tooltip>
          <template #default="scope">
            <span v-if="scope.row.status === 'error'" class="error-text">
              {{ scope.row.errorMessage || "索引失败" }}
            </span>
            <span v-else class="preview-text">{{ scope.row.contentPreview || "索引完成后显示预览摘要" }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center" class-name="small-padding fixed-width">
          <template #default="scope">
            <el-button
              link
              type="danger"
              icon="Delete"
              @click="handleDelete(scope.row)"
              v-hasPermi="['ai:knowledge:remove']"
            >
              删除
            </el-button>
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

    <el-dialog title="上传知识库文档" v-model="uploadOpen" width="460px" append-to-body class="knowledge-dialog">
      <el-form :model="uploadForm" label-width="90px">
        <el-form-item label="知识范围">
          <el-radio-group v-model="uploadForm.scope">
            <el-radio value="enterprise">企业知识</el-radio>
            <el-radio value="department">部门知识</el-radio>
            <el-radio value="personal">个人知识</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="选择文件">
          <input ref="fileRef" type="file" class="upload-input" @change="handleFileChange" />
          <div class="upload-hint">支持 pdf、docx、txt、md，大小不超过 20MB</div>
          <div v-if="uploadForm.file" class="upload-file-name">{{ uploadForm.file.name }}</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="uploadOpen = false">取消</el-button>
          <el-button type="primary" :loading="uploading" @click="submitUpload">开始上传</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="AiKnowledge">
import { delKnowledge, listKnowledge, uploadKnowledge } from "@/api/ai/knowledge";

const { proxy } = getCurrentInstance();
const baseApi = import.meta.env.VITE_APP_BASE_API;

const documentList = ref([]);
const loading = ref(false);
const uploading = ref(false);
const showSearch = ref(true);
const uploadOpen = ref(false);
const total = ref(0);
const fileRef = ref(null);
const pollingTimer = ref(null);

const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  originName: undefined,
  scope: undefined,
  status: undefined,
});

const uploadForm = reactive({
  scope: "personal",
  file: null,
});

const documentStats = computed(() => ({
  total: documentList.value.length,
  ready: documentList.value.filter((item) => item.status === "ready").length,
  indexing: documentList.value.filter((item) => item.status === "indexing").length,
  error: documentList.value.filter((item) => item.status === "error").length,
}));

function getList() {
  loading.value = true;
  listKnowledge(queryParams)
    .then((res) => {
      documentList.value = res.rows;
      total.value = res.total;
      managePolling();
    })
    .finally(() => {
      loading.value = false;
    });
}

function handleQuery() {
  queryParams.pageNum = 1;
  getList();
}

function resetQuery() {
  proxy.resetForm("queryRef");
  handleQuery();
}

function openUploadDialog() {
  uploadOpen.value = true;
  uploadForm.scope = "personal";
  uploadForm.file = null;
  if (fileRef.value) {
    fileRef.value.value = "";
  }
}

function handleFileChange(event) {
  uploadForm.file = event.target.files?.[0] || null;
}

function submitUpload() {
  if (!uploadForm.file) {
    proxy.$modal.msgWarning("请先选择文件");
    return;
  }
  const formData = new FormData();
  formData.append("scope", uploadForm.scope);
  formData.append("file", uploadForm.file);
  uploading.value = true;
  uploadKnowledge(formData)
    .then((res) => {
      proxy.$modal.msgSuccess(res.msg || "上传成功");
      uploadOpen.value = false;
      getList();
    })
    .finally(() => {
      uploading.value = false;
    });
}

function handleDelete(row) {
  proxy.$modal
    .confirm(`是否确认删除文档“${row.originName}”？`)
    .then(() => delKnowledge(row.documentId))
    .then(() => {
      proxy.$modal.msgSuccess("删除成功");
      getList();
    })
    .catch(() => {});
}

function statusLabel(status) {
  if (status === "ready") return "已就绪";
  if (status === "error") return "异常";
  return "索引中";
}

function scopeLabel(scope) {
  if (scope === "enterprise") return "企业知识";
  if (scope === "department") return "部门知识";
  return "个人知识";
}

function scopeTagType(scope) {
  if (scope === "enterprise") return "primary";
  if (scope === "department") return "success";
  return "info";
}

function statusTagType(status) {
  if (status === "ready") return "success";
  if (status === "error") return "danger";
  return "info";
}

function formatSize(size) {
  if (!size && size !== 0) return "-";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function clearPolling() {
  if (pollingTimer.value) {
    clearTimeout(pollingTimer.value);
    pollingTimer.value = null;
  }
}

function managePolling() {
  clearPolling();
  if (documentList.value.some((item) => item.status === "indexing")) {
    pollingTimer.value = setTimeout(() => {
      getList();
    }, 4000);
  }
}

onMounted(() => {
  getList();
});

onBeforeUnmount(() => {
  clearPolling();
});
</script>

<style scoped lang="scss">
.knowledge-page {
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

.doc-link {
  color: var(--app-text-primary);
  font-weight: 600;
  transition: color 0.2s ease;

  &:hover {
    color: var(--app-accent);
  }
}

.doc-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.doc-meta {
  font-size: 12px;
  color: var(--app-text-secondary);
}

.upload-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--app-text-secondary);
}

.upload-file-name {
  margin-top: 10px;
  color: var(--app-text-primary);
}

.error-text {
  color: var(--app-danger);
}

.preview-text {
  color: var(--app-text-secondary);
}

.upload-input {
  width: 100%;
}

.knowledge-dialog {
  :deep(.el-dialog__body) {
    padding-top: 12px;
  }
}
</style>
