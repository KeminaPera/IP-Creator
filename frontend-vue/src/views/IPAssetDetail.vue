<template>
  <div class="ip-asset-detail" v-loading="loading">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <el-button @click="$router.back()" circle>
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <h2>{{ ipAsset?.name || $t('ip.detail_title') }}</h2>
      </div>
      <div class="header-right">
        <el-tag>{{ getCategoryLabel(ipAsset?.category) }}</el-tag>
        <el-tag type="success">{{ ipAsset?.style_template }}</el-tag>
      </div>
    </div>

    <!-- 标签页 -->
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 基础信息 -->
      <el-tab-pane :label="$t('ip.tab_basic_info')" name="basic">
        <div class="tab-content">
          <el-descriptions :column="2" border>
            <el-descriptions-item :label="$t('ip.name')">
              {{ ipAsset?.name }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('ip.trigger_word')">
              <code>{{ ipAsset?.trigger_word }}</code>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('ip.category')">
              {{ getCategoryLabel(ipAsset?.category) }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('ip.style_template')">
              {{ ipAsset?.style_template }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('ip.description')" :span="2">
              {{ ipAsset?.description || $t('common.no_description') }}
            </el-descriptions-item>
          </el-descriptions>

          <!-- 参考图 -->
          <div class="reference-images">
            <h4>{{ $t('ip.reference_images_hint') }}</h4>
            <div class="image-grid">
              <div 
                v-for="(img, index) in (ipAsset?.reference_images || [])" 
                :key="index"
                class="image-item"
              >
                <el-image 
                  :src="getImageUrl(img.path || img)" 
                  fit="cover"
                  :preview-src-list="(ipAsset?.reference_images || []).map(i => getImageUrl(i.path || i))"
                  :initial-index="index"
                >
                  <template #error>
                    <div class="image-error">
                      <el-icon><Picture /></el-icon>
                    </div>
                  </template>
                </el-image>
                <div class="image-label">{{ img.angle || $t('ip.angle_unlabeled') }}</div>
              </div>
              <el-empty v-if="!ipAsset?.reference_images || ipAsset.reference_images.length === 0" :description="$t('ip.no_reference_images')" />
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 多视图 -->
      <el-tab-pane :label="$t('ip.tab_multi_view')" name="multiview">
        <div class="tab-content">
          <MultiViewManager 
            v-if="activeTab === 'multiview'"
            :ip-id="ipId" 
            @update="handleUpdate"
          />
        </div>
      </el-tab-pane>

      <!-- 特征库 -->
      <el-tab-pane :label="$t('ip.tab_feature_library')" name="features">
        <div class="tab-content">
          <FeatureLibrary 
            v-if="activeTab === 'features'"
            :ip-id="ipId" 
            @update="handleUpdate"
          />
        </div>
      </el-tab-pane>

      <!-- 统计信息 -->
      <el-tab-pane :label="$t('ip.tab_statistics')" name="stats">
        <div class="tab-content">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-card>
                <template #header>
                  <div class="card-header">
                    <span>{{ $t('ip.stats_multi_view_count') }}</span>
                  </div>
                </template>
                <div class="card-value">{{ stats.multiViewCount }}</div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card>
                <template #header>
                  <div class="card-header">
                    <span>{{ $t('ip.stats_feature_count') }}</span>
                  </div>
                </template>
                <div class="card-value">{{ stats.featureCount }}</div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card>
                <template #header>
                  <div class="card-header">
                    <span>{{ $t('ip.stats_feature_image_count') }}</span>
                  </div>
                </template>
                <div class="card-value">{{ stats.featureImageCount }}</div>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Picture } from '@element-plus/icons-vue'
import MultiViewManager from '@/components/ip/MultiViewManager.vue'
import FeatureLibrary from '@/components/ip/FeatureLibrary.vue'
import { getIPAsset } from '@/api/ip'
import { getMultiViews, getFeatures } from '@/api/ip-features'
import { getImageUrl } from '@/utils/image'
import { logger } from '@/utils/logger'

const route = useRoute()
const { t } = useI18n()
const ipId = computed(() => parseInt(route.params.id))

const loading = ref(false)
const activeTab = ref('basic')
const ipAsset = ref(null)
const loadedTabs = ref(new Set(['basic']))  // 记录已加载的页签
const stats = ref({
  multiViewCount: 0,
  featureCount: 0,
  featureImageCount: 0
})

// 加载 IP 资产信息
const loadIPAsset = async () => {
  loading.value = true
  try {
    const response = await getIPAsset(ipId.value)
    ipAsset.value = response.data.data
  } catch (error) {
    logger.error('[IPAssetDetail] Failed to load IP asset:', error)
    ElMessage.error(t('ip.load_failed'))
  } finally {
    loading.value = false
  }
}

// 加载统计信息
const loadStats = async () => {
  try {
    // 多视图数量
    const multiViews = await getMultiViews(ipId.value)
    stats.value.multiViewCount = (multiViews.data.data || []).length

    // 特征数量和图片数量
    const features = await getFeatures(ipId.value)
    const featuresList = features.data.data || []
    stats.value.featureCount = featuresList.length
    stats.value.featureImageCount = featuresList.reduce(
      (sum, f) => sum + (f.images || []).length, 
      0
    )
  } catch (error) {
    logger.error('[IPAssetDetail] Failed to load stats:', error)
  }
}

// 更新回调：刷新已加载的页签数据
const handleUpdate = () => {
  // 如果统计页签已加载过，重新加载
  if (loadedTabs.value.has('stats')) {
    loadStats()
  }
}

// 工具函数
const getCategoryLabel = (category) => {
  const map = {
    pet: 'ip.category_pet',
    human: 'ip.category_human',
    fantasy: 'ip.category_fantasy',
    animal: 'ip.category_animal',
    other: 'ip.category_other'
  }
  const key = map[category]
  return key ? t(key) : (category || t('common.unknown'))
}

onMounted(() => {
  loadIPAsset()
  // 不再在 onMounted 时加载统计数据，改为切换到页签时再加载
})

// 监听页签切换，懒加载统计数据
watch(activeTab, (newTab) => {
  // 首次切换到统计页签时加载数据
  if (newTab === 'stats' && !loadedTabs.value.has('stats')) {
    loadStats()
    loadedTabs.value.add('stats')
  }
})
</script>

<style scoped>
.ip-asset-detail {
  padding: 20px;
  min-height: 100vh;
  background: #f5f7fa;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 20px;
  background: white;
  border-radius: 8px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h2 {
  margin: 0;
  font-size: 24px;
}

.header-right {
  display: flex;
  gap: 12px;
}

.tab-content {
  padding: 20px;
  min-height: 500px;
}

.reference-images {
  margin-top: 30px;
}

.reference-images h4 {
  margin-bottom: 16px;
  font-size: 16px;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.image-item {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e4e7ed;
}

.image-item .el-image {
  width: 100%;
  height: 200px;
}

.image-error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  background: #f5f7fa;
  color: #909399;
}

.image-label {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  text-align: center;
  padding: 8px;
  font-size: 14px;
}

.card-header {
  font-weight: 600;
}

.card-value {
  font-size: 36px;
  font-weight: 700;
  color: #409eff;
  text-align: center;
  padding: 20px 0;
}

code {
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
  font-family: monospace;
  color: #409eff;
}
</style>
