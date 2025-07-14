from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

app = FastAPI(title="Trip Copilot API", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    # 这里是示例数据，实际应用中会连接到真实的推荐算法
    recommendations = [
        f"探索{request.destination}的历史文化景点",
        f"品尝{request.destination}的当地美食",
        f"参观{request.destination}的自然风光",
        f"体验{request.destination}的当地活动"
    ]
    
    return TripResponse(
        id=1,
        destination=request.destination,
        recommendations=recommendations,
        estimated_cost=request.budget if request.budget else 2000.0
    )

# 获取热门目的地
@app.get("/api/destinations/popular")
async def get_popular_destinations():
    return {
        "destinations": [
            {"name": "北京", "country": "中国", "image": "/images/beijing.jpg"},
            {"name": "上海", "country": "中国", "image": "/images/shanghai.jpg"},
            {"name": "杭州", "country": "中国", "image": "/images/hangzhou.jpg"},
            {"name": "成都", "country": "中国", "image": "/images/chengdu.jpg"},
            {"name": "西安", "country": "中国", "image": "/images/xian.jpg"}
        ]
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
