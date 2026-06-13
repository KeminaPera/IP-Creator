<template>
  <div class="content-library">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>{{ $t('content.title') }}</h2>
          <p>{{ $t('content.description') }}</p>
        </div>
      </template>

      <!-- Stats Bar -->
      <el-row :gutter="16" class="mb-20">
        <el-col :span="6">
          <el-statistic :title="$t('content.total_contents')" :value="stats.total || 0" />
        </el-col>
        <el-col :span="6">
          <el-statistic :title="$t('content.story_count')" :value="stats.by_type?.story || 0" />
        </el-col>
        <el-col :span="6">
          <el-statistic :title="$t('content.image_count')" :value="stats.by_type?.image || 0" />
        </el-col>
        <el-col :span="6">
          <el-statistic :title="$t('content.video_count')" :value="stats.by_type?.video || 0" />
        </el-col>
      </el-row>

      <!-- Filter Bar -->
      <el-form :inline="true" class="filter-bar">
        <el-form-item :label="$t('content.content_type')">
          <el-select v-model="filters.content_type" @change="loadContents" class="select-md" clearable :placeholder="$t('content.all_types')">
            <el-option :label="$t('content.all_types')" value="" />
            <el-option :label="$t('content.story')" value="story" />
            <el-option :label="$t('content.image')" value="image" />
            <el-option :label="$t('content.video')" value="video" />
          </el-select>
        </el-form-item>
        
        <el-form-item :label="$t('content.status')">
          <el-select v-model="filters.status" @change="loadContents" class="select-md" clearable :placeholder="$t('content.all_status')">
            <el-option :label="$t('content.all_status')" value="" />
            <el-option :label="$t('content.completed')" value="completed" />
            <el-option :label="$t('content.failed')" value="failed" />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('content.ip_asset')">
          <el-select v-model="filters.ip_asset_id" @change="loadContents" style="width: 180px" clearable :placeholder="$t('content.all_ips')">
            <el-option :label="$t('content.all_ips')" value="" />
            <el-option v-for="ip in ipAssets" :key="ip.id" :label="ip.name" :value="ip.id" />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('content.date_range')">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            :start-placeholder="$t('common.start_date')"
            :end-placeholder="$t('common.end_date')"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            @change="onDateRangeChange"
            style="width: 240px"
          />
        </el-form-item>

        <el-form-item :label="$t('common.search')">
          <el-input v-model="filters.search" :placeholder="$t('content.search_placeholder')" clearable @keyup.enter="loadContents" style="width: 250px" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="loadContents">{{ $t('common.search') }}</el-button>
          <el-button @click="resetFilters">{{ $t('common.cancel') }}</el-button>
          <el-button @click="toggleAdvancedFilters">
            <el-icon><Filter /></el-icon>
            {{ showAdvanced ? $t('content.hide_filters') : $t('content.show_filters') }}
          </el-button>
        </el-form-item>
      </el-form>

      <!-- Advanced Filters -->
      <el-collapse-transition>
        <div v-if="showAdvanced" class="advanced-filters">
          <el-form :inline="true">
            <el-form-item :label="$t('content.favorite_only')">
              <el-switch v-model="filters.is_favorite" @change="loadContents" />
            </el-form-item>

            <el-form-item :label="$t('content.tags')">
              <el-select
                v-model="filters.tags"
                multiple
                filterable
                allow-create
                default-first-option
                :placeholder="$t('content.add_tags')"
                @change="loadContents"
                style="width: 300px"
              >
                <el-option v-for="tag in popularTags" :key="tag" :label="tag" :value="tag" />
              </el-select>
            </el-form-item>

            <el-form-item :label="$t('content.execution_time')">
              <el-input-number 
                v-model="filters.min_execution_time" 
                :placeholder="$t('common.min')"
                :min="0"
                @change="loadContents"
                style="width: 120px"
              />
              <span style="margin: 0 8px">-</span>
              <el-input-number 
                v-model="filters.max_execution_time" 
                :placeholder="$t('common.max')"
                :min="0"
                @change="loadContents"
                style="width: 120px"
              />
            </el-form-item>
          </el-form>
        </div>
      </el-collapse-transition>

      <!-- Bulk Actions Toolbar -->
      <div v-if="selectedItems.length > 0" class="bulk-actions">
        <el-alert 
          :title="`${selectedItems.length} {$t('content.total_contents')} {$t('common.selected')}`" 
          type="info" 
          :closable="false"
          style="flex: 1"
        />
        <el-button type="primary" size="small" @click="bulkFavorite">
          <el-icon><Star /></el-icon>
          {{ $t('content.favorite') }}
        </el-button>
        <el-button type="danger" size="small" @click="bulkDelete">
          <el-icon><Delete /></el-icon>
          {{ $t('common.delete') }}
        </el-button>
        <el-button size="small" @click="clearSelection">{{ $t('common.cancel') }}</el-button>
      </div>
      
      <!-- View Mode Toggle -->
      <div class="view-controls">
        <el-button-group>
          <el-button 
            :type="viewMode === 'card' ? 'primary' : ''" 
            @click="viewMode = 'card'"
          >
            <el-icon><Grid /></el-icon>
            {{ $t('content.card_view') }}
          </el-button>
          <el-button 
            :type="viewMode === 'list' ? 'primary' : ''" 
            @click="viewMode = 'list'"
          >
            <el-icon><List /></el-icon>
            {{ $t('content.list_view') }}
          </el-button>
        </el-button-group>
              
        <!-- Column Settings (only in list view) -->
        <el-popover v-if="viewMode === 'list'" trigger="click" placement="bottom-end" width="200">
          <template #reference>
            <el-button>
              <el-icon><Setting /></el-icon>
              {{ $t('content.columns') }}
            </el-button>
          </template>
                
          <div class="column-settings">
            <el-checkbox v-model="visibleColumns.content_type">{{ $t('content.column_content_type') }}</el-checkbox>
            <el-checkbox v-model="visibleColumns.title">{{ $t('content.column_title') }}</el-checkbox>
            <el-checkbox v-model="visibleColumns.ip_asset">{{ $t('content.column_ip_asset') }}</el-checkbox>
            <el-checkbox v-model="visibleColumns.status">{{ $t('content.column_status') }}</el-checkbox>
            <el-checkbox v-model="visibleColumns.execution_time">{{ $t('content.column_execution_time') }}</el-checkbox>
            <el-checkbox v-model="visibleColumns.created_at">{{ $t('content.column_created_at') }}</el-checkbox>
            <el-checkbox v-model="visibleColumns.is_favorite">{{ $t('content.column_is_favorite') }}</el-checkbox>
            <el-checkbox v-model="visibleColumns.actions">{{ $t('content.column_actions') }}</el-checkbox>
          </div>
        </el-popover>
      </div>

      <!-- Content Grid -->
      <div v-loading="loading" style="min-height: 400px;">
        <el-empty v-if="contents.length === 0 && !loading" :description="$t('content.no_contents')">
          <el-button type="primary" @click="$router.push('/workflow')">{{ $t('content.go_to_generate') }}</el-button>
        </el-empty>

        <!-- Card View -->
        <el-row v-if="viewMode === 'card' && contents.length > 0" :gutter="16">
          <el-col v-for="item in contents" :key="item.id" :span="6" style="margin-bottom: 16px">
            <el-card 
            :id="`content-${item.id}`" 
            shadow="hover" 
            class="content-card" 
            :class="{ 
              selected: selectedItems.includes(item.id),
              highlighted: highlightedContentId === item.id
            }">
            <!-- Selection Checkbox -->
            <div class="card-checkbox">
              <el-checkbox 
                v-model="item.selected" 
                @change="toggleSelection(item)"
                @click.stop
              />
            </div>

            <!-- Favorite Star Icon -->
            <div class="favorite-star" @click.stop="toggleFavorite(item)">
              <el-icon :size="24">
                <StarFilled v-if="item.is_favorite" color="#E6A23C" />
                <Star v-else color="#C0C4CC" />
              </el-icon>
            </div>

            <!-- Content Icon/Preview -->
            <div class="content-icon">
              <el-icon v-if="item.content_type === 'story'" :size="60" color="#409EFF"><Document /></el-icon>
              <el-image
                v-else-if="item.content_type === 'image' && (item.thumbnail_path || item.file_path)"
                :src="getFileUrl(item.thumbnail_path || item.file_path)"
                :preview-src-list="[getFileUrl(item.file_path || item.thumbnail_path)]"
                preview-teleported
                fit="cover"
                class="card-thumbnail"
                @click.stop
              >
                <template #error>
                  <div class="card-thumbnail-fallback">
                    <el-icon :size="60" color="#67C23A"><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
              <el-icon v-else-if="item.content_type === 'image'" :size="60" color="#67C23A"><Picture /></el-icon>
              <el-icon v-else :size="60" color="#E6A23C"><VideoCamera /></el-icon>
            </div>

            <!-- Content Info -->
            <div class="content-info">
              <h4 class="content-title">{{ item.title || item.content_type }}</h4>
              <p class="content-meta">{{ formatTime(item.created_at) }}</p>
              
              <el-tag :type="getTypeTag(item.content_type)" size="small">
                {{ getTypeLabel(item.content_type) }}
              </el-tag>

              <el-tag v-if="item.is_favorite" type="danger" size="small" style="margin-left: 4px">
                ★
              </el-tag>
            </div>

            <!-- Actions -->
            <div class="content-actions">
              <el-button size="small" type="primary" @click="viewDetails(item)">{{ $t('content.view_details') }}</el-button>
              <el-button 
                v-if="item.file_path" 
                size="small" 
                type="success" 
                @click="downloadContent(item)"
              >
                <el-icon><Download /></el-icon>
                {{ $t('content.download') }}
              </el-button>
              <el-button size="small" type="danger" @click="deleteContent(item)">{{ $t('common.delete') }}</el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- List View -->
      <el-table 
        v-if="viewMode === 'list' && contents.length > 0"
        :data="contents" 
        stripe
        @selection-change="handleSelectionChange"
        row-key="id"
      >
        <!-- Selection Column -->
        <el-table-column type="selection" width="55" />
        
        <!-- Content Type -->
        <el-table-column 
          v-if="visibleColumns.content_type"
          prop="content_type" 
          :label="$t('content.content_type')" 
          width="120"
        >
          <template #default="{ row }">
            <div class="type-cell">
              <el-icon v-if="row.content_type === 'story'" :size="20" color="#409EFF">
                <Document />
              </el-icon>
              <el-icon v-else-if="row.content_type === 'image'" :size="20" color="#67C23A">
                <Picture />
              </el-icon>
              <el-icon v-else :size="20" color="#E6A23C">
                <VideoCamera />
              </el-icon>
              <el-tag :type="getTypeTag(row.content_type)" size="small">
                {{ getTypeLabel(row.content_type) }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        
        <!-- Title -->
        <el-table-column 
          v-if="visibleColumns.title"
          prop="title" 
          :label="$t('content.title')" 
          min-width="200"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <div class="title-cell">
              <el-image 
                v-if="row.content_type === 'image' && (row.thumbnail_path || row.file_path)"
                :src="getFileUrl(row.thumbnail_path || row.file_path)"
                :preview-src-list="[getFileUrl(row.file_path || row.thumbnail_path)]"
                preview-teleported
                fit="cover"
                class="table-thumbnail"
                @click.stop
              />
              <el-image
                v-else-if="row.content_type === 'video' && row.thumbnail_path"
                :src="getFileUrl(row.thumbnail_path)"
                fit="cover"
                class="table-thumbnail"
              />
              <span class="title-text">{{ row.title || row.content_type }}</span>
            </div>
          </template>
        </el-table-column>
        
        <!-- IP Asset -->
        <el-table-column 
          v-if="visibleColumns.ip_asset"
          prop="ip_asset_id" 
          :label="$t('content.ip_asset')" 
          width="150"
        >
          <template #default="{ row }">
            <el-tag size="small" type="info">
              {{ getIPName(row.ip_asset_id) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <!-- Status -->
        <el-table-column 
          v-if="visibleColumns.status"
          prop="status" 
          :label="$t('content.status')" 
          width="100"
        >
          <template #default="{ row }">
            <el-tag 
              :type="row.status === 'completed' ? 'success' : 'danger'" 
              size="small"
            >
              {{ row.status === 'completed' ? $t('content.completed') : $t('content.failed') }}
            </el-tag>
          </template>
        </el-table-column>
        
        <!-- Execution Time -->
        <el-table-column 
          v-if="visibleColumns.execution_time"
          prop="execution_time_seconds" 
          :label="$t('content.execution_time')" 
          width="120"
        >
          <template #default="{ row }">
            <span v-if="row.execution_time_seconds">
              {{ formatExecutionTime(row.execution_time_seconds) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        
        <!-- Created At -->
        <el-table-column 
          v-if="visibleColumns.created_at"
          prop="created_at" 
          :label="$t('common.created_at')" 
          width="180"
        >
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        
        <!-- Favorite -->
        <el-table-column 
          v-if="visibleColumns.is_favorite"
          prop="is_favorite" 
          :label="$t('content.favorite')" 
          width="80"
          align="center"
        >
          <template #default="{ row }">
            <el-icon 
              :size="20"
              @click="toggleFavorite(row)"
              class="favorite-star-icon"
            >
              <StarFilled v-if="row.is_favorite" color="#E6A23C" />
              <Star v-else color="#C0C4CC" />
            </el-icon>
          </template>
        </el-table-column>
        
        <!-- Actions -->
        <el-table-column 
          v-if="visibleColumns.actions"
          :label="$t('common.actions')" 
          min-width="200"
          fixed="right"
          align="center"
        >
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="viewDetails(row)">
              <el-icon><View /></el-icon> {{ $t('common.view_detail') }}
            </el-button>
            <el-button 
              v-if="row.file_path" 
              size="small" 
              type="success" 
              @click="downloadContent(row)"
            >
              <el-icon><Download /></el-icon>
              {{ $t('content.download') }}
            </el-button>
            <el-button size="small" type="danger" @click="deleteContent(row)">
              <el-icon><Delete /></el-icon> {{ $t('common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <el-pagination
        v-if="total > 0"
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, page-size, prev, pager, next"
        @current-change="loadContents"
        @size-change="loadContents"
        style="margin-top: 20px; justify-content: center"
      />
      </div>
    </el-card>

    <!-- Details Dialog with Preview -->
    <el-dialog v-model="detailsDialogVisible" :title="$t('content.view_details')" width="900px" top="5vh">
      <div v-if="selectedContent" class="content-details">
        <!-- Content Preview Section -->
        <div class="preview-section">
          <!-- Video Preview -->
          <div v-if="selectedContent.content_type === 'video'" class="video-preview">
            <video 
              v-if="selectedContent.file_path" 
              :src="getFileUrl(selectedContent.file_path)" 
              controls 
              style="width: 100%; max-height: 500px; border-radius: 8px;"
            >
              {{ $t('content.play_video') }}
            </video>
            <el-empty v-else :description="$t('content.no_contents')" />
          </div>

          <!-- Image Preview -->
          <div v-else-if="selectedContent.content_type === 'image'" class="image-preview">
            <el-image 
              v-if="selectedContent.file_path"
              :key="selectedContent.file_path"
              :src="getFileUrl(selectedContent.file_path)"
              :preview-src-list="[getFileUrl(selectedContent.file_path)]"
              fit="contain"
              style="width: 100%; max-height: 500px; border-radius: 8px;"
            >
              <template #error>
                <el-empty :description="$t('content.no_contents')" />
              </template>
            </el-image>
            <el-empty v-else :description="$t('content.no_contents')" />
          </div>

          <!-- Story Preview -->
          <div v-else-if="selectedContent.content_type === 'story'" class="story-preview">
            <el-card shadow="never" class="story-card">
              <template #header>
                <div class="story-header">
                  <h3>{{ selectedContent.title }}</h3>
                  <el-tag v-if="selectedContent.word_count" type="info" size="small">
                    {{ selectedContent.word_count }} {{ $t('content.word_count') }}
                  </el-tag>
                </div>
              </template>
              <div class="story-content">
                <pre v-if="storyContent">{{ storyContent }}</pre>
                <el-empty v-else :description="$t('content.no_contents')" />
              </div>
            </el-card>
          </div>
        </div>

        <!-- Metadata Section -->
        <el-divider>{{ $t('content.edit_metadata') }}</el-divider>
        <el-descriptions :column="2" border>
          <el-descriptions-item :label="$t('content.content_type')">
            {{ getTypeLabel(selectedContent.content_type) }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('content.status')">{{ getStatusLabel(selectedContent.status) }}</el-descriptions-item>
          <el-descriptions-item :label="$t('content.content_title')" :span="2">
            {{ selectedContent.title || '-' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('content.content_description')" :span="2">
            {{ selectedContent.description || '-' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('content.file_size')">
            {{ selectedContent.file_size ? formatFileSize(selectedContent.file_size) : '-' }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('content.execution_time')">
            {{ selectedContent.execution_time_seconds ? selectedContent.execution_time_seconds.toFixed(2) + ' ' + $t('content.seconds') : '-' }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedContent.word_count" :label="$t('content.word_count')">
            {{ selectedContent.word_count }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedContent.duration_seconds" :label="$t('content.duration')">
            {{ selectedContent.duration_seconds }} {{ $t('content.seconds') }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedContent.resolution" :label="$t('content.resolution')" :span="2">
            {{ selectedContent.resolution }}
          </el-descriptions-item>
          <el-descriptions-item :label="$t('common.created_at')" :span="2">
            {{ formatTime(selectedContent.created_at) }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Picture, VideoCamera, Download, Star, StarFilled, Delete, Filter, Grid, List, Setting, View } from '@element-plus/icons-vue'
import { getIPList } from '@/api/ip'
import request from '@/api/request'
import { formatTime } from '../utils/time'
import { logger } from '../utils/logger'

const { t } = useI18n()
const route = useRoute()

const contents = ref([])
const stats = ref({})
const total = ref(0)
const loading = ref(false)
const selectedContent = ref(null)
const detailsDialogVisible = ref(false)
const storyContent = ref('')
const selectedItems = ref([])
const ipAssets = ref([])
const dateRange = ref(null)
const showAdvanced = ref(false)
const popularTags = ref(['character', 'scene', 'action', 'dialogue', 'landscape', 'portrait'])
const highlightedContentId = ref(null)

const filters = ref({
  content_type: '',
  task_id: '',  // Add task_id filter
  status: 'completed',
  search: '',
  ip_asset_id: '',
  start_date: null,
  end_date: null,
  is_favorite: false,
  tags: [],
  min_execution_time: null,
  max_execution_time: null,
})

const pagination = ref({
  page: 1,
  pageSize: (() => {
    try {
      return parseInt(localStorage.getItem('contentLibrary_pageSize')) || 20
    } catch {
      return 20
    }
  })(),
})

// View mode state
const viewMode = ref((() => {
  try {
    return localStorage.getItem('contentLibrary_viewMode') || 'card'
  } catch {
    return 'card'
  }
})())
const sortConfig = ref({
  field: 'created_at',
  order: 'descending'
})
const visibleColumns = ref({
  content_type: true,
  title: true,
  ip_asset: true,
  status: true,
  execution_time: true,
  created_at: true,
  is_favorite: true,
  actions: true
})

// Watch for viewMode changes and save to localStorage
watch(
  () => viewMode.value,
  (newMode) => {
    try {
      localStorage.setItem('contentLibrary_viewMode', newMode)
    } catch {
      // Ignore storage errors
    }
  }
)

// Watch for pageSize changes and save to localStorage
watch(
  () => pagination.value.pageSize,
  (newSize) => {
    try {
      localStorage.setItem('contentLibrary_pageSize', newSize.toString())
    } catch {
      // Ignore storage errors
    }
  }
)

// Use relative URL - will be proxied by Vite/Nginx in production
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

async function loadContents() {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize,
      content_type: filters.value.content_type || undefined,
      task_id: filters.value.task_id || undefined,
      status: filters.value.status || undefined,
      search: filters.value.search || undefined,
      ip_asset_id: filters.value.ip_asset_id || undefined,
      start_date: filters.value.start_date || undefined,
      end_date: filters.value.end_date || undefined,
      is_favorite: filters.value.is_favorite || undefined,
      tags: filters.value.tags.length > 0 ? filters.value.tags.join(',') : undefined,
    }
    
    const { data } = await request.get('/contents', { params })
    contents.value = data.data || []
    total.value = data.pagination?.total || 0
  } catch (err) {
    if (import.meta.env.DEV) {
      console.error('[ContentLibrary] Error loading contents:', err)
    }
    ElMessage.error(t('common.error'))
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const { data } = await request.get('/contents/stats')
    // Unified response format: { success: true, data: {...} }
    stats.value = data.data || {}
  } catch (err) {
    logger.error('[ContentLibrary] Failed to load stats:', err)
  }
}

function resetFilters() {
  filters.value = {
    content_type: '',
    status: 'completed',
    search: '',
    ip_asset_id: '',
    start_date: null,
    end_date: null,
    is_favorite: false,
    tags: [],
    min_execution_time: null,
    max_execution_time: null,
  }
  dateRange.value = null
  pagination.value.page = 1
  loadContents()
}

function onDateRangeChange(dates) {
  if (dates && dates.length === 2) {
    filters.value.start_date = dates[0]
    filters.value.end_date = dates[1]
  } else {
    filters.value.start_date = null
    filters.value.end_date = null
  }
  loadContents()
}

function toggleAdvancedFilters() {
  showAdvanced.value = !showAdvanced.value
}

async function loadIPAssets() {
  try {
    const { data } = await getIPList({ skip: 0, limit: 1000 })
    // Unified response format
    ipAssets.value = data.data || []
  } catch (err) {
    logger.error('Failed to load IP assets:', err)
    ipAssets.value = []
  }
}

// Get IP name by ID
function getIPName(ipId) {
  const ip = ipAssets.value.find(i => i.id === ipId)
  return ip ? ip.name : '-'
}

// Format execution time
function formatExecutionTime(seconds) {
  if (!seconds) return '-'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${mins}m ${secs}s`
}

// Handle selection change from table
function handleSelectionChange(selection) {
  selectedItems.value = selection.map(item => item.id)
}

function getTypeTag(type) {
  const map = { story: 'primary', image: 'success', video: 'warning' }
  return map[type] || 'info'
}

function getTypeLabel(type) {
  const map = { story: t('content.story'), image: t('content.image'), video: t('content.video') }
  return map[type] || type
}

function getStatusLabel(status) {
  const map = { 
    completed: t('content.completed'), 
    failed: t('content.failed'),
    running: t('content.running'),
    pending: t('content.pending')
  }
  return map[status] || status
}

async function viewDetails(item) {
  selectedContent.value = item
  storyContent.value = '' // Reset story content
  detailsDialogVisible.value = true
  
  // Load story content if it's a story
  if (item.content_type === 'story' && item.file_path) {
    await loadStoryContent(item.file_path)
  }
}

async function loadStoryContent(filePath) {
  try {
    const response = await request.get(`/contents/files/${filePath}`, {
      responseType: 'text'
    })
    storyContent.value = response.data
  } catch (err) {
    logger.error('Failed to load story content:', err)
    storyContent.value = 'Unable to load story content. File may not be accessible.'
  }
}

function getFileUrl(filePath) {
  if (!filePath) return ''
  // Normalize path separators (Windows backslash to forward slash) for URL
  const normalizedPath = filePath.replace(/\\/g, '/')
  // Use the files endpoint from content router
  return `${BASE_URL}/contents/files/${normalizedPath}`
}

function formatFileSize(bytes) {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  
  return `${size.toFixed(2)} ${units[unitIndex]}`
}

async function downloadContent(item) {
  if (!item.file_path) {
    ElMessage.warning('No file available for download')
    return
  }
  
  try {
    const response = await request.get(`/contents/files/${item.file_path}`, {
      responseType: 'blob'
    })
    
    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    
    // Extract filename from path or use content title
    const filename = item.file_path.split('/').pop() || `${item.content_type}_${item.id}`
    link.setAttribute('download', filename)
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('Download started')
  } catch (err) {
    logger.error('Download failed:', err)
    ElMessage.error('Download failed')
  }
}

async function toggleFavorite(item) {
  try {
    await request.post(`/contents/${item.id}/favorite`)
    item.is_favorite = !item.is_favorite
    ElMessage.success(t('common.success'))
    loadStats()
  } catch (err) {
    ElMessage.error(t('common.error'))
  }
}

async function deleteContent(item) {
  try {
    await ElMessageBox.confirm(t('content.delete_confirm'), t('common.confirm'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    })
    
    await request.delete(`/contents/${item.id}`)
    ElMessage.success(t('content.delete_success'))
    loadContents()
    loadStats()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(t('content.delete_failed'))
    }
  }
}

onMounted(async () => {
  const highlightId = route.query.highlight
  const resetFilters = route.query.reset_filters
  const taskIdFilter = route.query.task_id
  
  // Reset filters if requested
  if (resetFilters === 'true') {
    filters.value = {
      content_type: '',
      task_id: taskIdFilter || '',
      status: 'completed',
      search: '',
      ip_asset_id: null,
      start_date: '',
      end_date: '',
      is_favorite: null,
      tags: [],
    }
    pagination.value.page = 1
  } else if (taskIdFilter) {
    filters.value.task_id = taskIdFilter
  }
  
  // Load data first
  await Promise.all([
    loadContents(),
    loadStats(),
    loadIPAssets()
  ])
  
  // After data is loaded, check if we need to highlight a specific content
  if (highlightId) {
    highlightedContentId.value = parseInt(highlightId)
    
    // Check if the highlighted content is in the current page
    const isInCurrentPage = contents.value.some(item => item.id === parseInt(highlightId))
    
    if (!isInCurrentPage) {
      // Need to find the right page - load all content to find the item
      // For now, just go to page 1 and show a message
      pagination.value.page = 1
      await loadContents()
    }
    
    // Scroll to the highlighted content
    nextTick(() => {
      const element = document.getElementById(`content-${highlightId}`)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' })
        // Add a temporary highlight effect
        element.classList.add('highlighted')
        setTimeout(() => {
          element.classList.remove('highlighted')
        }, 3000)
      }
    })
  }
})

// Bulk Operations
function toggleSelection(item) {
  const index = selectedItems.value.indexOf(item.id)
  if (index > -1) {
    selectedItems.value.splice(index, 1)
  } else {
    selectedItems.value.push(item.id)
  }
}

function clearSelection() {
  selectedItems.value = []
  contents.value.forEach(item => {
    item.selected = false
  })
}

async function bulkFavorite() {
  if (selectedItems.value.length === 0) {
    ElMessage.warning('No items selected')
    return
  }
  
  try {
    const promises = selectedItems.value.map(id =>
      request.post(`/contents/${id}/favorite`)
    )
    
    await Promise.all(promises)
    ElMessage.success(`Successfully favorited ${selectedItems.value.length} items`)
    clearSelection()
    loadContents()
    loadStats()
  } catch (err) {
    ElMessage.error('Bulk favorite failed')
  }
}

async function bulkDelete() {
  if (selectedItems.value.length === 0) {
    ElMessage.warning('No items selected')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `Are you sure you want to delete ${selectedItems.value.length} items?`,
      'Confirm Bulk Delete',
      {
        confirmButtonText: 'Confirm',
        cancelButtonText: 'Cancel',
        type: 'warning',
      }
    )
    
    const promises = selectedItems.value.map(id =>
      request.delete(`/contents/${id}`)
    )
    
    await Promise.all(promises)
    ElMessage.success(`Successfully deleted ${selectedItems.value.length} items`)
    clearSelection()
    loadContents()
    loadStats()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('Bulk delete failed')
    }
  }
}
</script>

<style scoped>
.content-library {
  padding: 20px;
}

.card-header h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
}

.card-header p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.filter-bar {
  margin-bottom: 20px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
}

.bulk-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: #ecf5ff;
  border: 1px solid #b3d8ff;
  border-radius: 4px;
}

.advanced-filters {
  margin-bottom: 20px;
  padding: 16px;
  background: #f0f9ff;
  border: 1px solid #d0e8ff;
  border-radius: 4px;
}

.content-card {
  height: 100%;
  transition: transform 0.2s;
  position: relative;
}

.content-card:hover {
  transform: translateY(-4px);
}

.content-card.selected {
  border: 2px solid #409EFF;
  box-shadow: 0 2px 12px 0 rgba(64, 158, 255, 0.3);
}

.content-card.highlighted {
  border: 2px solid #67C23A;
  box-shadow: 0 2px 12px 0 rgba(103, 194, 58, 0.5);
  animation: highlightPulse 3s ease-in-out;
}

@keyframes highlightPulse {
  0%, 100% {
    box-shadow: 0 2px 12px 0 rgba(103, 194, 58, 0.5);
  }
  50% {
    box-shadow: 0 4px 20px 0 rgba(103, 194, 58, 0.8);
  }
}

.card-checkbox {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 10;
}

.content-icon {
  text-align: center;
  padding: 20px 0;
  background: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 16px;
}

.card-thumbnail {
  width: 100%;
  height: 140px;
  border-radius: 4px;
  cursor: pointer;
  display: block;
}

.card-thumbnail-fallback {
  width: 100%;
  height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}

.content-info {
  margin-bottom: 16px;
}

.content-title {
  margin: 0 0 8px 0;
  font-size: 16px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.content-meta {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: #999;
}

.content-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* Content Details Dialog */
.content-details {
  max-height: 75vh;
  overflow-y: auto;
}

.preview-section {
  margin-bottom: 20px;
}

.video-preview,
.image-preview {
  text-align: center;
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
}

.story-preview {
  margin: 0;
}

.story-card {
  border: none;
  box-shadow: none;
}

.story-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.story-header h3 {
  margin: 0;
  font-size: 20px;
}

.story-content {
  max-height: 500px;
  overflow-y: auto;
  padding: 16px;
  background: #fafafa;
  border-radius: 4px;
}

.story-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
  color: #333;
}

/* Favorite Star Icon */
.favorite-star {
  position: absolute;
  top: 12px;
  right: 12px;
  cursor: pointer;
  transition: transform 0.2s ease;
  z-index: 10;
}

.favorite-star:hover {
  transform: scale(1.3);
}

.favorite-star-icon {
  cursor: pointer;
  transition: all 0.2s ease;
}

.favorite-star-icon:hover {
  transform: scale(1.3);
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}

/* View controls */
.view-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 4px;
}

/* Column settings popover */
.column-settings {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px;
  max-height: 300px;
  overflow-y: auto;
}

/* Table cell styles */
.type-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.table-thumbnail {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  flex-shrink: 0;
  cursor: pointer;
}

.title-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 操作列按钮容器 - 统一样式 */
:deep(.el-table__row td:last-child .cell) {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: nowrap;
  padding: 0 8px;
}

:deep(.el-table__row td:last-child .cell .el-button) {
  margin: 0;
  white-space: nowrap;
}
</style>
