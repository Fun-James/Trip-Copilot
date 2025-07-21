from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, SecretStr
from geopy.distance import geodesic
from typing import Optional, List
from datetime import datetime
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

# 从地点名称中提取城市信息
def extract_city_from_location(location: str):
    """从地点名称中提取城市信息"""
    # 常见城市列表
    major_cities = [
        "北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "西安", 
        "重庆", "武汉", "天津", "苏州", "青岛", "长沙", "大连", "厦门",
        "福州", "哈尔滨", "济南", "昆明", "沈阳", "石家庄", "合肥", 
        "郑州", "太原", "南昌", "贵阳", "南宁", "海口", "兰州", "银川",
        "西宁", "乌鲁木齐", "拉萨", "呼和浩特"
    ]
    
    # 先检查是否直接包含城市名
    for city in major_cities:
        if city in location:
            return city
    
    # 如果没有找到，尝试从大学名称等推断
    if "南开大学" in location:
        return "天津"
    elif "清华大学" in location or "北京大学" in location:
        return "北京"
    elif "复旦大学" in location or "上海交通大学" in location:
        return "上海"
    
    # 默认返回全国
    return "全国"

# POI搜索获取地点坐标
def get_location_coordinates_poi(location: str, city: Optional[str] = None):
    """通过POI搜索获取旅游景点的精确坐标"""
    try:
        # 添加延迟避免QPS限制（免费版3次/秒）
        time.sleep(0.4)  # 等待400ms
        
        api_key = get_amap_api_key()
        url = f"https://restapi.amap.com/v3/place/text"
        
        # 旅游景点相关的POI类型代码
        # 110000: 旅游景点类
        # 120000: 体育休闲服务类 
        # 130000: 文化场馆类
        # 140000: 风景名胜
        # 150000: 商务住宅
        # 160000: 政府机构及社会团体
        # 170000: 科教文化服务
        # 180000: 交通设施服务
        poi_types = "110000|130000|140000|170000"
        
        # 构建POI搜索参数
        params = {
            "key": api_key,
            "keywords": location,
            "types": poi_types,
            "extensions": "all",
            "page": 1,
            "size": 5  # 获取前5个结果进行筛选
        }
        
        # 如果提供了城市信息，添加城市限定
        if city:
            params["city"] = city
            
        response = requests.get(url, params=params)
        data = response.json()
        
        if data["status"] == "1" and data["pois"]:
            # 尝试找到最匹配的POI
            best_poi = None
            
            for poi in data["pois"]:
                poi_name = poi.get("name", "")
                poi_type = poi.get("type", "")
                
                # 优先选择名称匹配度高的景点
                if location in poi_name or poi_name in location:
                    best_poi = poi
                    break
            
            # 如果没有找到匹配的，使用第一个结果
            if not best_poi:
                best_poi = data["pois"][0]
            
            location_str = best_poi["location"]
            longitude_str, latitude_str = location_str.split(",")
            longitude = float(longitude_str)
            latitude = float(latitude_str)
            
            # 打印POI信息用于调试
            poi_info = {
                "name": best_poi.get("name", "Unknown"),
                "type": best_poi.get("type", "Unknown"),
                "address": best_poi.get("address", ""),
                "coords": f"({longitude}, {latitude})"
            }
            print(f"POI搜索成功: {location} -> {poi_info}")
            return longitude, latitude
        else:
            print(f"POI搜索无结果: {location}")
            return None, None
    except Exception as e:
        print(f"POI搜索失败: {e}")
        return None, None

