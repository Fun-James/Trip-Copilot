from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, SecretStr
from geopy.distance import geodesic
from typing import Optional, List
from datetime import datetime
import uvicorn
import os
import time
import re
import json
import hashlib
from functools import lru_cache
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
# 注释：删除了未使用的 TripRequest 和 TripResponse 模型（用于 /api/trip/suggest）

# 新增行程规划数据模型
class ItineraryPlanRequest(BaseModel):
    destination: str
    duration: int  # 天数，必填

class FinePlanRequest(BaseModel):
    plan: str
    destination: str
    duration: int

class ItineraryPlanResponse(BaseModel):
    success: bool
    plan_data: Optional[dict] = None
    error_message: Optional[str] = None

# 新增行程更新数据模型
class ItineraryUpdateRequest(BaseModel):
    current_plan: dict  # 前端传递的当前完整行程规划JSON
    modification_request: str  # 用户的修改指令，例如 "帮我把第一天的故宫去掉，换成颐和园"
    chat_context: Optional[str] = None  # 可选的聊天上下文

class ItineraryUpdateResponse(BaseModel):
    success: bool
    updated_plan: Optional[dict] = None
    error_message: Optional[str] = None

# 智能解析用户旅行请求的数据模型
class QueryParseRequest(BaseModel):
    query: str
    current_plan: Optional[dict] = None  # 当前行程计划，用于判断是否是修改行程的意图

class QueryParseResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error_message: Optional[str] = None
    estimated_cost: Optional[float] = None

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None

# 注释：删除了未使用的 ChatResponse 模型（用于非流式聊天）

class PathRequest(BaseModel):
    start: str
    end: str
    mode: Optional[str] = "driving"  # driving, walking, transit

class PathResponse(BaseModel):
    success: bool
    path_data: Optional[dict] = None
    error_message: Optional[str] = None

# 注释：删除了未使用的 LocationRequest 和 LocationResponse 模型（用于 /api/location/info）

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
# 注释：此API端点未被前端使用，已删除
# @app.post("/api/trip/suggest", response_model=TripResponse)

