<template>
  <el-dialog
    v-model="visible"
    :title="$t('lora.training_wizard.title')"
    width="800px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-steps :active="currentStep" finish-status="success" style="margin-bottom: 30px;">
      <el-step :title="$t('lora.training_wizard.step_preset')" />
      <el-step :title="$t('lora.training_wizard.step_config')" />
      <el-step :title="$t('lora.training_wizard.step_confirm')" />
    </el-steps>

    <!-- Step 1: Select Preset -->
    <div v-show="currentStep === 0" class="step-content" v-loading="loadingPresets">
      <h3>{{ $t('lora.training_wizard.select_preset') }}</h3>
      <p class="step-description">{{ $t('lora.training_wizard.preset_description') }}</p>
      
      <el-row :gutter="16">
        <el-col :span="12" v-for="preset in presets" :key="preset.name">
          <el-card
            :class="['preset-card', { 'preset-card-selected': selectedPreset === preset.name }]"
            @click="selectedPreset = preset.name"
            shadow="hover"
          >
            <template #header>
              <div class="preset-header">
                <el-tag :type="getPresetType(preset.name)" size="large">
                  {{ $t(`lora.training_wizard.presets.${preset.name}.name`) }}
                </el-tag>
                <el-icon v-if="selectedPreset === preset.name" color="#409EFF" size="20">
                  <Check />
                </el-icon>
              </div>
            </template>
            
            <div class="preset-info">
              <p>{{ $t(`lora.training_wizard.presets.${preset.name}.description`) }}</p>
              <el-descriptions :column="1" size="small" border>
                <el-descriptions-item :label="$t('lora.training_wizard.epochs')">
                  {{ preset.config.epochs }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('lora.training_wizard.learning_rate')">
                  {{ preset.config.learning_rate }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('lora.training_wizard.network_dim')">
                  {{ preset.config.network_dim }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('lora.training_wizard.estimated_time')">
                  {{ formatTime(preset.estimated_minutes) }}
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-alert
        :title="$t('lora.training_wizard.custom_hint')"
        type="info"
        :closable="false"
        show-icon
        style="margin-top: 20px;"
      />
    </div>

    <!-- Step 2: Custom Configuration (Optional) -->
    <div v-show="currentStep === 1" class="step-content">
      <el-checkbox v-model="useCustomConfig" style="margin-bottom: 20px;">
        {{ $t('lora.training_wizard.enable_custom') }}
      </el-checkbox>

      <el-form
        v-if="useCustomConfig"
        :model="customConfig"
        label-width="180px"
        :rules="configRules"
        ref="configFormRef"
      >
        <el-divider content-position="left">{{ $t('lora.training_wizard.basic_config') }}</el-divider>
        
        <el-form-item :label="$t('lora.training_wizard.epochs')" prop="epochs">
          <el-slider v-model="customConfig.epochs" :min="1" :max="100" show-input />
        </el-form-item>

        <el-form-item :label="$t('lora.training_wizard.learning_rate')" prop="learning_rate">
          <el-input-number
            v-model="customConfig.learning_rate"
            :min="0.00001"
            :max="0.01"
            :step="0.00001"
            :precision="5"
            style="width: 100%;"
          />
        </el-form-item>

        <el-form-item :label="$t('lora.training_wizard.network_dim')" prop="network_dim">
          <el-select v-model="customConfig.network_dim" style="width: 100%;">
            <el-option :label="8" :value="8" />
            <el-option :label="16" :value="16" />
            <el-option :label="32" :value="32" />
            <el-option :label="64" :value="64" />
            <el-option :label="128" :value="128" />
            <el-option :label="256" :value="256" />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">{{ $t('lora.training_wizard.advanced_config') }}</el-divider>

        <el-form-item :label="$t('lora.training_wizard.batch_size')" prop="batch_size">
          <el-input-number v-model="customConfig.batch_size" :min="1" :max="16" style="width: 100%;" />
        </el-form-item>

        <el-form-item :label="$t('lora.training_wizard.resolution')" prop="resolution">
          <el-select v-model="customConfig.resolution" style="width: 100%;">
            <el-option :label="$t('lora.training_wizard.resolutions.512')" :value="512" />
            <el-option :label="$t('lora.training_wizard.resolutions.768')" :value="768" />
            <el-option :label="$t('lora.training_wizard.resolutions.1024')" :value="1024" />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('lora.training_wizard.optimizer')">
          <el-select v-model="customConfig.optimizer" style="width: 100%;">
            <el-option :label="$t('lora.training_wizard.optimizers.adamw8bit')" value="AdamW8bit" />
            <el-option :label="$t('lora.training_wizard.optimizers.adamw')" value="AdamW" />
            <el-option :label="$t('lora.training_wizard.optimizers.dadaptation')" value="DAdaptation" />
          </el-select>
        </el-form-item>

        <el-alert
          :title="$t('lora.training_wizard.estimated') + ': ' + formatTime(estimatedTime)"
          type="success"
          :closable="false"
          show-icon
          style="margin-top: 20px;"
        />
      </el-form>

      <el-alert
        v-else
        :title="$t('lora.training_wizard.using_preset') + ': ' + selectedPreset"
        type="success"
        :closable="false"
        show-icon
      />
    </div>

    <!-- Step 3: Confirm -->
    <div v-show="currentStep === 2" class="step-content">
      <h3>{{ $t('lora.training_wizard.confirm_title') }}</h3>
      <p class="step-description">{{ $t('lora.training_wizard.confirm_description') }}</p>

      <el-card shadow="never">
        <el-descriptions :column="2" border>
          <el-descriptions-item :label="$t('lora.training_wizard.preset')">
            {{ useCustomConfig ? $t('common.custom') : selectedPreset }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('lora.training_wizard.epochs')">
            {{ finalConfig.epochs }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('lora.training_wizard.learning_rate')">
            {{ finalConfig.learning_rate }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('lora.training_wizard.network_dim')">
            {{ finalConfig.network_dim }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('lora.training_wizard.batch_size')">
            {{ finalConfig.batch_size }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('lora.training_wizard.resolution')">
            {{ finalConfig.resolution }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('lora.training_wizard.estimated_time')" :span="2">
            {{ formatTime(estimatedTime) }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-alert
        :title="$t('lora.training_wizard.warning')"
        type="warning"
        :closable="false"
        show-icon
        style="margin-top: 20px;"
      />
    </div>

    <template #footer>
      <el-button @click="handleClose">{{ $t('common.cancel') }}</el-button>
      <el-button v-if="currentStep > 0" @click="currentStep--">
        {{ $t('lora.training_wizard.previous') }}
      </el-button>
      <el-button
        v-if="currentStep < 2"
        type="primary"
        @click="nextStep"
        :disabled="!canProceed"
      >
        {{ $t('lora.training_wizard.next') }}
      </el-button>
      <el-button
        v-if="currentStep === 2"
        type="primary"
        @click="handleStartTraining"
        :loading="training"
      >
        {{ $t('lora.training_wizard.start_training') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import { getTrainingPresets, startTraining } from '../../api/lora'

const { t } = useI18n()

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  loraId: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['update:modelValue', 'training-started'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const currentStep = ref(0)
const presets = ref([])
const selectedPreset = ref('standard')
const useCustomConfig = ref(false)
const training = ref(false)
const loadingPresets = ref(false)
const configFormRef = ref(null)

const customConfig = ref({
  epochs: 10,
  learning_rate: 0.0001,
  network_dim: 64,
  batch_size: 1,
  resolution: 512,
  optimizer: 'AdamW8bit'
})

const configRules = {
  epochs: [
    { required: true, message: t('lora.training_wizard.rules.epochs_required'), trigger: 'blur' }
  ],
  learning_rate: [
    { required: true, message: t('lora.training_wizard.rules.lr_required'), trigger: 'blur' }
  ],
  network_dim: [
    { required: true, message: t('lora.training_wizard.rules.dim_required'), trigger: 'change' }
  ]
}

const canProceed = computed(() => {
  if (currentStep.value === 0) {
    return !!selectedPreset.value
  }
  if (currentStep.value === 1 && useCustomConfig.value) {
    return true
  }
  return true
})

const finalConfig = computed(() => {
  if (useCustomConfig.value) {
    return customConfig.value
  }
  const preset = presets.value.find(p => p.name === selectedPreset.value)
  return preset?.config || {}
})

const estimatedTime = computed(() => {
  const preset = presets.value.find(p => p.name === selectedPreset.value)
  if (useCustomConfig.value) {
    // Simple estimation based on epochs
    return customConfig.value.epochs * 5 // 5 minutes per epoch
  }
  return preset?.estimated_minutes || 50
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    loadPresets()
    currentStep.value = 0
  }
})

async function loadPresets() {
  loadingPresets.value = true
  try {
    const { data } = await getTrainingPresets()
    presets.value = data.data || []
  } catch (err) {
    ElMessage.error(t('lora.training_wizard.load_presets_error'))
  } finally {
    loadingPresets.value = false
  }
}

function nextStep() {
  if (currentStep.value === 1 && useCustomConfig.value) {
    configFormRef.value?.validate((valid) => {
      if (valid) {
        currentStep.value++
      }
    })
  } else {
    currentStep.value++
  }
}

function getPresetType(name) {
  const types = {
    quick_test: 'info',
    standard: 'success',
    high_quality: 'warning',
    anime_style: ''
  }
  return types[name] || ''
}

function formatTime(minutes) {
  if (minutes < 60) {
    return `${minutes} ${t('lora.training_wizard.minutes')}`
  }
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${hours} ${t('lora.training_wizard.hours')} ${mins} ${t('lora.training_wizard.minutes')}`
}

async function handleStartTraining() {
  training.value = true
  try {
    const requestData = {}
    
    if (useCustomConfig.value) {
      requestData.custom_config = customConfig.value
    } else {
      requestData.use_preset = selectedPreset.value
    }

    await startTraining(props.loraId, requestData)
    ElMessage.success(t('lora.training_wizard.training_started'))
    emit('training-started')
    handleClose()
  } catch (err) {
    ElMessage.error(t('lora.training_wizard.start_error'))
  } finally {
    training.value = false
  }
}

function handleClose() {
  visible.value = false
  currentStep.value = 0
  useCustomConfig.value = false
}

onMounted(() => {
  if (props.modelValue) {
    loadPresets()
  }
})
</script>

<style scoped>
.step-content {
  min-height: 400px;
}

.step-description {
  color: #909399;
  margin-bottom: 20px;
}

.preset-card {
  cursor: pointer;
  margin-bottom: 16px;
  transition: all 0.3s;
  border: 2px solid transparent;
}

.preset-card:hover {
  transform: translateY(-2px);
}

.preset-card-selected {
  border-color: #409EFF;
  box-shadow: 0 2px 12px 0 rgba(64, 158, 255, 0.3);
}

.preset-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preset-info p {
  margin-bottom: 12px;
  color: #606266;
  font-size: 14px;
}
</style>
