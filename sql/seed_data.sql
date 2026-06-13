-- =============================================
-- IP-Creator Initial Data
-- Description: Seed data for LLM providers and models
-- Version: 1.0
-- Created: 2026-05-05
-- =============================================

-- =============================================
-- 1. Default LLM Providers
-- =============================================
INSERT OR IGNORE INTO llm_providers (code, name_cn, name_en, icon_class, website, api_docs_url, default_endpoint, requires_api_key, is_active, is_recommended, sort_order, description_cn, description_en) VALUES
('openai', 'OpenAI', 'OpenAI', 'fa-brands fa-openai', 'https://openai.com', 'https://platform.openai.com/docs', 'https://api.openai.com/v1', 1, 1, 1, 1, '领先的人工智能研究公司，提供GPT系列模型', 'Leading AI research company providing GPT series models'),
('zhipu', '智谱AI', 'Zhipu AI', 'fa-solid fa-brain', 'https://www.zhipuai.cn', 'https://open.bigmodel.cn/dev/api', 'https://open.bigmodel.cn/api/paas/v4', 1, 1, 1, 2, '中国领先的人工智能公司，提供GLM系列模型', 'Leading Chinese AI company providing GLM series models'),
('qwen', '通义千问', 'Qwen', 'fa-solid fa-robot', 'https://tongyi.aliyun.com', 'https://help.aliyun.com/zh/dashscope', 'https://dashscope.aliyuncs.com/compatible-mode/v1', 1, 1, 1, 3, '阿里巴巴旗下的大语言模型', 'Alibaba''s large language model'),
('ollama', 'Ollama', 'Ollama', 'fa-solid fa-server', 'https://ollama.com', 'https://github.com/ollama/ollama', 'http://localhost:11434', 0, 1, 0, 4, '本地运行的大型语言模型框架', 'Framework for running large language models locally'),
('deepseek', '深度求索', 'DeepSeek', 'fa-solid fa-microchip', 'https://www.deepseek.com', 'https://platform.deepseek.com/api-docs', 'https://api.deepseek.com', 1, 1, 1, 5, '中国人工智能公司，提供高性能推理模型', 'Chinese AI company providing high-performance reasoning models');


-- =============================================
-- 2. Default LLM Models
-- =============================================

-- OpenAI Models
INSERT OR IGNORE INTO llm_models (provider_id, code, name, version, capabilities, max_tokens, max_output_tokens, supports_streaming, supports_function_calling, supports_vision, input_price_per_million, output_price_per_million, speed_rating, quality_rating, is_active, is_recommended, sort_order, description) VALUES
((SELECT id FROM llm_providers WHERE code='openai'), 'gpt-4o', 'GPT-4o', '2024-05-13', '["text_generation", "vision", "chat"]', 128000, 4096, 1, 1, 1, 5.0, 15.0, 5, 5, 1, 1, 1, '最新的旗舰模型，支持多模态输入'),
((SELECT id FROM llm_providers WHERE code='openai'), 'gpt-4o-mini', 'GPT-4o Mini', '2024-07-18', '["text_generation", "vision", "chat"]', 128000, 4096, 1, 1, 1, 0.15, 0.6, 5, 4, 1, 1, 2, '轻量级高性价比模型'),
((SELECT id FROM llm_providers WHERE code='openai'), 'gpt-3.5-turbo', 'GPT-3.5 Turbo', '0125', '["text_generation", "chat"]', 16385, 4096, 1, 1, 0, 0.5, 1.5, 5, 3, 1, 0, 3, '快速且经济的对话模型');

-- Zhipu AI Models
INSERT OR IGNORE INTO llm_models (provider_id, code, name, version, capabilities, max_tokens, max_output_tokens, supports_streaming, supports_function_calling, supports_vision, input_price_per_million, output_price_per_million, speed_rating, quality_rating, is_active, is_recommended, sort_order, description) VALUES
((SELECT id FROM llm_providers WHERE code='zhipu'), 'glm-4.7', 'GLM-4.7', 'latest', '["text_generation", "chat", "function_calling"]', 200000, 128000, 1, 1, 0, 2.0, 8.0, 4, 5, 1, 1, 1, '智谱高智能模型，面向Agentic Coding场景强化编码能力'),
((SELECT id FROM llm_providers WHERE code='zhipu'), 'glm-4', 'GLM-4', 'latest', '["text_generation", "vision", "chat"]', 128000, 4096, 1, 1, 1, 50.0, 50.0, 4, 5, 1, 1, 2, '智谱旗舰模型，支持多模态'),
((SELECT id FROM llm_providers WHERE code='zhipu'), 'glm-4-plus', 'GLM-4 Plus', 'latest', '["text_generation", "chat"]', 128000, 4096, 1, 1, 0, 50.0, 50.0, 4, 4, 1, 1, 3, '增强版对话模型'),
((SELECT id FROM llm_providers WHERE code='zhipu'), 'glm-4-flash', 'GLM-4 Flash', 'latest', '["text_generation", "chat"]', 128000, 4096, 1, 0, 0, 0.0, 0.0, 5, 3, 1, 1, 4, '免费高速模型');

-- Qwen Models
INSERT OR IGNORE INTO llm_models (provider_id, code, name, version, capabilities, max_tokens, max_output_tokens, supports_streaming, supports_function_calling, supports_vision, input_price_per_million, output_price_per_million, speed_rating, quality_rating, is_active, is_recommended, sort_order, description) VALUES
((SELECT id FROM llm_providers WHERE code='qwen'), 'qwen-max', 'Qwen-Max', 'latest', '["text_generation", "chat"]', 32000, 8000, 1, 1, 0, 40.0, 40.0, 4, 5, 1, 1, 1, '通义千问最强模型'),
((SELECT id FROM llm_providers WHERE code='qwen'), 'qwen-plus', 'Qwen-Plus', 'latest', '["text_generation", "chat"]', 32000, 8000, 1, 1, 0, 20.0, 20.0, 4, 4, 1, 1, 2, '均衡性能模型'),
((SELECT id FROM llm_providers WHERE code='qwen'), 'qwen-turbo', 'Qwen-Turbo', 'latest', '["text_generation", "chat"]', 32000, 8000, 1, 0, 0, 2.0, 2.0, 5, 3, 1, 1, 3, '快速经济模型');

-- DeepSeek Models
INSERT OR IGNORE INTO llm_models (provider_id, code, name, version, capabilities, max_tokens, max_output_tokens, supports_streaming, supports_function_calling, supports_vision, input_price_per_million, output_price_per_million, speed_rating, quality_rating, is_active, is_recommended, sort_order, description) VALUES
((SELECT id FROM llm_providers WHERE code='deepseek'), 'deepseek-chat', 'DeepSeek Chat', 'latest', '["text_generation", "chat"]', 128000, 4096, 1, 1, 0, 2.0, 8.0, 4, 4, 1, 1, 1, '高性价比对话模型'),
((SELECT id FROM llm_providers WHERE code='deepseek'), 'deepseek-reasoner', 'DeepSeek Reasoner', 'latest', '["text_generation", "chat"]', 128000, 4096, 1, 1, 0, 4.0, 16.0, 3, 5, 1, 1, 2, '深度推理模型');


-- =============================================
-- 3. Default Admin User (password: admin123)
-- =============================================
-- Note: Run init_admin.py script to create admin user with hashed password
-- This is just a placeholder comment


-- =============================================
-- Data Summary
-- =============================================
-- Providers: 5 (OpenAI, Zhipu AI, Qwen, Ollama, DeepSeek)
-- Models: 12 (across all providers)
-- Admin User: Created via init_admin.py script
-- =============================================