# 快速意图识别引擎（规则引擎）
def quick_intent_detection(query: str, current_plan: dict = None) -> dict:
    """
    使用规则引擎快速判断用户意图，避免每次都调用大模型
    返回格式: {"confident": bool, "result": dict}
    """
    query_lower = query.lower().strip()
    
    # 高置信度模式匹配
    
    # 1. 明确的新行程规划请求
    new_plan_patterns = [
        r'(我想|我要|帮我)(去|到)(.+?)(玩|旅游|旅行)(\d+)天',
        r'(规划|安排|制定)(.+?)(\d+)天(的)?(行程|旅行)',
        r'去(.+?)(\d+)天(的)?(行程|计划|旅游)',
        r'(我想|想要|想去)(.+?)(玩|旅游|游玩)(\d+)天',
        r'(\d+)天(.+?)(行程|旅游|旅行|游玩)',
        r'(想|要)去(.+?)(玩|旅游|旅行|游览)(\d+)天?',
        r'去(.+?)(\d+)天(旅游|游玩|玩)',  # 新增：去杭州3天旅游
        r'到(.+?)(\d+)天(的)?(旅游|旅行|游玩)'
    ]
    
    for pattern in new_plan_patterns:
        match = re.search(pattern, query)
        if match:
            # 提取目的地和天数
            destination = ""
            duration = 3
            
            if '玩' in query or '旅游' in query or '旅行' in query:
                # 尝试提取目的地和天数
                dest_match = re.search(r'(去|到)(.+?)(玩|旅游|旅行)', query)
                if dest_match:
                    destination = dest_match.group(2).strip()
                
                day_match = re.search(r'(\d+)天', query)
                if day_match:
                    duration = int(day_match.group(1))
            
            return {
                "confident": True,
                "result": {
                    "is_plan": True,
                    "is_modification": False,
                    "destination": destination,
                    "duration": duration,
                    "start_point": None,
                    "intent_confidence": 0.9,
                    "intent_type": "new_plan",
                    "needs_confirmation": False
                }
            }
    
    # 2. 明确的行程修改请求（仅在有当前行程时）
    if current_plan and current_plan.get("itinerary"):
        modification_patterns = [
            r'(修改|更改|调整|变更)(第\d+天|行程)',
            r'(删除|去掉|移除|取消)(.+?)',
            r'(添加|增加|加上|新增)(.+?)',
            r'把(.+?)(换成|替换为|改为)(.+?)',
            r'(第\d+天)(不去|改成|换成)(.+?)',
            r'(重新)(规划|安排)(行程|第\d+天)'
        ]
        
        # 提取当前行程中的景点名称
        attraction_names = []
        if isinstance(current_plan.get("itinerary"), list):
            for day in current_plan["itinerary"]:
                if isinstance(day.get("places"), list):
                    for place in day["places"]:
                        if place.get("name"):
                            attraction_names.append(place["name"])
        
        for pattern in modification_patterns:
            if re.search(pattern, query):
                return {
                    "confident": True,
                    "result": {
                        "is_plan": False,
                        "is_modification": True,
                        "destination": None,
                        "duration": current_plan.get("total_days", 3),
                        "start_point": None,
                        "intent_confidence": 0.9,
                        "intent_type": "modify",
                        "needs_confirmation": False
                    }
                }
        
        # 检查是否提到了当前行程中的景点
        mentioned_attractions = [name for name in attraction_names if name in query]
        if mentioned_attractions and any(word in query_lower for word in ['修改', '调整', '换', '改', '删除', '去掉']):
            return {
                "confident": True,
                "result": {
                    "is_plan": False,
                    "is_modification": True,
                    "destination": None,
                    "duration": current_plan.get("total_days", 3),
                    "start_point": None,
                    "intent_confidence": 0.85,
                    "intent_type": "modify",
                    "needs_confirmation": False
                }
            }
    
    # 3. 明确的信息查询/聊天请求
    chat_patterns = [
        r'^(你好|hello|hi)$',
        r'(什么是|介绍一下|告诉我)(.+?)',
        r'(.+?)(有什么|怎么样|好玩吗|特色|著名)',
        r'^(请问|能告诉我|我想知道|想了解)',
        r'(推荐|建议)(一些|几个)?(.+?)',
        r'(谢谢|感谢|不用了|算了|再见)'
    ]
    
    for pattern in chat_patterns:
        if re.search(pattern, query):
            return {
                "confident": True,
                "result": {
                    "is_plan": False,
                    "is_modification": False,
                    "destination": None,
                    "duration": 3,
                    "start_point": None,
                    "intent_confidence": 0.9,
                    "intent_type": "chat",
                    "needs_confirmation": False
                }
            }
    
    # 4. 不确定的情况
    return {"confident": False, "result": None}

# 缓存大模型结果
@lru_cache(maxsize=100)
def cached_llm_intent_detection(query_hash: str, current_plan_hash: str) -> dict:
    """
    缓存的大模型意图检测，使用哈希值作为键
    """
    # 这个函数的实际实现在下面的 parse_query_with_llm 中
    pass

