#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
针对免费版QPS限制的高德地图API测试脚本
免费版限制：3次/秒，需要在调用之间添加延迟
"""

import os
import requests
import time
from dotenv import load_dotenv
import json

# 加载环境变量
load_dotenv()

def get_amap_api_key():
    """获取高德地图API密钥"""
    api_key = os.getenv("AMAP_API_KEY")
    if not api_key:
        raise ValueError("AMAP_API_KEY not found in environment variables")
    return api_key

def safe_api_call(func, *args, **kwargs):
    """安全的API调用，自动处理QPS限制"""
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # 每次调用前等待，确保不超过QPS限制
            time.sleep(0.5)  # 等待500ms，确保每秒不超过2次调用
            
            result = func(*args, **kwargs)
            return result
            
        except Exception as e:
            error_msg = str(e)
            if "QPS" in error_msg or "限制" in error_msg:
                print(f"⚠️ QPS限制触发，第{attempt + 1}次重试...")
                time.sleep(retry_delay * (attempt + 1))  # 递增延迟
            else:
                raise e
    
    raise Exception("达到最大重试次数，请稍后再试")

def test_geocode_safe(location_name):
    """安全的地理编码测试"""
    print(f"\n=== 安全测试地理编码：{location_name} ===")
    
    def _geocode():
        api_key = get_amap_api_key()
        url = "https://restapi.amap.com/v3/geocode/geo"
        params = {
            "key": api_key,
            "address": location_name
        }
        
        response = requests.get(url, params=params)
        return response.json()
    
    try:
        data = safe_api_call(_geocode)
        print(f"响应状态: {data.get('status')}")
        
        if data["status"] == "1" and data["geocodes"]:
            geocode = data["geocodes"][0]
            location_str = geocode["location"]
            longitude, latitude = location_str.split(",")
            print(f"✅ 成功获取坐标: 经度={longitude}, 纬度={latitude}")
            print(f"   详细地址: {geocode.get('formatted_address')}")
            return float(longitude), float(latitude)
        else:
            print(f"❌ 地理编码失败: {data.get('info', 'unknown')}")
            return None, None
            
    except Exception as e:
        print(f"❌ 地理编码异常: {e}")
        return None, None

def test_route_planning_safe(start_coords, end_coords, mode="driving"):
    """安全的路径规划测试"""
    print(f"\n=== 安全测试路径规划：{start_coords} -> {end_coords} ({mode}) ===")
    
    def _route_planning():
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
        return response.json()
    
    try:
        data = safe_api_call(_route_planning)
        print(f"响应状态: {data.get('status')}")
        print(f"响应信息: {data.get('info')}")
        
        if data.get("status") == "1":
            if mode == "driving" and "route" in data:
                route = data["route"]
                print(f"✅ 驾车路径规划成功")
                if route.get('paths'):
                    path = route['paths'][0]
                    distance = int(path.get('distance', 0))
                    duration = int(path.get('duration', 0))
                    print(f"   距离: {distance}米 ({distance/1000:.1f}公里)")
                    print(f"   预计时间: {duration}秒 ({duration//60}分{duration%60}秒)")
                    print(f"   步骤数量: {len(path.get('steps', []))}")
            elif mode == "walking" and "route" in data:
                route = data["route"]
                print(f"✅ 步行路径规划成功")
                if route.get('paths'):
                    path = route['paths'][0]
                    distance = int(path.get('distance', 0))
                    duration = int(path.get('duration', 0))
                    print(f"   距离: {distance}米")
                    print(f"   预计时间: {duration}秒 ({duration//60}分{duration%60}秒)")
            
            return data
        else:
            print(f"❌ 路径规划失败: {data.get('info', 'unknown')}")
            return None
            
    except Exception as e:
        print(f"❌ 路径规划异常: {e}")
        return None

def main():
    """主测试函数 - 针对免费版优化"""
    print("🚀 开始测试高德地图API（免费版优化）...")
    print("⚠️ 免费版QPS限制：3次/秒，测试过程会比较慢")
    
    # 测试地点（减少数量避免超出限制）
    test_locations = ["天安门广场", "故宫博物院"]
    
    coordinates = {}
    
    print("\n📍 开始地理编码测试...")
    for i, location in enumerate(test_locations, 1):
        print(f"\n进度: {i}/{len(test_locations)}")
        lng, lat = test_geocode_safe(location)
        if lng and lat:
            coordinates[location] = (lng, lat)
        
        # 在每个地点测试之间添加额外延迟
        if i < len(test_locations):
            print("⏳ 等待中以避免QPS限制...")
            time.sleep(1.0)
    
    print(f"\n✅ 地理编码完成，成功获取 {len(coordinates)} 个地点坐标")
    
    # 测试路径规划
    if len(coordinates) >= 2:
        locations_list = list(coordinates.items())
        start_name, start_coords = locations_list[0]
        end_name, end_coords = locations_list[1]
        
        print("\n🚗 开始路径规划测试...")
        print("⏳ 等待中以避免QPS限制...")
        time.sleep(2.0)
        
        driving_result = test_route_planning_safe(start_coords, end_coords, "driving")
        
        if driving_result:
            print("\n🚶 继续测试步行路径...")
            print("⏳ 等待中以避免QPS限制...")
            time.sleep(2.0)
            walking_result = test_route_planning_safe(start_coords, end_coords, "walking")
    
    print("\n✅ 测试完成！")
    print("\n📊 针对免费版的建议:")
    print("   1. 在生产环境中，需要在每次API调用之间添加延迟")
    print("   2. 考虑升级到付费版本以获得更高的QPS限制")
    print("   3. 可以使用缓存来减少重复的API调用")
    print("   4. 批量处理地理编码，避免频繁调用")

if __name__ == "__main__":
    main()
