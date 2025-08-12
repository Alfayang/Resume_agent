# 组件结构说明

## 组件架构

```
src/components/
├── index.js              # 组件导出索引
├── Sidebar/              # 侧边栏组件
│   └── Sidebar.jsx       # 对话列表和搜索
├── ChatHeader/           # 聊天头部组件
│   └── ChatHeader.jsx    # 聊天标题和用户信息
├── MessageItem/          # 消息项组件
│   └── MessageItem.jsx   # 单条消息显示
├── MessageList/          # 消息列表组件
│   └── MessageList.jsx   # 消息列表容器
├── ChatInput/            # 聊天输入组件
│   └── ChatInput.jsx     # 输入框和快捷操作
└── ChatArea/             # 聊天区域组件
    └── ChatArea.jsx      # 聊天区域容器
```

## 组件职责

### Sidebar (侧边栏)
- 对话搜索功能
- 对话列表显示
- 新建对话按钮
- 对话切换功能

### ChatHeader (聊天头部)
- 显示当前对话的Agent信息
- 用户ID显示
- 信息按钮

### MessageItem (消息项)
- 单条消息的显示
- 支持用户和助手消息
- 附件显示
- 思考过程显示
- 操作按钮

### MessageList (消息列表)
- 消息列表容器
- 自动滚动到底部
- 文件拖拽上传功能

### ChatInput (聊天输入)
- 文本输入框
- 文件上传功能
- 快捷操作菜单
- 发送按钮

### ChatArea (聊天区域)
- 整合聊天头部、消息列表和输入框
- 统一的状态管理

## 主题颜色

使用自定义紫色主题：
- 主色：`purple-500` (#7879F1)
- 浅色：`purple-50` (#f0f0ff)
- 深色：`purple-600` (#6a6be3)

## 使用方式

```jsx
import { Sidebar, ChatArea } from './components';

function App() {
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar {...sidebarProps} />
      <ChatArea {...chatAreaProps} />
    </div>
  );
}
``` 