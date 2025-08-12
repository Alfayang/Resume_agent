import React, { useState } from 'react';
import { Sidebar, ChatArea } from './components';

function App() {
  const [conversations, setConversations] = useState([
    { id: 1, title: '信息润色为简历', time: '08/11 8PM', active: true }
  ]);
  
  const [currentMessages, setCurrentMessages] = useState([
    {
      id: 1,
      type: 'assistant',
      content: '你好，我是留学助手，Agent有什么可以帮助您？',
      time: '8:00 PM'
    },
    {
      id: 2,
      type: 'user',
      content: '参考附件信息，帮助我润色留学简历',
      time: '8:00 PM',
      hasAttachment: true,
      attachment: {
        name: '个人介绍.txt',
        size: '222kb'
      }
    },
    {
      id: 3,
      type: 'assistant',
      content: '深度思考，用时25s',
      time: '8:00 PM',
      isThinking: true,
      thinkingProcess: [
        '用户让我帮忙润色留学简历，还提供了一个附件文件。',
        '附件里说用户叫小明，是上海大学22级的新闻传播专业学生，获得过上海市宝钢奖学金。',
        '用户是新闻传播专业的，那应该重点突出这个专业的优势。',
        '我应该在回复时先分析现有信息，然后给个润色后的简历模板。'
      ]
    },
    {
      id: 4,
      type: 'assistant',
      content: `好的！根据你提供的附件信息（上海大学22级新闻传播专业，获得上海市宝钢奖学金），我为你润色并构建了一个留学简历的核心框架。

润色后的简历核心部分（示例）：
[Your Name]
[Your Phone Number] | [Your Email Address] | [Your LinkedIn Profile (Optional)]

EDUCATION
Shanghai University | Shanghai, China
Bachelor of Arts in Journalism and Communication | Expected Graduation: [Month, Year]
GPA: [Your GPA]
Relevant Coursework: [List 3-5 core or advanced courses]`,
      time: '8:00 PM',
      hasActions: true
    }
  ]);
  
  const [inputValue, setInputValue] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [showQuickActions, setShowQuickActions] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const handleFileUpload = (files) => {
    const newFiles = Array.from(files).map(file => ({
      id: Date.now() + Math.random(),
      name: file.name,
      size: file.size,
      type: file.type,
      file: file
    }));
    setUploadedFiles(prev => [...prev, ...newFiles]);
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

  const sendMessage = () => {
    if (inputValue.trim() || uploadedFiles.length > 0) {
      const newMessage = {
        id: currentMessages.length + 1,
        type: 'user',
        content: inputValue,
        files: [...uploadedFiles],
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setCurrentMessages(prev => [...prev, newMessage]);
      setInputValue('');
      setUploadedFiles([]);
      
      // 模拟AI回复
      setTimeout(() => {
        const aiResponse = {
          id: currentMessages.length + 2,
          type: 'assistant',
          content: '我已经收到您的消息和文件。让我为您分析一下...',
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setCurrentMessages(prev => [...prev, aiResponse]);
      }, 1000);
    }
  };

  const addNewConversation = () => {
    const newConversation = {
      id: Date.now(),
      title: '新对话',
      time: new Date().toLocaleDateString() + ' ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      active: false
    };
    setConversations(prev => prev.map(conv => ({ ...conv, active: false })).concat(newConversation));
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar 
        conversations={conversations}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        setConversations={setConversations}
        addNewConversation={addNewConversation}
      />
      <ChatArea 
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
  );
}

export default App;
