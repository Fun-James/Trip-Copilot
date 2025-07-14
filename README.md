# Trip Copilot - 智能旅行助手

一个现代化的前后端分离旅行规划应用，前端使用 Vue 3 + Element Plus，后端使用 FastAPI。

## 项目结构

```
Trip Copilot/
├── frontend/          # Vue 3 前端项目
│   ├── src/
│   │   ├── views/     # 页面组件
│   │   ├── App.vue    # 根组件
│   │   └── main.js    # 入口文件
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
└── backend/           # FastAPI 后端项目
    ├── main.py        # FastAPI 应用主文件
    └── requirements.txt
```

## 快速开始

### 后端启动

1. 进入后端目录：
```bash
cd backend
```

2. 创建虚拟环境（推荐）：
```bash
python -m venv venv
```

3. 激活虚拟环境：
- Windows: `venv\Scripts\activate`
- macOS/Linux: `source venv/bin/activate`

4. 安装依赖：
```bash
pip install -r requirements.txt
```

5. 启动后端服务：
```bash
python main.py
```

后端将在 http://localhost:8000 启动

### 前端启动

1. 进入前端目录：
```bash
cd frontend
```

2. 安装依赖：
```bash
npm install
```

3. 启动开发服务器：
```bash
npm run dev
```

前端将在 http://localhost:3000 启动

## API 接口

### 后端 API 端点

- `GET /` - 根路径，返回欢迎消息
- `GET /health` - 健康检查
- `POST /api/trip/suggest` - 获取旅行建议
- `GET /api/destinations/popular` - 获取热门目的地

### 示例请求

```bash
# 获取旅行建议
curl -X POST "http://localhost:8000/api/trip/suggest" \
     -H "Content-Type: application/json" \
     -d '{
       "destination": "北京",
       "duration": 5,
       "budget": 3000,
       "interests": ["历史", "美食"]
     }'
```

## 功能特性

### 前端特性
- 🎨 现代化 UI 设计，使用 Element Plus 组件库
- 💬 聊天式交互界面
- 📱 响应式设计，支持移动端
- ⚡ Vite 构建工具，快速开发体验
- 🎭 Vue 3 Composition API

### 后端特性
- 🚀 FastAPI 高性能异步框架
- 📝 自动生成 API 文档
- 🔄 CORS 跨域支持
- 📊 Pydantic 数据验证
- 🔧 热重载开发模式

## 开发指南

### 添加新的 API 端点

在 `backend/main.py` 中添加新的路由：

```python
@app.get("/api/new-endpoint")
async def new_endpoint():
    return {"message": "新的API端点"}
```

### 添加新的前端页面

1. 在 `frontend/src/views/` 创建新的 Vue 组件
2. 在 `frontend/src/main.js` 中添加路由配置

## 部署说明

### 前端部署
```bash
cd frontend
npm run build
```
构建产物在 `frontend/dist` 目录

### 后端部署
使用 uvicorn 部署：
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 技术栈

### 前端
- Vue 3
- Vue Router 4
- Element Plus
- Axios
- Vite

### 后端
- FastAPI
- Uvicorn
- Pydantic
- Python 3.8+

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License