@app.post("/api/trip/parse-query", response_model=QueryParseResponse)
async def parse_query_with_llm(request: QueryParseRequest):
    """
    使用混合策略解析用户查询：优先使用快速规则引擎，复杂情况才使用大模型
    """
    try:
        # 1. 首先尝试快速规则引擎
        quick_result = quick_intent_detection(request.query, request.current_plan)
        
        if quick_result["confident"]:
            # 规则引擎有信心，直接返回结果
            print(f"[快速识别] 查询: {request.query[:50]}... -> {quick_result['result']['intent_type']}")
            return QueryParseResponse(success=True, data=quick_result["result"])
        
        # 2. 规则引擎不确定，使用大模型（但简化输入）
        print(f"[大模型识别] 查询: {request.query[:50]}...")
        
        # 生成缓存键
        query_hash = hashlib.md5(request.query.encode()).hexdigest()
        plan_hash = "none"
        if request.current_plan:
            # 只使用行程的关键信息生成哈希，而不是完整数据
            plan_summary = {
                "destination": request.current_plan.get("destination", ""),
                "total_days": request.current_plan.get("total_days", 0),
                "attraction_names": []
            }
            if request.current_plan.get("itinerary"):
                for day in request.current_plan["itinerary"]:
                    if day.get("places"):
                        for place in day["places"]:
                            if place.get("name"):
                                plan_summary["attraction_names"].append(place["name"])
            plan_hash = hashlib.md5(json.dumps(plan_summary, sort_keys=True).encode()).hexdigest()
        
        cache_key = f"{query_hash}_{plan_hash}"
        
        # 3. 简化的大模型调用
        llm = get_tongyi_client()

        # 构建简化的上下文（只包含景点名称，不包含完整行程数据）
        current_attractions = []
        if request.current_plan and request.current_plan.get("itinerary"):
            for day in request.current_plan["itinerary"]:
                if day.get("places"):
                    for place in day["places"]:
                        if place.get("name"):
                            current_attractions.append(place["name"])
        
        attractions_context = ""
        if current_attractions:
            attractions_context = f"用户当前行程包含的景点: {', '.join(current_attractions[:10])}"  # 最多10个景点

        # 大幅简化的提示词
        prompt = f"""分析用户查询并判断意图，返回JSON格式。

查询: "{request.query}"
{attractions_context}

判断规则:
- 新规划: 包含"去xxx玩x天"、"规划行程"等
- 修改行程: 包含"修改"、"调整"、"删除"、"添加"或提到当前景点名称
- 普通聊天: 询问信息、问候、推荐等

返回JSON (不要其他文字):
{{
  "is_plan": true/false,
  "is_modification": true/false,
  "destination": "目的地或null",
  "duration": 天数或3,
  "intent_confidence": 0到1的数字
}}"""

        messages = [
            SystemMessage(content="你是意图识别助手，只返回JSON，不要解释。"),
            HumanMessage(content=prompt)
        ]

        # 使用较短的超时时间
        response = llm.invoke(messages)

        ai_content = response.content
        if isinstance(ai_content, list):
            text_content = ""
            for item in ai_content:
                if isinstance(item, dict) and "text" in item:
                    text_content += item["text"]
                elif isinstance(item, str):
                    text_content += item
            ai_content = text_content

        # 提取JSON部分
        json_match = re.search(r'\{.*\}', str(ai_content), re.DOTALL)
        if not json_match:
            # 大模型解析失败，使用保守的默认值
            return QueryParseResponse(
                success=True, 
                data={
                    "is_plan": False,
                    "is_modification": False,
                    "destination": None,
                    "duration": 3,
                    "start_point": None,
                    "intent_confidence": 0.3,
                    "intent_type": "chat",
                    "needs_confirmation": True
                }
            )

        json_str = json_match.group()
        parsed_data = json.loads(json_str)

        # 标准化布尔值
        if isinstance(parsed_data.get("is_plan"), str):
            parsed_data["is_plan"] = parsed_data["is_plan"].lower() == "true"
        if isinstance(parsed_data.get("is_modification"), str):
            parsed_data["is_modification"] = parsed_data["is_modification"].lower() == "true"
            
        # 设置默认值
        if "duration" not in parsed_data or not isinstance(parsed_data["duration"], int):
            parsed_data["duration"] = 3
            
        if "intent_confidence" not in parsed_data:
            parsed_data["intent_confidence"] = 0.5
        
        # 设置意图类型
        if parsed_data.get("is_plan"):
            parsed_data["intent_type"] = "new_plan"
        elif parsed_data.get("is_modification"):
            parsed_data["intent_type"] = "modify"
        else:
            parsed_data["intent_type"] = "chat"
            
        # 置信度阈值
        confidence_threshold = 0.6  # 降低阈值，减少确认次数
        parsed_data["needs_confirmation"] = parsed_data.get("intent_confidence", 0) < confidence_threshold

        # 如果是新规划但没有目的地，降低置信度
        if parsed_data.get("is_plan") and not parsed_data.get("destination"):
            parsed_data["intent_confidence"] = 0.3
            parsed_data["needs_confirmation"] = True

        return QueryParseResponse(success=True, data=parsed_data)

    except Exception as e:
        print(f"[错误] 意图识别失败: {str(e)}")
        # 发生错误时返回保守的默认值
        return QueryParseResponse(
            success=True,  # 不返回错误，而是返回默认意图
            data={
                "is_plan": False,
                "is_modification": False,
                "destination": None,
                "duration": 3,
                "start_point": None,
                "intent_confidence": 0.2,
                "intent_type": "chat",
                "needs_confirmation": True
            }
        )

