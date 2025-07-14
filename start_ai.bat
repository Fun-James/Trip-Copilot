@echo off
echo ========================================
echo    启动 Trip Copilot AI 服务 (简化版)
echo ========================================
echo.

cd /d "%~dp0backend"

echo 检查Python环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到Python，请确保Python已安装并添加到PATH
    pause
    exit /b 1
)

echo.
echo 检查依赖包...
pip show fastapi uvicorn dashscope langchain-community python-dotenv >nul 2>&1
if errorlevel 1 (
    echo 安装必要的依赖包...
    pip install -r requirements.txt
)

echo.
echo 检查API密钥...
if not exist ".env" (
    echo 错误: 未找到.env文件，请确保文件存在并包含DASHSCOPE_API_KEY
    pause
    exit /b 1
)

echo.
echo 🚀 启动服务器...
echo 📍 API文档: http://localhost:8000/docs
echo 💬 聊天接口: POST http://localhost:8000/api/chat
echo 🗺️ 旅行规划: POST http://localhost:8000/api/trip/plan
echo.
echo 按 Ctrl+C 停止服务器
echo.

python simple_main.py

pause
