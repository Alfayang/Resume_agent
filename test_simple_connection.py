#!/usr/bin/env python3
import requests
import sys

def test_backend_connection():
    """测试后端连接"""
    
    print("🔍 测试后端连接...")
    
    # 测试健康检查
    try:
        print("1. 测试健康检查端点...")
        response = requests.get("http://localhost:8002/health", timeout=5)
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("✅ 健康检查成功")
        else:
            print("❌ 健康检查失败")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接错误 - 后端可能没有运行")
        return False
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False
    
    # 测试状态端点
    try:
        print("\n2. 测试状态端点...")
        trace_id = "20502bc3-9f75-44fd-81e5-76c9a577f072"
        response = requests.get(f"http://localhost:8002/state/{trace_id}", timeout=10)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 状态端点成功")
            print(f"   todo数量: {len(data.get('todo', []))}")
            print(f"   steps数量: {len(data.get('steps', []))}")
            return True
        else:
            print(f"❌ 状态端点失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 状态端点错误: {e}")
        return False

if __name__ == "__main__":
    success = test_backend_connection()
    if success:
        print("\n✅ 后端连接正常")
    else:
        print("\n❌ 后端连接异常")
    sys.exit(0 if success else 1) 