<template>
  <div class="quality-report-container">
    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading"><Loading /></el-icon>
      <p>{{ t('quality_report.loading') }}</p>
    </div>

    <div v-else-if="error" class="error-state">
      <el-alert type="error" :title="error" :closable="false" />
      <el-button type="primary" @click="loadReport" style="margin-top: 16px">
        {{ t('common.retry') }}
      </el-button>
    </div>

    <div v-else-if="report" class="report-content">
      <!-- Header -->
      <div class="report-header">
        <h1>{{ t('quality_report.title') }}</h1>
        <el-button @click="$router.back()">{{ t('quality_report.back_to_lora') }}</el-button>
      </div>

      <!-- Overall Score -->
      <el-card class="score-card">
        <div class="score-display">
          <div class="score-circle" :class="'grade-' + report.grade">
            <div class="score-number">{{ report.overall_score }}</div>
            <div class="score-label">/ 100</div>
          </div>
          <div class="grade-badge" :class="'grade-' + report.grade">
            Grade {{ report.grade }}
          </div>
        </div>
        <div class="score-meta">
          <el-tag :type="diagnosisStatusType">
            {{ diagnosisStatusText }}
          </el-tag>
          <span class="report-date">
            Assessed: {{ formatDate(report.created_at) }}
          </span>
        </div>
      </el-card>

      <!-- Training Diagnosis Alert -->
      <el-alert
        v-if="report.training_diagnosis && report.training_diagnosis.overall_status !== 'healthy'"
        :type="diagnosisAlertType"
        :title="diagnosisAlertTitle"
        :closable="false"
        show-icon
        style="margin: 20px 0"
      >
        <template #default>
          <ul class="diagnosis-list">
            <li v-for="(rec, idx) in report.training_diagnosis.recommendations" :key="idx">
              {{ rec }}
            </li>
          </ul>
        </template>
      </el-alert>

      <!-- Detailed Scores -->
      <el-card class="detail-card">
        <template #header>
          <h2>{{ t('quality_report.detailed_scores') }}</h2>
        </template>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <div class="score-item">
              <div class="score-item-header">
                <span class="score-item-label">{{ t('quality_report.training_loss') }}</span>
                <span class="score-item-value">{{ report.loss_score || 0 }}</span>
              </div>
              <el-progress 
                :percentage="report.loss_score || 0" 
                :color="getScoreColor" 
              />
            </div>
          </el-col>
          
          <el-col :span="12">
            <div class="score-item">
              <div class="score-item-header">
                <span class="score-item-label">{{ t('quality_report.training_completion') }}</span>
                <span class="score-item-value">{{ report.completion_score || 0 }}</span>
              </div>
              <el-progress 
                :percentage="report.completion_score || 0" 
                :color="getScoreColor" 
              />
            </div>
          </el-col>
          
          <el-col :span="12">
            <div class="score-item">
              <div class="score-item-header">
                <span class="score-item-label">{{ t('quality_report.model_file_quality') }}</span>
                <span class="score-item-value">{{ report.file_score || 0 }}</span>
              </div>
              <el-progress 
                :percentage="report.file_score || 0" 
                :color="getScoreColor" 
              />
            </div>
          </el-col>
          
          <el-col :span="12">
            <div class="score-item">
              <div class="score-item-header">
                <span class="score-item-label">Generation Success Rate</span>
                <span class="score-item-value">{{ report.generation_success || 0 }}%</span>
              </div>
              <el-progress 
                :percentage="report.generation_success || 0" 
                :color="getScoreColor" 
              />
            </div>
          </el-col>
          
          <el-col :span="24">
            <div class="score-item">
              <div class="score-item-header">
                <span class="score-item-label">CLIP Character Consistency</span>
                <span class="score-item-value">{{ report.clip_consistency || 0 }}</span>
              </div>
              <el-progress 
                :percentage="report.clip_consistency || 0" 
                :color="getScoreColor" 
              />
            </div>
          </el-col>
        </el-row>
      </el-card>

      <!-- Training Diagnosis Details -->
      <el-card v-if="report.training_diagnosis" class="diagnosis-card">
        <template #header>
          <h2>Training Diagnosis</h2>
        </template>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <h3>Overfitting Detection</h3>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="Status">
                <el-tag :type="report.training_diagnosis.overfitting.is_overfitting ? 'danger' : 'success'">
                  {{ report.training_diagnosis.overfitting.is_overfitting ? 'Detected' : 'Not Detected' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="Severity">
                {{ capitalizeFirst(report.training_diagnosis.overfitting.severity) }}
              </el-descriptions-item>
              <el-descriptions-item label="Confidence">
                {{ (report.training_diagnosis.overfitting.confidence * 100).toFixed(0) }}%
              </el-descriptions-item>
            </el-descriptions>
            
            <div v-if="report.training_diagnosis.overfitting.indicators.length > 0" class="indicators">
              <h4>Indicators:</h4>
              <ul>
                <li v-for="(indicator, idx) in report.training_diagnosis.overfitting.indicators" :key="idx">
                  {{ indicator }}
                </li>
              </ul>
            </div>
          </el-col>
          
          <el-col :span="12">
            <h3>Underfitting Detection</h3>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="Status">
                <el-tag :type="report.training_diagnosis.underfitting.is_underfitting ? 'warning' : 'success'">
                  {{ report.training_diagnosis.underfitting.is_underfitting ? 'Detected' : 'Not Detected' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="Severity">
                {{ capitalizeFirst(report.training_diagnosis.underfitting.severity) }}
              </el-descriptions-item>
              <el-descriptions-item label="Confidence">
                {{ (report.training_diagnosis.underfitting.confidence * 100).toFixed(0) }}%
              </el-descriptions-item>
            </el-descriptions>
            
            <div v-if="report.training_diagnosis.underfitting.indicators.length > 0" class="indicators">
              <h4>Indicators:</h4>
              <ul>
                <li v-for="(indicator, idx) in report.training_diagnosis.underfitting.indicators" :key="idx">
                  {{ indicator }}
                </li>
              </ul>
            </div>
          </el-col>
        </el-row>
      </el-card>

      <!-- Test Images -->
      <el-card v-if="report.test_images && report.test_images.length > 0" class="images-card">
        <template #header>
          <h2>Test Images ({{ report.test_images.length }})</h2>
        </template>
        
        <el-row :gutter="16">
          <el-col v-for="(img, idx) in report.test_images" :key="idx" :span="8">
            <el-card shadow="hover" class="test-image-card">
              <div class="image-placeholder">
                <el-icon :size="48"><Picture /></el-icon>
                <p>{{ img.scenario }}</p>
              </div>
              <div class="image-info">
                <p class="prompt-text" :title="img.prompt">{{ truncateText(img.prompt, 80) }}</p>
                <el-tag size="small">Seed: {{ img.seed }}</el-tag>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-card>

      <!-- Recommendations -->
      <el-card v-if="report.recommendations && report.recommendations.length > 0" class="recommendations-card">
        <template #header>
          <h2>{{ t('quality_report.recommendations') }}</h2>
        </template>
        
        <el-timeline>
          <el-timeline-item
            v-for="(rec, idx) in report.recommendations"
            :key="idx"
            :type="idx < 2 ? 'warning' : 'info'"
          >
            {{ rec }}
          </el-timeline-item>
        </el-timeline>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Loading, Picture } from '@element-plus/icons-vue'
import { getQualityReport } from '@/api/lora'

const { t } = useI18n()
const route = useRoute()
const loading = ref(false)
const error = ref(null)
const report = ref(null)

const loraId = computed(() => parseInt(route.params.loraId))

// Computed properties for diagnosis display
const diagnosisStatusType = computed(() => {
  if (!report.value?.training_diagnosis) return 'info'
  const status = report.value.training_diagnosis.overall_status
  const map = {
    healthy: 'success',
    overfitting: 'danger',
    underfitting: 'warning',
    inconsistent: 'warning'
  }
  return map[status] || 'info'
})

const diagnosisStatusText = computed(() => {
  if (!report.value?.training_diagnosis) return t('quality_report.diagnosis_unknown')
  const status = report.value.training_diagnosis.overall_status
  const map = {
    healthy: t('quality_report.diagnosis_healthy'),
    overfitting: t('quality_report.diagnosis_overfitting'),
    underfitting: t('quality_report.diagnosis_underfitting'),
    inconsistent: t('quality_report.diagnosis_inconsistent')
  }
  return map[status] || t('quality_report.diagnosis_unknown')
})

const diagnosisAlertType = computed(() => {
  if (!report.value?.training_diagnosis) return 'info'
  const status = report.value.training_diagnosis.overall_status
  if (status === 'overfitting') return 'error'
  if (status === 'underfitting') return 'warning'
  return 'warning'
})

const diagnosisAlertTitle = computed(() => {
  if (!report.value?.training_diagnosis) return ''
  const status = report.value.training_diagnosis.overall_status
  const map = {
    overfitting: t('quality_report.diagnosis_overfitting'),
    underfitting: t('quality_report.diagnosis_underfitting'),
    inconsistent: t('quality_report.diagnosis_inconsistent')
  }
  return map[status] || t('quality_report.diagnosis_unknown')
})

// Utility functions
const getScoreColor = (percentage) => {
  if (percentage >= 90) return '#67c23a'
  if (percentage >= 80) return '#85ce61'
  if (percentage >= 70) return '#e6a23c'
  if (percentage >= 60) return '#f56c6c'
  return '#ff4949'
}

const formatDate = (dateStr) => {
  if (!dateStr) return t('common.none')
  return new Date(dateStr).toLocaleString()
}

const capitalizeFirst = (str) => {
  if (!str) return t('common.none')
  return str.charAt(0).toUpperCase() + str.slice(1)
}

const truncateText = (text, maxLength) => {
  if (!text) return ''
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
}

// Load report
const loadReport = async () => {
  loading.value = true
  error.value = null
  
  try {
    const response = await getQualityReport(loraId.value)
    report.value = response.data
  } catch (err) {
    error.value = err.message || t('quality_report.load_failed')
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadReport()
})
</script>

<style scoped>
.quality-report-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.loading-state, .error-state {
  text-align: center;
  padding: 60px 20px;
}

.loading-state .el-icon {
  font-size: 48px;
  color: #409eff;
  margin-bottom: 16px;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.report-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.score-card {
  margin-bottom: 20px;
}

.score-display {
  display: flex;
  align-items: center;
  gap: 32px;
  padding: 20px;
}

.score-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 4px solid;
}

.score-circle.grade-S { border-color: #67c23a; background: #f0f9ff; }
.score-circle.grade-A { border-color: #85ce61; background: #f0f9ff; }
.score-circle.grade-B { border-color: #e6a23c; background: #fdf6ec; }
.score-circle.grade-C { border-color: #f56c6c; background: #fef0f0; }
.score-circle.grade-D { border-color: #ff4949; background: #fef0f0; }
.score-circle.grade-F { border-color: #ff4949; background: #fef0f0; }

.score-number {
  font-size: 36px;
  font-weight: bold;
  color: #303133;
}

.score-label {
  font-size: 14px;
  color: #909399;
}

.grade-badge {
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 24px;
  font-weight: bold;
}

.grade-badge.grade-S { background: #f0f9ff; color: #67c23a; }
.grade-badge.grade-A { background: #f0f9ff; color: #85ce61; }
.grade-badge.grade-B { background: #fdf6ec; color: #e6a23c; }
.grade-badge.grade-C { background: #fef0f0; color: #f56c6c; }
.grade-badge.grade-D { background: #fef0f0; color: #ff4949; }
.grade-badge.grade-F { background: #fef0f0; color: #ff4949; }

.score-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 20px 20px;
}

.report-date {
  color: #909399;
  font-size: 14px;
}

.detail-card, .diagnosis-card, .images-card, .recommendations-card {
  margin-bottom: 20px;
}

.score-item {
  padding: 16px;
}

.score-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.score-item-label {
  font-size: 14px;
  color: #606266;
}

.score-item-value {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.diagnosis-card h3 {
  margin-top: 0;
  margin-bottom: 16px;
  font-size: 16px;
  color: #303133;
}

.indicators {
  margin-top: 16px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.indicators h4 {
  margin: 0 0 8px;
  font-size: 14px;
  color: #606266;
}

.indicators ul {
  margin: 0;
  padding-left: 20px;
}

.indicators li {
  margin-bottom: 4px;
  font-size: 13px;
  color: #606266;
}

.diagnosis-list {
  margin: 8px 0 0;
  padding-left: 20px;
}

.diagnosis-list li {
  margin-bottom: 4px;
  font-size: 14px;
}

.test-image-card {
  margin-bottom: 16px;
}

.image-placeholder {
  height: 150px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  border-radius: 4px;
  color: #909399;
}

.image-placeholder p {
  margin: 8px 0 0;
  font-size: 14px;
}

.image-info {
  margin-top: 12px;
}

.prompt-text {
  font-size: 12px;
  color: #606266;
  margin-bottom: 8px;
  line-height: 1.4;
}

h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
</style>
