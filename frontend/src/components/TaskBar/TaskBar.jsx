import React from 'react';

const TaskBar = ({ taskState, onRefresh, onRetry, onInterrupt, onResend, onTest, onToggle }) => {
  const { isExecuting, currentStep, todoList, executionSteps, planRationale, traceId } = taskState;

  // 调试模式：总是显示TaskBar
  const isDebugMode = process.env.NODE_ENV === 'development' || window.forceDebugMode;
  
  // 修改显示逻辑：只要有任务数据就显示，不管是否完成
  const hasTaskData = todoList.length > 0 || executionSteps.length > 0 || isExecuting;
  
  // 如果正在执行或有任务数据，或者处于调试模式，就显示TaskBar
  if (!hasTaskData && !isDebugMode) {
    return null;
  }
  
  // 调试信息：显示为什么TaskBar显示或隐藏
  console.log('TaskBar显示条件:', {
    hasTaskData,
    isDebugMode,
    todoList: todoList.length,
    executionSteps: executionSteps.length,
    isExecuting,
    traceId
  });

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return '✅';
      case 'in_progress':
        return '🔄';
      case 'failed':
        return '❌';
      case 'pending':
        return '⏳';
      default:
        return '⏳';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'text-green-600';
      case 'in_progress':
        return 'text-blue-600';
      case 'failed':
        return 'text-red-600';
      case 'pending':
        return 'text-gray-500';
      default:
        return 'text-gray-500';
    }
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* 标题栏 */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-900">AI执行状态</h3>
        {onToggle && (
          <button
            onClick={onToggle}
            className="p-1 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
            title="隐藏AI执行状态"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        )}
      </div>
      
      {/* 内容区域 */}
      <div className="flex-1 overflow-y-auto p-4 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
                    {/* 调试模式下的简单显示 */}
            {isDebugMode && !isExecuting && todoList.length === 0 && executionSteps.length === 0 && (
              <div className="text-center py-4 text-gray-500">
                <div className="text-sm">TaskBar 已加载</div>
                <div className="text-xs mt-1">等待任务开始...</div>
                {onTest && (
                  <button
                    onClick={onTest}
                    className="mt-2 px-3 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
                  >
                    🧪 测试TaskBar
                  </button>
                )}
              </div>
            )}
            
            {/* 强制开启调试模式按钮 */}
            {!isDebugMode && (
              <div className="text-center py-2">
                <button
                  onClick={() => {
                    window.forceDebugMode = true;
                    window.location.reload();
                  }}
                  className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200"
                >
                  🔧 强制开启调试模式
                </button>
              </div>
            )}
            
            {/* 调试信息 - 显示当前状态 */}
            {isDebugMode && (
              <div className="text-xs bg-yellow-50 p-2 rounded border border-yellow-200 mb-4">
                <div className="font-medium text-yellow-800">调试信息:</div>
                <div className="text-yellow-700 space-y-1">
                  <div>isExecuting: {isExecuting.toString()}</div>
                  <div>todoList.length: {todoList.length}</div>
                  <div>executionSteps.length: {executionSteps.length}</div>
                  <div>hasTaskData: {hasTaskData.toString()}</div>
                  <div>currentStep: {currentStep || 'null'}</div>
                  <div>traceId: {traceId || 'null'}</div>
                  {todoList.length > 0 && (
                    <div>todoList[0]: {JSON.stringify(todoList[0])}</div>
                  )}
                  {executionSteps.length > 0 && (
                    <div>executionSteps[0]: {JSON.stringify(executionSteps[0])}</div>
                  )}
                </div>
                {/* 手动测试trace_id */}
                <div className="mt-2">
                  <input 
                    type="text" 
                    placeholder="输入trace_id测试" 
                    className="w-full px-2 py-1 text-xs border rounded"
                    id="test-trace-id"
                  />
                  <button
                    onClick={() => {
                      console.log('测试按钮被点击');
                      const testTraceId = document.getElementById('test-trace-id').value;
                      console.log('输入的trace_id:', testTraceId);
                      console.log('onRefresh函数:', onRefresh);
                      
                      if (testTraceId && onRefresh) {
                        console.log('手动测试trace_id:', testTraceId);
                        // 临时设置traceId并刷新
                        window.testTraceId = testTraceId;
                        onRefresh();
                      } else {
                        console.log('条件不满足:', { testTraceId: !!testTraceId, onRefresh: !!onRefresh });
                      }
                    }}
                    className="mt-1 px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
                  >
                    🧪 测试指定trace_id
                  </button>
                  <button
                    onClick={() => {
                      console.log('获取最新状态按钮被点击');
                      
                      // 直接获取最新的trace_id并更新状态
                      console.log('开始获取状态列表...');
                      fetch('/api/states')
                        .then(response => {
                          console.log('状态列表响应状态:', response.status);
                          console.log('状态列表响应URL:', response.url);
                          if (!response.ok) {
                            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                          }
                          return response.json();
                        })
                        .then(data => {
                          console.log('所有状态:', data);
                          console.log('状态列表长度:', data.items?.length);
                          console.log('最新状态对象:', data.items?.[data.items.length - 1]);
                          if (data.items && data.items.length > 0) {
                            // 获取最新的trace_id
                            const latestTraceId = data.items[data.items.length - 1].trace_id;
                            console.log('最新trace_id:', latestTraceId);
                            
                            // 直接获取该trace_id的状态
                            return fetch(`/api/state/${latestTraceId}`);
                          } else {
                            throw new Error('没有找到状态数据');
                          }
                        })
                        .then(response => response.json())
                        .then(stateData => {
                          console.log('获取到最新状态:', stateData);
                          console.log('设置window.testTraceId为:', stateData.trace_id);
                          
                          // 更新前端状态
                          if (typeof onRefresh === 'function') {
                            window.testTraceId = stateData.trace_id;
                            console.log('调用onRefresh函数');
                            onRefresh();
                          }
                          
                          alert(`成功获取最新状态！\ntrace_id: ${stateData.trace_id}\ntodo数量: ${stateData.todo?.length}\nsteps数量: ${stateData.steps?.length}`);
                        })
                        .catch(error => {
                          console.error('获取最新状态失败:', error);
                          alert(`获取最新状态失败: ${error.message}`);
                        });
                    }}
                    className="mt-1 px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                  >
                    📊 获取最新状态
                  </button>
                  <button
                    onClick={() => {
                      console.log('直接测试按钮被点击');
                      
                      // 先获取最新的trace_id
                      console.log('获取最新的trace_id...');
                      fetch('/api/states')
                        .then(response => response.json())
                        .then(data => {
                          console.log('所有状态:', data);
                          if (data.items && data.items.length > 0) {
                            // 获取最新的trace_id
                            const latestTraceId = data.items[data.items.length - 1].trace_id;
                            console.log('最新trace_id:', latestTraceId);
                            
                            // 使用最新的trace_id测试
                            testWithTraceId(latestTraceId);
                          } else {
                            // 如果没有状态，使用固定的trace_id
                            const testTraceId = '52f12f8e-4bf3-4762-84f2-0d9a0bd096f2';
                            console.log('使用固定trace_id:', testTraceId);
                            testWithTraceId(testTraceId);
                          }
                        })
                        .catch(error => {
                          console.error('获取状态列表失败:', error);
                          // 使用固定的trace_id
                          const testTraceId = '52f12f8e-4bf3-4762-84f2-0d9a0bd096f2';
                          console.log('使用固定trace_id:', testTraceId);
                          testWithTraceId(testTraceId);
                        });
                      
                      function testWithTraceId(testTraceId) {
                        console.log('使用trace_id测试:', testTraceId);
                        
                        // 直接测试后端连接
                        console.log('直接测试后端连接...');
                        
                        // 方法1: 使用代理路径 (避免CORS)
                        console.log('方法1: 使用代理路径...');
                        const xhr = new XMLHttpRequest();
                        xhr.open('GET', '/api/health', true);
                        xhr.setRequestHeader('Content-Type', 'application/json');
                        
                        xhr.onreadystatechange = function() {
                          console.log('XHR状态变化:', xhr.readyState, xhr.status);
                          if (xhr.readyState === 4) {
                            if (xhr.status === 200) {
                              try {
                                const data = JSON.parse(xhr.responseText);
                                console.log('XHR健康检查成功:', data);
                                alert(`XHR连接成功！后端状态: ${data.status}`);
                                
                                // 继续测试状态端点
                                testStateEndpoint(testTraceId);
                              } catch (e) {
                                console.error('XHR解析失败:', e);
                                alert(`XHR解析失败: ${e.message}`);
                              }
                            } else {
                              console.error('XHR健康检查失败:', xhr.status, xhr.statusText);
                              alert(`XHR健康检查失败: ${xhr.status} ${xhr.statusText}`);
                            }
                          }
                        };
                        
                        xhr.onerror = function() {
                          console.error('XHR网络错误，尝试fetch...');
                          // 如果XHR失败，尝试fetch
                          testWithFetch();
                        };
                        
                        xhr.ontimeout = function() {
                          console.error('XHR超时，尝试fetch...');
                          testWithFetch();
                        };
                        
                        // 添加状态码0的处理
                        if (xhr.status === 0) {
                          console.error('XHR状态码0 - CORS被阻止，尝试其他方法...');
                          testWithFetch();
                        }
                        
                        xhr.timeout = 5000;
                        xhr.send();
                        
                        function testStateEndpoint(traceId) {
                          console.log('测试状态端点:', traceId);
                          const stateXhr = new XMLHttpRequest();
                          stateXhr.open('GET', `/api/state/${traceId}`, true);
                          stateXhr.setRequestHeader('Content-Type', 'application/json');
                          
                          stateXhr.onreadystatechange = function() {
                            console.log('状态XHR状态:', stateXhr.readyState, stateXhr.status);
                            if (stateXhr.readyState === 4) {
                              if (stateXhr.status === 200) {
                                try {
                                  const data = JSON.parse(stateXhr.responseText);
                                  console.log('状态数据获取成功:', data);
                                  alert(`状态获取成功！todo数量: ${data.todo?.length}, steps数量: ${data.steps?.length}`);
                                  
                                  // 更新前端状态
                                  updateFrontendState(traceId, data);
                                } catch (e) {
                                  console.error('状态解析失败:', e);
                                  alert(`状态解析失败: ${e.message}`);
                                }
                              } else {
                                console.error('状态请求失败:', stateXhr.status, stateXhr.statusText);
                                alert(`状态请求失败: ${stateXhr.status} ${stateXhr.statusText}`);
                              }
                            }
                          };
                          
                          stateXhr.onerror = function() {
                            console.error('状态XHR网络错误');
                            alert('状态请求网络错误');
                          };
                          
                          stateXhr.ontimeout = function() {
                            console.error('状态XHR超时');
                            alert('状态请求超时');
                          };
                          
                          stateXhr.timeout = 10000;
                          stateXhr.send();
                        }
                        
                        function testWithFetch() {
                          console.log('方法2: 使用fetch...');
                          fetch('/api/health')
                            .then(response => {
                              console.log('fetch健康检查响应:', response.status);
                              if (response.ok) {
                                return response.json();
                              } else {
                                throw new Error(`HTTP ${response.status}`);
                              }
                            })
                            .then(data => {
                              console.log('fetch健康检查成功:', data);
                              alert(`fetch连接成功！后端状态: ${data.status}`);
                              return fetch(`/api/state/${testTraceId}`);
                            })
                            .then(response => {
                              console.log('fetch状态响应:', response.status);
                              if (response.ok) {
                                return response.json();
                              } else {
                                throw new Error(`HTTP ${response.status}`);
                              }
                            })
                            .then(data => {
                              console.log('fetch状态数据:', data);
                              alert(`fetch获取成功！todo数量: ${data.todo?.length}, steps数量: ${data.steps?.length}`);
                              updateFrontendState(testTraceId, data);
                            })
                            .catch(error => {
                              console.error('fetch失败:', error);
                              console.log('方法3: 尝试绕过CORS...');
                              testWithCorsBypass();
                            });
                        }
                        
                        function testWithCorsBypass() {
                          console.log('方法3: 尝试绕过CORS...');
                          
                          // 方法3a: 使用no-cors模式
                          console.log('方法3a: 使用no-cors模式...');
                          fetch('/api/health', {
                            method: 'GET',
                            mode: 'no-cors'
                          })
                          .then(response => {
                            console.log('no-cors响应:', response);
                            if (response.type === 'opaque') {
                              alert('no-cors成功，但无法读取数据。CORS问题确认。\n\n解决方案：\n1. 重启前端开发服务器\n2. 检查Vite代理配置\n3. 或者手动在控制台测试');
                              
                              // 提供手动测试指令
                              console.log('手动测试指令:');
                              console.log('1. 在控制台执行: fetch("/api/health")');
                              console.log('2. 查看是否有CORS错误');
                            }
                          })
                          .catch(error => {
                            console.error('no-cors也失败:', error);
                            alert(`所有方法都失败。请手动测试:\n\n1. 打开浏览器控制台\n2. 输入: fetch('/api/health')\n3. 查看具体错误信息`);
                          });
                        }
                        
                        function updateFrontendState(traceId, data) {
                          // 更新前端状态
                          if (window.testTraceId) {
                            window.testTraceId = traceId;
                            // 触发状态更新
                            setTimeout(() => {
                              if (window.currentPollInterval) {
                                clearInterval(window.currentPollInterval);
                              }
                              // 手动调用刷新
                              if (typeof onRefresh === 'function') {
                                onRefresh();
                              }
                            }, 100);
                          }
                        }
                      }
                      
                      // 方法1: 使用代理路径 (避免CORS)
                      console.log('方法1: 使用代理路径...');
                      const xhr = new XMLHttpRequest();
                      xhr.open('GET', '/api/health', true);
                      xhr.setRequestHeader('Content-Type', 'application/json');
                      
                      xhr.onreadystatechange = function() {
                        console.log('XHR状态变化:', xhr.readyState, xhr.status);
                        if (xhr.readyState === 4) {
                          if (xhr.status === 200) {
                            try {
                              const data = JSON.parse(xhr.responseText);
                              console.log('XHR健康检查成功:', data);
                              alert(`XHR连接成功！后端状态: ${data.status}`);
                              
                              // 继续测试状态端点
                              testStateEndpoint(testTraceId);
                            } catch (e) {
                              console.error('XHR解析失败:', e);
                              alert(`XHR解析失败: ${e.message}`);
                            }
                          } else {
                            console.error('XHR健康检查失败:', xhr.status, xhr.statusText);
                            alert(`XHR健康检查失败: ${xhr.status} ${xhr.statusText}`);
                          }
                        }
                      };
                      
                      xhr.onerror = function() {
                        console.error('XHR网络错误，尝试fetch...');
                        // 如果XHR失败，尝试fetch
                        testWithFetch();
                      };
                      
                      xhr.ontimeout = function() {
                        console.error('XHR超时，尝试fetch...');
                        testWithFetch();
                      };
                      
                      // 添加状态码0的处理
                      if (xhr.status === 0) {
                        console.error('XHR状态码0 - CORS被阻止，尝试其他方法...');
                        testWithFetch();
                      }
                      
                      xhr.timeout = 5000;
                      xhr.send();
                      
                      function testStateEndpoint(traceId) {
                        console.log('测试状态端点:', traceId);
                        const stateXhr = new XMLHttpRequest();
                        stateXhr.open('GET', `/api/state/${traceId}`, true);
                        stateXhr.setRequestHeader('Content-Type', 'application/json');
                        
                        stateXhr.onreadystatechange = function() {
                          console.log('状态XHR状态:', stateXhr.readyState, stateXhr.status);
                          if (stateXhr.readyState === 4) {
                            if (stateXhr.status === 200) {
                              try {
                                const data = JSON.parse(stateXhr.responseText);
                                console.log('状态数据获取成功:', data);
                                alert(`状态获取成功！todo数量: ${data.todo?.length}, steps数量: ${data.steps?.length}`);
                                
                                // 更新前端状态
                                updateFrontendState(traceId, data);
                              } catch (e) {
                                console.error('状态解析失败:', e);
                                alert(`状态解析失败: ${e.message}`);
                              }
                            } else {
                              console.error('状态请求失败:', stateXhr.status, stateXhr.statusText);
                              alert(`状态请求失败: ${stateXhr.status} ${stateXhr.statusText}`);
                            }
                          }
                        };
                        
                        stateXhr.onerror = function() {
                          console.error('状态XHR网络错误');
                          alert('状态请求网络错误');
                        };
                        
                        stateXhr.ontimeout = function() {
                          console.error('状态XHR超时');
                          alert('状态请求超时');
                        };
                        
                        stateXhr.timeout = 10000;
                        stateXhr.send();
                      }
                      
                      function testWithFetch() {
                        console.log('方法2: 使用fetch...');
                        fetch('/api/health')
                          .then(response => {
                            console.log('fetch健康检查响应:', response.status);
                            if (response.ok) {
                              return response.json();
                            } else {
                              throw new Error(`HTTP ${response.status}`);
                            }
                          })
                          .then(data => {
                            console.log('fetch健康检查成功:', data);
                            alert(`fetch连接成功！后端状态: ${data.status}`);
                            return fetch(`/api/state/${testTraceId}`);
                          })
                          .then(response => {
                            console.log('fetch状态响应:', response.status);
                            if (response.ok) {
                              return response.json();
                            } else {
                              throw new Error(`HTTP ${response.status}`);
                            }
                          })
                          .then(data => {
                            console.log('fetch状态数据:', data);
                            alert(`fetch获取成功！todo数量: ${data.todo?.length}, steps数量: ${data.steps?.length}`);
                            updateFrontendState(testTraceId, data);
                          })
                          .catch(error => {
                            console.error('fetch失败:', error);
                            console.log('方法3: 尝试绕过CORS...');
                            testWithCorsBypass();
                          });
                      }
                      
                      function testWithCorsBypass() {
                        console.log('方法3: 尝试绕过CORS...');
                        
                        // 方法3a: 使用no-cors模式
                        console.log('方法3a: 使用no-cors模式...');
                        fetch('/api/health', {
                          method: 'GET',
                          mode: 'no-cors'
                        })
                        .then(response => {
                          console.log('no-cors响应:', response);
                          if (response.type === 'opaque') {
                            alert('no-cors成功，但无法读取数据。CORS问题确认。\n\n解决方案：\n1. 重启前端开发服务器\n2. 检查Vite代理配置\n3. 或者手动在控制台测试');
                            
                            // 提供手动测试指令
                            console.log('手动测试指令:');
                            console.log('1. 在控制台执行: fetch("/api/health")');
                            console.log('2. 查看是否有CORS错误');
                          }
                        })
                        .catch(error => {
                          console.error('no-cors也失败:', error);
                          alert(`所有方法都失败。请手动测试:\n\n1. 打开浏览器控制台\n2. 输入: fetch('/api/health')\n3. 查看具体错误信息`);
                        });
                      }
                      
                      function updateFrontendState(traceId, data) {
                        // 更新前端状态
                        if (window.testTraceId) {
                          window.testTraceId = traceId;
                          // 触发状态更新
                          setTimeout(() => {
                            if (window.currentPollInterval) {
                              clearInterval(window.currentPollInterval);
                            }
                            // 手动调用刷新
                            if (typeof onRefresh === 'function') {
                              onRefresh();
                            }
                          }, 100);
                        }
                      }
                    }}
                    className="mt-1 px-2 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200"
                  >
                    🚀 直接测试API
                  </button>
                </div>
              </div>
            )}
            
                        {/* 任务准备阶段显示 - 只在真正的准备阶段显示 */}
            {isExecuting && todoList.length === 1 && todoList[0].step === 'prepare' && executionSteps.length <= 1 && !traceId && (
              <div className="text-center py-4 text-blue-600">
                <div className="text-sm font-medium">🚀 正在启动AI任务</div>
                <div className="text-xs mt-1">正在准备任务环境，请稍候...</div>
                <div className="mt-2">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{width: '60%'}}></div>
                  </div>
                </div>
                {/* 准备阶段的中断按钮 */}
                {onInterrupt && (
                  <div className="mt-3">
                    <button
                      onClick={onInterrupt}
                      className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
                    >
                      ⏹️ 中断任务
                    </button>
                  </div>
                )}
              </div>
            )}
        
            {/* 正常任务状态显示 - 简化逻辑，有任务数据就显示 */}
            {hasTaskData && (
          <>
            {/* 执行状态头部 */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${
                  isExecuting ? 'bg-blue-500 animate-pulse' : 
                  currentStep === 'stuck' ? 'bg-red-500' :
                  currentStep === 'interrupted' ? 'bg-orange-500' : 'bg-green-500'
                }`}></div>
                <span className="font-medium text-gray-900 text-sm">
                  {isExecuting ? 
                    (currentStep && currentStep !== 'processing' ? 
                      `${currentStep} (${todoList.filter(t => t.status === 'completed').length}/${todoList.length})` :
                      `AI正在执行任务... (${todoList.filter(t => t.status === 'completed').length}/${todoList.length})`
                    ) : 
                   currentStep === 'stuck' ? '任务执行卡住' :
                   currentStep === 'interrupted' ? '任务已中断' : '任务执行完成'}
                </span>
                {todoList.length > 0 && (
                  <span className="text-xs text-gray-600">
                    ({todoList.filter(t => t.status === 'completed').length}/{todoList.length} 完成)
                  </span>
                )}
              </div>
            </div>
            
            {/* 操作按钮 */}
            <div className="flex flex-wrap gap-2 mb-4">
              {onRefresh && traceId && (
                <button
                  onClick={onRefresh}
                  className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                >
                  🔄 刷新状态
                </button>
              )}
              {onRefresh && (
                <button
                  onClick={onRefresh}
                  className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200"
                >
                  🔄 强制刷新
                </button>
              )}
              {onInterrupt && traceId && isExecuting && (
                <button
                  onClick={onInterrupt}
                  className="px-2 py-1 text-xs bg-orange-100 text-orange-700 rounded hover:bg-orange-200"
                >
                  ⏹️ 中断任务
                </button>
              )}
              {onRetry && traceId && currentStep === 'stuck' && (
                <button
                  onClick={onRetry}
                  className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200"
                >
                  🔄 重试任务
                </button>
              )}
              
              {/* 始终显示中断按钮（当正在执行时） */}
              {isExecuting && (
                <button
                  onClick={onInterrupt}
                  className="px-2 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200"
                >
                  ⏹️ 立即中断
                </button>
              )}
              
              {/* 显示重新发送按钮（当任务中断或完成时） */}
              {!isExecuting && (currentStep === 'interrupted' || currentStep === 'stuck' || currentStep === 'timeout') && onResend && (
                <button
                  onClick={onResend}
                  className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200"
                >
                  🔄 重新发送
                </button>
              )}
            </div>

            {/* 任务清单 - 一直显示 */}
            {todoList.length > 0 && (
              <div className="mb-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2">任务清单</h4>
                <div className="space-y-2">
                  {todoList.map((todo, index) => (
                    <div key={index} className="flex items-center space-x-2 text-sm p-2 bg-gray-50 rounded">
                      <span className="text-lg">{getStatusIcon(todo.status)}</span>
                      <div className="flex-1 min-w-0">
                        <span className={`font-medium ${getStatusColor(todo.status)} text-xs`}>
                          {todo.step === 'prepare' && '🚀 准备任务'}
                          {todo.step === 'plan' && '🤔 任务规划'}
                          {todo.step?.startsWith('step-') && todo.step?.endsWith('-validate') && '✅ 验证步骤'}
                          {todo.step?.startsWith('step-') && !todo.step?.endsWith('-validate') && '⚡ 执行步骤'}
                          {!todo.step?.startsWith('step-') && todo.step !== 'plan' && todo.step !== 'prepare' && (todo.step || `任务 ${index + 1}`)}
                        </span>
                        {todo.desc && (
                          <div className="text-xs text-gray-500 mt-1 truncate">{todo.desc}</div>
                        )}
                      </div>
                      <span className={`px-2 py-1 rounded text-xs ${getStatusColor(todo.status)}`}>
                        {todo.status === 'completed' && '完成'}
                        {todo.status === 'in_progress' && '进行中'}
                        {todo.status === 'pending' && '等待'}
                        {todo.status === 'failed' && '失败'}
                        {todo.status !== 'completed' && todo.status !== 'in_progress' && todo.status !== 'pending' && todo.status !== 'failed' && todo.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 执行步骤详情 - 一直显示 */}
            {executionSteps.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">实时执行详情 ({executionSteps.length} 步)</h4>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                              {/* 最新步骤高亮显示 */}
            {executionSteps.length > 0 && (
              <div className="text-xs bg-blue-50 p-2 rounded border-l-2 border-blue-400">
                <div className="font-medium text-blue-800">最新步骤:</div>
                <div className="text-blue-700">
                  {executionSteps[executionSteps.length - 1].name === 'prepare' && '🚀 准备任务'}
                  {executionSteps[executionSteps.length - 1].name === 'planner' && '🤔 任务规划'}
                  {executionSteps[executionSteps.length - 1].name === 'executor' && '⚡ 执行任务'}
                  {executionSteps[executionSteps.length - 1].name === 'validator' && '✅ 验证结果'}
                  {executionSteps[executionSteps.length - 1].name === 'planner_review' && '🔍 总体复评'}
                  {executionSteps[executionSteps.length - 1].name === 'log' && '📝 日志记录'}
                  {executionSteps[executionSteps.length - 1].name === 'persist_memory' && '💾 保存记忆'}
                  {executionSteps[executionSteps.length - 1].name === 'interrupt' && '⏹️ 中断操作'}
                  {!['prepare', 'planner', 'executor', 'validator', 'planner_review', 'log', 'persist_memory', 'interrupt'].includes(executionSteps[executionSteps.length - 1].name) && executionSteps[executionSteps.length - 1].name}
                </div>
                <div className="text-blue-600 text-xs mt-1">
                  状态: {executionSteps[executionSteps.length - 1].status === 'started' ? '进行中' : 
                         executionSteps[executionSteps.length - 1].status === 'ok' ? '成功' : 
                         executionSteps[executionSteps.length - 1].status === 'interrupted' ? '已中断' :
                         executionSteps[executionSteps.length - 1].status}
                </div>
                <div className="text-blue-500 text-xs">
                  时间: {executionSteps[executionSteps.length - 1].ts}
                </div>
                {/* 显示详细信息 */}
                {executionSteps[executionSteps.length - 1].details && (
                  <div className="text-blue-600 text-xs mt-1">
                    {executionSteps[executionSteps.length - 1].details.action && <div>动作: {executionSteps[executionSteps.length - 1].details.action}</div>}
                    {executionSteps[executionSteps.length - 1].details.step && <div>步骤: {executionSteps[executionSteps.length - 1].details.step}</div>}
                    {executionSteps[executionSteps.length - 1].details.tool && <div>工具: {executionSteps[executionSteps.length - 1].details.tool}</div>}
                    {executionSteps[executionSteps.length - 1].details.rationale && <div>理由: {executionSteps[executionSteps.length - 1].details.rationale}</div>}
                  </div>
                )}
              </div>
            )}
                  {executionSteps.map((step, index) => (
                    <div key={index} className={`text-xs p-2 rounded border-l-2 ${
                      step.status === 'interrupted' ? 'bg-red-50 border-red-300' :
                      step.status === 'ok' ? 'bg-green-50 border-green-300' :
                      step.status === 'error' ? 'bg-red-50 border-red-200' :
                      step.status === 'warn' ? 'bg-yellow-50 border-yellow-200' :
                      'bg-gray-50 border-blue-200'
                    }`}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-gray-700">
                          {step.name === 'prepare' && '🚀 准备阶段'}
                          {step.name === 'planner' && '🤔 规划阶段'}
                          {step.name === 'executor' && '⚡ 执行阶段'}
                          {step.name === 'validator' && '✅ 验证阶段'}
                          {step.name === 'planner_review' && '🔍 总体复评'}
                          {step.name === 'log' && '📝 日志'}
                          {step.name === 'persist_memory' && '💾 保存记忆'}
                          {step.name === 'interrupt' && '⏹️ 中断操作'}
                          {!['prepare', 'planner', 'executor', 'validator', 'planner_review', 'log', 'persist_memory', 'interrupt'].includes(step.name) && step.name}
                        </span>
                        <span className={`px-2 py-1 rounded text-xs ${getStatusColor(step.status)}`}>
                          {step.status === 'started' && '开始'}
                          {step.status === 'ok' && '成功'}
                          {step.status === 'warn' && '警告'}
                          {step.status === 'error' && '错误'}
                          {step.status === 'info' && '信息'}
                          {step.status === 'interrupted' && '已中断'}
                          {step.status !== 'started' && step.status !== 'ok' && step.status !== 'warn' && step.status !== 'error' && step.status !== 'info' && step.status !== 'interrupted' && step.status}
                        </span>
                      </div>
                      {step.details && (
                        <div className="text-gray-600 space-y-1">
                          {step.details.action && <div>动作: {step.details.action}</div>}
                          {step.details.step && <div>步骤: {step.details.step}</div>}
                          {step.details.feedback && <div>反馈: {step.details.feedback}</div>}
                          {step.details.tool && <div>工具: {step.details.tool}</div>}
                          {step.details.rationale && <div>理由: {step.details.rationale}</div>}
                          {step.details.steps && <div>子任务: {step.details.steps.join(', ')}</div>}
                          {step.details.attempt && <div>尝试次数: {step.details.attempt}</div>}
                          {step.details.outputs_keys && <div>输出: {step.details.outputs_keys.join(', ')}</div>}
                          {step.details.msg && <div>消息: {step.details.msg}</div>}
                          {step.details.reason && <div>原因: {step.details.reason}</div>}
                          {step.details.interrupted_by && <div>中断者: {step.details.interrupted_by}</div>}
                          {step.details.timestamp && <div>时间戳: {new Date(step.details.timestamp * 1000).toLocaleString()}</div>}
                        </div>
                      )}
                      <div className="text-gray-500 text-xs mt-1">
                        {step.ts}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* 卡住状态提示 */}
            {currentStep === 'stuck' && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded">
                <h4 className="text-sm font-medium text-red-800 mb-2">⚠️ 任务执行卡住</h4>
                <div className="text-sm text-red-700 space-y-1">
                  <div>• 任务可能因为网络问题或AI响应慢而卡住</div>
                  <div>• 您可以点击"重试任务"按钮重新开始</div>
                  <div>• 或者等待一段时间后再次尝试</div>
                </div>
              </div>
            )}
            
            {/* 中断状态提示 */}
            {currentStep === 'interrupted' && (
              <div className="mt-4 p-3 bg-orange-50 border border-orange-200 rounded">
                <h4 className="text-sm font-medium text-orange-800 mb-2">⏹️ 任务已中断</h4>
                <div className="text-sm text-orange-700 space-y-1">
                  <div>• 任务已被用户主动中断</div>
                  <div>• 您可以重新发送请求开始新的任务</div>
                  <div>• 或者尝试其他操作</div>
                </div>
              </div>
            )}
            
            {/* 任务完成提示 */}
            {!isExecuting && currentStep !== 'stuck' && currentStep !== 'interrupted' && todoList.length > 0 && (
              <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded">
                <h4 className="text-sm font-medium text-green-800 mb-2">✅ 任务执行完成</h4>
                <div className="text-sm text-green-700 space-y-1">
                  <div>• 所有任务步骤已完成</div>
                  <div>• 您可以查看下方的执行详情了解完整过程</div>
                  <div>• 可以发送新消息开始新的任务</div>
                </div>
              </div>
            )}
            
            {/* 调试信息 */}
            {process.env.NODE_ENV === 'development' && traceId && (
              <div className="mt-4 p-2 bg-yellow-50 border border-yellow-200 rounded">
                <h4 className="text-xs font-medium text-yellow-800 mb-1">调试信息</h4>
                <div className="text-xs text-yellow-700">
                  <div>Trace ID: {traceId}</div>
                  <div>执行状态: {isExecuting ? '进行中' : currentStep === 'stuck' ? '卡住' : currentStep === 'interrupted' ? '已中断' : '已完成'}</div>
                  <div>任务数量: {todoList.length}</div>
                  <div>步骤数量: {executionSteps.length}</div>
                  <div>轮询状态: {window.currentPollInterval ? '活跃' : '停止'}</div>
                  {executionSteps.length > 0 && (
                    <div>最后步骤时间: {executionSteps[executionSteps.length - 1].ts}</div>
                  )}
                  <div>当前时间: {new Date().toLocaleTimeString()}</div>
                  <div>中断状态: {currentStep === 'interrupted' ? '已中断' : '正常'}</div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default TaskBar; 