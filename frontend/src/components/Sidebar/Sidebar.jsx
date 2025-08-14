import React from 'react';

const Sidebar = ({ 
  conversations, 
  searchQuery, 
  setSearchQuery, 
  setConversations, 
  addNewConversation,
  onConversationSelect
}) => {
  const filteredConversations = conversations.filter(conv => 
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const deleteConversation = (conversationId, e) => {
    // 阻止事件冒泡，避免触发选择对话
    e.stopPropagation();
    
    // 从localStorage中删除对话的消息
    localStorage.removeItem(`messages_${conversationId}`);
    
    // 更新对话列表状态
    setConversations(prev => {
      const updatedConversations = prev.filter(conv => conv.id !== conversationId);
      
      // 如果删除的是当前激活的对话且还有其他对话，激活第一个对话
      if (prev.find(conv => conv.id === conversationId)?.active && updatedConversations.length > 0) {
        updatedConversations[0].active = true;
        if (onConversationSelect) {
          onConversationSelect(updatedConversations[0]);
        }
      }
      
      // 如果删除对话后没有对话了，创建一个新的空对话
      if (updatedConversations.length === 0) {
        addNewConversation();
        return [];
      }
      
      return updatedConversations;
    });
  };

  return (
    <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
      {/* 头部搜索 */}
      <div className="p-4 border-b border-gray-200">
        <div className="relative">
          <svg className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="搜索对话..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-100 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
        </div>
      </div>

      {/* 对话列表 */}
      <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
        {filteredConversations.map((conv) => (
          <div
            key={conv.id}
            className={`p-4 border-b border-gray-100 cursor-pointer hover:bg-gray-50 ${
              conv.active ? 'bg-purple-50 border-l-4 border-l-purple-500' : ''
            }`}
            onClick={() => {
              setConversations(prev => prev.map(c => ({ ...c, active: c.id === conv.id })));
              if (onConversationSelect) {
                onConversationSelect(conv);
              }
            }}
          >
            <div className="flex items-center justify-between mb-1">
              <h3 className="font-medium text-gray-900 text-sm truncate">{conv.title}</h3>
              <div className="flex items-center">
                <span className="text-xs text-gray-500 mr-2">{conv.time}</span>
                {/* 删除按钮 */}
                <button 
                  onClick={(e) => deleteConversation(conv.id, e)}
                  className="text-gray-400 hover:text-red-500 transition-colors"
                  title="删除对话"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="flex items-center text-xs text-gray-500">
              <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              多条对话
            </div>
          </div>
        ))}
      </div>

      {/* 新建对话按钮 */}
      <div className="p-4 border-t border-gray-200">
        <button
          onClick={addNewConversation}
          className="w-full flex items-center justify-center px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          新建对话
        </button>
      </div>
    </div>
  );
};

export default Sidebar; 