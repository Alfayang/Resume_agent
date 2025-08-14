#!/usr/bin/env python3
"""
测试实时状态更新功能
"""

import time
import json
import os
from src.deepagents.run_state import create_run_state, append_step, set_todo_status, load_state

def test_realtime_state():
    """测试实时状态更新"""
    print("🧪 开始测试实时状态更新功能...")
    
    # 1. 创建新的运行状态
    session_id = "test-session-" + str(int(time.time()))
    user_input = "测试实时状态更新"
    
    print(f"📝 创建运行状态: session_id={session_id}")
    state = create_run_state(session_id, user_input)
    trace_id = state["trace_id"]
    
    print(f"✅ 运行状态已创建: trace_id={trace_id}")
    print(f"📁 状态文件位置: run_store/{trace_id}.json")
    
    # 2. 模拟任务执行过程
    print("\n🔄 模拟任务执行过程...")
    
    # 添加规划步骤
    print("  📋 添加规划步骤...")
    append_step(trace_id, "planner", "started", {"action": "开始任务规划"})
    time.sleep(1)
    
    # 更新todo状态
    print("  📝 更新todo状态...")
    set_todo_status(trace_id, "plan", "in_progress")
    time.sleep(1)
    
    # 完成规划
    print("  ✅ 完成规划...")
    append_step(trace_id, "planner", "ok", {"action": "任务规划完成"})
    set_todo_status(trace_id, "plan", "completed")
    time.sleep(1)
    
    # 开始执行
    print("  ⚡ 开始执行...")
    append_step(trace_id, "executor", "started", {"action": "开始执行任务"})
    set_todo_status(trace_id, "step-1", "in_progress")
    time.sleep(1)
    
    # 完成执行
    print("  ✅ 完成执行...")
    append_step(trace_id, "executor", "ok", {"action": "任务执行完成"})
    set_todo_status(trace_id, "step-1", "completed")
    time.sleep(1)
    
    # 3. 验证状态文件
    print("\n📊 验证状态文件内容...")
    final_state = load_state(trace_id)
    
    print(f"  📈 总步骤数: {len(final_state.get('steps', []))}")
    print(f"  📋 Todo项目数: {len(final_state.get('todo', []))}")
    print(f"  ⏰ 创建时间: {final_state.get('created_at')}")
    
    # 显示所有步骤
    print("\n📝 执行步骤详情:")
    for i, step in enumerate(final_state.get('steps', [])):
        print(f"  {i+1}. {step.get('name')} - {step.get('status')} ({step.get('ts')})")
    
    # 显示todo状态
    print("\n📋 Todo状态:")
    for todo in final_state.get('todo', []):
        print(f"  - {todo.get('step')}: {todo.get('status')}")
    
    print(f"\n✅ 测试完成！状态文件: run_store/{trace_id}.json")
    print("💡 前端现在应该能够实时看到这些状态更新")

if __name__ == "__main__":
    test_realtime_state() 