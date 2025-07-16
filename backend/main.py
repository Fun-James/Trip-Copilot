from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, SecretStr
from typing import Optional, List
import uvicorn
import os
import time
import re
import json
from dotenv import load_dotenv
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import HumanMessage, SystemMessage
import requests

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

# 新增行程规划数据模型
class ItineraryPlanRequest(BaseModel):
    destination: str
    duration: int  # 天数，必填

class ItineraryPlanResponse(BaseModel):
    success: bool
    plan_data: Optional[dict] = None
    error_message: Optional[str] = None

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

class PathRequest(BaseModel):
    start: str
    end: str
    mode: Optional[str] = "driving"  # driving, walking, transit

class PathResponse(BaseModel):
    success: bool
    path_data: Optional[dict] = None
    error_message: Optional[str] = None

class LocationRequest(BaseModel):
    location: str

class LocationResponse(BaseModel):
    success: bool
    location_data: Optional[dict] = None
    error_message: Optional[str] = None

# 新增：为行程中的地点生成路径规划的请求模型
class ItineraryRouteRequest(BaseModel):
    places: List[dict]  # 地点列表，每个地点包含name, longitude, latitude
    mode: Optional[str] = "driving"  # 出行方式

class ItineraryRouteResponse(BaseModel):
    success: bool
    routes_data: Optional[List[dict]] = None
    error_message: Optional[str] = None

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

# 获取高德地图API密钥
def get_amap_api_key():
    api_key = os.getenv("AMAP_API_KEY")
    if not api_key:
        raise ValueError("AMAP_API_KEY not found in environment variables")
    return api_key

