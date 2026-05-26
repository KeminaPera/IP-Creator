<template>
  <div class="feature-library">
    <div class="section-header">
      <h3>{{ $t('feature_library.title') }}</h3>
    </div>

    <!-- 动态渲染特征类型 -->
    <div v-loading="loading">
      <div 
        v-for="featureType in featureTypes" 
        :key="featureType.type" 
        class="feature-section"
      >
        <div class="feature-section-header">
          <h4>
            <span class="feature-icon">{{ featureType.icon }}</span>
            {{ $t(`feature_library.type_${featureType.type}`) }}
          </h4>
          <el-button 
            type="primary" 
            size="small"
            @click="showAddDialog(featureType.type)"
          >
            <el-icon><Plus /></el-icon>
            {{ $t('feature_library.add') }}{{ $t(`feature_library.type_${featureType.type}`) }}
          </el-button>
        </div>

        <p class="feature-section-desc">{{ $t(`feature_library.desc_${featureType.type}`) }}</p>

        <!-- 特征列表 -->
        <div class="features-grid">
          <div 
            v-for="feature in getFeaturesByType(featureType.type)" 
            :key="feature.id" 
            class="feature-card"
          >
            <div class="feature-header">
              <div class="feature-title">
                <h5>{{ feature.display_name || feature.feature_name }}</h5>
                <span class="feature-name">({{ feature.feature_name }})</span>
              </div>
              <el-tag 
                size="small" 
                :type="feature.is_active ? 'success' : 'info'"
              >
                {{ feature.is_active ? $t('common.enable') : $t('common.disable') }}
              </el-tag>
            </div>

            <p class="feature-desc">{{ feature.description || $t('common.no_description') }}</p>

            <!-- 触发词 -->
            <div class="trigger-phrase">
              <span class="label">{{ $t('feature_library.trigger_phrase_label') }}：</span>
              <code>{{ feature.trigger_phrase }}</code>
            </div>

            <!-- 图片列表 -->
            <div class="feature-images">
              <div 
                v-for="img in feature.images" 
                :key="img.id" 
                class="feature-image-item"
              >
                <el-image 
                  :src="getImageUrl(img.image_path)" 
                  fit="cover"
                  class="feature-image"
                >
                  <template #error>
                    <div class="image-placeholder">
                      {{ getAngleLabel(img.angle) }}
                    </div>
                  </template>
                </el-image>
                <div class="angle-label">{{ getAngleLabel(img.angle) }}</div>
              </div>
              
              <!-- 缺少角度的提示 -->
              <div 
                v-for="angle in getMissingAngles(feature)" 
                :key="angle" 
                class="feature-image-item missing"
              >
                <div class="image-placeholder">
                  <el-icon><Plus /></el-icon>
                </div>
                <div class="angle-label">{{ getAngleLabel(angle) }}</div>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="feature-actions">
              <el-button size="small" @click="editFeature(feature)">
                {{ $t('common.edit') }}
              </el-button>
              <el-button 
                size="small" 
                type="danger" 
                @click="handleDelete(feature)"
              >
                {{ $t('common.delete') }}
              </el-button>
            </div>
          </div>

          <!-- 空状态 -->
          <el-empty 
            v-if="getFeaturesByType(featureType.type).length === 0" 
            :description="`${$t('feature_library.empty')}${$t(`feature_library.type_${featureType.type}`)}`"
            :image-size="80"
          />
        </div>
      </div>
    </div>

    <!-- 添加/编辑特征对话框 -->
    <el-dialog 
      v-model="showDialog" 
      :title="editingFeature ? $t('feature_library.edit_title') : $t('feature_library.add_title')"
      width="700px"
    >
      <el-form :model="featureForm" label-width="120px">
        <el-form-item :label="$t('feature_library.feature_type')">
          <el-input 
            :value="getFeatureTypeLabel(featureForm.feature_type)" 
            disabled
          />
        </el-form-item>
        <el-form-item :label="$t('feature_library.feature_name_en')" required>
          <el-input 
            v-model="featureForm.feature_name" 
            :placeholder="$t('feature_library.feature_name_placeholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('feature_library.display_name')">
          <el-input 
            v-model="featureForm.display_name" 
            :placeholder="$t('feature_library.display_name_placeholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('feature_library.trigger_phrase')">
          <el-input 
            v-model="featureForm.trigger_phrase" 
            :placeholder="$t('feature_library.trigger_phrase_placeholder')"
          />
        </el-form-item>
        <el-form-item :label="$t('feature_library.description')">
          <el-input 
            v-model="featureForm.description" 
            type="textarea"
            :rows="3"
            :placeholder="$t('feature_library.description_placeholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">
          {{ $t('common.save') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { 
  getFeatures, 
  createFeature, 
  updateFeature, 
  deleteFeature,
  getFeatureTypes
} from '@/api/ip-features'
import { logger } from '@/utils/logger'

const { t } = useI18n()

const props = defineProps({
  ipId: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['update'])

const loading = ref(false)
const saving = ref(false)
const features = ref([])
const featureTypes = ref([])
const showDialog = ref(false)
const editingFeature = ref(null)

const featureForm = ref({
  feature_type: '',
  feature_name: '',
  display_name: '',
  trigger_phrase: '',
  description: ''
})

// 加载特征类型
const loadFeatureTypes = async () => {
  try {
    const response = await getFeatureTypes()
    featureTypes.value = response.data.data || []
  } catch (error) {
    logger.error('[FeatureLibrary] Failed to load feature types:', error)
  }
}

// 加载特征
const loadFeatures = async () => {
  loading.value = true
  try {
    const response = await getFeatures(props.ipId)
    features.value = response.data.data || []
  } catch (error) {
    logger.error('[FeatureLibrary] Failed to load features:', error)
    ElMessage.error(t('feature_library.load_failed'))
  } finally {
    loading.value = false
  }
}

// 根据类型筛选特征
const getFeaturesByType = (type) => {
  return features.value.filter(f => f.feature_type === type)
}

// 获取缺失的角度
const getMissingAngles = (feature) => {
  const typeConfig = featureTypes.value.find(t => t.type === feature.feature_type)
  if (!typeConfig) return []

  const minImages = typeConfig.min_images
  const existingAngles = feature.images.map(img => img.angle)
  
  const allAngles = ['front', 'side', 'back']
  const requiredAngles = allAngles.slice(0, minImages)
  
  return requiredAngles.filter(angle => !existingAngles.includes(angle))
}

// 显示添加对话框
const showAddDialog = (type) => {
  editingFeature.value = null
  featureForm.value = {
    feature_type: type,
    feature_name: '',
    display_name: '',
    trigger_phrase: '',
    description: ''
  }
  showDialog.value = true
}

// 编辑特征
const editFeature = (feature) => {
  editingFeature.value = feature
  featureForm.value = {
    feature_type: feature.feature_type,
    feature_name: feature.feature_name,
    display_name: feature.display_name,
    trigger_phrase: feature.trigger_phrase,
    description: feature.description
  }
  showDialog.value = true
}

// 保存特征
const handleSave = async () => {
  if (!featureForm.value.feature_name) {
    ElMessage.warning(t('feature_library.name_required'))
    return
  }

  saving.value = true
  try {
    if (editingFeature.value) {
      await updateFeature(props.ipId, editingFeature.value.id, featureForm.value)
      ElMessage.success(t('feature_library.update_success'))
    } else {
      await createFeature(props.ipId, featureForm.value)
      ElMessage.success(t('feature_library.create_success'))
    }
    showDialog.value = false
    loadFeatures()
    emit('update')
  } catch (error) {
    logger.error('[FeatureLibrary] Save failed:', error)
    ElMessage.error(t('feature_library.save_failed'))
  } finally {
    saving.value = false
  }
}

// 删除特征
const handleDelete = async (feature) => {
  try {
    await ElMessageBox.confirm(
      `${t('common.confirm_delete')}`,
      t('common.warning'),
      { type: 'warning' }
    )
    
    await deleteFeature(props.ipId, feature.id)
    ElMessage.success(t('feature_library.delete_success'))
    loadFeatures()
    emit('update')
  } catch (error) {
    if (error !== 'cancel') {
      logger.error('[FeatureLibrary] Delete failed:', error)
      ElMessage.error(t('feature_library.delete_failed'))
    }
  }
}

// 工具函数
const getFeatureTypeLabel = (type) => {
  const found = featureTypes.value.find(t => t.type === type)
  return found ? `${found.icon} ${t(`feature_library.type_${found.type}`)}` : type
}

const getAngleLabel = (angle) => {
  const map = {
    front: 'feature_library.angle_front',
    side: 'feature_library.angle_side',
    back: 'feature_library.angle_back'
  }
  const key = map[angle]
  return key ? t(key) : (angle || t('common.unknown'))
}

import { getImageUrl } from '@/utils/image'

// 工具函数已移至 utils/image.js

// 监听 IP ID 变化
watch(() => props.ipId, () => {
  loadFeatures()
}, { immediate: true })

onMounted(() => {
  loadFeatureTypes()
  loadFeatures()
})
</script>

<style scoped>
.feature-library {
  padding: 20px;
}

.section-header {
  margin-bottom: 30px;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
}

.feature-section {
  margin-bottom: 40px;
  padding: 20px;
  background: #f9fafb;
  border-radius: 8px;
}

.feature-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.feature-section-header h4 {
  margin: 0;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.feature-icon {
  font-size: 20px;
}

.feature-section-desc {
  color: #909399;
  font-size: 14px;
  margin: 0 0 20px 0;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.feature-card {
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  transition: all 0.3s;
}

.feature-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.feature-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.feature-title h5 {
  margin: 0 0 4px 0;
  font-size: 16px;
}

.feature-name {
  color: #909399;
  font-size: 12px;
}

.feature-desc {
  color: #606266;
  font-size: 14px;
  margin: 0 0 12px 0;
}

.trigger-phrase {
  background: #f5f7fa;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 13px;
  margin-bottom: 16px;
}

.trigger-phrase .label {
  color: #909399;
  margin-right: 8px;
}

.trigger-phrase code {
  color: #409eff;
  font-family: monospace;
}

.feature-images {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.feature-image-item {
  position: relative;
  width: 80px;
  height: 80px;
  border-radius: 4px;
  overflow: hidden;
}

.feature-image {
  width: 100%;
  height: 100%;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  color: #909399;
  font-size: 12px;
}

.feature-image-item.missing .image-placeholder {
  border: 2px dashed #dcdfe6;
  background: white;
}

.angle-label {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  font-size: 11px;
  text-align: center;
  padding: 2px;
}

.feature-actions {
  display: flex;
  gap: 8px;
  border-top: 1px solid #e4e7ed;
  padding-top: 12px;
}

.feature-actions .el-button {
  flex: 1;
}
</style>
