import React from 'react';
import ChatHeader from '../ChatHeader/ChatHeader';
import MessageList from '../MessageList/MessageList';
import ChatInput from '../ChatInput/ChatInput';

const ChatArea = ({
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
    <div className="flex-1 flex flex-col">
      <ChatHeader />
      <MessageList 
        messages={messages}
        isDragging={isDragging}
        handleDrop={handleDrop}
        handleDragOver={handleDragOver}
        handleDragLeave={handleDragLeave}
      />
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