# 获取地点坐标
def get_location_coordinates(location: str):
    """通过地点名称获取经纬度坐标"""
    try:
        # 添加延迟避免QPS限制（免费版3次/秒）
        time.sleep(0.4)  # 等待400ms
        
        api_key = get_amap_api_key()
        url = f"https://restapi.amap.com/v3/geocode/geo"
        params = {
            "key": api_key,
            "address": location
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if data["status"] == "1" and data["geocodes"]:
            location_str = data["geocodes"][0]["location"]
            longitude_str, latitude_str = location_str.split(",")
            # 确保返回浮点数类型
            longitude = float(longitude_str)
            latitude = float(latitude_str)
            return longitude, latitude
        else:
            return None, None
    except Exception as e:
        print(f"获取坐标失败: {e}")
        return None, None

# 获取路径规划
def get_route_planning(start_coords: tuple, end_coords: tuple, mode: str = "driving"):
    """获取两点间的路径规划"""
    try:
        # 添加延迟避免QPS限制（免费版3次/秒）
        time.sleep(0.4)  # 等待400ms
        
        api_key = get_amap_api_key()
        origin = f"{start_coords[0]},{start_coords[1]}"
        destination = f"{end_coords[0]},{end_coords[1]}"
        
        url = f"https://restapi.amap.com/v3/direction/{mode}"
        params = {
            "key": api_key,
            "origin": origin,
            "destination": destination
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        return data
    except Exception as e:
        print(f"获取路径规划失败: {e}")
        return None

# 路径规划API
@app.post("/api/trip/path", response_model=PathResponse)
async def get_trip_path(request: PathRequest):
    """获取起点到终点的路径规划"""
    try:
        # 获取起点坐标
        start_lng, start_lat = get_location_coordinates(request.start)
        if start_lng is None or start_lat is None:
            return PathResponse(
                success=False,
                error_message=f"无法获取起点'{request.start}'的坐标信息"
            )
        
        # 获取终点坐标
        end_lng, end_lat = get_location_coordinates(request.end)
        if end_lng is None or end_lat is None:
            return PathResponse(
                success=False,
                error_message=f"无法获取终点'{request.end}'的坐标信息"
            )
        
        # 验证坐标有效性
        try:
            start_lng = float(start_lng)
            start_lat = float(start_lat)
            end_lng = float(end_lng)
            end_lat = float(end_lat)
            
            # 检查坐标范围
            if not (-180 <= start_lng <= 180 and -90 <= start_lat <= 90):
                return PathResponse(
                    success=False,
                    error_message=f"起点坐标无效: ({start_lng}, {start_lat})"
                )
            
            if not (-180 <= end_lng <= 180 and -90 <= end_lat <= 90):
                return PathResponse(
                    success=False,
                    error_message=f"终点坐标无效: ({end_lng}, {end_lat})"
                )
                
        except (ValueError, TypeError):
            return PathResponse(
                success=False,
                error_message="坐标格式错误，无法进行路径规划"
            )
        
        # 获取路径规划
        mode = request.mode or "driving"  # 如果mode为None，默认使用driving
        route_data = get_route_planning(
            (start_lng, start_lat), 
            (end_lng, end_lat), 
            mode
        )
        
        if not route_data or route_data.get("status") != "1":
            return PathResponse(
                success=False,
                error_message="获取路径规划失败，请检查起点和终点是否正确"
            )
        
        # 处理返回数据，提取关键信息
        processed_data = {
            "start_point": {
                "name": request.start,
                "longitude": start_lng,  # 已经是 float 类型
                "latitude": start_lat    # 已经是 float 类型
            },
            "end_point": {
                "name": request.end,
                "longitude": end_lng,    # 已经是 float 类型
                "latitude": end_lat      # 已经是 float 类型
            },
            "mode": mode,
            "route_info": route_data.get("route", {}),
            "raw_data": route_data  # 完整的原始数据，供前端使用
        }
        
        return PathResponse(
            success=True,
            path_data=processed_data
        )
        
    except ValueError as ve:
        return PathResponse(
            success=False,
            error_message=str(ve)
        )
    except Exception as e:
        return PathResponse(
            success=False,
            error_message=f"服务器内部错误: {str(e)}"
        )

# 行程地点间路径规划API
@app.post("/api/trip/itinerary-routes", response_model=ItineraryRouteResponse)
async def get_itinerary_routes(request: ItineraryRouteRequest):
    """为行程中的地点生成相邻地点间的路径规划"""
    try:
        if not request.places or len(request.places) < 2:
            return ItineraryRouteResponse(
                success=False,
                error_message="至少需要2个地点才能进行路径规划"
            )
        
        routes = []
        mode = request.mode or "driving"
        
        # 为相邻的地点生成路径规划
        for i in range(len(request.places) - 1):
            start_place = request.places[i]
            end_place = request.places[i + 1]
            
            # 验证地点数据
            if not all(key in start_place for key in ['name', 'longitude', 'latitude']):
                return ItineraryRouteResponse(
                    success=False,
                    error_message=f"地点 {i+1} 缺少必要的坐标信息"
                )
                
            if not all(key in end_place for key in ['name', 'longitude', 'latitude']):
                return ItineraryRouteResponse(
                    success=False,
                    error_message=f"地点 {i+2} 缺少必要的坐标信息"
                )
            
            # 获取路径规划
            start_coords = (float(start_place['longitude']), float(start_place['latitude']))
            end_coords = (float(end_place['longitude']), float(end_place['latitude']))
            
            route_data = get_route_planning(start_coords, end_coords, mode)
            
            if route_data and route_data.get("status") == "1":
                # 处理路径数据
                route_info = {
                    "segment_index": i,
                    "start_point": {
                        "name": start_place['name'],
                        "longitude": float(start_place['longitude']),
                        "latitude": float(start_place['latitude'])
                    },
                    "end_point": {
                        "name": end_place['name'],
                        "longitude": float(end_place['longitude']),
                        "latitude": float(end_place['latitude'])
                    },
                    "mode": mode,
                    "route_info": route_data.get("route", {}),
                    "success": True
                }
            else:
                # 如果路径规划失败，创建简单路径
                route_info = {
                    "segment_index": i,
                    "start_point": {
                        "name": start_place['name'],
                        "longitude": float(start_place['longitude']),
                        "latitude": float(start_place['latitude'])
                    },
                    "end_point": {
                        "name": end_place['name'],
                        "longitude": float(end_place['longitude']),
                        "latitude": float(end_place['latitude'])
                    },
                    "mode": mode,
                    "route_info": None,
                    "success": False,
                    "fallback": "simple_line"  # 标记为简单直线连接
                }
            
            routes.append(route_info)
        
        return ItineraryRouteResponse(
            success=True,
            routes_data=routes
        )
        
    except Exception as e:
        return ItineraryRouteResponse(
            success=False,
            error_message=f"生成行程路径规划失败: {str(e)}"
        )

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

# 获取地点详细信息API
@app.post("/api/location/info", response_model=LocationResponse)
async def get_location_info(request: LocationRequest):
    """获取地点的详细信息和坐标"""
    try:
        api_key = get_amap_api_key()
        url = f"https://restapi.amap.com/v3/geocode/geo"
        params = {
            "key": api_key,
            "address": request.location
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data["status"] == "1" and data["geocodes"]:
            geocode = data["geocodes"][0]
            location_data = {
                "name": request.location,
                "formatted_address": geocode.get("formatted_address", ""),
                "province": geocode.get("province", ""),
                "city": geocode.get("city", ""),
                "district": geocode.get("district", ""),
                "location": geocode.get("location", ""),
                "longitude": float(geocode.get("location", "0,0").split(",")[0]),
                "latitude": float(geocode.get("location", "0,0").split(",")[1]),
                "level": geocode.get("level", "")
            }
            
            return LocationResponse(
                success=True,
                location_data=location_data
            )
        else:
            return LocationResponse(
                success=False,
                error_message=f"无法找到地点'{request.location}'的信息"
            )
            
    except ValueError as ve:
        return LocationResponse(
            success=False,
            error_message=str(ve)
        )
    except Exception as e:
        return LocationResponse(
            success=False,
            error_message=f"服务器内部错误: {str(e)}"
        )

# 行程规划API
@app.post("/api/trip/itinerary", response_model=ItineraryPlanResponse)
async def plan_itinerary(request: ItineraryPlanRequest):
    """根据目的地和天数规划行程"""
    try:
        # 获取通义千问客户端
        llm = get_tongyi_client()
        
        # 构建提示词
        prompt = f"""
        请为用户制定一个为期{request.duration}天的{request.destination}旅行行程。
        
        用户信息：
        - 目的地：{request.destination}
        - 旅行天数：{request.duration}天
        
        请按以下格式返回行程安排：
        {
            "day_1": ["活动1", "活动2"],
            "day_2": ["活动1", "活动2"],
            ...
        }
        
        每个活动要具体，包含地点和活动名称。
        """
        
        # 使用通义千问生成行程
        messages = [
            SystemMessage(content="你是一位专业的旅行规划师，擅长为用户提供个性化的旅行行程规划。"),
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
        
        # 尝试解析为字典
        try:
            plan_data = json.loads(str(ai_content))
        except json.JSONDecodeError:
            plan_data = None
        
        if not plan_data:
            return ItineraryPlanResponse(
                success=False,
                error_message="无法解析行程规划，请稍后再试"
            )
        
        return ItineraryPlanResponse(
            success=True,
            plan_data=plan_data
        )
        
    except Exception as e:
        return ItineraryPlanResponse(
            success=False,
            error_message=f"服务器内部错误: {str(e)}"
        )

# 新增行程规划API
@app.post("/api/trip/plan", response_model=ItineraryPlanResponse)
async def get_trip_plan(request: ItineraryPlanRequest):
    """获取完整的行程规划，包含每日详细安排、地点坐标和路径规划数据"""
    try:
        # 获取通义千问客户端
        llm = get_tongyi_client()
        
        # 构建高级LLM Prompt
        prompt = f"""
        请为用户制定一个详细的{request.destination}{request.duration}天旅行行程规划。

        要求：
        1. 为每一天按顺序推荐3-4个逻辑上顺路的地点
        2. 每天都要有一个主题描述
        3. 必须严格按照以下JSON格式返回，不能有任何额外的解释性文字
        
        返回格式示例：
        {{
          "destination": "{request.destination}",
          "total_days": {request.duration},
          "itinerary": [
            {{
              "day": 1,
              "theme": "第一天主题描述",
              "places": [
                {{ "name": "具体地点名称1" }},
                {{ "name": "具体地点名称2" }},
                {{ "name": "具体地点名称3" }}
              ]
            }},
            {{
              "day": 2,
              "theme": "第二天主题描述",
              "places": [
                {{ "name": "具体地点名称4" }},
                {{ "name": "具体地点名称5" }},
                {{ "name": "具体地点名称6" }}
              ]
            }}
          ]
        }}
        
        注意：
        - 只返回JSON格式，不要其他任何文字
        - 地点名称要具体准确，便于地图定位
        - 同一天的地点应该地理位置相对集中，便于游览
        - 每天3-4个地点即可，不要过多
        """
        
        # 使用通义千问生成行程规划
        messages = [
            SystemMessage(content="你是一位专业的旅行规划师，擅长制定详细的旅行行程。你必须严格按照要求的JSON格式返回结果。"),
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
        
        # 解析JSON
        
        # 提取JSON部分
        json_match = re.search(r'\{.*\}', str(ai_content), re.DOTALL)
        if not json_match:
            raise ValueError("AI返回的内容不包含有效的JSON格式")
        
        json_str = json_match.group()
        plan_data = json.loads(json_str)
        
        # 为每个地点获取坐标并生成路径规划
        if "itinerary" in plan_data:
            for day_plan in plan_data["itinerary"]:
                if "places" in day_plan:
                    # 第一步：为每个地点获取坐标
                    valid_places = []
                    for place in day_plan["places"]:
                        if "name" in place:
                            lng, lat = get_location_coordinates(place["name"])
                            if lng is not None and lat is not None:
                                # 确保坐标是有效的浮点数
                                try:
                                    place["longitude"] = float(lng)
                                    place["latitude"] = float(lat)
                                    # 验证坐标范围
                                    if (-180 <= place["longitude"] <= 180 and -90 <= place["latitude"] <= 90):
                                        valid_places.append(place)
                                    else:
                                        print(f"警告：地点 '{place['name']}' 坐标超出有效范围: ({lng}, {lat})")
                                        place["longitude"] = None
                                        place["latitude"] = None
                                except (ValueError, TypeError):
                                    print(f"警告：地点 '{place['name']}' 坐标转换失败: ({lng}, {lat})")
                                    place["longitude"] = None
                                    place["latitude"] = None
                            else:
                                place["longitude"] = None
                                place["latitude"] = None
                                print(f"警告：无法获取地点 '{place['name']}' 的坐标")
                    
                    # 第二步：为相邻地点生成路径规划数据
                    day_plan["routes"] = []
                    if len(valid_places) >= 2:
                        print(f"第{day_plan['day']}天开始生成 {len(valid_places)-1} 条路径...")
                        for i in range(len(valid_places) - 1):
                            start_place = valid_places[i]
                            end_place = valid_places[i + 1]
                            
                            # 获取两地点间的路径规划
                            try:
                                route_data = get_route_planning(
                                    (start_place["longitude"], start_place["latitude"]),
                                    (end_place["longitude"], end_place["latitude"]),
                                    "driving"  # 默认使用驾车模式
                                )
                                
                                if route_data and route_data.get("status") == "1":
                                    # 构建路径数据，参考手动路径规划的数据结构
                                    route_info = {
                                        "start_point": {
                                            "name": start_place["name"],
                                            "longitude": start_place["longitude"],
                                            "latitude": start_place["latitude"]
                                        },
                                        "end_point": {
                                            "name": end_place["name"],
                                            "longitude": end_place["longitude"],
                                            "latitude": end_place["latitude"]
                                        },
                                        "mode": "driving",
                                        "route_info": route_data.get("route", {}),
                                        "raw_data": route_data,
                                        "sequence": i + 1  # 标记这是第几段路径
                                    }
                                    day_plan["routes"].append(route_info)
                                    print(f"✓ 成功生成路径 {i+1}/{len(valid_places)-1}：{start_place['name']} -> {end_place['name']}")
                                else:
                                    print(f"✗ 无法生成路径 {i+1}/{len(valid_places)-1}：{start_place['name']} -> {end_place['name']}")
                            except Exception as e:
                                print(f"✗ 生成路径时出错 {i+1}/{len(valid_places)-1}：{start_place['name']} -> {end_place['name']}, 错误: {e}")
                    
                    print(f"第{day_plan['day']}天：有效地点 {len(valid_places)} 个，成功生成路径 {len(day_plan['routes'])} 条")
        
        return ItineraryPlanResponse(
            success=True,
            plan_data=plan_data
        )
        
    except json.JSONDecodeError as je:
        return ItineraryPlanResponse(
            success=False,
            error_message=f"解析AI返回的JSON数据失败: {str(je)}"
        )
    except ValueError as ve:
        return ItineraryPlanResponse(
            success=False,
            error_message=str(ve)
        )
    except Exception as e:
        return ItineraryPlanResponse(
            success=False,
            error_message=f"服务器内部错误: {str(e)}"
        )

# 新增：为行程地点生成路径规划API
@app.post("/api/trip/routes", response_model=ItineraryRouteResponse)
async def generate_itinerary_routes(request: ItineraryRouteRequest):
    """为行程中的地点列表生成相邻地点间的路径规划"""
    try:
        if not request.places or len(request.places) < 2:
            return ItineraryRouteResponse(
                success=False,
                error_message="至少需要2个地点才能生成路径规划"
            )
        
        routes = []
        mode = request.mode or "driving"
        
        # 验证所有地点的坐标有效性
        valid_places = []
        for place in request.places:
            if not all(key in place for key in ["name", "longitude", "latitude"]):
                continue
            
            try:
                lng = float(place["longitude"])
                lat = float(place["latitude"])
                
                # 检查坐标范围
                if (-180 <= lng <= 180 and -90 <= lat <= 90):
                    valid_places.append({
                        "name": place["name"],
                        "longitude": lng,
                        "latitude": lat
                    })
                else:
                    print(f"警告：地点 '{place['name']}' 坐标超出有效范围: ({lng}, {lat})")
            except (ValueError, TypeError):
                print(f"警告：地点 '{place['name']}' 坐标格式错误")
                continue
        
        if len(valid_places) < 2:
            return ItineraryRouteResponse(
                success=False,
                error_message="没有足够的有效地点生成路径规划"
            )
        
        # 为相邻地点生成路径规划
        for i in range(len(valid_places) - 1):
            start_place = valid_places[i]
            end_place = valid_places[i + 1]
            
            try:
                route_data = get_route_planning(
                    (start_place["longitude"], start_place["latitude"]),
                    (end_place["longitude"], end_place["latitude"]),
                    mode
                )
                
                if route_data and route_data.get("status") == "1":
                    # 构建路径数据，与手动路径规划保持一致的数据结构
                    route_info = {
                        "start_point": {
                            "name": start_place["name"],
                            "longitude": start_place["longitude"],
                            "latitude": start_place["latitude"]
                        },
                        "end_point": {
                            "name": end_place["name"],
                            "longitude": end_place["longitude"],
                            "latitude": end_place["latitude"]
                        },
                        "mode": mode,
                        "route_info": route_data.get("route", {}),
                        "raw_data": route_data,
                        "sequence": i + 1
                    }
                    routes.append(route_info)
                    print(f"成功生成路径：{start_place['name']} -> {end_place['name']}")
                else:
                    print(f"无法生成路径：{start_place['name']} -> {end_place['name']}")
                    # 即使某段路径失败，也继续处理其他路径
                    
            except Exception as e:
                print(f"生成路径时出错：{start_place['name']} -> {end_place['name']}, 错误: {e}")
                continue
        
        return ItineraryRouteResponse(
            success=True,
            routes_data=routes
        )
        
    except Exception as e:
        return ItineraryRouteResponse(
            success=False,
            error_message=f"服务器内部错误: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
