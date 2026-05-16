# LoRA训练模式配置功能

## 功能概述

允许用户通过系统设置页面动态切换LoRA训练模式（Mock/Real），无需修改`.env`文件或重启服务。

## 实现细节

### 1. 数据库设置

在 `system_settings` 表中添加了新配置项：

```sql
INSERT INTO system_settings (
    category, setting_key, setting_value, value_type,
    display_name_cn, display_name_en,
    description_cn, description_en,
    validation_rule, default_value,
    is_system, is_active
)
VALUES (
    'system_feature', 'lora_training_mode', 'mock', 'string',
    'LoRA训练模式', 'LoRA Training Mode',
    '训练模式：mock（模拟训练，用于流程验证）或real（真实Kohya训练）',
    'Training mode: mock (simulated for workflow validation) or real (real Kohya training)',
    '{"options": ["mock", "real"]}', 'mock',
    0, 1
)
```

### 2. 后端实现

#### 2.1 Settings类增强 (`app/config/settings.py`)

添加了 `get_lora_training_mode()` 方法：

```python
def get_lora_training_mode(self) -> str:
    """
    Get LoRA training mode from database settings, fallback to .env config.
    
    This allows dynamic configuration via the Settings Management UI.
    
    Returns:
        Training mode: "mock" or "real"
    """
    try:
        # Import here to avoid circular dependency
        from app.services.settings_service import settings_service
        from app.config.database import async_session_factory
        import asyncio
        
        # Try to get from database
        async def fetch_mode():
            async with async_session_factory() as db:
                settings_dict = await settings_service.get_settings_by_category(db, "system_feature")
                return settings_dict.get("lora_training_mode", self.LORA_TRAINING_MODE)
        
        # Run async function
        mode = asyncio.run(fetch_mode())
        return mode
    except Exception as e:
        # Fallback to .env config if database read fails
        return self.LORA_TRAINING_MODE
```

**关键特性：**
- 优先从数据库读取配置
- 如果数据库读取失败，自动回退到`.env`配置
- 避免循环导入（在方法内部import）

#### 2.2 Celery任务更新 (`celery_worker.py`)

修改了 `train_lora_task` 函数：

```python
@celery_app.task(bind=True, max_retries=0)
def train_lora_task(self, lora_id: int, training_params: dict) -> dict:
    """LoRA training task - supports both mock and real training modes."""
    from app.config.settings import settings
    
    # Check training mode from database settings (with .env fallback)
    training_mode = settings.get_lora_training_mode()
    
    if training_mode == "mock":
        return _mock_training(self, lora_id, training_params)
    else:
        return _real_training(self, lora_id, training_params)
```

### 3. 前端实现

#### 3.1 SettingsGroup组件增强 (`frontend-vue/src/components/settings/SettingsGroup.vue`)

**新增功能：**
- 支持带 `options` 验证规则的 `string` 类型设置显示为下拉选择器
- 自动从API获取完整的设置详情（包括 `validation_rule`）
- 友好的选项标签显示

**关键代码：**

```vue
<!-- String 类型：如果有options则使用下拉选择器，否则使用输入框 -->
<el-select 
  v-else-if="setting.value_type === 'string' && setting.validation_rule?.options"
  v-model="localSettings[setting.setting_key]"
  style="width: 100%; max-width: 500px;"
>
  <el-option
    v-for="option in setting.validation_rule.options"
    :key="option"
    :label="getOptionLabel(setting, option)"
    :value="option"
  />
</el-select>
```

**辅助函数：**

```javascript
const getOptionLabel = (setting, option) => {
  const labels = {
    lora_training_mode: {
      mock: 'Mock（模拟训练）',
      real: 'Real（真实训练）'
    }
  }
  
  // 尝试从设置键名获取翻译
  const keyLabels = labels[setting.setting_key]
  if (keyLabels && keyLabels[option]) {
    return keyLabels[option]
  }
  
  // 否则使用选项值加上显示名称
  return `${option} (${setting.display_name_en || setting.setting_key})`
}
```

