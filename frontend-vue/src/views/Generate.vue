<template>
  <div class="generate-page">
    <h1 class="page-title">{{ $t('generate.title') }}</h1>

    <!-- IP Selector -->
    <el-card shadow="never" class="ip-selector-card">
      <el-row :gutter="16" align="middle">
        <el-col :span="18">
          <el-select v-model="selectedIPId" :placeholder="$t('generate.select_ip_placeholder')" style="width:100%" @change="onIPChange">
            <el-option v-for="ip in ipAssets" :key="ip.id" :label="ip.name" :value="ip.id" />
          </el-select>
        </el-col>
        <el-col :span="6" style="text-align:right;">
          <el-button @click="router.push('/ip')">
            <el-icon><Plus /></el-icon> {{ $t('ip.create_asset') }}
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- IP Info Card (shown when IP selected) -->
    <el-card v-if="currentIP" shadow="never" class="ip-info-card">
      <el-descriptions :column="3" border size="small">
        <el-descriptions-item :label="$t('generate.ip_name')">{{ currentIP.name }}</el-descriptions-item>
        <el-descriptions-item :label="$t('generate.ip_trigger_word')">
          <el-tag>{{ currentIP.trigger_word || '-' }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item :label="$t('generate.ip_style')">{{ currentIP.style_template || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('generate.ip_lora_status')" :span="3">
          <el-tag v-if="currentIP.lora_model_id" type="success" size="small">{{ $t('generate.lora_trained') }}</el-tag>
          <el-tag v-else type="info" size="small">{{ $t('generate.lora_not_trained') }}</el-tag>
          <el-switch
            v-model="loraEnabled"
            :disabled="!currentIP.lora_model_id"
            :active-text="$t('generate.enable_lora')"
            style="margin-left: 12px;"
          />
          <router-link v-if="!currentIP.lora_model_id" to="/lora" style="margin-left: 12px;">
            <el-link type="primary" size="small">{{ $t('generate.go_to_lora') }}</el-link>
          </router-link>
        </el-descriptions-item>
      </el-descriptions>
      <div style="margin-top: 12px;">
        <el-switch v-model="ipAdapterEnabled" :active-text="$t('generate.ip_adapter_mode')" />
        <span style="margin-left: 8px; color: #909399; font-size: 12px;">{{ $t('generate.ip_adapter_desc') }}</span>
      </div>
    </el-card>

    <!-- No IP hint -->
    <el-empty v-if="!currentIP && ipAssetsLoaded" :description="$t('generate.no_ip_hint')">
      <el-button type="primary" @click="$router.push('/ip')">{{ $t('ip.create_asset') }}</el-button>
    </el-empty>

    <!-- Generation Tabs -->
    <el-card v-if="currentIP" shadow="never" style="margin-top: 16px;">
      <el-tabs v-model="activeTab">
        <!-- Story Tab -->
        <el-tab-pane :label="$t('generate.story_script')" name="story">
          <el-form label-width="100px">
            <el-form-item :label="$t('generate.select_model')">
              <el-select v-model="storyChannelId" :placeholder="$t('generate.select_model_placeholder')" style="width:100%">
                <el-option v-for="ch in textChannels" :key="ch.id" :label="formatChannelLabel(ch)" :value="ch.id">
                  <span>{{ ch.name }}</span>
                  <span v-for="cap in (ch.capabilities||[])" :key="cap" style="margin-left:4px;">
                    <el-tag size="small" :type="capTagType(cap)">{{ capLabel(cap) }}</el-tag>
                  </span>
                </el-option>
              </el-select>
              <div v-if="textChannels.length === 0" class="no-model-hint">
                <el-text type="info" size="small">{{ $t('generate.no_models_available') }}</el-text>
              </div>
            </el-form-item>
            <el-form-item :label="$t('generate.story_prompt')">
              <el-input v-model="storyPrompt" type="textarea" :rows="4" :placeholder="$t('generate.story_prompt_placeholder')" />
            </el-form-item>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item :label="$t('generate.style')">
                  <el-select v-model="storyStyle" style="width:100%">
                    <el-option :label="$t('generate.style_healing')" value="healing" />
                    <el-option :label="$t('generate.style_comedy')" value="comedy" />
                    <el-option :label="$t('generate.style_adventure')" value="adventure" />
                    <el-option :label="$t('generate.style_romance')" value="romance" />
                    <el-option :label="$t('generate.style_slice_of_life')" value="slice_of_life" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item :label="$t('generate.duration')">
                  <el-input-number v-model="storyDuration" :min="5" :max="60" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item>
              <el-button type="primary" :loading="storyLoading" @click="handleGenerateStory">
                <el-icon><MagicStick /></el-icon> {{ $t('generate.generate_story_btn') }}
              </el-button>
              <el-button type="success" :loading="storyAsyncLoading" @click="handleGenerateStoryAsync" style="margin-left: 12px;">
                <el-icon><Refresh /></el-icon> {{ $t('common.generate_async_story_btn') }}
              </el-button>
            </el-form-item>
          </el-form>
          <!-- Story Result -->
          <el-card v-if="storyResult" shadow="never" class="result-card">
            <template #header>{{ $t('generate.generated_story') }}</template>
            <pre class="story-content">{{ storyResult }}</pre>
          </el-card>
        </el-tab-pane>

        <!-- Image Tab -->
        <el-tab-pane :label="$t('generate.image')" name="image">
          <el-form label-width="100px">
            <el-form-item :label="$t('generate.select_model')">
              <el-select v-model="imageChannelId" :placeholder="$t('generate.select_model_placeholder')" style="width:100%">
                <el-option v-for="ch in imageChannels" :key="ch.id" :label="formatChannelLabel(ch)" :value="ch.id">
                  <span>{{ ch.name }}</span>
                  <span v-for="cap in (ch.capabilities||[])" :key="cap" style="margin-left:4px;">
                    <el-tag size="small" :type="capTagType(cap)">{{ capLabel(cap) }}</el-tag>
                  </span>
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('generate.image_prompt')">
              <el-input v-model="imagePrompt" type="textarea" :rows="3" :placeholder="$t('generate.image_prompt_placeholder')" />
            </el-form-item>
            <el-form-item :label="$t('generate.negative_prompt')">
              <el-input v-model="imageNegativePrompt" type="textarea" :rows="2" :placeholder="$t('generate.negative_prompt_placeholder')" />
            </el-form-item>
            <el-collapse>
              <el-collapse-item :title="$t('generate.advanced_settings')">
                <el-row :gutter="16">
                  <el-col :span="8">
                    <el-form-item :label="$t('generate.width')">
                      <el-input-number v-model="imageWidth" :min="256" :max="2048" :step="64" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item :label="$t('generate.height')">
                      <el-input-number v-model="imageHeight" :min="256" :max="2048" :step="64" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item :label="$t('generate.steps')">
                      <el-input-number v-model="imageSteps" :min="1" :max="100" />
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-row :gutter="16">
                  <el-col :span="8">
                    <el-form-item :label="$t('generate.cfg_scale')">
                      <el-input-number v-model="imageCfgScale" :min="1" :max="30" :step="0.5" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item :label="$t('generate.seed')">
                      <el-input-number v-model="imageSeed" :min="-1" :max="999999999" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item :label="$t('generate.lora_weight')" v-if="loraEnabled">
                      <el-slider v-model="loraWeight" :min="0" :max="1" :step="0.1" show-input />
                    </el-form-item>
                  </el-col>
                </el-row>
                
                <!-- IP-Adapter Scale (shown when IP-Adapter is enabled) -->
                <el-row :gutter="16" v-if="ipAdapterEnabled">
                  <el-col :span="12">
                    <el-form-item :label="$t('generate.ip_adapter_scale')">
                      <el-slider v-model="ipAdapterScale" :min="0" :max="1" :step="0.05" show-input />
                      <div class="param-hint">
                        <el-icon><InfoFilled /></el-icon>
                        <span>{{ $t('generate.ip_adapter_scale_hint') }}</span>
                      </div>
                    </el-form-item>
                  </el-col>
                </el-row>
                
                <!-- More Parameters (collapsible) -->
                <el-collapse v-model="moreParamsCollapse" style="margin-top: 12px;">
                  <el-collapse-item :title="$t('generate.more_params')" name="more">
                    <el-row :gutter="16">
                      <el-col :span="8">
                        <el-form-item :label="$t('generate.sampler')">
                          <el-select v-model="sampler" style="width:100%">
                            <el-option :label="$t('generate.samplers.dpm_2m_karras')" value="DPM++ 2M Karras" />
                            <el-option :label="$t('generate.samplers.euler_a')" value="Euler a" />
                            <el-option :label="$t('generate.samplers.ddim')" value="DDIM" />
                            <el-option :label="$t('generate.samplers.dpm_sde_karras')" value="DPM++ SDE Karras" />
                          </el-select>
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item :label="$t('generate.scheduler')">
                          <el-select v-model="scheduler" style="width:100%">
                            <el-option :label="$t('generate.schedulers.karras')" value="karras" />
                            <el-option :label="$t('generate.schedulers.normal')" value="normal" />
                            <el-option :label="$t('generate.schedulers.exponential')" value="exponential" />
                          </el-select>
                        </el-form-item>
                      </el-col>
                    </el-row>
                  </el-collapse-item>
                </el-collapse>
              </el-collapse-item>
            </el-collapse>
            <el-form-item>
              <el-button type="primary" :loading="imageLoading" @click="handleGenerateImage">
                <el-icon><PictureFilled /></el-icon> {{ $t('generate.generate_image_btn') }}
              </el-button>
              <el-button type="success" :loading="imageAsyncLoading" @click="handleGenerateImageAsync" style="margin-left: 12px;">
                <el-icon><Refresh /></el-icon> {{ $t('common.generate_async_image_btn') }}
              </el-button>
            </el-form-item>
          </el-form>
          <!-- Image Result -->
          <el-card v-if="imageResult" shadow="never" class="result-card">
            <template #header>{{ $t('generate.generated_image') }}</template>
            <el-image :src="imageResult" fit="contain" style="max-height:512px;" :preview-src-list="[imageResult]" />
          </el-card>
        </el-tab-pane>

        <!-- Video Tab -->
        <el-tab-pane :label="$t('generate.video')" name="video">
          <el-form label-width="100px">
            <el-form-item :label="$t('generate.select_model')">
              <el-select v-model="videoChannelId" :placeholder="$t('generate.select_model_placeholder')" style="width:100%">
                <el-option v-for="ch in videoChannels" :key="ch.id" :label="formatChannelLabel(ch)" :value="ch.id">
                  <span>{{ ch.name }}</span>
                  <span v-for="cap in (ch.capabilities||[])" :key="cap" style="margin-left:4px;">
                    <el-tag size="small" :type="capTagType(cap)">{{ capLabel(cap) }}</el-tag>
                  </span>
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('generate.video_prompt')">
              <el-input v-model="videoPrompt" type="textarea" :rows="3" :placeholder="$t('generate.video_prompt_placeholder')" />
            </el-form-item>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item :label="$t('generate.duration')">
                  <el-input-number v-model="videoDuration" :min="2" :max="15" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item :label="$t('generate.fps')">
                  <el-input-number v-model="videoFps" :min="4" :max="30" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item>
              <el-button type="primary" :loading="videoLoading" @click="handleGenerateVideo">
                <el-icon><VideoCameraFilled /></el-icon> {{ $t('generate.generate_video_btn') }}
              </el-button>
              <el-button type="success" :loading="videoAsyncLoading" @click="handleGenerateVideoAsync" style="margin-left: 12px;">
                <el-icon><Refresh /></el-icon> {{ $t('common.generate_async_video_btn') }}
              </el-button>
            </el-form-item>
          </el-form>
          <!-- Video Result -->
          <el-card v-if="videoResult" shadow="never" class="result-card">
            <template #header>{{ $t('generate.generated_video') }}</template>
            <video :src="videoResult" controls style="max-width:100%;max-height:480px;" />
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getIPList } from '@/api/ip'
import { getChannelsByCapability } from '@/api/llm'
import { generateStory, generateStoryAsync, generateImage, generateImageAsync, generateVideo, generateVideoAsync, getSmartReferences, getAdaptiveScale } from '@/api/generate'

const router = useRouter()

const { t } = useI18n()

// IP state
const ipAssets = ref([])
const ipAssetsLoaded = ref(false)
const selectedIPId = ref(null)
const currentIP = ref(null)
const ipAdapterEnabled = ref(false)
const loraEnabled = ref(false)
const loraWeight = ref(0.8)

// Channel state
const textChannels = ref([])
const imageChannels = ref([])
const videoChannels = ref([])

// Tab state
const activeTab = ref('story')

// Story form
const storyChannelId = ref(null)
const storyPrompt = ref('')
const storyStyle = ref('healing')
const storyDuration = ref(10)
const storyLoading = ref(false)
const storyAsyncLoading = ref(false)
const storyResult = ref('')

// Image form
const imageChannelId = ref(null)
const imagePrompt = ref('')
const imageNegativePrompt = ref('')
const imageWidth = ref(512)
const imageHeight = ref(512)
const imageSteps = ref(30)
const imageCfgScale = ref(7.5)
const imageSeed = ref(-1)
const imageLoading = ref(false)
const imageAsyncLoading = ref(false)
const imageResult = ref('')

// Smart IP-Adapter features
const ipAdapterScale = ref(0.85)
const smartReferences = ref([])
const adaptiveScale = ref(0.7)
const promptAnalysis = ref(null)
const autoSelectRefs = ref(true) // Auto-select reference images

// More parameters collapse
const moreParamsCollapse = ref('')
const sampler = ref('DPM++ 2M Karras')
const scheduler = ref('karras')

// Video form
const videoChannelId = ref(null)
const videoPrompt = ref('')
const videoDuration = ref(5)
const videoFps = ref(8)
const videoLoading = ref(false)
const videoAsyncLoading = ref(false)
const videoResult = ref('')

// Capability badge helpers
const capLabelMap = {
  text_generation: 'Text', chat: 'Chat', vision: 'Vision', code: 'Code',
  text_to_image: 'Image', image_generation: 'Image',
  text_to_video: 'Video', video_generation: 'Video',
}
function capLabel(cap) { return t(`generate.model_badge_${capLabelMap[cap]?.toLowerCase()}`) || capLabelMap[cap] || cap }
function capTagType(cap) {
  if (['text_generation', 'chat'].includes(cap)) return ''
  if (['text_to_image', 'image_generation'].includes(cap)) return 'danger'
  if (['text_to_video', 'video_generation'].includes(cap)) return 'warning'
  if (cap === 'vision') return 'success'
  return 'info'
}
function formatChannelLabel(ch) {
  let label = ch.name || `${ch.provider} - ${ch.model_name}`
  return label
}

async function loadIPs() {
  try {
    const { data } = await getIPList({ skip: 0, limit: 100 })
    // Unified response format
    ipAssets.value = data.data || []
    ipAssetsLoaded.value = true
    if (ipAssets.value.length > 0) {
      selectedIPId.value = ipAssets.value[0].id
      onIPChange(selectedIPId.value)
    }
  } catch (err) {
    if (import.meta.env.DEV) {
      console.error('Failed to load IPs:', err)
    }
  }
}

async function loadChannels() {
  try {
    const [textRes, imageRes, videoRes] = await Promise.all([
      getChannelsByCapability('text_generation'),
      getChannelsByCapability('text_to_image'),
      getChannelsByCapability('text_to_video'),
    ])
    // Unified response format: { success: true, data: {...}, message: "..." }
    textChannels.value = textRes.data.data || []
    imageChannels.value = imageRes.data.data || []
    videoChannels.value = videoRes.data.data || []
    
    // 为故事生成默认选择第一个文本模型
    if (textChannels.value.length > 0 && !storyChannelId.value) {
      storyChannelId.value = textChannels.value[0].id
    }
    
    // 为图片生成默认选择第一个图片模型
    if (imageChannels.value.length > 0 && !imageChannelId.value) {
      imageChannelId.value = imageChannels.value[0].id
    }
    
    // 为视频生成默认选择第一个视频模型
    if (videoChannels.value.length > 0 && !videoChannelId.value) {
      videoChannelId.value = videoChannels.value[0].id
    }
    
    // 如果没有可用模型，显示警告
    // No text models available - user will see warning in UI
  } catch (err) {
    if (import.meta.env.DEV) {
      console.error('Failed to load channels:', err)
    }
  }
}

function onIPChange(ipId) {
  currentIP.value = ipAssets.value.find(ip => ip.id === ipId) || null
  if (currentIP.value) {
    loraEnabled.value = !!currentIP.value.lora_model_id
  }
}

// Smart reference selection with debounce
let smartRefDebounceTimer = null

async function loadSmartReferences() {
  if (!selectedIPId.value || !imagePrompt.value) {
    return
  }
  
  try {
    const { data } = await getSmartReferences({
      ip_asset_id: selectedIPId.value,
      prompt: imagePrompt.value,
      max_images: 3,
    })
    
    const result = data.data || {}
    smartReferences.value = result.selected_references || []
    adaptiveScale.value = result.adaptive_scale || 0.7
    promptAnalysis.value = result.prompt_analysis || null
  } catch (err) {
    if (import.meta.env.DEV) {
      console.error('Failed to load smart references:', err)
    }
    // Fallback to empty array, will use manual selection
    smartReferences.value = []
  }
}

// Watch for prompt changes to auto-update smart references with debounce
watch([imagePrompt, selectedIPId], () => {
  if (autoSelectRefs.value && ipAdapterEnabled.value) {
    // Clear previous timer
    if (smartRefDebounceTimer) {
      clearTimeout(smartRefDebounceTimer)
    }
    
    // Set new timer (500ms debounce)
    smartRefDebounceTimer = setTimeout(async () => {
      await loadSmartReferences()
    }, 500)
  }
})

async function handleGenerateStory() {
  if (!storyPrompt.value) { ElMessage.warning(t('generate.validation_error')); return }
  storyLoading.value = true
  storyResult.value = ''
  try {
    const { data } = await generateStory({
      prompt: storyPrompt.value,
      ip_id: selectedIPId.value,
      channel_id: storyChannelId.value,
      style: storyStyle.value,
      duration: storyDuration.value,
    })
    // Unified response format: { success: true, data: {...}, message: "..." }
    storyResult.value = data.data?.content || data.data?.story || data.data?.result || JSON.stringify(data.data)
    ElMessage.success(t('generate.submit_success'))
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || 'Generation failed')
  } finally {
    storyLoading.value = false
  }
}

async function handleGenerateStoryAsync() {
  if (!storyPrompt.value) { ElMessage.warning(t('generate.validation_error')); return }
  storyAsyncLoading.value = true
  storyResult.value = ''
  try {
    const { data } = await generateStoryAsync({
      prompt: storyPrompt.value,
      ip_asset_id: selectedIPId.value,
      channel_id: storyChannelId.value,
      style: storyStyle.value,
      duration_seconds: storyDuration.value,
    })
    ElMessage.success(t('common.async_submit_success'))
    // Redirect to task monitor page
    router.push('/tasks')
  } catch (err) {
    const errorMsg = err.response?.data?.detail || err.response?.data?.message || err.message || t('common.async_submit_failed');
    ElMessage.error(errorMsg);
  } finally {
    storyAsyncLoading.value = false
  }
}

async function handleGenerateImage() {
  if (!imagePrompt.value) { ElMessage.warning(t('generate.validation_error')); return }
  imageLoading.value = true
  imageResult.value = ''
  
  try {
    // Use smart references if already loaded
    let selectedRefs = []
    let scale = adaptiveScale.value
    
    // If smart references haven't been loaded yet, load them now
    if (autoSelectRefs.value && ipAdapterEnabled.value && selectedIPId.value && smartReferences.value.length === 0) {
      try {
        await loadSmartReferences()
        selectedRefs = smartReferences.value.map(r => r.path)
      } catch (err) {
        if (import.meta.env.DEV) {
          console.warn('Failed to load smart references, using manual selection:', err)
        }
      }
    } else if (smartReferences.value.length > 0) {
      // Use already-loaded references
      selectedRefs = smartReferences.value.map(r => r.path)
    }
    
    const { data } = await generateImage({
      prompt: imagePrompt.value,
      negative_prompt: imageNegativePrompt.value,
      ip_id: selectedIPId.value,
      channel_id: imageChannelId.value,
      width: imageWidth.value,
      height: imageHeight.value,
      num_inference_steps: imageSteps.value,
      guidance_scale: imageCfgScale.value,
      seed: imageSeed.value,
      use_lora: loraEnabled.value,
      lora_weight: loraWeight.value,
      use_ip_adapter: ipAdapterEnabled.value,
      ip_adapter_scale: ipAdapterEnabled.value ? ipAdapterScale.value : scale,
      reference_images: selectedRefs.length > 0 ? selectedRefs : undefined,
    })
    // Unified response format: { success: true, data: {...}, message: "..." }
    imageResult.value = data.data?.image_url || data.data?.url || data.data?.result
    ElMessage.success(t('generate.submit_success'))
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || 'Generation failed')
  } finally {
    imageLoading.value = false
  }
}