# 获取热门目的地（AI生成）
# 注释：此API端点未被前端使用，已删除
# @app.get("/api/destinations/popular")

# 获取高德地图API密钥
def get_amap_api_key():
    api_key = os.getenv("AMAP_API_KEY")
    if not api_key:
        raise ValueError("AMAP_API_KEY not found in environment variables")
    return api_key


# POI搜索获取地点坐标
def get_location_coordinates_poi(location: str, city: Optional[str] = None):
    """通过POI搜索获取旅游景点的精确坐标"""
    try:
        
          
        
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
        
          
        
        api_key = get_amap_api_key()
        origin = f"{start_coords[0]},{start_coords[1]}"
        destination = f"{end_coords[0]},{end_coords[1]}"
        
        # 根据出行方式选择不同的API端点
        if mode == "transit":
            # 公交路径规划使用不同的API
            url = "https://restapi.amap.com/v3/direction/transit/integrated"
            
            # 尝试从地点名称中提取城市
            start_city = extract_city_from_coords(start_coords[0], start_coords[1])
            end_city = extract_city_from_coords(end_coords[0], end_coords[1])
            
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
        if route_data is not None:
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

# 聊天API - 非流式版本
# 注释：此API端点未被前端使用，前端使用流式版本，已删除
# @app.post("/api/chat", response_model=ChatResponse)

# 新增：流式聊天API
@app.post("/api/chat/stream")
async def chat_with_ai_stream(request: ChatRequest):
    """流式聊天API，返回Server-Sent Events流"""
    
    def generate_response():
        try:
            # 获取通义千问客户端
            llm = get_tongyi_client()
            
            # 构建增强的系统提示词
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
            
            # 处理上下文信息
            if request.context:
                try:
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
            
            # 使用流式调用
            response = llm.stream(messages)
            
            # 流式返回响应内容
            for chunk in response:
                content = chunk.content
                if isinstance(content, list):
                    # 如果是列表格式，提取文本内容
                    text_content = ""
                    for item in content:
                        if isinstance(item, dict) and "text" in item:
                            text_content += item["text"]
                        elif isinstance(item, str):
                            text_content += item
                    content = text_content
                
                if content:
                    # 发送 SSE 数据
                    yield f"data: {json.dumps({'content': str(content), 'type': 'chunk'})}\n\n"
            
            # 发送结束标记
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
            
        except Exception as e:
            # 发送错误信息
            error_msg = f"抱歉，我遇到了一些技术问题。请稍后再试。错误信息：{str(e)}"
            yield f"data: {json.dumps({'content': error_msg, 'type': 'error'})}\n\n"
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

# 获取地点详细信息API
# 注释：此API端点未被前端使用，已删除
# @app.post("/api/location/info", response_model=LocationResponse)

