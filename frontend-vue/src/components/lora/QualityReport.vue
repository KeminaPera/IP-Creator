<template>
  <el-dialog
    v-model="visible"
    :title="$t('lora.quality.title')"
    width="900px"
    @close="handleClose"
  >
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="10" animated />
    </div>

    <div v-else-if="report" class="quality-report">
      <!-- 总体评分 -->
      <div class="score-overview">
        <div class="score-circle" :class="gradeClass">
          <div class="score-number">{{ report.overall_score }}</div>
          <div class="score-grade">{{ report.grade }}</div>
        </div>
        <div class="score-info">
          <h3>{{ getGradeText(report.grade) }}</h3>
          <p class="score-time">
            {{ $t('lora.quality.assessed_at') }}: {{ formatTime(report.created_at) }}
          </p>
        </div>
      </div>

      <!-- 详细评分 -->
      <el-card class="detail-card">
        <template #header>
          <div class="card-header">
            <span>{{ $t('lora.quality.detailed_scores') }}</span>
            <el-tag size="small" type="info">{{ $t('lora.quality.dimension_count') }}</el-tag>
          </div>
        </template>

        <div class="score-bars">
          <div class="score-bar-item">
            <div class="bar-label">
              <span>{{ $t('lora.quality.loss_score') }}</span>
              <span class="bar-value">{{ report.loss_score }}</span>
            </div>
            <el-progress
              :percentage="report.loss_score"
              :color="getScoreColor(report.loss_score)"
              :stroke-width="20"
            />
          </div>

          <div class="score-bar-item">
            <div class="bar-label">
              <span>{{ $t('lora.quality.completion_score') }}</span>
              <span class="bar-value">{{ report.completion_score }}</span>
            </div>
            <el-progress
              :percentage="report.completion_score"
              :color="getScoreColor(report.completion_score)"
              :stroke-width="20"
            />
          </div>

          <div class="score-bar-item">
            <div class="bar-label">
              <span>{{ $t('lora.quality.file_score') }}</span>
              <span class="bar-value">{{ report.file_score }}</span>
            </div>
            <el-progress
              :percentage="report.file_score"
              :color="getScoreColor(report.file_score)"
              :stroke-width="20"
            />
          </div>

          <div class="score-bar-item">
            <div class="bar-label">
              <span>{{ $t('lora.quality.generation_success') }}</span>
              <span class="bar-value">{{ report.generation_success }}%</span>
            </div>
            <el-progress
              :percentage="report.generation_success"
              :color="getScoreColor(report.generation_success)"
              :stroke-width="20"
            />
          </div>

          <div class="score-bar-item">
            <div class="bar-label">
              <span>{{ $t('lora.quality.clip_consistency') }}</span>
              <span class="bar-value">{{ report.clip_consistency }}</span>
            </div>
            <el-progress
              :percentage="report.clip_consistency || 0"
              :color="getScoreColor(report.clip_consistency || 0)"
              :stroke-width="20"
            />
          </div>
        </div>
      </el-card>

      <!-- 测试图片 -->
      <el-card v-if="report.test_images && report.test_images.length > 0" class="images-card">
        <template #header>
          <div class="card-header">
            <span>{{ $t('lora.quality.test_images') }} ({{ report.test_images.length }})</span>
          </div>
        </template>

        <el-row :gutter="16">
          <el-col
            v-for="(img, index) in report.test_images"
            :key="index"
            :span="8"
          >
            <div class="test-image-card">
              <div class="image-placeholder">
                <img 
                  v-if="img.image_path" 
                  :src="getImageUrl(img.image_path)" 
                  :alt="img.scenario"
                  @error="handleImageError"
                />
                <el-icon v-else :size="48"><Picture /></el-icon>
                <p>{{ img.scenario }}</p>
              </div>
              <div class="image-info">
                <el-tooltip :content="img.prompt" placement="top">
                  <p class="image-prompt">{{ truncateText(img.prompt, 50) }}</p>
                </el-tooltip>
                <p class="image-seed">Seed: {{ img.seed }}</p>
              </div>
            </div>
          </el-col>
        </el-row>
      </el-card>

      <!-- 优化建议 -->
      <el-card v-if="report.recommendations && report.recommendations.length > 0" class="recommendations-card">
        <template #header>
          <div class="card-header">
            <span>{{ $t('lora.quality.recommendations') }}</span>
          </div>
        </template>

        <el-alert
          v-for="(rec, index) in report.recommendations"
          :key="index"
          :title="rec.text"
          :type="rec.type || 'info'"
          :closable="false"
          show-icon
          class="recommendation-item"
        />
      </el-card>
    </div>

    <div v-else class="empty-container">
      <el-empty :description="$t('lora.quality.no_report')">
        <el-button type="primary" @click="handleFirstAssess" :loading="assessing">
          {{ $t('lora.quality.start_assess') }}
        </el-button>
      </el-empty>
    </div>

    <template #footer>
      <el-button @click="handleClose">{{ $t('common.close') }}</el-button>
      <el-button
        v-if="report"
        type="primary"
        @click="handleReassess"
        :loading="loading"
      >
        {{ $t('lora.quality.reassess') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Picture } from '@element-plus/icons-vue'
import { getQualityReport, assessQuality } from '../../api/lora'
import { formatTime } from '../../utils/time'
import { getGradeDescription } from '../../utils/grade'
import { getImageUrl } from '../../utils/image'

const { t } = useI18n()

const props = defineProps({
  loraId: {
    type: Number,
    required: true,
  },
})

const emit = defineEmits(['update', 'close'])

const visible = ref(false)
const loading = ref(false)
const assessing = ref(false)  // 评估中状态
const report = ref(null)

// 等级样式
const gradeClass = computed(() => {
  if (!report.value) return ''
  const grade = report.value.grade
  return `grade-${grade.toLowerCase()}`
})

// 打开对话框
async function open(loraId) {
  // 优先使用传入的参数，其次使用prop
  const id = loraId || props.loraId
  
  if (!id) {
    ElMessage.error(t('lora.invalid_model_id'))
    return
  }
  visible.value = true
  await loadReport(id)
}

// 加载质量报告
async function loadReport(loraId) {
  const id = loraId || props.loraId
  
  if (!id) {
    ElMessage.error(t('lora.invalid_model_id'))
    return
  }
  
  loading.value = true
  try {
    const { data } = await getQualityReport(id)
    report.value = data.data
  } catch (err) {
    if (err.response?.status === 404) {
      // 没有报告，正常
      report.value = null
    } else {
      ElMessage.error(t('lora.quality.load_failed'))
    }
  } finally {
    loading.value = false
  }
}

// 重新评估
async function handleReassess() {
  const id = props.loraId
  if (!id) {
    ElMessage.error(t('lora.invalid_model_id'))
    return
  }
  
  try {
    loading.value = true
    const { data } = await assessQuality(id, { num_test_images: 5 })
    ElMessage.success(t('lora.quality.assess_success', {
      score: data.data.overall_score,
      grade: data.data.grade,
    }))
    await loadReport(id)
    emit('update')
  } catch (err) {
    ElMessage.error(t('lora.quality.assess_failed'))
  } finally {
    loading.value = false
  }
}

// 首次评估
async function handleFirstAssess() {
  const id = props.loraId
  if (!id) {
    ElMessage.error(t('lora.invalid_model_id'))
    return
  }
  
  assessing.value = true
  try {
    const { data } = await assessQuality(id, { num_test_images: 5 })
    ElMessage.success(t('lora.quality.assess_success', {
      score: data.data.overall_score,
      grade: data.data.grade,
    }))
    await loadReport(id)
    emit('update')
  } catch (err) {
    ElMessage.error(t('lora.quality.assess_failed'))
  } finally {
    assessing.value = false
  }
}

// 关闭
function handleClose() {
  visible.value = false
  emit('close')
}

// 获取等级颜色
function getScoreColor(score) {
  if (score >= 90) return '#67C23A'  // green
  if (score >= 80) return '#95D475'  // light green
  if (score >= 70) return '#E6A23C'  // yellow
  if (score >= 60) return '#F56C6C'  // red
  return '#C0C4CC'  // gray
}

// 获取等级文本
function getGradeText(grade) {
  return getGradeDescription(grade, t)
}

// 截断文本
function truncateText(text, maxLength) {
  if (!text) return ''
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
}

// 图片加载错误处理
function handleImageError(event) {
  console.warn('Failed to load image:', event.target.src)
  // 隐藏img，显示icon
  event.target.style.display = 'none'
}

// 暴露方法
defineExpose({
  open,
})
</script>

<style scoped>
.loading-container,
.empty-container {
  padding: 40px 0;
}

.quality-report {
  max-height: 70vh;
  overflow-y: auto;
}

/* 总体评分 */
.score-overview {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  color: white;
  margin-bottom: 24px;
}

.score-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 4px solid rgba(255, 255, 255, 0.3);
}