async function handleGenerateImageAsync() {
  if (!imagePrompt.value) { ElMessage.warning(t('generate.validation_error')); return }
  imageAsyncLoading.value = true
  imageResult.value = ''
  
  try {
    // Use smart references if already loaded
    let selectedRefs = []
    let scale = adaptiveScale.value
    
    // If smart references haven't been loaded yet, load them now
    if (autoSelectRefs.value && ipAdapterEnabled.value && selectedIPId.value && smartReferences.value.length === 0) {
      try {
        await loadSmartReferences()
        selectedRefs = smartReferences.value.map(r => r.path)
      } catch (err) {
        if (import.meta.env.DEV) {
          console.warn('Failed to load smart references, using manual selection:', err)
        }
      }
    } else if (smartReferences.value.length > 0) {
      // Use already-loaded references
      selectedRefs = smartReferences.value.map(r => r.path)
    }
    
    const { data } = await generateImageAsync({
      prompt: imagePrompt.value,
      negative_prompt: imageNegativePrompt.value,
      ip_asset_id: selectedIPId.value,
      channel_id: imageChannelId.value,
      width: imageWidth.value,
      height: imageHeight.value,
      steps: imageSteps.value,
      cfg_scale: imageCfgScale.value,
      seed: imageSeed.value,
      use_lora: loraEnabled.value,
      lora_weight: loraWeight.value,
      use_ip_adapter: ipAdapterEnabled.value,
      ip_adapter_scale: ipAdapterEnabled.value ? ipAdapterScale.value : scale,
      reference_images: selectedRefs.length > 0 ? selectedRefs : undefined,
    })
    ElMessage.success(t('common.async_submit_success'))
    // Redirect to task monitor page
    router.push('/tasks')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || 'Async generation failed')
  } finally {
    imageAsyncLoading.value = false
  }
}

