import React, { useState, useEffect } from 'react';
import { Sidebar, ChatArea, TaskBar } from './components';
import { getApiUrl, API_CONFIG } from './config';

function App() {
  // 生成唯一ID的函数
  const generateUniqueId = () => {
    return Date.now() + Math.random();
  };

  // 从localStorage恢复对话列表
  const [conversations, setConversations] = useState(() => {
    const savedConversations = localStorage.getItem('conversations');
    if (savedConversations) {
      try {
        const parsed = JSON.parse(savedConversations);
        return parsed;
      } catch (e) {
        console.error('恢复对话列表失败:', e);
      }
    }
    // 如果没有保存的对话，创建一个新的空对话
    const now = new Date();
    return [
      {
        id: Date.now(),
        title: '新对话',
        time: now.toLocaleDateString() + ' ' + now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        createdAt: now.toISOString(),
        active: true,
        isDemo: false
      }
    ];
  });

  // 从localStorage恢复当前对话的消息
  const [currentMessages, setCurrentMessages] = useState(() => {
    // 默认欢迎消息
    return [
      {
        id: 1,
        type: 'assistant',
        content: '你好！我是AI助手，可以帮助您处理各种文档任务，包括简历润色、推荐信生成、个人陈述等。请告诉我您需要什么帮助？',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ];
  });

  const [inputValue, setInputValue] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [showQuickActions, setShowQuickActions] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // 任务执行状态
  const [taskState, setTaskState] = useState(() => {
    // 从localStorage恢复任务状态
    const savedState = localStorage.getItem('taskState');
    if (savedState) {
      try {
        const parsed = JSON.parse(savedState);
        // 如果任务还在执行中，重置为未执行状态
        if (parsed.isExecuting) {
          return {
            isExecuting: false,
            currentStep: null,
            todoList: [],
            executionSteps: [],
            traceId: null,
            planRationale: ''
          };
        }
        return parsed;
      } catch (e) {
        console.error('恢复任务状态失败:', e);
      }
    }
    return {
      isExecuting: false,
      currentStep: null,
      todoList: [],
      executionSteps: [],
      traceId: null,
      planRationale: ''
    };
  });

  const [showTaskBar, setShowTaskBar] = useState(true);

  // 保存对话列表到localStorage
  useEffect(() => {
    localStorage.setItem('conversations', JSON.stringify(conversations));
  }, [conversations]);

  // 保存当前对话的消息到localStorage
  useEffect(() => {
    const activeConversation = conversations.find(c => c.active);
    if (activeConversation) {
      localStorage.setItem(`messages_${activeConversation.id}`, JSON.stringify(currentMessages));
    }
  }, [currentMessages, conversations]);

  // 组件卸载时清理轮询
  useEffect(() => {
    return () => {
      if (window.currentPollInterval) {
        clearInterval(window.currentPollInterval);
        window.currentPollInterval = null;
      }
    };
  }, []);

  // 初始化时加载当前对话的消息
  useEffect(() => {
    const activeConversation = conversations.find(c => c.active);
    if (activeConversation) {
      const savedMessages = localStorage.getItem(`messages_${activeConversation.id}`);
      if (savedMessages) {
        try {
          const messages = JSON.parse(savedMessages);
          setCurrentMessages(messages);
        } catch (e) {
          console.error('加载对话消息失败:', e);
          loadDefaultMessages(activeConversation);
        }
      } else {
        loadDefaultMessages(activeConversation);
      }
    }
  }, [conversations]);

  // 加载默认消息的函数
  const loadDefaultMessages = (conversation) => {
    // 所有对话都显示相同的欢迎消息
    const welcomeMessage = {
      id: 1,
      type: 'assistant',
      content: '你好！我是AI助手，可以帮助您处理各种文档任务，包括推荐信生成、个人陈述等。请告诉我您需要什么帮助？',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setCurrentMessages([welcomeMessage]);
  };

  const addNewConversation = () => {
    const now = new Date();
    const newConversation = {
      id: Date.now(),
      title: '新对话',
      time: now.toLocaleDateString() + ' ' + now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      createdAt: now.toISOString(),
      active: false,
      isDemo: false
    };
    setConversations(prev => prev.map(conv => ({ ...conv, active: false })).concat(newConversation));

    // 切换到新对话时，清空消息并显示欢迎信息
    const welcomeMessage = {
      id: 1,
      type: 'assistant',
      content: '你好！我是AI助手，可以帮助您处理各种文档任务，包括推荐信生成、个人陈述等。请告诉我您需要什么帮助？',
      time: now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setCurrentMessages([welcomeMessage]);
  };

  // 文件上传处理
  const handleFileUpload = (files) => {
    const fileArray = Array.from(files).map(file => ({
      file,
      name: file.name,
      size: file.size,
      type: file.type
    }));
    setUploadedFiles(prev => [...prev, ...fileArray]);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    handleFileUpload(files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const sendMessage = async () => {
    if (inputValue.trim() || uploadedFiles.length > 0) {
      const currentConversation = conversations.find(c => c.active);
      const isDemo = currentConversation?.isDemo || false;

      // 如果当前有任务在执行，先中断
      if (taskState.isExecuting) {
        console.log('检测到正在执行的任务，先中断');
        await interruptTask();
        // 等待一小段时间确保中断完成
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      const newMessage = {
        id: generateUniqueId(),
        type: 'user',
        content: inputValue,
        files: [...uploadedFiles],
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setCurrentMessages(prev => [...prev, newMessage]);
      setInputValue('');
      setUploadedFiles([]);

      // 如果是演示对话，显示模拟回复
      if (isDemo) {
        setTimeout(() => {
          const aiResponse = {
            id: generateUniqueId(),
            type: 'assistant',
            content: '这是演示模式的回复。请创建新对话来体验真实的AI对话功能。',
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          };
          setCurrentMessages(prev => [...prev, aiResponse]);
        }, 1000);
        return;
      }

      // 立即初始化任务状态，让TaskBar立即显示
      const initialTaskState = {
        isExecuting: true,
        currentStep: '正在准备任务...',
        todoList: [
          { step: 'prepare', status: 'in_progress', desc: '正在准备任务环境' }
        ],
        executionSteps: [
          {
            name: 'prepare',
            status: 'started',
            ts: new Date().toLocaleString(),
            details: { action: '初始化任务' }
          }
        ],
        traceId: null,
        planRationale: '正在分析您的请求...'
      };
      setTaskState(initialTaskState);

      // 真实对话：调用后端API
      const thinkingMessage = {
        id: generateUniqueId(),
        type: 'assistant',
        content: '正在处理您的请求...',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isThinking: true
      };
      setCurrentMessages(prev => [...prev, thinkingMessage]);

      try {
        // 处理文件内容
        let fileContent = '';
        if (uploadedFiles.length > 0) {
          const file = uploadedFiles[0];
          try {
            fileContent = await file.file.text();
          } catch (error) {
            console.error('读取文件失败:', error);
            fileContent = `文件: ${file.name} (无法读取内容)`;
          }
        }

        // 构建请求体
        const requestBody = {
          user_input: inputValue + (fileContent ? `\n\n附件内容:\n${fileContent}` : '')
        };

        // 只有在有会话ID时才添加
        if (currentConversation?.id) {
          requestBody.session_id = currentConversation.id.toString();
        }

        console.log('发送请求:', requestBody);
        console.log('trace_id:', requestBody.session_id);
        console.log('session_id:', requestBody.session_id);

        const response = await fetch(getApiUrl(API_CONFIG.ENDPOINTS.GENERATE), {
          method: 'POST',
          headers: API_CONFIG.REQUEST_CONFIG.headers,
          body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
          const errorText = await response.text();
          console.error('API错误详情:', errorText);
          throw new Error(`API请求失败: ${response.status} - ${errorText}`);
        }

        const data = await response.json();
        console.log('API响应:', data);
        console.log('API响应中的trace_id:', data.trace_id);
        console.log('API响应类型:', typeof data.trace_id);
        console.log('API响应完整结构:', JSON.stringify(data, null, 2));

        // 更新任务状态，保留准备阶段的信息
        console.log('设置taskState，trace_id:', data.trace_id);
        setTaskState(prev => {
          const newState = {
            ...prev,
            isExecuting: true, // 保持执行状态
            traceId: data.trace_id,
            planRationale: data.plan_rationale || '',
            // 注意：初始API响应可能没有完整的todo和steps数据，需要等待轮询获取
            todoList: data.todo || data.steps || [],
            executionSteps: [
              ...prev.executionSteps.filter(step => step.name === 'prepare'), // 保留准备步骤
              ...(data.steps || [])
            ]
          };
          console.log('新的taskState:', newState);
          return newState;
        });

        // 移除思考状态，添加处理中的消息
        setCurrentMessages(prev => {
          const filtered = prev.filter(msg => msg.id !== thinkingMessage.id);
          return [...filtered, {
            id: generateUniqueId(),
            type: 'assistant',
            content: '正在处理您的请求，请稍候...',
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            trace_id: data.trace_id,
            isProcessing: true // 标记为正在处理中
          }];
        });

        // 如果有trace_id，开始流式状态监听
        if (data.trace_id) {
          // 立即获取一次状态
          try {
            const stateResponse = await fetch(getApiUrl(`${API_CONFIG.ENDPOINTS.STATE}/${data.trace_id}`));
            if (stateResponse.ok) {
              const stateData = await stateResponse.json();
              setTaskState(prev => ({
                ...prev,
                todoList: stateData.todo || [],
                executionSteps: stateData.steps || [],
                planRationale: stateData.plan_rationale || prev.planRationale
              }));
            }
          } catch (error) {
            console.error('立即获取状态失败:', error);
          }

          // 开始轮询状态监听
          console.log('开始轮询状态监听，trace_id:', data.trace_id);
          pollExecutionStatus(data.trace_id);
        }

      } catch (error) {
        console.error('API调用失败:', error);
        setTaskState(prev => ({ ...prev, isExecuting: false }));

        // 移除思考状态，添加错误消息
        setCurrentMessages(prev => {
          const filtered = prev.filter(msg => msg.id !== thinkingMessage.id);
          return [...filtered, {
            id: generateUniqueId(),
            type: 'assistant',
            content: `抱歉，处理您的请求时出现了错误：${error.message}`,
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }];
        });
      }
    }
  };

  // 手动刷新状态
  const refreshTaskState = async () => {
    // 支持手动测试指定的trace_id
    console.log('当前taskState:', taskState);
    console.log('window.testTraceId:', window.testTraceId);
    const traceIdToUse = window.testTraceId || taskState.traceId;
    console.log('使用的traceIdToUse:', traceIdToUse);

    if (traceIdToUse) {
      try {
        console.log('手动刷新状态，使用trace_id:', traceIdToUse);
        console.log('请求URL:', getApiUrl(`${API_CONFIG.ENDPOINTS.STATE}/${traceIdToUse}`));
        console.log('当前API配置:', API_CONFIG);

        const response = await fetch(getApiUrl(`${API_CONFIG.ENDPOINTS.STATE}/${traceIdToUse}`));
        console.log('状态响应状态码:', response.status);
        console.log('响应头:', response.headers);
        console.log('响应URL:', response.url);

        if (response.ok) {
          const stateData = await response.json();
          console.log('获取到的状态数据:', stateData);

          setTaskState(prev => ({
            ...prev,
            traceId: traceIdToUse, // 更新traceId
            todoList: stateData.todo || [],
            executionSteps: stateData.steps || [],
            planRationale: stateData.plan_rationale || prev.planRationale,
            isExecuting: !stateData.validation?.ok // 根据验证状态判断是否还在执行
          }));

          // 清除测试用的trace_id
          if (window.testTraceId) {
            delete window.testTraceId;
          }
        } else {
          const errorText = await response.text();
          console.error('状态请求失败:', response.status, errorText);
          alert(`状态请求失败: ${response.status} - ${errorText}`);
        }
      } catch (error) {
        console.error('手动刷新状态失败:', error);
        console.error('错误详情:', error.stack);
        alert(`刷新状态失败: ${error.message}`);
      }
    } else {
      console.log('没有可用的trace_id');
      alert('没有可用的trace_id');
    }
  };

  // 重试任务
  const retryTask = async () => {
    if (taskState.traceId) {
      console.log('重试任务:', taskState.traceId);
      setTaskState(prev => ({ ...prev, isExecuting: true, currentStep: null }));
      pollExecutionStatus(taskState.traceId);
    }
  };

  // 全局中断函数
  const forceInterrupt = async () => {
    console.log('强制中断所有任务');

    // 如果有traceId，先调用后端中断端点
    if (taskState.traceId) {
      try {
        console.log('调用后端中断端点:', taskState.traceId);
        const response = await fetch(getApiUrl(`/interrupt/${taskState.traceId}`), {
          method: 'POST',
          headers: API_CONFIG.REQUEST_CONFIG.headers
        });

        if (response.ok) {
          const result = await response.json();
          console.log('后端中断响应:', result);
        } else {
          console.error('后端中断失败:', response.status);
        }
      } catch (error) {
        console.error('调用后端中断端点失败:', error);
      }
    }

    // 清除轮询
    if (window.currentPollInterval) {
      clearInterval(window.currentPollInterval);
      window.currentPollInterval = null;
    }

    // 保留任务数据，只重置执行状态
    setTaskState(prev => ({
      ...prev,
      isExecuting: false,
      currentStep: 'interrupted'
    }));

    // 移除思考状态消息，添加中断提示
    setCurrentMessages(prev => {
      const filtered = prev.filter(msg => !msg.isThinking);
      return [...filtered, {
        id: generateUniqueId(),
        type: 'assistant',
        content: '⚠️ 任务已被强制中断。您可以重新发送请求或尝试其他操作。',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }];
    });

    // 清除localStorage中的任务状态
    localStorage.removeItem('taskState');

    console.log('任务已中断，界面已更新');
  };

  // 中断任务
  const interruptTask = async () => {
    console.log('中断按钮被点击');
    console.log('当前任务状态:', taskState);

    // 清除轮询（如果存在）
    if (window.currentPollInterval) {
      clearInterval(window.currentPollInterval);
      window.currentPollInterval = null;
    }

    // 立即更新状态为中断
    setTaskState(prev => ({
      ...prev,
      isExecuting: false,
      currentStep: 'interrupted'
    }));

    // 立即移除思考状态消息
    setCurrentMessages(prev => {
      const filtered = prev.filter(msg => !msg.isThinking);
      return [...filtered, {
        id: generateUniqueId(),
        type: 'assistant',
        content: '⚠️ 任务已被用户中断。您可以重新发送请求或尝试其他操作。',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }];
    });

    // 如果有traceId，调用后端中断端点
    if (taskState.traceId) {
      try {
        console.log('调用后端中断端点:', taskState.traceId);
        const response = await fetch(getApiUrl(`/interrupt/${taskState.traceId}`), {
          method: 'POST',
          headers: API_CONFIG.REQUEST_CONFIG.headers
        });

        if (response.ok) {
          const result = await response.json();
          console.log('后端中断响应:', result);
        } else {
          console.error('后端中断失败:', response.status);
        }
      } catch (error) {
        console.error('调用后端中断端点失败:', error);
      }
    }

    // 清除localStorage中的任务状态
    localStorage.removeItem('taskState');

    console.log('任务已中断，界面已更新');
  };

  // 重新发送最后一条消息
  const resendLastMessage = () => {
    const lastUserMessage = currentMessages
      .filter(msg => msg.type === 'user')
      .pop();

    if (lastUserMessage) {
      setInputValue(lastUserMessage.content);

      // 添加重新发送提示
      const resendMessage = {
        id: generateUniqueId(),
        type: 'assistant',
        content: '🔄 准备重新发送您的消息...',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setCurrentMessages(prev => [...prev, resendMessage]);

      // 自动发送消息
      setTimeout(() => {
        sendMessage();
      }, 500);
    }
  };

  // 轮询执行状态监听
  const pollExecutionStatus = (traceId) => {
    if (!traceId) return;

    // 清除之前的轮询
    if (window.currentPollInterval) {
      clearInterval(window.currentPollInterval);
    }

    // 设置轮询间隔（1秒，便于调试）
    const pollInterval = 1000;

    const pollState = async () => {
      try {
        console.log('轮询请求URL:', getApiUrl(`${API_CONFIG.ENDPOINTS.STATE}/${traceId}`));
        const response = await fetch(getApiUrl(`${API_CONFIG.ENDPOINTS.STATE}/${traceId}`));
        console.log('轮询响应状态:', response.status);
        if (response.ok) {
          const stateData = await response.json();

          console.log('轮询获取到状态:', stateData);

          // 更新任务状态
          setTaskState(prev => ({
            ...prev,
            isExecuting: !stateData.validation?.ok,
            todoList: stateData.todo || prev.todoList,
            executionSteps: stateData.steps || prev.executionSteps,
            planRationale: stateData.plan_rationale || prev.planRationale,
          }));

          // 若包含最终文本，则更新最后一条"处理中"消息
          const finalText = stateData.final_text || stateData.rewritten_letter || stateData.result;
          if (finalText) {
            setCurrentMessages(prev => {
              const idx = [...prev].reverse().findIndex(m => m.isProcessing);
              if (idx !== -1) {
                const realIdx = prev.length - 1 - idx;
                const updated = [...prev];
                updated[realIdx] = { ...updated[realIdx], content: finalText, isProcessing: false };
                return updated;
              }
              return prev;
            });
          }

          // 如果任务完成，停止轮询并更新最终状态
          if (stateData.validation?.ok || stateData.status === 'completed' || stateData.status === 'interrupted' || stateData.status === 'timeout') {
            console.log(`轮询结束，状态: ${stateData.status}`);
            clearInterval(window.currentPollInterval);
            window.currentPollInterval = null;
            setTaskState(prev => ({ ...prev, isExecuting: false, currentStep: stateData.status }));

            // 更新最终消息内容 - 无论验证是否通过都显示最终结果
            console.log('任务完成，更新最终消息...');
            setCurrentMessages(prev => {
              const idx = [...prev].reverse().findIndex(m => m.isProcessing);
              if (idx !== -1) {
                const realIdx = prev.length - 1 - idx;
                const updated = [...prev];
                // 优先使用之前获取的finalText，然后尝试从stateData中获取
                const finalContent = finalText || stateData.final_text || stateData.rewritten_letter || stateData.result || '✅ 任务执行完成！请查看右侧的执行详情了解完整过程。';

                updated[realIdx] = {
                  ...updated[realIdx],
                  content: finalContent, // 使用最终内容
                  isProcessing: false
                };
                return updated;
              }
              return prev;
            });
          }
        } else {
          console.error('轮询状态请求失败:', response.status);
        }
      } catch (error) {
        console.error('轮询状态失败:', error);
      }
    };

    // 立即执行一次
    pollState();

    // 设置定时轮询
    window.currentPollInterval = setInterval(pollState, pollInterval);
  };

  // 获取步骤显示名称
  const getStepDisplayName = (stepName) => {
    const stepNames = {
      'planner': '规划任务',
      'executor': '执行任务',
      'validator': '验证结果',
      'prepare': '准备任务',
      'log': '记录日志'
    };
    return stepNames[stepName] || stepName;
  };

  // 测试TaskBar功能
  const testTaskBar = () => {
    const testState = {
      isExecuting: true,
      currentStep: '测试中',
      todoList: [
        { step: 'test-1', status: 'completed', desc: '测试步骤1' },
        { step: 'test-2', status: 'in_progress', desc: '测试步骤2' },
        { step: 'test-3', status: 'pending', desc: '测试步骤3' }
      ],
      executionSteps: [
        { name: 'test-1', status: 'ok', ts: new Date().toLocaleString(), details: { action: '测试动作1' } },
        { name: 'test-2', status: 'started', ts: new Date().toLocaleString(), details: { action: '测试动作2' } }
      ],
      traceId: 'test-123',
      planRationale: '这是一个测试任务'
    };
    setTaskState(testState);
  };

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar
        conversations={conversations}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        setConversations={setConversations}
        addNewConversation={addNewConversation}
        onConversationSelect={(conversation) => {
          // 切换对话
          setConversations(prev => prev.map(conv => ({ ...conv, active: conv.id === conversation.id })));

          // 从localStorage加载对话消息
          const savedMessages = localStorage.getItem(`messages_${conversation.id}`);
          if (savedMessages) {
            try {
              const messages = JSON.parse(savedMessages);
              setCurrentMessages(messages);
            } catch (e) {
              console.error('加载对话消息失败:', e);
              // 如果加载失败，显示默认消息
              loadDefaultMessages(conversation);
            }
          } else {
            // 如果没有保存的消息，显示默认消息
            loadDefaultMessages(conversation);
          }
        }}
      />
      <div className="flex-1 flex">
        {/* 左侧：聊天区域 */}
        <div className="flex-1 flex flex-col">
          <ChatArea
            conversation={conversations.find(c => c.active)}
            messages={currentMessages}
            inputValue={inputValue}
            setInputValue={setInputValue}
            uploadedFiles={uploadedFiles}
            setUploadedFiles={setUploadedFiles}
            isDragging={isDragging}
            showQuickActions={showQuickActions}
            setShowQuickActions={setShowQuickActions}
            sendMessage={sendMessage}
            handleFileUpload={handleFileUpload}
            handleDrop={handleDrop}
            handleDragOver={handleDragOver}
            handleDragLeave={handleDragLeave}
          />
        </div>

        {/* 右侧：TaskBar区域 */}
        {showTaskBar && (
          <div className="w-80 border-l border-gray-200 bg-gray-50">
            <TaskBar
              taskState={taskState}
              onRefresh={refreshTaskState}
              onRetry={retryTask}
              onInterrupt={forceInterrupt}
              onResend={resendLastMessage}
              onTest={testTaskBar}
              onToggle={() => setShowTaskBar(false)}
            />
          </div>
        )}

        {/* TaskBar切换按钮 */}
        {!showTaskBar && (
          <div className="w-8 border-l border-gray-200 bg-gray-50 flex items-center justify-center">
            <button
              onClick={() => setShowTaskBar(true)}
              className="p-1 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
              title="显示AI执行状态"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;