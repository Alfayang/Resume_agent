#!/usr/bin/env python3
"""
测试后端状态
"""

import requests
import json

def test_backend_health():
    """测试后端健康状态"""
    try:
        response = requests.get("http://localhost:8002/health", timeout=5)
        print(f"健康检查状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"健康状态: {data}")
            return True
        else:
            print(f"健康检查失败: {response.text}")
            return False
    except Exception as e:
        print(f"健康检查异常: {e}")
        return False

def test_generate_endpoint():
    """测试generate端点"""
    try:
        response = requests.post(
            "http://localhost:8002/generate",
            json={"user_input": "测试消息"},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        print(f"Generate端点状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"成功响应: {data}")
            return True
        else:
            print(f"Generate端点失败: {response.text}")
            return False
    except Exception as e:
        print(f"Generate端点异常: {e}")
        return False

def main():
    print("🧪 测试后端状态")
    print("=" * 30)
    
    # 1. 测试健康状态
    print("1. 测试健康状态...")
    health_ok = test_backend_health()
    print()
    
    # 2. 测试generate端点
    print("2. 测试generate端点...")
    generate_ok = test_generate_endpoint()
    print()
    
    # 总结
    print("=" * 30)
    if health_ok and generate_ok:
        print("✅ 后端状态正常")
    else:
        print("❌ 后端存在问题")
        if not health_ok:
            print("  - 健康检查失败")
        if not generate_ok:
            print("  - Generate端点失败")

if __name__ == "__main__":
    main() 