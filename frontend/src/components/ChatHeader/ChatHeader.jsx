import React from 'react';

const ChatHeader = () => {
  return (
    <div className="bg-white border-b border-gray-200 p-4 flex items-center justify-between">
      <div className="flex items-center">
        <div className="w-10 h-10 bg-purple-500 rounded-full flex items-center justify-center text-white font-medium">
          Ag
        </div>
        <div className="ml-3">
          <h2 className="font-semibold text-gray-900">Suporte ADMIN</h2>
          <p className="text-sm text-gray-500">#CU6798H</p>
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