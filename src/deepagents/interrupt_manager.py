import threading
import time
import signal
import os
from typing import Dict, Set, Optional
from dataclasses import dataclass, field

@dataclass
class TaskInfo:
    """任务信息"""
    trace_id: str
    start_time: float
    status: str = "running"  # running, interrupted, completed
    user_input: str = ""
    current_step: str = ""
    thread_id: Optional[int] = None
    process_id: Optional[int] = None

class InterruptManager:
    """全局中断管理器"""
    
    def __init__(self):
        self.interrupted_tasks: Set[str] = set()
        self.active_tasks: Dict[str, TaskInfo] = {}
        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()
        
        # 注册信号处理器
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except (OSError, ValueError):
            # Windows可能不支持某些信号
            pass
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"🛑 收到中断信号 {signum}，正在清理所有任务...")
        self.interrupt_all_tasks()
        self._shutdown_event.set()
    
    def register_task(self, trace_id: str, user_input: str = "", thread_id: Optional[int] = None):
        """注册一个活跃任务"""
        with self._lock:
            task_info = TaskInfo(
                trace_id=trace_id,
                start_time=time.time(),
                user_input=user_input[:100] + "..." if len(user_input) > 100 else user_input,
                thread_id=thread_id or threading.get_ident(),
                process_id=os.getpid()
            )
            self.active_tasks[trace_id] = task_info
            print(f"🚀 任务注册: {trace_id} (线程: {task_info.thread_id})")
    
    def update_task_status(self, trace_id: str, current_step: str = ""):
        """更新任务状态"""
        with self._lock:
            if trace_id in self.active_tasks:
                self.active_tasks[trace_id].current_step = current_step
    
    def interrupt_task(self, trace_id: str) -> bool:
        """中断指定任务"""
        with self._lock:
            if trace_id not in self.active_tasks:
                print(f"⚠️ 任务 {trace_id} 不存在或已完成")
                return False
            
            self.interrupted_tasks.add(trace_id)
            task_info = self.active_tasks[trace_id]
            task_info.status = "interrupted"
            
            print(f"🚫 任务中断请求: {trace_id}")
            print(f"   - 线程ID: {task_info.thread_id}")
            print(f"   - 进程ID: {task_info.process_id}")
            print(f"   - 运行时间: {time.time() - task_info.start_time:.2f}秒")
            print(f"   - 当前步骤: {task_info.current_step}")
            
            return True
    
    def interrupt_all_tasks(self):
        """中断所有任务"""
        with self._lock:
            for trace_id in list(self.active_tasks.keys()):
                self.interrupt_task(trace_id)
    
    def is_interrupted(self, trace_id: str) -> bool:
        """检查任务是否被中断"""
        return trace_id in self.interrupted_tasks
    
    def cleanup_task(self, trace_id: str):
        """清理任务"""
        with self._lock:
            self.interrupted_tasks.discard(trace_id)
            if trace_id in self.active_tasks:
                task_info = self.active_tasks.pop(trace_id)
                duration = time.time() - task_info.start_time
                print(f"🧹 任务清理: {trace_id} (运行时间: {duration:.2f}秒)")
    
    def get_task_status(self, trace_id: str) -> Optional[Dict]:
        """获取任务状态"""
        with self._lock:
            if trace_id in self.active_tasks:
                task_info = self.active_tasks[trace_id]
                return {
                    "trace_id": trace_id,
                    "status": task_info.status,
                    "start_time": task_info.start_time,
                    "duration": time.time() - task_info.start_time,
                    "current_step": task_info.current_step,
                    "user_input": task_info.user_input,
                    "thread_id": task_info.thread_id,
                    "process_id": task_info.process_id,
                    "interrupted": self.is_interrupted(trace_id)
                }
            return None
    
    def get_all_status(self) -> Dict:
        """获取所有任务状态"""
        with self._lock:
            return {
                "interrupted_tasks": list(self.interrupted_tasks),
                "active_tasks": {
                    tid: {
                        "status": info.status,
                        "start_time": info.start_time,
                        "duration": time.time() - info.start_time,
                        "current_step": info.current_step,
                        "user_input": info.user_input,
                        "thread_id": info.thread_id,
                        "process_id": info.process_id
                    }
                    for tid, info in self.active_tasks.items()
                },
                "active_count": len(self.active_tasks),
                "interrupted_count": len(self.interrupted_tasks)
            }
    
    def wait_for_shutdown(self, timeout: Optional[float] = None):
        """等待关闭信号"""
        return self._shutdown_event.wait(timeout)

# 全局中断管理器实例
interrupt_manager = InterruptManager()

def get_interrupt_manager() -> InterruptManager:
    """获取全局中断管理器实例"""
    return interrupt_manager 