"""
模型完整性校验测试脚本

用于验证健康检查修复是否正确工作。
运行前请确保已安装依赖：pip install -r requirements.txt
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))


def test_model_integrity():
    """测试模型完整性校验功能"""
    from app.services.model_downloader import model_downloader
    
    print("=" * 60)
    print("模型完整性校验测试")
    print("=" * 60)
    
    # 测试1: Stable Diffusion
    print("\n[测试1] Stable Diffusion 1.5 完整性检查")
    sd_integrity = model_downloader.validate_model_integrity("stable_diffusion")
    print(f"  状态: {sd_integrity['status']}")
    print(f"  有效: {sd_integrity['valid']}")
    print(f"  路径: {sd_integrity['path']}")
    print(f"  已存在文件: {len(sd_integrity['existing_files'])}")
    print(f"  缺失文件: {len(sd_integrity['missing_files'])}")
    
    if sd_integrity['missing_files']:
        print("  缺失文件列表:")
        for f in sd_integrity['missing_files'][:5]:  # 只显示前5个
            print(f"    - {f}")
    
    # 测试2: IP-Adapter
    print("\n[测试2] IP-Adapter 完整性检查")
    ip_integrity = model_downloader.validate_model_integrity("ip_adapter")
    print(f"  状态: {ip_integrity['status']}")
    print(f"  有效: {ip_integrity['valid']}")
    print(f"  路径: {ip_integrity['path']}")
    print(f"  已存在文件: {len(ip_integrity['existing_files'])}")
    print(f"  缺失文件: {len(ip_integrity['missing_files'])}")
    
    # 测试3: is_model_installed
    print("\n[测试3] is_model_installed() 方法")
    sd_installed = model_downloader.is_model_installed("stable_diffusion")
    ip_installed = model_downloader.is_model_installed("ip_adapter")
    print(f"  Stable Diffusion: {'✅ 已安装' if sd_installed else '❌ 未完整安装'}")
    print(f"  IP-Adapter: {'✅ 已安装' if ip_installed else '❌ 未完整安装'}")
    
    print("\n" + "=" * 60)


def test_health_checker():
    """测试健康检查功能"""
    from app.api.v1.system_health import HealthChecker
    
    print("\n" + "=" * 60)
    print("系统健康检查测试")
    print("=" * 60)
    
    # 测试扩散模型检查
    print("\n[测试] 扩散模型健康检查")
    result = HealthChecker.check_diffusion_models()
    
    print(f"  状态: {result['status']}")
    print(f"  消息: {result['message']}")
    print(f"  模型路径: {result['models_path']}")
    
    if result.get('required_models'):
        print("\n  模型详情:")
        for model_id, model_info in result['required_models'].items():
            status_icon = {
                'installed': '✅',
                'downloading': '⏳',
                'incomplete': '⚠️',
                'missing': '❌'
            }.get(model_info['status'], '❓')
            
            print(f"    {status_icon} {model_info['name']}: {model_info['status']}")
    
    if result.get('downloading_tasks'):
        print(f"\n  下载中任务: {len(result['downloading_tasks'])}")
        for task in result['downloading_tasks']:
            print(f"    - {task['model_id']}: {task['progress']}%")
    
    print("\n" + "=" * 60)


def test_scenarios():
    """测试不同场景"""
    print("\n" + "=" * 60)
    print("场景测试说明")
    print("=" * 60)
    
    print("""
请按以下步骤手动测试：

场景1: 模型完全缺失
  1. 删除 ~/.cache/huggingface/hub/models--runwayml--stable-diffusion-v1-5
  2. 运行此脚本
  预期: status = "missing"

场景2: 模型下载中断（模拟不完整）
  1. 创建目录但不放置完整文件:
     mkdir -p ~/.cache/huggingface/hub/models--runwayml--stable-diffusion-v1-5/snapshots/test
  2. 运行此脚本
  预期: status = "incomplete", missing_files 包含关键文件

场景3: 模型完整安装
  1. 正常下载模型
  2. 运行此脚本
  预期: status = "installed", valid = True

场景4: 健康检查API
  1. 启动后端: python -m app.main
  2. 访问: http://localhost:8000/api/v1/system/health
  预期: 返回完整的健康状态，不报错
""")


if __name__ == "__main__":
    try:
        print("开始测试...\n")
        
        # 运行测试
        test_model_integrity()
        test_health_checker()
        test_scenarios()
        
        print("\n✅ 测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