#### 3.2 设置加载逻辑优化

```javascript
const loadSettings = async () => {
  loading.value = true
  try {
    const { data } = await getSettingsByCategory(props.category)
    const settingsData = data.data || {}
    
    // 获取完整的设置详情（包括 validation_rule）
    const settingsArray = []
    for (const key of Object.keys(settingsData)) {
      try {
        const detailResponse = await import('../../api/settings').then(mod => 
          mod.getSettingDetail(props.category, key)
        )
        const detail = detailResponse.data.data || detailResponse.data
        settingsArray.push(detail)
      } catch (error) {
        // 如果获取详情失败，使用基本格式
        console.warn(`Failed to load detail for ${key}, using basic format:`, error)
        settingsArray.push({
          setting_key: key,
          setting_value: settingsData[key],
          value_type: getTypeFromValue(settingsData[key]),
          display_name_cn: getDisplayName(key),
          description_cn: getDescription(key),
          validation_rule: getValidationRule(key),
          default_value: settingsData[key],
          is_system: isSystemSetting(key)
        })
      }
    }
    settingsList.value = settingsArray
    
    // Initialize local settings
    localSettings.value = {}
    for (const setting of settingsArray) {
      localSettings.value[setting.setting_key] = setting.setting_value
    }
  } catch (error) {
    ElMessage.error(t('common.load_failed'))
    console.error('Failed to load settings:', error)
  } finally {
    loading.value = false
  }
}
```

### 4. 数据库迁移

迁移脚本：`sql/migrations/006_add_lora_training_mode_setting.py`

执行方式：
```bash
PYTHONPATH=/Users/yanglin/Codes/IP-Creator \
/Users/yanglin/Codes/IP-Creator/venv/bin/python \
sql/migrations/006_add_lora_training_mode_setting.py
```

## 使用方法

### 通过系统设置页面

1. 登录系统
2. 进入"系统设置"页面
3. 切换到"系统功能"标签页
4. 找到"LoRA训练模式"设置项
5. 从下拉菜单选择：
   - **Mock（模拟训练）**：快速验证流程，无需GPU
   - **Real（真实训练）**：使用Kohya-ss进行真实训练，需要GPU
6. 点击"保存设置"

### 通过.env文件（备用）

如果数据库不可用，可以在`.env`文件中设置：

```env
LORA_TRAINING_MODE=mock  # 或 real
```

## 技术优势

1. **动态配置**：无需重启服务即可切换训练模式
2. **用户友好**：通过UI直观切换，无需修改配置文件
3. **容错设计**：数据库不可用时自动回退到.env配置
4. **类型安全**：通过validation_rule限制可选值
5. **可扩展**：相同的模式可用于其他枚举类型配置

## 注意事项

1. **Celery Worker**：切换模式后，正在执行的任务不受影响，新任务会使用新模式
2. **权限控制**：需要登录才能修改设置
3. **系统级配置**：修改后对所有用户生效
4. **默认值**：系统初始化为`mock`模式，保证开箱即用

## 相关文件

- `sql/init_system_settings.py` - 系统设置初始化
- `sql/migrations/006_add_lora_training_mode_setting.py` - 数据库迁移
- `app/config/settings.py` - Settings类增强
- `celery_worker.py` - Celery任务更新
- `frontend-vue/src/components/settings/SettingsGroup.vue` - 前端组件增强
- `frontend-vue/src/api/settings.js` - 设置API

## 测试验证

1. 访问系统设置页面 → 系统功能标签
2. 确认"LoRA训练模式"显示为下拉选择器
3. 切换到"Real（真实训练）"并保存
4. 开始一个新的LoRA训练任务
5. 检查Celery Worker日志，确认使用了真实训练模式
6. 切换回"Mock（模拟训练）"并保存
7. 开始新的训练任务，确认使用模拟模式
