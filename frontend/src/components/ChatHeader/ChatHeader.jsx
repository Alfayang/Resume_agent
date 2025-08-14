import React from 'react';

const ChatHeader = ({ conversation }) => {
  // 格式化时间的函数
  const formatTime = (timeString) => {
    if (!timeString) return '';
    
    try {
      const date = new Date(timeString);
      if (isNaN(date.getTime())) {
        // 如果不是有效日期，尝试解析其他格式
        return timeString;
      }
      
      const now = new Date();
      const diffInHours = (now - date) / (1000 * 60 * 60);
      
      if (diffInHours < 24) {
        // 今天：显示时间
        return date.toLocaleTimeString('zh-CN', { 
          hour: '2-digit', 
          minute: '2-digit',
          hour12: false 
        });
      } else if (diffInHours < 48) {
        // 昨天
        return '昨天 ' + date.toLocaleTimeString('zh-CN', { 
          hour: '2-digit', 
          minute: '2-digit',
          hour12: false 
        });
      } else {
        // 更早：显示日期和时间
        return date.toLocaleDateString('zh-CN', { 
          month: '2-digit', 
          day: '2-digit' 
        }) + ' ' + date.toLocaleTimeString('zh-CN', { 
          hour: '2-digit', 
          minute: '2-digit',
          hour12: false 
        });
      }
    } catch (error) {
      return timeString;
    }
  };

  return (
    <div className="bg-white border-b border-gray-200 p-4 flex items-center justify-between">
      <div className="flex items-center">
        <div className="w-10 h-10 bg-purple-500 rounded-full flex items-center justify-center text-white font-medium">
          Ag
        </div>
        <div className="ml-3">
          <h2 className="font-semibold text-gray-900">
            {conversation?.title || 'Agent'}
          </h2>
          <p className="text-sm text-gray-500">
            {conversation ? formatTime(conversation.createdAt || conversation.time) : ''}
          </p>
        </div>
      </div>
      <button className="text-gray-400 hover:text-gray-600">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </button>
    </div>
  );
};

export default ChatHeader; 