# 辅助函数：精简行程数据，减少LLM的输入大小
def simplify_plan_for_llm(plan):
    """
    从行程计划中移除不必要的详细信息，以减少传递给LLM的数据量，避免超出最大输入长度限制
    """
    if not plan or not isinstance(plan, dict):
        return plan
    
    simplified_plan = {
        "destination": plan.get("destination", ""),
        "total_days": plan.get("total_days", 0),
        "itinerary": []
    }
    
    # 复制行程数据，但排除路线详情和原始响应数据
    if "itinerary" in plan and isinstance(plan["itinerary"], list):
        for day in plan["itinerary"]:
            simplified_day = {
                "day": day.get("day", 0),
                "theme": day.get("theme", ""),
                "places": []
            }
            
            # 只保留地点的基本信息
            if "places" in day and isinstance(day["places"], list):
                for place in day["places"]:
                    simplified_place = {
                        "name": place.get("name", ""),
                        "description": place.get("description", ""),
                        "duration": place.get("duration", 0)
                    }
                    # 可选保留坐标信息
                    if "longitude" in place and "latitude" in place:
                        simplified_place["longitude"] = place["longitude"]
                        simplified_place["latitude"] = place["latitude"]
                    
                    # 不包含交通详情、路线步骤等信息
                    simplified_day["places"].append(simplified_place)
            
            # 完全移除路线数据
            if "routes" in day:
                del day["routes"]
            
            simplified_plan["itinerary"].append(simplified_day)
    
    return simplified_plan

# 行程规划API - 简单版本
# 注释：此API端点未被前端使用，前端使用复杂版本 /api/trip/plan，已删除
# @app.post("/api/trip/itinerary", response_model=ItineraryPlanResponse)

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

# 注释：删除了未使用的 extract_hours_minutes 函数

# 新增函数：检查地点附近是否有公交/地铁站
def has_nearby_transit_station(lng, lat, radius=500):
    """检查指定坐标附近是否有公交或地铁站"""
    try:
          # 避免QPS限制
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

@app.post("/api/trip/streamplan", response_model=ItineraryPlanResponse)
async def get_trip_plan_stream(request: ItineraryPlanRequest):
    def generate_response():
        """生成行程规划的Server-Sent Events流"""
        try:
            llm = get_tongyi_client()
            prompt = f"""请为用户制定一个详细的{request.destination}{request.duration}天旅行行程规划。

            要求：
            1. 为每一天按顺序推荐3-4个逻辑上顺路的地点
            2. 每天都要有一个主题描述
            3. 每个地点按照省市+具体地点名称的形式输出，不要包含区县名称，例如"四川省成都市武侯祠"而不是"四川省成都市武侯区武侯祠"
            4. 为每个地点添加详细介绍
            5. 为每个地点添加建议停留时间（小时）
            6. 地点名称要具体准确，便于地图定位，格式为"省市+景点名称"
            7. 不要包含区县信息，避免定位错误
            8. 同一天的地点应该地理位置相对集中，便于游览
            9. 每天3-4个地点即可，不要过多"""

            messages = [
                SystemMessage(content="你是一位专业友好的旅行助手，名叫Trip Copilot。你可以："),
                HumanMessage(content=prompt)
            ]

            response = llm.stream(messages)
            for chunk in response:
                content = chunk.content
                if isinstance(content, list):
                    text_content = ""
                    for item in content:
                        if isinstance(item, dict) and "text" in item:
                            text_content += item["text"]
                        elif isinstance(item, str):
                            text_content += item
                    content = text_content
                if content:
                    # 发送 SSE 数据
                    yield f"data: {json.dumps({'content': str(content), 'type': 'chunk'})}\n\n"
            # 发送结束标记
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

        except Exception as e:
            # 发送错误信息
            error_msg = f"抱歉，我遇到了一些技术问题。请稍后再试。错误信息：{str(e)}"
            yield f"data: {json.dumps({'content': error_msg, 'type': 'error'})}\n\n"
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )


