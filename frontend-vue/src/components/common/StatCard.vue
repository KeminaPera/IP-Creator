<template>
  <el-card shadow="hover" :class="['stat-card', `stat-${type}`]">
    <div class="stat-content">
      <div class="stat-info">
        <p class="stat-label">{{ label }}</p>
        <p class="stat-value">{{ value }}</p>
        <p v-if="subLabel" class="stat-sub">{{ subLabel }}: {{ subValue }}</p>
      </div>
      <el-icon :size="48" class="stat-icon">
        <slot name="icon" />
      </el-icon>
    </div>
  </el-card>
</template>

<script setup>
/**
 * 统计卡片组件
 * 
 * 用于展示系统统计数据，支持不同颜色和图标
 * 
 * @example
 * <StatCard
 *   label="IP 资产"
 *   :value="stats.ip_count"
 *   type="green"
 *   sub-label="活跃"
 *   :sub-value="stats.active_count"
 * >
 *   <template #icon><PictureFilled /></template>
 * </StatCard>
 */

const props = defineProps({
  // 卡片标签
  label: {
    type: String,
    required: true
  },
  
  // 卡片数值
  value: {
    type: [String, Number],
    required: true
  },
  
  // 卡片类型（颜色主题）
  type: {
    type: String,
    default: 'blue',
    validator: (value) => ['blue', 'green', 'orange', 'purple', 'red', 'cyan'].includes(value)
  },
  
  // 子标签（可选）
  subLabel: {
    type: String,
    default: ''
  },
  
  // 子数值（可选）
  subValue: {
    type: [String, Number],
    default: ''
  }
})
</script>

<style scoped>
.stat-card {
  border-radius: 8px;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-4px);
}

.stat-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
}

.stat-info {
  flex: 1;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin: 0 0 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 4px;
  line-height: 1.2;
}

.stat-sub {
  font-size: 12px;
  color: #909399;
  margin: 0;
}

.stat-icon {
  opacity: 0.8;
}

/* 颜色主题 */
.stat-blue .stat-value {
  color: #409eff;
}

.stat-blue .stat-icon {
  color: #409eff;
}

.stat-green .stat-value {
  color: #67c23a;
}

.stat-green .stat-icon {
  color: #67c23a;
}

.stat-orange .stat-value {
  color: #e6a23c;
}

.stat-orange .stat-icon {
  color: #e6a23c;
}

.stat-purple .stat-value {
  color: #9c27b0;
}

.stat-purple .stat-icon {
  color: #9c27b0;
}

.stat-red .stat-value {
  color: #f56c6c;
}

.stat-red .stat-icon {
  color: #f56c6c;
}

.stat-cyan .stat-value {
  color: #00bcd4;
}

.stat-cyan .stat-icon {
  color: #00bcd4;
}
</style>
