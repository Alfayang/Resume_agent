// App.jsx

// 移除 pollExecutionStatus 和相关的 setInterval 逻辑
// ...

// 新增一个函数来处理流式更新
const streamExecutionStatus = (traceId) => {
  if (!traceId) return;

  // 注意：URL需要正确构建，指向你的流式端点
  const eventSourceUrl = getApiUrl(`/stream/state/${traceId}`);
  const eventSource = new EventSource(eventSourceUrl);

  // 监听 'message' 事件，这是默认事件类型
  eventSource.onmessage = (event) => {
    const stateData = JSON.parse(event.data);

    // 检查特殊状态信号
    if (stateData.status === 'completed' || stateData.status === 'interrupted' || stateData.status === 'timeout') {
      console.log(`流式更新结束，状态: ${stateData.status}`);
      setTaskState(prev => ({ ...prev, isExecuting: false, currentStep: stateData.status }));
      eventSource.close(); // 关闭连接
      return;
    }
    
    if (stateData.error) {
      console.error('流式更新错误:', stateData.error);
      setTaskState(prev => ({ ...prev, isExecuting: false, currentStep: 'error' }));
      eventSource.close(); // 关闭连接
      return;
    }

    // 更新UI状态
    console.log('接收到状态流更新:', stateData);
    setTaskState(prev => ({
      ...prev,
      isExecuting: !stateData.validation?.ok, // 持续更新执行状态
      todoList: stateData.todo || prev.todoList,
      executionSteps: stateData.steps || prev.executionSteps,
      planRationale: stateData.plan_rationale || prev.planRationale,
    }));
  };

  // 监听错误事件
  eventSource.onerror = (err) => {
    console.error('EventSource 失败:', err);
    setTaskState(prev => ({ ...prev, isExecuting: false, currentStep: 'error' }));
    eventSource.close();
  };

  // 将 eventSource 实例存到 window 对象，以便在组件卸载或中断时可以关闭它
  window.currentEventSource = eventSource;
};

// 在 sendMessage 函数中，用 streamExecutionStatus 替换 pollExecutionStatus
const sendMessage = async () => {
  // ...
  if (data.trace_id) {
    // pollExecutionStatus(data.trace_id); // 旧方法
    streamExecutionStatus(data.trace_id); // ✨ 新方法
  }
  // ...
};

// 在 interruptTask 函数中，确保关闭 EventSource 连接
const interruptTask = async () => {
    // ...
    if (window.currentEventSource) {
        window.currentEventSource.close();
        window.currentEventSource = null;
    }
    // ...
}