# 地理编码获取地点坐标（备用方法）
def get_location_coordinates_geocode(location: str, city: Optional[str] = None):
    """通过地理编码获取地点坐标（备用方法）"""
    try:
        # 添加延迟避免QPS限制（免费版3次/秒）
        time.sleep(0.4)  # 等待400ms
        
        api_key = get_amap_api_key()
        url = f"https://restapi.amap.com/v3/geocode/geo"
        
        # 构建搜索参数
        params = {
            "key": api_key,
            "address": location
        }
        
        # 如果提供了城市信息，添加城市限定
        if city:
            params["city"] = city
            
        response = requests.get(url, params=params)
        data = response.json()
        
        if data["status"] == "1" and data["geocodes"]:
            location_str = data["geocodes"][0]["location"]
            longitude_str, latitude_str = location_str.split(",")
            longitude = float(longitude_str)
            latitude = float(latitude_str)
            print(f"地理编码成功: {location} -> ({longitude}, {latitude})")
            return longitude, latitude
        else:
            print(f"地理编码无结果: {location}")
            return None, None
    except Exception as e:
        print(f"地理编码失败: {e}")
        return None, None

# 获取地点坐标（优化版本：POI优先 + 地理编码备用）
def get_location_coordinates(location: str, city: Optional[str] = None):
    """通过地点名称获取经纬度坐标（POI搜索优先，地理编码备用）"""
    # 第一步：尝试POI搜索（适合旅游景点）
    lng, lat = get_location_coordinates_poi(location, city)
    
    if lng is not None and lat is not None:
        return lng, lat
    
    # 第二步：如果POI搜索失败，使用地理编码备用
    print(f"POI搜索失败，尝试地理编码: {location}")
    lng, lat = get_location_coordinates_geocode(location, city)
    
    if lng is not None and lat is not None:
        return lng, lat
    
    # 都失败了
    print(f"所有搜索方法都失败: {location}")
    return None, None

