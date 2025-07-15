#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
后端API接口测试脚本
测试Trip Copilot后端的各个API接口
"""

import requests
import json
import time

# 后端服务地址
BASE_URL = "http://localhost:8000"

def test_health_check():
    """测试健康检查接口"""
    print("\n=== 测试健康检查接口 ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False

def test_location_info(location):
    """测试地点信息接口"""
    print(f"\n=== 测试地点信息接口：{location} ===")
    try:
        url = f"{BASE_URL}/api/location/info"
        data = {"location": location}
        
        print(f"请求URL: {url}")
        print(f"请求数据: {data}")
        
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        
        result = response.json()
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get("success"):
            location_data = result.get("location_data", {})
            print(f"✅ 成功获取地点信息:")
            print(f"   经度: {location_data.get('longitude')}")
            print(f"   纬度: {location_data.get('latitude')}")
            print(f"   详细地址: {location_data.get('formatted_address')}")
            return location_data
        else:
            print(f"❌ 获取地点信息失败: {result.get('error_message')}")
            return None
            
    except Exception as e:
        print(f"❌ 地点信息接口异常: {e}")
        return None

def test_path_planning(start, end, mode="driving"):
    """测试路径规划接口"""
    print(f"\n=== 测试路径规划接口：{start} -> {end} ({mode}) ===")
    try:
        url = f"{BASE_URL}/api/trip/path"
        data = {
            "start": start,
            "end": end,
            "mode": mode
        }
        
        print(f"请求URL: {url}")
        print(f"请求数据: {data}")
        
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        
        result = response.json()
        print(f"响应成功状态: {result.get('success')}")
        
        if result.get("success"):
            path_data = result.get("path_data", {})
            print(f"✅ 路径规划成功:")
            print(f"   起点: {path_data.get('start_point', {}).get('name')}")
            print(f"   终点: {path_data.get('end_point', {}).get('name')}")
            print(f"   模式: {path_data.get('mode')}")
            
            # 检查路径信息
            route_info = path_data.get('route_info', {})
            if route_info:
                print(f"   路径信息: 包含详细路径数据")
            
            return path_data
        else:
            print(f"❌ 路径规划失败: {result.get('error_message')}")
            print(f"完整响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return None
            
    except Exception as e:
        print(f"❌ 路径规划接口异常: {e}")
        return None

def test_trip_suggestions(destination, duration=3):
    """测试旅行建议接口"""
    print(f"\n=== 测试旅行建议接口：{destination} ===")
    try:
        url = f"{BASE_URL}/api/trip/suggest"
        data = {
            "destination": destination,
            "duration": duration,
            "interests": ["文化", "历史"]
        }
        
        print(f"请求URL: {url}")
        print(f"请求数据: {data}")
        
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        
        result = response.json()
        print(f"✅ 旅行建议:")
        for i, recommendation in enumerate(result.get("recommendations", []), 1):
            print(f"   {i}. {recommendation}")
            
        return result
        
    except Exception as e:
        print(f"❌ 旅行建议接口异常: {e}")
        return None

def test_itinerary_planning(destination, duration=3):
    """测试行程规划接口"""
    print(f"\n=== 测试行程规划接口：{destination} ({duration}天) ===")
    try:
        url = f"{BASE_URL}/api/trip/plan"
        data = {
            "destination": destination,
            "duration": duration
        }
        
        print(f"请求URL: {url}")
        print(f"请求数据: {data}")
        
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        
        result = response.json()
        print(f"响应成功状态: {result.get('success')}")
        
        if result.get("success"):
            plan_data = result.get("plan_data", {})
            print(f"✅ 行程规划成功:")
            print(f"   目的地: {plan_data.get('destination')}")
            print(f"   总天数: {plan_data.get('total_days')}")
            
            itinerary = plan_data.get('itinerary', [])
            for day_plan in itinerary:
                day = day_plan.get('day')
                theme = day_plan.get('theme')
                places = day_plan.get('places', [])
                print(f"   第{day}天 - {theme}:")
                for place in places:
                    name = place.get('name')
                    lng = place.get('longitude')
                    lat = place.get('latitude')
                    coord_status = "✅有坐标" if lng and lat else "❌无坐标"
                    print(f"     - {name} {coord_status}")
            
            return plan_data
        else:
            print(f"❌ 行程规划失败: {result.get('error_message')}")
            return None
            
    except Exception as e:
        print(f"❌ 行程规划接口异常: {e}")
        return None

def main():
    """主测试函数"""
    print("🚀 开始测试Trip Copilot后端API...")
    
    # 1. 测试健康检查
    if not test_health_check():
        print("\n❌ 后端服务未启动或不可用，请先启动后端服务")
        print("启动命令: cd backend && python main.py")
        return
    
    # 2. 测试地点信息接口
    test_locations = ["天安门广场", "故宫博物院", "景山公园"]
    location_results = {}
    
    for location in test_locations:
        result = test_location_info(location)
        if result:
            location_results[location] = result
    
    # 3. 测试路径规划接口
    if len(location_results) >= 2:
        locations_list = list(location_results.keys())
        start_location = locations_list[0]
        end_location = locations_list[1]
        
        # 测试驾车路径
        driving_result = test_path_planning(start_location, end_location, "driving")
        
        # 测试步行路径
        walking_result = test_path_planning(start_location, end_location, "walking")
        
        # 测试公交路径（如果支持）
        # transit_result = test_path_planning(start_location, end_location, "transit")
    
    # 4. 测试旅行建议接口
    test_trip_suggestions("北京")
    
    # 5. 测试行程规划接口
    test_itinerary_planning("北京", 3)
    
    print("\n✅ 所有API接口测试完成！")
    print("\n📊 测试总结:")
    print("   - 如果以上测试都成功，说明后端API工作正常")
    print("   - 如果路径规划失败但地点信息成功，可能是高德API权限问题")
    print("   - 注意检查坐标获取情况，这对前端地图显示很重要")

if __name__ == "__main__":
    main()
