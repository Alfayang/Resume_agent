import React from 'react';
import ChatHeader from '../ChatHeader/ChatHeader';
import MessageList from '../MessageList/MessageList';
import ChatInput from '../ChatInput/ChatInput';

const ChatArea = ({
  conversation,
  messages,
  inputValue,
  setInputValue,
  uploadedFiles,
  setUploadedFiles,
  isDragging,
  showQuickActions,
  setShowQuickActions,
  sendMessage,
  handleFileUpload,
  handleDrop,
  handleDragOver,
  handleDragLeave
}) => {
  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      <ChatHeader conversation={conversation} />
      <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
        <MessageList 
          messages={messages}
          isDragging={isDragging}
          handleDrop={handleDrop}
          handleDragOver={handleDragOver}
          handleDragLeave={handleDragLeave}
        />
      </div>
      <ChatInput 
        inputValue={inputValue}
        setInputValue={setInputValue}
        uploadedFiles={uploadedFiles}
        setUploadedFiles={setUploadedFiles}
        showQuickActions={showQuickActions}
        setShowQuickActions={setShowQuickActions}
        sendMessage={sendMessage}
        handleFileUpload={handleFileUpload}
      />
    </div>
  );
};

export default ChatArea; 