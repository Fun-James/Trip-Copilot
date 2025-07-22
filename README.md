
# Trip Copilot - 智能旅行助手

> 让旅行更智能，规划更轻松！

Trip Copilot 是一款现代化的智能旅行助手，采用前后端分离架构，前端基于 Vue 3 + Element Plus，后端基于 FastAPI。支持智能行程建议、热门目的地推荐、天气展示等功能，适合个人及团队旅行规划。

---

## 项目亮点

- 🤖 智能旅行建议，结合兴趣、天数等多维度生成个性化行程
- 🌏 热门目的地推荐，快速发现旅行灵感
- 🌦️ 天气预报集成，出行更安心
- 💬 聊天式交互体验，操作简单
- ⚡ 极速开发体验，前后端热重载

---


## 目录结构

```

Trip-Copilot/
├── frontend/          # Vue 3 前端项目
│   ├── src/           # 前端源码
│   │   ├── views/     # 页面组件
│   │   ├── App.vue    # 根组件
│   │   └── main.js    # 入口文件
│   ├── package.json   # 前端依赖
│   ├── vite.config.js # Vite 配置
│   └── index.html     # 入口 HTML
└── backend/           # FastAPI 后端项目
    ├── main.py        # FastAPI 应用主文件
    └── requirements.txt # 后端依赖
```


---

## 环境要求

- Node.js >= 16.x（推荐 LTS 版本）
- npm >= 8.x
- Python >= 3.8
- pip >= 21.x

---

## 快速开始


### 后端启动（FastAPI）

1. 进入后端目录：
   ```powershell
   cd backend
   ```
2. 创建虚拟环境（推荐）：
   ```powershell
   python -m venv venv
   ```
3. 激活虚拟环境：
   - Windows:
     ```powershell
     .\venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
4. 安装依赖：
   ```powershell
   pip install -r requirements.txt
   ```
5. 启动后端服务：
   ```powershell
   python main.py
   ```

> 默认后端服务地址：http://localhost:8000

---

### 前端启动（Vue 3 + Vite）

1. 进入前端目录：
   ```powershell
   cd frontend
   ```
2. 安装依赖：
   ```powershell
   npm install
   ```
3. 启动开发服务器：
   ```powershell
   npm run dev
   ```

> 默认前端访问地址：http://localhost:3000


---

## API 接口文档


### 后端 API 端点

- `GET /` - 根路径，返回欢迎消息
- `GET /health` - 健康检查
- `POST /api/trip/suggest` - 获取旅行建议
- `GET /api/destinations/popular` - 获取热门目的地


### 示例请求

```bash
# 获取旅行建议
curl -X POST "http://localhost:8000/api/trip/suggest" ^
     -H "Content-Type: application/json" ^
     -d "{
       \"destination\": \"北京\",
       \"duration\": 5,
       \"budget\": 3000,
       \"interests\": [\"历史\", \"美食\"]
     }"
```


---

## 功能特性


### 前端特性
- 🎨 现代化 UI 设计，Element Plus 组件库
- 💬 聊天式交互界面
- 📱 响应式设计，支持移动端
- ⚡ Vite 构建工具，极速热重载
- 🎭 Vue 3 Composition API

### 后端特性
- 🚀 FastAPI 高性能异步框架
- 📝 自动生成 API 文档（/docs）
- 🔄 CORS 跨域支持
- 📊 Pydantic 数据验证
- 🔧 热重载开发模式


---

## 开发指南


### 添加新的 API 端点
1. 在 `backend/main.py` 中添加新的路由：
   ```python
   @app.get("/api/new-endpoint")
   async def new_endpoint():
       return {"message": "新的API端点"}
   ```

### 添加新的前端页面
1. 在 `frontend/src/views/` 创建新的 Vue 组件
2. 在 `frontend/src/router/index.js` 中添加路由配置


---

## 部署说明


### 前端部署
```powershell
cd frontend
npm run build
```
构建产物在 `frontend/dist` 目录，可部署至任意静态服务器（如 nginx、Vercel、Netlify 等）。

### 后端部署
推荐使用 uvicorn 部署生产环境：
```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```


---

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


---

## 贡献指南

1. Fork 项目
2. 创建功能分支（如：`feature/xxx`）
3. 提交更改并推送到远程分支
4. 创建 Pull Request，描述你的更改内容
5. 等待审核与合并

欢迎 issue 反馈和建议！

---

## 常见问题（FAQ）

**Q: 前端/后端端口冲突怎么办？**
A: 可在 `vite.config.js` 或 `main.py`/`uvicorn` 命令中自定义端口。

**Q: 如何跨域访问？**
A: FastAPI 已开启 CORS 支持，前端无需额外配置。

**Q: 启动报错依赖缺失？**
A: 请确保已正确安装依赖，且 Python/Node 版本符合要求。

---

## 联系方式

如有问题或合作意向，请通过 issue 联系项目维护者。


---

## 许可证

MIT License
