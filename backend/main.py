from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, SecretStr
from typing import Optional, List
import uvicorn
import os
from dotenv import load_dotenv
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import HumanMessage, SystemMessage

# 加载环境变量
load_dotenv()

app = FastAPI(title="Trip Copilot API", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化通义千问模型
def get_tongyi_client():
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("DASHSCOPE_API_KEY not found in environment variables")
    
    return ChatTongyi(api_key=SecretStr(api_key), model="qwen-plus")

# 数据模型
class TripRequest(BaseModel):
    destination: str
    duration: Optional[int] = None
    budget: Optional[float] = None
    interests: Optional[List[str]] = []

class TripResponse(BaseModel):
    id: int
    destination: str
    recommendations: List[str]
    estimated_cost: Optional[float] = None

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    success: bool = True

# 根路径
@app.get("/")
async def root():
    return {"message": "欢迎使用 Trip Copilot API"}

# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 获取旅行建议
@app.post("/api/trip/suggest", response_model=TripResponse)
async def get_trip_suggestions(request: TripRequest):
    try:
        # 获取通义千问客户端
        llm = get_tongyi_client()
        
        # 构建提示词
        interests_text = "、".join(request.interests) if request.interests else "一般旅游"
        budget_text = f"，预算约{request.budget}元" if request.budget else ""
        duration_text = f"，计划{request.duration}天" if request.duration else ""
        
        prompt = f"""
        请为用户制定一个详细的{request.destination}旅行计划。
        
        用户信息：
        - 目的地：{request.destination}
        - 兴趣爱好：{interests_text}
        {duration_text}{budget_text}
        
        请按以下格式返回4个具体的旅行建议，每行一个建议：
        1. [建议内容]
        2. [建议内容]  
        3. [建议内容]
        4. [建议内容]
        
        每个建议都要实用且详细，包含具体的地点或活动名称。
        """
        
        # 使用通义千问生成建议
        messages = [
            SystemMessage(content="你是一位专业的旅行规划师，擅长为用户提供个性化的旅行建议。"),
            HumanMessage(content=prompt)
        ]
        
        response = llm.invoke(messages)
        
        # 处理AI响应内容
        ai_content = response.content
        if isinstance(ai_content, list):
            text_content = ""
            for item in ai_content:
                if isinstance(item, dict) and "text" in item:
                    text_content += item["text"]
                elif isinstance(item, str):
                    text_content += item
            ai_content = text_content
        
        # 解析建议列表
        import re
        lines = str(ai_content).split('\n')
        recommendations = []
        
        for line in lines:
            line = line.strip()
            # 匹配数字开头的行
            if re.match(r'^\d+\.?\s*', line):
                # 去掉数字前缀
                clean_line = re.sub(r'^\d+\.?\s*', '', line).strip()
                if clean_line:
                    recommendations.append(clean_line)
        
        # 如果解析不到足够的建议，使用整体文本
        if len(recommendations) < 4:
            recommendations = [line.strip() for line in lines if line.strip() and not line.strip().startswith('请')]
            recommendations = recommendations[:4]
        
        # 确保有4条建议
        while len(recommendations) < 4:
            recommendations.append(f"探索{request.destination}的更多精彩体验")
        
        return TripResponse(
            id=1,
            destination=request.destination,
            recommendations=recommendations[:4],
            estimated_cost=request.budget if request.budget else None
        )
        
    except Exception as e:
        return TripResponse(
            id=1,
            destination=request.destination,
            recommendations=[f"抱歉，无法生成{request.destination}的旅行建议，请稍后再试。错误：{str(e)}"],
            estimated_cost=request.budget if request.budget else None
        )

# 获取热门目的地（AI生成）
@app.get("/api/destinations/popular")
async def get_popular_destinations():
    try:
        llm = get_tongyi_client()
        
        prompt = """请推荐5个中国最受欢迎的旅游目的地，每个目的地包含名称和简短描述。
        请按以下JSON格式返回：
        [
            {"name": "城市名", "country": "中国", "description": "简短描述"},
            ...
        ]
        只返回JSON格式，不要其他文字。"""
        
        messages = [
            SystemMessage(content="你是一位旅游专家，了解中国各地的热门旅游目的地。"),
            HumanMessage(content=prompt)
        ]
        
        response = llm.invoke(messages)
        
        # 处理AI响应
        ai_content = response.content
        if isinstance(ai_content, list):
            text_content = ""
            for item in ai_content:
                if isinstance(item, dict) and "text" in item:
                    text_content += item["text"]
                elif isinstance(item, str):
                    text_content += item
            ai_content = text_content
        
        # 尝试解析JSON
        import json
        import re
        
        # 提取JSON部分
        json_match = re.search(r'\[.*\]', str(ai_content), re.DOTALL)
        if json_match:
            json_str = json_match.group()
            destinations = json.loads(json_str)
            return {"destinations": destinations}
        else:
            # 如果解析失败，返回默认数据
            raise Exception("无法解析AI响应")
            
    except Exception as e:
        # fallback到简单的推荐
        return {
            "destinations": [
                {"name": "北京", "country": "中国", "description": "历史文化名城，故宫、长城等著名景点"},
                {"name": "上海", "country": "中国", "description": "现代化国际都市，外滩、迪士尼等"},
                {"name": "杭州", "country": "中国", "description": "人间天堂，西湖美景闻名世界"},
                {"name": "成都", "country": "中国", "description": "天府之国，美食与熊猫的故乡"},
                {"name": "西安", "country": "中国", "description": "千年古都，兵马俑等历史遗迹"}
            ]
        }

# 聊天API
@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    try:
        # 获取通义千问客户端
        llm = get_tongyi_client()
        
        # 构建消息
        system_prompt = """你是一位专业友好的旅行助手，名叫Trip Copilot。你可以：
1. 为用户提供旅行建议和规划
2. 回答关于目的地的问题
3. 推荐景点、美食、住宿等
4. 帮助估算旅行费用
请用友好、专业的语气回复用户。"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=request.message)
        ]
        
        if request.context:
            messages.append(HumanMessage(content=f"背景信息：{request.context}"))
        
        response = llm.invoke(messages)
        
        # 处理响应内容
        ai_content = response.content
        if isinstance(ai_content, list):
            # 如果是列表格式，提取文本内容
            text_content = ""
            for item in ai_content:
                if isinstance(item, dict) and "text" in item:
                    text_content += item["text"]
                elif isinstance(item, str):
                    text_content += item
            ai_reply = text_content.strip()
        else:
            ai_reply = str(ai_content).strip()
        
        return ChatResponse(reply=ai_reply, success=True)
        
    except Exception as e:
        return ChatResponse(
            reply=f"抱歉，我遇到了一些技术问题。请稍后再试。错误信息：{str(e)}", 
            success=False
        )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