async function handleGenerateVideo() {
  if (!videoPrompt.value) { ElMessage.warning(t('generate.validation_error')); return }
  videoLoading.value = true
  videoResult.value = ''
  try {
    const { data } = await generateVideo({
      prompt: videoPrompt.value,
      ip_id: selectedIPId.value,
      channel_id: videoChannelId.value,
      duration: videoDuration.value,
      fps: videoFps.value,
    })
    // Unified response format: { success: true, data: {...}, message: "..." }
    videoResult.value = data.data?.video_url || data.data?.url || data.data?.result
    ElMessage.success(t('generate.submit_success'))
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || 'Generation failed')
  } finally {
    videoLoading.value = false
  }
}

async function handleGenerateVideoAsync() {
  if (!videoPrompt.value) { ElMessage.warning(t('generate.validation_error')); return }
  videoAsyncLoading.value = true
  videoResult.value = ''
  try {
    const { data } = await generateVideoAsync({
      prompt: videoPrompt.value,
      ip_asset_id: selectedIPId.value,
      channel_id: videoChannelId.value,
      duration_seconds: videoDuration.value,
      fps: videoFps.value,
      width: 512,
      height: 512,
      steps: 30,
      cfg_scale: 7.0,
    })
    ElMessage.success(t('common.async_submit_success'))
    // Redirect to task monitor page
    router.push('/tasks')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || 'Async generation failed')
  } finally {
    videoAsyncLoading.value = false
  }
}

onMounted(() => {
  loadIPs()
  loadChannels()
})
</script>

<style scoped>
.generate-page { padding: 0; }
.page-title { font-size: 24px; font-weight: 700; color: #303133; margin: 0 0 20px; }
.ip-selector-card { margin-bottom: 16px; }
.ip-info-card { margin-bottom: 16px; background: linear-gradient(135deg, #f0f5ff 0%, #f5f0ff 100%); }
.result-card { margin-top: 16px; }
.story-content {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.6;
  color: #303133;
}
.no-model-hint { margin-top: 4px; }

/* Parameter hint style */
.param-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}
.param-hint .el-icon {
  flex-shrink: 0;
}
</style>
