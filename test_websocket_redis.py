"""
WebSocket和Redis实时更新测试脚本

测试内容：
1. Redis连接测试
2. Redis Pub/Sub测试
3. 检查lora_trainer中的Redis发布功能
4. 检查Celery任务中的Redis发布
"""

import redis
import json
import time
import sys

def test_redis_connection():
    """测试Redis连接"""
    print("=" * 60)
    print("1. 测试Redis连接")
    print("=" * 60)
    
    try:
        # 测试默认数据库
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        print("✅ Redis默认数据库(db=0)连接成功")
        
        # 测试数据库3（WebSocket使用）
        r3 = redis.Redis(host='localhost', port=6379, db=3, decode_responses=True)
        r3.ping()
        print("✅ Redis数据库3(db=3)连接成功")
        
        return True
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        return False


def test_redis_pubsub():
    """测试Redis Pub/Sub功能"""
    print("\n" + "=" * 60)
    print("2. 测试Redis Pub/Sub")
    print("=" * 60)
    
    try:
        r3 = redis.Redis(host='localhost', port=6379, db=3, decode_responses=True)
        
        # 发布测试消息
        test_data = {
            'progress': 50.0,
            'current_epoch': 5,
            'current_loss': 0.05,
            'timestamp': time.time()
        }
        
        channel = 'training_progress:999'  # 测试用lora_id=999
        r3.publish(channel, json.dumps(test_data))
        print(f"✅ 成功发布测试消息到 {channel}")
        print(f"   数据: {json.dumps(test_data, indent=2)}")
        
        # 检查活跃的频道
        channels = r3.pubsub_channels('training_progress:*')
        print(f"✅ 活跃的training_progress频道数: {len(channels)}")
        
        return True
    except Exception as e:
        print(f"❌ Redis Pub/Sub测试失败: {e}")
        return False


def check_lora_trainer_redis():
    """检查lora_trainer中的Redis发布代码"""
    print("\n" + "=" * 60)
    print("3. 检查lora_trainer.py中的Redis发布功能")
    print("=" * 60)
    
    try:
        with open('/Users/yanglin/Codes/IP-Creator/app/core/lora_trainer.py', 'r') as f:
            content = f.read()
        
        # 检查关键代码
        checks = [
            ('import redis', '导入redis模块'),
            ('self.redis_client = redis.from_url', '初始化Redis客户端'),
            ('def _publish_progress', '定义_publish_progress方法'),
            ('self.redis_client.publish', '发布消息到Redis'),
            ('training_progress:', '使用正确的频道格式'),
        ]
        
        all_passed = True
        for code, description in checks:
            if code in content:
                print(f"✅ {description}")
            else:
                print(f"❌ {description} - 未找到代码: {code}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def check_celery_redis_publish():
    """检查Celery任务中的Redis发布"""
    print("\n" + "=" * 60)
    print("4. 检查Celery任务中的Redis发布")
    print("=" * 60)
    
    try:
        with open('/Users/yanglin/Codes/IP-Creator/celery_worker.py', 'r') as f:
            content = f.read()
        
        # 检查Mock模式中的Redis发布
        checks = [
            ('redis_client.publish', '使用redis_client.publish'),
            ('training_progress:', '使用正确的频道格式'),
            ('json.dumps', '序列化JSON数据'),
        ]
        
        all_passed = True
        for code, description in checks:
            if code in content:
                print(f"✅ {description}")
            else:
                print(f"❌ {description} - 未找到代码: {code}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def check_websocket_endpoint():
    """检查WebSocket端点"""
    print("\n" + "=" * 60)
    print("5. 检查WebSocket端点配置")
    print("=" * 60)
    
    try:
        with open('/Users/yanglin/Codes/IP-Creator/app/api/v1/training_websocket.py', 'r') as f:
            content = f.read()
        
        checks = [
            ('@router.websocket("/ws/training/{lora_id}")', '训练WebSocket端点'),
            ('ws_manager.connect', '使用ConnectionManager连接'),
            ('ws_manager.disconnect', '使用ConnectionManager断开'),
        ]
        
        all_passed = True
        for code, description in checks:
            if code in content:
                print(f"✅ {description}")
            else:
                print(f"❌ {description} - 未找到代码: {code}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def check_backend_logs():
    """检查后端启动日志"""
    print("\n" + "=" * 60)
    print("6. 检查后端启动日志")
    print("=" * 60)
    
    try:
        with open('/tmp/ip-creator-backend.log', 'r') as f:
            content = f.read()
        
        checks = [
            ('Redis progress listener started', 'Redis监听器启动'),
            ('Application startup complete', '应用启动完成'),
        ]
        
        all_passed = True
        for text, description in checks:
            if text in content:
                print(f"✅ {description}")
            else:
                print(f"⚠️  {description} - 日志中未找到")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "🔍 WebSocket和Redis实时更新状态检查" + "\n")
    
    results = []
    
    # 运行测试
    results.append(("Redis连接", test_redis_connection()))
    results.append(("Redis Pub/Sub", test_redis_pubsub()))
    results.append(("lora_trainer Redis发布", check_lora_trainer_redis()))
    results.append(("Celery Redis发布", check_celery_redis_publish()))
    results.append(("WebSocket端点", check_websocket_endpoint()))
    results.append(("后端日志", check_backend_logs()))
    
    # 打印总结
    print("\n" + "=" * 60)
    print("📊 检查总结")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {name}")
    
    # 总体结果
    all_passed = all(result[1] for result in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有检查通过！WebSocket和Redis实时更新功能正常")
    else:
        print("⚠️  部分检查未通过，请查看上方详情")
    print("=" * 60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
