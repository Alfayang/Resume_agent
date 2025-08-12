import React, { useRef, useEffect } from 'react';
import MessageItem from '../MessageItem/MessageItem';

const MessageList = ({ 
  messages, 
  isDragging, 
  handleDrop, 
  handleDragOver, 
  handleDragLeave 
}) => {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div 
      className={`flex-1 overflow-y-auto p-4 ${isDragging ? 'bg-purple-50' : ''}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      {messages.map((message) => (
        <MessageItem key={message.id} message={message} />
      ))}
      <div ref={messagesEndRef} />
      
      {isDragging && (
        <div className="fixed inset-0 bg-purple-100 bg-opacity-50 flex items-center justify-center pointer-events-none">
          <div className="bg-white p-8 rounded-lg shadow-lg border-2 border-dashed border-purple-400">
            <svg className="w-12 h-12 text-purple-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-purple-600 text-lg font-medium">拖拽文件到此处上传</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default MessageList; 