<template>
  <div class="dataset-annotation" v-loading="loading">
    <!-- 页面工具栏 -->
    <PageToolbar
      :show-search="false"
      :show-create="false"
    >
      <template #actions>
        <el-select v-model="selectedDataset" :placeholder="t('dataset.annotation.select_dataset')" @change="loadDataset" style="width: 300px;">
          <el-option
            v-for="ds in datasets"
            :key="ds.id"
            :label="ds.name"
            :value="ds.id"
          />
        </el-select>
      </template>
    </PageToolbar>

    <!-- 数据集信息 -->
    <el-alert
      v-if="datasetInfo"
      :title="`${t('common.dataset')}: ${datasetInfo.name}`"
      :description="`${t('dataset.image_count')}: ${datasetInfo.image_count} | ${t('dataset.status')}: ${datasetInfo.status}`"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 20px"
    />

    <!-- 操作栏 -->
    <div class="action-bar">
      <el-button type="primary" @click="batchAnnotate" :disabled="!selectedImages.length">
        <el-icon><Edit /></el-icon>
        {{ t('dataset.annotation.batch_annotate') }} ({{ selectedImages.length }})
      </el-button>
      <el-button type="success" @click="showCaptionDialog" :disabled="!datasetInfo">
        <el-icon><Document /></el-icon>
        {{ t('dataset.annotation.generate_captions') }}
      </el-button>
      <el-button @click="selectAll">
        {{ selectAllFlag ? t('dataset.annotation.deselect_all') : t('dataset.annotation.select_all') }}
      </el-button>
    </div>

    <!-- 图片网格 -->
    <div class="image-grid">
      <div
        v-for="image in images"
        :key="image.id"
        class="image-card"
        :class="{ selected: selectedImages.includes(image.id) }"
        @click="toggleSelect(image.id)"
      >
        <el-checkbox
          v-model="selectedImages"
          :label="image.id"
          @click.stop
          class="checkbox"
        />
        
        <el-image
          :src="getImageUrl(image.file_path)"
          fit="cover"
          class="image"
        >
          <template #error>
            <div class="image-error">
              <el-icon><Picture /></el-icon>
            </div>
          </template>
        </el-image>

        <!-- 标注信息 -->
        <div class="annotation-info">
          <el-tag v-if="image.angle" size="small" type="primary">
            {{ getAngleLabel(image.angle) }}
          </el-tag>
          <el-tag v-if="image.expression" size="small" type="success">
            {{ image.expression }}
          </el-tag>
          <el-tag v-if="image.pose" size="small" type="warning">
            {{ image.pose }}
          </el-tag>
        </div>

        <!-- Caption 预览 -->
        <div v-if="captions[image.id]" class="caption-preview">
          <code>{{ captions[image.id] }}</code>
        </div>

        <!-- 编辑按钮 -->
        <el-button
          size="small"
          type="primary"
          class="edit-btn"
          @click.stop="editImage(image)"
        >
          {{ t('dataset.annotation.edit') }}
        </el-button>
      </div>
    </div>

    <!-- 批量标注对话框 -->
    <el-dialog v-model="annotateDialogVisible" :title="t('dataset.annotation.batch_annotate')" width="500px">
      <el-form :model="annotationForm" label-width="100px">
        <el-form-item :label="t('dataset.annotation.angle')">
          <el-select v-model="annotationForm.angle" :placeholder="t('dataset.annotation.angle')">
            <el-option :label="t('dataset.annotation.front')" value="front" />
            <el-option :label="t('dataset.annotation.side')" value="side" />
            <el-option :label="t('dataset.annotation.back')" value="back" />
            <el-option :label="t('dataset.annotation.full_body')" value="full_body" />
            <el-option :label="t('dataset.annotation.half_body')" value="half_body" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('dataset.annotation.expression')">
          <el-input v-model="annotationForm.expression" :placeholder="t('dataset.annotation.expression')" />
        </el-form-item>
        <el-form-item :label="t('dataset.annotation.pose')">
          <el-input v-model="annotationForm.pose" :placeholder="t('dataset.annotation.pose')" />
        </el-form-item>
        <el-form-item :label="t('dataset.annotation.background')">
          <el-select v-model="annotationForm.background" :placeholder="t('dataset.annotation.background')">
            <el-option :label="t('dataset.annotation.simple')" value="simple" />
            <el-option :label="t('dataset.annotation.complex')" value="complex" />
            <el-option :label="t('dataset.annotation.indoor')" value="indoor" />
            <el-option :label="t('dataset.annotation.outdoor')" value="outdoor" />
            <el-option :label="t('dataset.annotation.white')" value="white" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="annotateDialogVisible = false">{{ t('dataset.annotation.cancel') }}</el-button>
        <el-button type="primary" @click="submitAnnotation">{{ t('dataset.annotation.confirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- Caption 生成对话框 -->
    <el-dialog v-model="captionDialogVisible" :title="t('dataset.annotation.generate_captions')" width="500px">
      <el-form :model="captionForm" label-width="120px">
        <el-form-item :label="t('dataset.annotation.trigger_word')">
          <el-input v-model="captionForm.trigger_word" :placeholder="t('dataset.annotation.trigger_word')" />
        </el-form-item>
        <el-form-item :label="t('dataset.annotation.use_ai')">
          <el-switch v-model="captionForm.use_ai" />
          <span style="margin-left: 10px; color: #909399; font-size: 12px;">
            {{ t('dataset.annotation.ai_note') }}
          </span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="captionDialogVisible = false">{{ t('dataset.annotation.cancel') }}</el-button>
        <el-button type="primary" @click="submitCaptionGeneration">{{ t('dataset.annotation.submit_caption') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Edit, Document, Picture } from '@element-plus/icons-vue'
import PageToolbar from '@/components/common/PageToolbar.vue'
import { getDatasetList, getDatasetDetail, batchAnnotateImages, generateCaptions } from '@/api/dataset'

const { t } = useI18n()

const loading = ref(false)
const selectedDataset = ref(null)
const datasetInfo = ref(null)
const images = ref([])
const selectedImages = ref([])
const selectAllFlag = ref(false)
const captions = ref({})

// 对话框
const annotateDialogVisible = ref(false)
const captionDialogVisible = ref(false)

// 表单
const annotationForm = ref({
  angle: '',
  expression: '',
  pose: '',
  background: ''
})

const captionForm = ref({
  trigger_word: '',
  use_ai: false
})

// 数据集列表
const datasets = ref([])

// 加载数据集列表
const loadDatasets = async () => {
  try {
    const response = await getDatasetList()
    datasets.value = response.data.data || []
  } catch (error) {
    ElMessage.error(t('dataset.annotation.load_list_error'))
  }
}

// 加载数据集详情
const loadDataset = async () => {
  if (!selectedDataset.value) return
  
  loading.value = true
  try {
    const response = await getDatasetDetail(selectedDataset.value, { include_images: true })
    datasetInfo.value = response.data.data
    images.value = response.data.data.images || []
    selectedImages.value = []
    captions.value = {}
  } catch (error) {
    ElMessage.error(t('dataset.annotation.load_dataset_error'))
  } finally {
    loading.value = false
  }
}

// 选择/取消选择
const toggleSelect = (imageId) => {
  const index = selectedImages.value.indexOf(imageId)
  if (index > -1) {
    selectedImages.value.splice(index, 1)
  } else {
    selectedImages.value.push(imageId)
  }
}

// 全选/取消全选
const selectAll = () => {
  if (selectAllFlag.value) {
    selectedImages.value = []
  } else {
    selectedImages.value = images.value.map(img => img.id)
  }
  selectAllFlag.value = !selectAllFlag.value
}

// 批量标注
const batchAnnotate = () => {
  if (!selectedImages.value.length) {
    ElMessage.warning(t('dataset.annotation.please_select_images'))
    return
  }
  annotateDialogVisible.value = true
}

// 提交标注
const submitAnnotation = async () => {
  const annotations = {}
  selectedImages.value.forEach(imageId => {
    annotations[imageId] = { ...annotationForm.value }
  })

  try {
    await batchAnnotateImages(selectedDataset.value, annotations)
    ElMessage.success(t('dataset.annotation.annotation_success'))
    annotateDialogVisible.value = false
    loadDataset() // 刷新
  } catch (error) {
    ElMessage.error(t('dataset.annotation.annotation_failed'))
  }
}

// 编辑单张图片
const editImage = (image) => {
  selectedImages.value = [image.id]
  annotationForm.value = {
    angle: image.angle || '',
    expression: image.expression || '',
    pose: image.pose || '',
    background: image.background || ''
  }
  annotateDialogVisible.value = true
}

// 显示 Caption 生成对话框
const showCaptionDialog = () => {
  if (!datasetInfo.value) return
  
  // 自动填充触发词
  captionForm.value.trigger_word = datasetInfo.value.trigger_word || ''
  captionDialogVisible.value = true
}

// 生成 Captions
const submitCaptionGeneration = async () => {
  if (!captionForm.value.trigger_word) {
    ElMessage.warning(t('dataset.annotation.enter_trigger_word'))
    return
  }

  try {
    const response = await generateCaptions(
      selectedDataset.value,
      captionForm.value.trigger_word,
      captionForm.value.use_ai
    )
    
    // 保存生成的 captions
    response.data.data.captions.forEach(item => {
      captions.value[item.image_id] = item.caption
    })
    
    ElMessage.success(t('dataset.annotation.caption_success', { count: response.data.data.total_generated }))
    captionDialogVisible.value = false
  } catch (error) {
    ElMessage.error(t('dataset.annotation.caption_failed'))
  }
}

// 工具函数
const getAngleLabel = (angle) => {
  const key = `dataset.annotation.${angle}`
  return t(key) || angle
}

const getImageUrl = (path) => {
  return path ? `${import.meta.env.VITE_API_BASE_URL}${path}` : ''
}

onMounted(() => {
  loadDatasets()
})
</script>

<style scoped>
.dataset-annotation {
  padding: 20px;
  min-height: 100vh;
  background: #f5f7fa;
}

.action-bar {
  margin: 20px 0;
  display: flex;
  gap: 12px;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.image-card {
  position: relative;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.3s;
}

.image-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.image-card.selected {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.checkbox {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 10;
}

.image {
  width: 100%;
  height: 250px;
}

.image-error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  background: #f5f7fa;
  color: #909399;
}

.annotation-info {
  padding: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.caption-preview {
  padding: 0 10px 10px;
}

.caption-preview code {
  display: block;
  background: #f5f7fa;
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  color: #606266;
  word-break: break-all;
}

.edit-btn {
  position: absolute;
  bottom: 10px;
  right: 10px;
}
</style>