# 新增行程规划API
@app.post("/api/trip/plan", response_model=ItineraryPlanResponse)
async def get_trip_plan(request: FinePlanRequest):
    """获取完整的行程规划，包含每日详细安排、地点坐标和路径规划数据"""
    try:
        # 获取通义千问客户端
        llm = get_tongyi_client()
        
        # 构建高级LLM Prompt
        prompt = f"""给你一个已经计划好的行程规划，你必须严格按照要求的JSON格式返回结果，每个地点按照省市+具体地点名称的形式输出。
        
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
        """
        
        # 使用通义千问生成行程规划
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=request.plan)
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

# 新增：行程更新API
@app.post("/api/trip/update", response_model=ItineraryUpdateResponse)
async def update_trip_plan(request: ItineraryUpdateRequest):
    """根据用户的修改要求更新已有的行程规划"""
    try:
        llm = get_tongyi_client()

        # 创建精简版行程数据，移除路径规划详情以减少输入大小
        simplified_plan = simplify_plan_for_llm(request.current_plan)
        
        # 将精简后的行程JSON转换为字符串以便传递给LLM
        current_plan_str = json.dumps(simplified_plan, ensure_ascii=False, indent=2)

        prompt = f"""
你是一个智能行程规划编辑助手。你的任务是根据用户的修改要求，更新一份已有的JSON格式的旅行计划。

**当前行程规划 (JSON格式):**
{current_plan_str}

**用户的修改要求:**
"{request.modification_request}"

**你的任务:**
1. 理解用户的修改要求（可能是增加、删除或替换某个地点）。
2. 修改上面的JSON数据以反映这些变化。
3. **严格要求**：返回一个完整的、经过修改的JSON对象。除了JSON本身，不要包含任何额外的解释、注释或道歉。其结构必须与原始JSON完全一致。
4. 对于新增的地点，请按照"省市+具体地点名称"的格式，例如"四川省成都市武侯祠"。
5. 保持每天的地点数量适中（3-4个），确保地理位置相对集中。
6. 新增地点需要包含详细描述和建议停留时间。

请严格按照以下JSON格式返回，不要包含任何额外的解释性文字：
"""

        messages = [
            SystemMessage(content="你是一个JSON编辑专家，专门根据指令修改旅行计划。"),
            HumanMessage(content=prompt)
        ]

        try:
            # 检查请求大小，并打印调试信息
            request_size = len(current_plan_str)
            print(f"发送给LLM的请求大小: {request_size} 字符")
            if request_size > 100000:
                print("警告: 请求大小接近模型限制")

            # 调用LLM
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

            # 打印响应长度和前100个字符用于调试
            content_length = len(str(ai_content))
            print(f"AI响应长度: {content_length} 字符")
            print(f"AI响应前100个字符: {str(ai_content)[:100]}")

            # 提取JSON部分
            json_match = re.search(r'\{.*\}', str(ai_content), re.DOTALL)
            if not json_match:
                raise ValueError("AI返回的内容不包含有效的JSON格式，可能是输入内容过长导致模型响应不完整")
                
        except Exception as e:
            error_msg = f"处理AI响应失败: {str(e)}"
            print(error_msg)
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"API错误详情: {e.response.text}")
            raise ValueError(error_msg)

        # 提取JSON并解析
        json_str = json_match.group()
        try:
            updated_plan_data = json.loads(json_str)
        except json.JSONDecodeError as je:
            print(f"JSON解析失败: {str(je)}")
            print(f"JSON内容: {json_str[:200]}...")
            raise ValueError(f"无法解析返回的JSON: {str(je)}")

        # 为更新后的行程中的每个地点重新获取坐标并计算交通信息
        if "itinerary" in updated_plan_data:
            for day_plan in updated_plan_data["itinerary"]:
                if "places" in day_plan:
                    # 第一步：为每个地点获取坐标
                    valid_places = []
                    for place in day_plan["places"]:
                        if "name" in place:
                            # 尝试从地点名称中提取城市信息
                            place_name = place["name"]
                            city_info = None
                            
                            # 从目的地中提取城市信息
                            if updated_plan_data.get("destination"):
                                destination = updated_plan_data["destination"]
                                if "市" in destination:
                                    city_parts = destination.split("市")
                                    if len(city_parts) > 0:
                                        city_info = city_parts[0] + "市"
                                elif "省" in destination and len(destination) > 2:
                                    city_info = destination
                            
                            lng, lat = get_location_coordinates(place_name, city_info)
                            if lng is not None and lat is not None:
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
                                        valid_places.append(place)  # 仍然保留，但坐标为空
                                except (ValueError, TypeError):
                                    print(f"警告：地点 '{place['name']}' 坐标转换失败: ({lng}, {lat})")
                                    place["longitude"] = None
                                    place["latitude"] = None
                                    valid_places.append(place)  # 仍然保留，但坐标为空
                            else:
                                place["longitude"] = None
                                place["latitude"] = None
                                valid_places.append(place)  # 仍然保留，但坐标为空
                                print(f"警告：无法获取地点 '{place['name']}' 的坐标")
                    
                    # 更新places列表
                    day_plan["places"] = valid_places
                    
                    # 第二步：为相邻地点生成路径规划数据
                    day_plan["routes"] = []
                    valid_coord_places = [p for p in valid_places if p.get("longitude") and p.get("latitude")]
                    
                    if len(valid_coord_places) >= 2:
                        print(f"第{day_plan['day']}天开始生成 {len(valid_coord_places)-1} 条路径...")
                        for i in range(len(valid_coord_places) - 1):
                            start_place = valid_coord_places[i]
                            end_place = valid_coord_places[i + 1]
                            
                            try:
                                route_data = get_route_planning(
                                    (start_place["longitude"], start_place["latitude"]),
                                    (end_place["longitude"], end_place["latitude"]),
                                    "driving"  # 默认使用驾车模式
                                )
                                
                                if route_data and route_data.get("status") == "1":
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
                                        "sequence": i + 1
                                    }
                                    day_plan["routes"].append(route_info)
                                    print(f"✓ 成功生成路径 {i+1}/{len(valid_coord_places)-1}：{start_place['name']} -> {end_place['name']}")
                                else:
                                    print(f"✗ 无法生成路径 {i+1}/{len(valid_coord_places)-1}：{start_place['name']} -> {end_place['name']}")
                            except Exception as e:
                                print(f"✗ 生成路径时出错 {i+1}/{len(valid_coord_places)-1}：{start_place['name']} -> {end_place['name']}, 错误: {e}")
                    
                    print(f"第{day_plan['day']}天：有效地点 {len(valid_places)} 个，有坐标地点 {len(valid_coord_places)} 个，成功生成路径 {len(day_plan['routes'])} 条")

        # 第三步：计算交通时间和推荐交通方式（复用原有逻辑）
        if "itinerary" in updated_plan_data:
            for day_plan in updated_plan_data["itinerary"]:
                if "places" in day_plan:
                    valid_places = [p for p in day_plan["places"] if p.get("longitude") and p.get("latitude")]
                    
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

        return ItineraryUpdateResponse(
            success=True,
            updated_plan=updated_plan_data
        )

    except json.JSONDecodeError as je:
        return ItineraryUpdateResponse(
            success=False,
            error_message=f"解析AI返回的JSON数据失败: {str(je)}"
        )
    except ValueError as ve:
        return ItineraryUpdateResponse(
            success=False,
            error_message=str(ve)
        )
    except Exception as e:
        return ItineraryUpdateResponse(
            success=False,
            error_message=f"更新行程时发生错误: {str(e)}"
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
# 注释：此API端点未被前端使用，前端使用 /api/trip/itinerary-routes，已删除
# @app.post("/api/trip/routes", response_model=ItineraryRouteResponse)

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