# 获取路径规划
def get_route_planning(start_coords: tuple, end_coords: tuple, mode: str = "driving", start_location: str = "", end_location: str = ""):
    """获取两点间的路径规划"""
    try:
        # 添加延迟避免QPS限制（免费版3次/秒）
        time.sleep(0.4)  # 等待400ms
        
        api_key = get_amap_api_key()
        origin = f"{start_coords[0]},{start_coords[1]}"
        destination = f"{end_coords[0]},{end_coords[1]}"
        
        # 根据出行方式选择不同的API端点
        if mode == "transit":
            # 公交路径规划使用不同的API
            url = "https://restapi.amap.com/v3/direction/transit/integrated"
            
            # 尝试从地点名称中提取城市
            start_city = extract_city_from_location(start_location)
            end_city = extract_city_from_location(end_location)
            
            # 如果起点和终点在同一个城市，使用该城市；否则使用全国
            if start_city != "全国" and end_city != "全国" and start_city == end_city:
                city = start_city
            elif start_city != "全国":
                city = start_city
            elif end_city != "全国":
                city = end_city
            else:
                city = "全国"
            
            params = {
                "key": api_key,
                "origin": origin,
                "destination": destination,
                "city": city,  # 使用智能提取的城市
                "cityd": city  # 目的地城市，公交通常在同一城市内
            }
        elif mode == "bicycling": 
            # 骑行路径规划使用新的API
            url = "https://restapi.amap.com/v4/direction/bicycling"
            params = {
                "key": api_key,
                "origin": origin,
                "destination": destination
            }
            
        else:
            # 驾车和步行使用原来的API
            url = f"https://restapi.amap.com/v3/direction/{mode}"
            params = {
                "key": api_key,
                "origin": origin,
                "destination": destination
            }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        # 打印调试信息
        print(f"路径规划请求: {mode}, URL: {url}")
        if mode == "transit":
            print(f"使用城市: {params['city']}")
        print(f"响应状态: {data.get('status')}, 信息: {data.get('info')}")
        
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
            mode,
            request.start,  # 传递起点名称
            request.end     # 传递终点名称
        )
        
        # 针对不同交通方式检查响应状态
        is_success = False
        if mode == "bicycling":
            is_success = route_data and route_data.get("errcode") == 0
        else:
            is_success = route_data and route_data.get("status") == "1"
            
        if not is_success:
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
            "raw_data": route_data  # 完整的原始数据，供前端使用
        }
        
        # 根据不同交通方式提取路径信息
        if mode == "bicycling":
            processed_data["route_info"] = route_data.get("data", {})
        else:
            processed_data["route_info"] = route_data.get("route", {})
        
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
        
        # 构建增强的系统提示词，包含地图和行程规划功能描述
        system_prompt = """你是一位专业友好的旅行助手，名叫Trip Copilot。你可以：
1. 为用户提供旅行建议和规划
2. 回答关于目的地的问题
3. 推荐景点、美食、住宿等
4. 帮助估算旅行费用
5. 解释地图上的标记和路径规划
6. 基于当前行程规划提供建议和修改意见
7. 解答关于具体景点位置和交通方式的问题

重要提示：
- 如果用户提到地图、路径、行程或具体景点，请结合提供的背景信息回答
- 如果背景信息中包含行程规划数据，你可以参考这些信息来回答用户问题
- 如果用户询问路径或交通，你可以基于已规划的路线给出建议
- 请用友好、专业的语气回复用户。"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=request.message)
        ]
        
        # 增强的上下文处理：解析结构化的背景信息
        if request.context:
            try:
                # 尝试解析上下文为JSON，如果失败则当作普通文本处理
                import json
                context_data = json.loads(request.context)
                
                # 构建结构化的上下文描述
                context_parts = []
                
                # 处理行程规划数据
                if "currentPlan" in context_data and context_data["currentPlan"]:
                    plan = context_data["currentPlan"]
                    context_parts.append(f"当前行程规划：{plan.get('destination', '未知目的地')}{plan.get('total_days', 'N')}日游")
                    
                    if "itinerary" in plan:
                        context_parts.append("详细安排：")
                        for day_plan in plan["itinerary"]:
                            day_places = [place["name"] for place in day_plan.get("places", [])]
                            context_parts.append(f"第{day_plan['day']}天（{day_plan.get('theme', '主题未定')}）：{' -> '.join(day_places)}")
                
                # 处理路径规划数据
                if "currentRoute" in context_data and context_data["currentRoute"]:
                    route = context_data["currentRoute"]
                    start_name = route.get("start_point", {}).get("name", "起点")
                    end_name = route.get("end_point", {}).get("name", "终点")
                    mode = route.get("mode", "driving")
                    mode_text = {"driving": "驾车", "walking": "步行", "transit": "公交"}.get(mode, mode)
                    context_parts.append(f"当前路径规划：{start_name} → {end_name}（{mode_text}）")
                
                # 处理地图中心和选中天数
                if "selectedDay" in context_data:
                    context_parts.append(f"当前查看：第{context_data['selectedDay']}天的行程")
                
                if context_parts:
                    enhanced_context = "当前状态：\n" + "\n".join(context_parts)
                    messages.append(HumanMessage(content=f"背景信息：{enhanced_context}"))
                else:
                    # 如果没有结构化数据，使用原始上下文
                    messages.append(HumanMessage(content=f"背景信息：{request.context}"))
                    
            except (json.JSONDecodeError, KeyError):
                # 如果不是JSON格式或解析失败，当作普通文本处理
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
        
        # 首先尝试POI搜索获取更精确的景点信息
        poi_url = f"https://restapi.amap.com/v3/place/text"
        poi_params = {
            "key": api_key,
            "keywords": request.location,
            "types": "110000|130000|140000|170000",
            "extensions": "all",
            "size": 1
        }
        
        poi_response = requests.get(poi_url, params=poi_params)
        poi_data = poi_response.json()
        
        if poi_data["status"] == "1" and poi_data["pois"]:
            # 使用POI搜索结果
            poi = poi_data["pois"][0]
            location_coords = poi["location"].split(",")
            
            location_data = {
                "name": request.location,
                "poi_name": poi.get("name", ""),
                "formatted_address": poi.get("address", ""),
                "province": poi.get("pname", ""),
                "city": poi.get("cityname", ""),
                "district": poi.get("adname", ""),
                "location": poi["location"],
                "longitude": float(location_coords[0]),
                "latitude": float(location_coords[1]),
                "type": poi.get("type", ""),
                "tel": poi.get("tel", ""),
                "business_area": poi.get("business_area", ""),
                "source": "POI"
            }
            
            return LocationResponse(
                success=True,
                location_data=location_data
            )
        
        # 如果POI搜索失败，fallback到地理编码
        geo_url = f"https://restapi.amap.com/v3/geocode/geo"
        geo_params = {
            "key": api_key,
            "address": request.location
        }
        
        geo_response = requests.get(geo_url, params=geo_params)
        geo_data = geo_response.json()
        
        if geo_data["status"] == "1" and geo_data["geocodes"]:
            geocode = geo_data["geocodes"][0]
            location_data = {
                "name": request.location,
                "formatted_address": geocode.get("formatted_address", ""),
                "province": geocode.get("province", ""),
                "city": geocode.get("city", ""),
                "district": geocode.get("district", ""),
                "location": geocode.get("location", ""),
                "longitude": float(geocode.get("location", "0,0").split(",")[0]),
                "latitude": float(geocode.get("location", "0,0").split(",")[1]),
                "level": geocode.get("level", ""),
                "source": "Geocode"
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

def get_transportation_text(mode):
    """获取交通方式的友好文本"""
    mode_map = {
        'driving': '驾车',
        'walking': '步行',
        'transit': '公交',
        'bicycling': '骑行'
    }
    return mode_map.get(mode, mode)

def get_transit_time(start_lng, start_lat, end_lng, end_lat, mode="driving"):
    """使用高德地图API计算两点间的实际交通时间，并提取换乘路线"""
    try:
        time.sleep(0.4)
        api_key = get_amap_api_key()
        origin = f"{start_lng},{start_lat}"
        destination = f"{end_lng},{end_lat}"
        
        # 公交路径规划
        if mode == "transit":
            url = "https://restapi.amap.com/v3/direction/transit/integrated"
            
            # 提取城市信息
            start_city = extract_city_from_coords(start_lng, start_lat)
            end_city = extract_city_from_coords(end_lng, end_lat)
            
            # 使用智能提取的城市
            city = start_city if start_city != "全国" else (end_city if end_city != "全国" else "全国")
            
            params = {
                "key": api_key,
                "origin": origin,
                "destination": destination,
                "city": city,
                "cityd": city,
                "extensions": "all"  # 获取详细信息
            }
        else:  # 其他交通方式
            if mode == "walking":
                url = "https://restapi.amap.com/v3/direction/walking"
            elif mode == "bicycling":  
                url = "https://restapi.amap.com/v4/direction/bicycling"
            else:  # 默认为驾车
                url = "https://restapi.amap.com/v3/direction/driving"
                
            params = {
                "key": api_key,
                "origin": origin,
                "destination": destination
            }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        # 处理响应获取交通时间和换乘路线
        time_str = "交通时间未知"
        route_steps = []
        
        # 检查是否成功 - 骑行模式使用errcode:0，其他模式使用status:"1"
        is_success = False
        if mode == "bicycling":
            is_success = data.get("errcode") == 0
        else:
            is_success = data.get("status") == "1"
            
        if is_success:
            # 公交方式 - 提取换乘路线
            if mode == "transit" and data.get("route") and data["route"].get("transits"):
                transit = data["route"]["transits"][0]
                duration = int(transit["duration"])  # 秒
                
                # 提取换乘路线
                for segment in transit.get("segments", []):
                    if segment.get("bus"):
                        buslines = segment["bus"].get("buslines", [])
                        if buslines:
                            route_steps.append(buslines[0].get("name", "公交"))
                    elif segment.get("railway"):
                        railways = segment["railway"].get("lines", [])
                        if railways:
                            route_steps.append(railways[0].get("name", "地铁"))
            
            # 骑行方式 - 特殊处理骑行API的返回格式
            elif mode == "bicycling" and data.get("data") and data["data"].get("paths"):
                path = data["data"]["paths"][0]
                duration = int(path["duration"])  # 秒
            
            # 步行方式
            elif mode == "walking" and data.get("route") and data["route"].get("paths"):
                path = data["route"]["paths"][0]
                duration = int(path["duration"])  # 秒
                
            # 驾车方式
            elif data.get("route") and data["route"].get("paths"):
                path = data["route"]["paths"][0]
                duration = int(path["duration"])  # 秒
            
            # 如果成功获取到了时间
            if 'duration' in locals():
                # 转换为更友好的格式
                minutes = duration // 60
                if minutes < 60:
                    time_str = f"{minutes}分钟"
                else:
                    hours = minutes // 60
                    remaining_minutes = minutes % 60
                    if remaining_minutes > 0:
                        time_str = f"{hours}小时{remaining_minutes}分钟"
                    else:
                        time_str = f"{hours}小时"
        
        # 对于公交方式，返回时间和换乘路线
        if mode == "transit":
            return {
                "time": time_str,
                "steps": "->".join(route_steps) if route_steps else "公交"
            }
        return {
            "time": time_str,
            "steps": get_transportation_text(mode)
        }
            
    except Exception as e:
        print(f"计算交通时间失败: {str(e)}")
        return {
            "time": "交通时间未知",
            "steps": get_transportation_text(mode)
        }

# 新增辅助函数：从坐标提取城市
def extract_city_from_coords(lng, lat):
    """从坐标反查所在城市"""
    try:
        time.sleep(0.4)
        api_key = get_amap_api_key()
        url = "https://restapi.amap.com/v3/geocode/regeo"
        
        params = {
            "key": api_key,
            "location": f"{lng},{lat}",
            "extensions": "base"
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data["status"] == "1" and data.get("regeocode"):
            address_component = data["regeocode"]["addressComponent"]
            city = address_component.get("city")
            if not city:
                city = address_component.get("province")
            return city if city else "全国"
        return "全国"
    except Exception as e:
        print(f"坐标反查城市失败: {e}")
        return "全国"

def recommend_transportation(start_lng, start_lat, end_lng, end_lat, distance_km):
    """根据距离和地点特性推荐交通方式"""
    # 检查起点和终点附近是否有公交/地铁站
    start_has_transit = has_nearby_transit_station(start_lng, start_lat)
    end_has_transit = has_nearby_transit_station(end_lng, end_lat)
    
    # 默认推荐的交通方式
    default_mode = "driving"  # 默认驾车

    # 根据条件推荐
    if start_has_transit and end_has_transit and distance_km > 1:
        default_mode = "transit"
    elif distance_km < 1:  # 1公里以内步行
        default_mode = "walking"
    elif distance_km < 5:  # 1-5公里骑行
        default_mode = "bicycling"
    
    # 可选交通方式：根据距离和位置特性确定
    available_modes = []
    
    # 驾车总是可用
    available_modes.append("driving")
    
    # 公交：需要两端都有车站
    if start_has_transit and end_has_transit:
        available_modes.append("transit")
    
    # 步行：短距离可用
    if distance_km < 5:
        available_modes.append("walking")
    
    # 骑行：中短距离可用
    if distance_km < 10:
        available_modes.append("bicycling")
    
    return {
        "default_mode": default_mode,
        "available_modes": available_modes
    }

def extract_hours_minutes(time_str):
    """
    从字符串中提取小时和分钟
    
    参数:
        time_str (str): 包含时间的字符串，如 "1小时24分钟" 或 "24分钟"
    
    返回:
        tuple: (小时, 分钟)，例如 "1小时24分钟" -> (1, 24)，"24分钟" -> (0, 24)
    """
    # 初始化小时和分钟为 0
    hours = 0
    minutes = 0
    
    # 用正则表达式匹配小时和分钟
    hours_match = re.search(r'(\d+)小时', time_str)
    minutes_match = re.search(r'(\d+)分钟', time_str)
    
    if hours_match:
        hours = int(hours_match.group(1))
    if minutes_match:
        minutes = int(minutes_match.group(1))
    
    return (hours, minutes)

# 新增函数：检查地点附近是否有公交/地铁站
def has_nearby_transit_station(lng, lat, radius=500):
    """检查指定坐标附近是否有公交或地铁站"""
    try:
        time.sleep(0.4)  # 避免QPS限制
        api_key = get_amap_api_key()
        url = "https://restapi.amap.com/v3/place/around"
        
        params = {
            "key": api_key,
            "location": f"{lng},{lat}",
            "radius": radius,
            "types": "150500|150700",  # 公交站|地铁站
            "offset": 1  # 只需要一个结果即可
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data["status"] == "1" and data.get("pois") and len(data["pois"]) > 0:
            return True
        return False
    except Exception as e:
        print(f"检查附近交通站点失败: {e}")
        return False

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
        4. 每个地点按照省市+具体地点名称的形式输出，不要包含区县名称，例如"四川省成都市武侯祠"而不是"四川省成都市武侯区武侯祠"
        5. 为每个地点添加详细介绍
        6. 为每个地点添加建议停留时间（小时）

        
        返回格式示例：
        {{
          "destination": "{request.destination}",
          "total_days": {request.duration},
          "itinerary": [
            {{
              "day": 1,
              "theme": "第一天主题描述",
              "places": [
                {{ "name": "具体地点名称1",
              "description": "地点详细描述",
              "duration": 2.5
              }},
                {{ "name": "具体地点名称2",
              "description": "地点详细描述",
              "duration": 2.0 
              }},
                {{ "name": "具体地点名称3",
              "description": "地点详细描述",
              "duration": 1.5 
              }}
              ]
            }},
            {{
              "day": 2,
              "theme": "第二天主题描述",
              "places": [
                {{ "name": "具体地点名称4",
              "description": "地点详细描述",
              "duration": 2.5,
              }},
                {{ "name": "具体地点名称5",
              "description": "地点详细描述",
              "duration": 2.0  
              }},
                {{ "name": "具体地点名称6",
              "description": "地点详细描述",
              "duration": 1.5
              }}
              ]
            }}
          ]
        }}
        
        注意：
        - 只返回JSON格式，不要其他任何文字
        - 地点名称要具体准确，便于地图定位，格式为"省市+景点名称"
        - 不要包含区县信息，避免定位错误
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
                            # 尝试从地点名称中提取城市信息
                            place_name = place["name"]
                            city_info = None
                            
                            # 从目的地中提取城市信息
                            if request.destination:
                                # 简单提取：如果目的地包含"市"，则提取城市部分
                                if "市" in request.destination:
                                    city_parts = request.destination.split("市")
                                    if len(city_parts) > 0:
                                        city_info = city_parts[0] + "市"
                                elif "省" in request.destination and len(request.destination) > 2:
                                    # 如果是省份，提取省份信息
                                    city_info = request.destination
                            
                            lng, lat = get_location_coordinates(place_name, city_info)
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
        
        # 在生成行程后添加交通时间计算
        if "itinerary" in plan_data:
            for day_plan in plan_data["itinerary"]:
                if "places" in day_plan:
                    # 计算直线距离并推荐交通方式
                    valid_places = [p for p in day_plan["places"] if "longitude" in p and "latitude" in p]
                    
                    if len(valid_places) >= 2:
                        for i in range(len(valid_places) - 1):
                            start = valid_places[i]
                            end = valid_places[i + 1]
                            
                            # 计算直线距离（公里）
                            distance_km = geodesic(
                                (start["latitude"], start["longitude"]),
                                (end["latitude"], end["longitude"])
                            ).kilometers
                            
                            # 获取交通方式信息
                            transportation_info = recommend_transportation(
                                start["longitude"], start["latitude"],
                                end["longitude"], end["latitude"],
                                distance_km
                            )
                            
                            # 更新到起点地点
                            start["transportation"] = transportation_info["default_mode"]
                            start["available_transportations"] = transportation_info["available_modes"]

                            # 计算交通时间和路线
                            transit_info = get_transit_time(
                                start["longitude"], start["latitude"],
                                end["longitude"], end["latitude"],
                                mode=start["transportation"]
                            )

                            start["transition_time"] = transit_info["time"]
                            start["route_steps"] = transit_info["steps"]

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

# 新增交通方式切换API
@app.post("/api/trip/transportation")
async def get_transportation_info(request: dict):
    """根据起终点和交通方式获取交通信息"""
    try:
        start = request.get("start")
        end = request.get("end")
        mode = request.get("mode", "driving")
        
        if not start or not end:
            return {"error": "缺少起终点信息"}
        
        # 获取交通信息
        transit_info = get_transit_time(
            start["longitude"], start["latitude"],
            end["longitude"], end["latitude"],
            mode=mode
        )
        
        return {
            "time": transit_info["time"],
            "steps": transit_info["steps"]
        }
        
    except Exception as e:
        return {"error": f"获取交通信息失败: {str(e)}"}

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

# 获取天气预报
@app.get("/api/weather/{location}")
async def get_weather(location: str):
    """获取指定地点的天气预报"""
    try:
        api_key = get_amap_api_key()
        
        # 先通过地理编码获取城市编码
        geocode_url = "https://restapi.amap.com/v3/geocode/geo"
        params = {
            "key": api_key,
            "address": location
        }
        
        response = requests.get(geocode_url, params=params)
        geocode_data = response.json()
        
        if geocode_data["status"] != "1" or not geocode_data["geocodes"]:
            return {
                "success": False,
                "error": f"无法找到{location}的地理位置信息"
            }
        
        # 获取城市编码
        adcode = geocode_data["geocodes"][0]["adcode"]
        
        # 获取天气预报
        weather_url = "https://restapi.amap.com/v3/weather/weatherInfo"
        params = {
            "key": api_key,
            "city": adcode,
            "extensions": "all"  # 获取预报天气
        }
        
        response = requests.get(weather_url, params=params)
        data = response.json()
        
        if data["status"] != "1" or "forecasts" not in data or not data["forecasts"]:
            return {
                "success": False,
                "error": f"获取{location}的天气信息失败"
            }
        
        # 处理天气数据
        forecasts = []
        weather_data = data["forecasts"][0]["casts"]
        today = datetime.now().date()
        
        for day in weather_data:
            forecast_date = datetime.strptime(day["date"], "%Y-%m-%d").date()
            date_diff = (forecast_date - today).days
            
            if date_diff == 0:
                display_date = "今天"
            elif date_diff == 1:
                display_date = "明天"
            elif date_diff == 2:
                display_date = "后天"
            else:
                display_date = day["date"][5:]  # 只显示月-日
            
            forecast = {
                "date": display_date,
                "tempHigh": int(day["daytemp"]),
                "tempLow": int(day["nighttemp"]),
                "description": day["dayweather"],
                "daywind": day["daywind"],
                "nightwind": day["nightwind"],
                "daypower": day["daypower"],
                "nightpower": day["nightpower"]
            }
            forecasts.append(forecast)
        
        return {
            "success": True,
            "location": location,
            "forecasts": forecasts[:3]  # 只返回未来3天的预报
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"获取天气信息时发生错误: {str(e)}"
        }
    
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