.score-number {
  font-size: 36px;
  font-weight: bold;
}

.score-grade {
  font-size: 24px;
  font-weight: bold;
  margin-top: 4px;
}

.grade-s .score-circle { border-color: #67C23A; }
.grade-a .score-circle { border-color: #95D475; }
.grade-b .score-circle { border-color: #E6A23C; }
.grade-c .score-circle { border-color: #F56C6C; }
.grade-d .score-circle { border-color: #E6A23C; }
.grade-f .score-circle { border-color: #F56C6C; }

.score-info h3 {
  margin: 0 0 8px 0;
  font-size: 24px;
}

.score-time {
  margin: 0;
  opacity: 0.8;
  font-size: 14px;
}

/* 详细评分 */
.detail-card,
.images-card,
.recommendations-card {
  margin-bottom: 24px;
}

.card-header {
  font-weight: bold;
  font-size: 16px;
}

.score-bars {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.score-bar-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bar-label {
  display: flex;
  justify-content: space-between;
  font-weight: 500;
}

.bar-value {
  font-weight: bold;
  color: #409EFF;
}

/* 测试图片 */
.test-image-card {
  border: 1px solid #EBEEF5;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 16px;
}

.image-placeholder {
  height: 200px;
  background: #F5F7FA;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
  position: relative;
  overflow: hidden;
}

.image-placeholder img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-placeholder p {
  margin-top: 8px;
  font-size: 14px;
  text-transform: capitalize;
  z-index: 1;
  background: rgba(255, 255, 255, 0.8);
  padding: 4px 12px;
  border-radius: 4px;
}

.image-info {
  padding: 12px;
  background: white;
}

.image-prompt {
  margin: 0 0 4px 0;
  font-size: 12px;
  color: #606266;
  line-height: 1.4;
}

.image-seed {
  margin: 0;
  font-size: 11px;
  color: #909399;
}

/* 优化建议 */
.recommendation-item {
  margin-bottom: 12px;
}

.recommendation-item:last-child {
  margin-bottom: 0;
}
</style>
