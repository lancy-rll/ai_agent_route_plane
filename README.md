# ai_agent_route_plane
# 智能路线规划助手

一个基于FastAPI + Vue3的智能路线规划应用，集成了AI大模型、地图API和本地知识库检索。

## 项目结构

```
route_planning_agent/
├── backend/              # 后端代码
│   ├── agent/           # Agent逻辑
│   ├── model/           # 模型工厂
│   ├── rag/             # 知识检索
│   ├── tools/           # 工具函数
│   └── utils/           # 工具类
├── frontend/            # 前端代码
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.js
│   │   └── style.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── main.py             # FastAPI主入口
└── .env               # 环境变量配置
```
## LangGraph


<img width="601" height="205" alt="image" src="https://github.com/user-attachments/assets/f9a43a38-801c-443a-ba3a-6c56385b121b" />



## 环境配置

在项目根目录创建 `.env` 文件，配置以下内容：

```env
# 高德地图API Key
AMAP_KEY=your_amap_api_key_here
AMAP_DRIVING_API_URL=https://restapi.amap.com/v3/direction/driving
AMAP_BASE_URL=https://restapi.amap.com/v3

# 阿里云DashScope API
DASHSCOPE_API_KEY=your_dashscope_api_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

## 安装依赖

### 后端依赖

在项目根目录运行：

```bash
pip install fastapi uvicorn aiohttp python-dotenv langgraph chromadb sentence-transformers
```

### 前端依赖

进入frontend目录并安装依赖：

```bash
cd frontend
npm install
```

## 运行项目

### 后端运行

在项目根目录运行：

```bash
python main.py
```

后端服务将在 http://localhost:8001 启动

### 前端运行

在另一个终端中：

```bash
cd frontend
npm run dev
```

前端服务将在 http://localhost:5173 启动

## 功能特性

- 🧭 智能路线规划
- 🏙️ POI搜索推荐
- 📷 图片理解支持
- 📚 本地知识库检索
- 💬 多轮对话支持
- 🎨 现代化UI设计

## API接口

### POST /api/chat
发送聊天消息

请求体：
```json
{
  "user_query": "从北京到上海怎么走",
  "image_base64": null,
  "session_id": null
}
```

### POST /api/select-route
选择路线

请求体：
```json
{
  "session_id": "xxx",
  "selected_route_id": "route_0"
}
```

### WebSocket /ws/chat
WebSocket实时通信

## 技术栈

- **后端**: FastAPI, LangGraph, DashScope
- **前端**: Vue3, Vite, Axios, Marked
- **AI**: 通义千问, 通义向量模型, 通义重排模型
- **地图**: 高德地图API

### 模型调用
- chat_model (qwen-max)：意图识别/评估/闲聊
- visual_model (qwen3-omni-flash)：图片理解
- embed_model (text-embedding-v3)：RAG向量嵌入/检索
- rerank_model (qwen3-rerank)：RAG 重排序
