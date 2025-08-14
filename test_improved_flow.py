#!/usr/bin/env python3
"""
测试改进后的流式状态更新功能
"""

import requests
import json
import time

# 测试配置
BASE_URL = "http://localhost:8002"
API_URL = "http://localhost:5173/api"  # 前端代理地址

def test_backend_generate():
    """测试后端 /generate 端点是否立即返回 trace_id"""
    print("🧪 测试后端 /generate 端点...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/generate",
            json={"user_input": "请帮我润色一下简历"},
            headers={"Content-Type": "application/json"},
            timeout=5  # 5秒超时，确保不会等待AI处理完成
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 后端立即返回响应: {data}")
            
            if "trace_id" in data:
                print(f"✅ 成功获取 trace_id: {data['trace_id']}")
                return data["trace_id"]
            else:
                print("❌ 响应中没有 trace_id")
                return None
        else:
            print(f"❌ 后端请求失败: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return None

def test_stream_state(trace_id):
    """测试流式状态端点"""
    print(f"🧪 测试流式状态端点: {trace_id}")
    
    try:
        response = requests.get(
            f"{BASE_URL}/stream/state/{trace_id}",
            stream=True,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ 流式端点连接成功")
            
            # 读取前几条消息
            count = 0
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # 去掉 'data: ' 前缀
                        try:
                            data = json.loads(data_str)
                            print(f"📡 接收到状态更新: {data}")
                            count += 1
                            
                            # 检查是否完成
                            if data.get('status') in ['completed', 'interrupted', 'timeout']:
                                print(f"✅ 任务状态: {data['status']}")
                                break
                                
                        except json.JSONDecodeError:
                            print(f"⚠️ 无法解析JSON: {data_str}")
                    
                    if count >= 5:  # 只读取前5条消息
                        break
        else:
            print(f"❌ 流式端点请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 流式测试失败: {e}")

def test_frontend_proxy():
    """测试前端代理配置"""
    print("🧪 测试前端代理配置...")
    
    try:
        # 测试健康检查端点
        response = requests.get(f"{API_URL}/health", timeout=5)
        
        if response.status_code == 200:
            print("✅ 前端代理工作正常")
            data = response.json()
            print(f"📊 健康状态: {data}")
        else:
            print(f"❌ 前端代理失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 前端代理测试失败: {e}")

def main():
    print("🚀 开始测试改进后的流式状态更新功能")
    print("=" * 50)
    
    # 1. 测试前端代理
    test_frontend_proxy()
    print()
    
    # 2. 测试后端立即返回
    trace_id = test_backend_generate()
    print()
    
    # 3. 测试流式状态更新
    if trace_id:
        test_stream_state(trace_id)
    else:
        print("❌ 无法获取 trace_id，跳过流式测试")
    
    print()
    print("=" * 50)
    print("🏁 测试完成")

if __name__ == "__main__":
    main() 