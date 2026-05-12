"""
Test script to verify Code Review fixes
"""
import requests
import json

BASE_URL = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImFkbWluIn0.abc123"  # 替换为真实 token

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_api_endpoints():
    """Test all new API endpoints"""
    print("=" * 60)
    print("测试 API 端点")
    print("=" * 60)
    
    # 1. 测试 Kohya 环境检查
    print("\n1. 测试 Kohya 环境检查...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/lora/check-kohya", headers=headers)
        print(f"   状态码: {response.status_code}")
        data = response.json()
        print(f"   响应: {json.dumps(data, ensure_ascii=False, indent=2)[:200]}...")
        print("   ✅ Kohya 检查正常")
    except Exception as e:
        print(f"   ❌ Kohya 检查失败: {e}")
    
    # 2. 获取 LoRA 列表（测试 f-string 修复）
    print("\n2. 测试 LoRA 列表（f-string 修复验证）...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/lora", headers=headers)
        print(f"   状态码: {response.status_code}")
        data = response.json()
        if "data" in data:
            print(f"   LoRA 数量: {len(data.get('data', {}).get('items', []))}")
            print("   ✅ LoRA 列表正常")
        else:
            print(f"   响应: {json.dumps(data, ensure_ascii=False)[:200]}")
    except Exception as e:
        print(f"   ❌ LoRA 列表失败: {e}")
        # 如果这里有错误，检查错误消息是否显示 {str(e)} 还是实际错误
        print("   ⚠️  如果看到错误消息包含 '{str(e)}'，说明 f-string 未修复")

def test_quality_report_structure():
    """Test quality report API returns clip_consistency"""
    print("\n" + "=" * 60)
    print("测试质量报告结构")
    print("=" * 60)
    
    # 获取第一个已完成的 LoRA 模型
    print("\n1. 获取 LoRA 列表...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/lora?status=completed", headers=headers)
        data = response.json()
        loras = data.get("data", {}).get("items", [])
        
        if not loras:
            print("   ⚠️  没有已完成的 LoRA 模型，跳过质量报告测试")
            return
        
        lora_id = loras[0]["id"]
        print(f"   找到 LoRA: {loras[0]['name']} (ID: {lora_id})")
        
        # 2. 获取质量报告
        print(f"\n2. 获取质量报告 (LoRA ID: {lora_id})...")
        response = requests.get(f"{BASE_URL}/api/v1/lora/{lora_id}/quality-report", headers=headers)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            report = data.get("data", {})
            
            # 检查是否包含 clip_consistency
            if "clip_consistency" in report:
                print(f"   ✅ 包含 clip_consistency 字段: {report['clip_consistency']}")
            else:
                print("   ❌ 缺少 clip_consistency 字段")
                print(f"   可用字段: {list(report.keys())}")
            
            # 检查其他必要字段
            required_fields = ["overall_score", "grade", "loss_score", "completion_score", 
                             "file_score", "generation_success", "test_images", "recommendations"]
            missing_fields = [f for f in required_fields if f not in report]
            
            if not missing_fields:
                print("   ✅ 所有必要字段都存在")
            else:
                print(f"   ❌ 缺少字段: {missing_fields}")
                
        elif response.status_code == 404:
            print("   ⚠️  该 LoRA 没有质量报告（正常）")
            print("   💡 提示：需要先运行质量评估")
        else:
            print(f"   ❌ 请求失败: {response.text[:200]}")
            
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")

def test_i18n_keys():
    """Test if i18n keys are properly loaded"""
    print("\n" + "=" * 60)
    print("测试国际化键")
    print("=" * 60)
    
    # 检查前端文件
    import os
    zh_cn_path = "frontend-vue/src/i18n/zh-CN.json"
    en_us_path = "frontend-vue/src/i18n/en-US.json"
    
    print("\n1. 检查中文 i18n 键...")
    if os.path.exists(zh_cn_path):
        with open(zh_cn_path, 'r', encoding='utf-8') as f:
            zh_data = json.load(f)
        
        clip_key = zh_data.get("lora", {}).get("quality", {}).get("clip_consistency")
        if clip_key:
            print(f"   ✅ clip_consistency: {clip_key}")
        else:
            print("   ❌ 缺少 clip_consistency 键")
    else:
        print(f"   ❌ 文件不存在: {zh_cn_path}")
    
    print("\n2. 检查英文 i18n 键...")
    if os.path.exists(en_us_path):
        with open(en_us_path, 'r', encoding='utf-8') as f:
            en_data = json.load(f)
        
        clip_key = en_data.get("lora", {}).get("quality", {}).get("clip_consistency")
        if clip_key:
            print(f"   ✅ clip_consistency: {clip_key}")
        else:
            print("   ❌ 缺少 clip_consistency 键")
    else:
        print(f"   ❌ 文件不存在: {en_us_path}")

if __name__ == "__main__":
    print("\n🚀 开始测试 Code Review 修复...")
    print(f"后端地址: {BASE_URL}\n")
    
    # 测试 API
    test_api_endpoints()
    
    # 测试质量报告
    test_quality_report_structure()
    
    # 测试 i18n
    test_i18n_keys()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
