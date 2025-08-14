import React from 'react';

const MessageItem = ({ message }) => {
  return (
    <div className={`mb-6 flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex max-w-[70%] ${message.type === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* 头像 */}
        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          message.type === 'user' ? 'bg-purple-500 text-white ml-3' : 'bg-purple-500 text-white mr-3'
        }`}>
          {message.type === 'user' ? 'Stu' : 'Ag'}
        </div>

        {/* 消息内容 */}
        <div className={`rounded-2xl px-4 py-2 ${
          message.type === 'user' 
            ? 'bg-purple-500 text-white' 
            : 'bg-white border border-gray-200'
        }`}>
          {/* 附件显示 */}
          {message.hasAttachment && (
            <div className="mb-3 p-3 bg-gray-50 rounded-lg border">
              <div className="flex items-center text-sm">
                <svg className="w-4 h-4 mr-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
                <span className="font-medium">{message.attachment.name}</span>
                <span className="text-gray-500 ml-2">({message.attachment.size})</span>
              </div>
            </div>
          )}
          
          {/* 思考过程 */}
          {message.isThinking && (
            <div className="mb-3">
              <div className="flex items-center text-sm text-gray-600 mb-2">
                <div className="w-4 h-4 mr-2">💡</div>
                思考过程
              </div>
              <ul className="text-sm text-gray-600 space-y-1">
                {message.thinkingProcess && message.thinkingProcess.map((step, index) => (
                  <li key={index} className="flex items-start">
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full mt-2 mr-2 flex-shrink-0"></span>
                    {step}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          <div className="whitespace-pre-wrap">{message.content}</div>
          
          {/* 操作按钮 */}
          {message.hasActions && (
            <div className="mt-3 flex space-x-2">
              <button className="flex items-center px-3 py-1 bg-purple-100 text-purple-700 rounded-lg text-sm hover:bg-purple-200">
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                继续润色
              </button>
              <button className="flex items-center px-3 py-1 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200">
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                重新生成
              </button>
            </div>
          )}
          
          <div className={`text-xs mt-2 ${
            message.type === 'user' ? 'text-purple-100' : 'text-gray-500'
          }`}>
            {message.time}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MessageItem; 