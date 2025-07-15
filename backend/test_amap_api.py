#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高德地图API测试脚本
用于测试地理编码、路径规划等功能
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

def test_geocode(location_name):
    """测试地理编码（地名转坐标）"""
    print(f"\n=== 测试地理编码：{location_name} ===")
    try:
        # 添加延迟避免QPS限制
        time.sleep(0.5)  # 等待500ms，确保不超过3次/秒
        
        api_key = get_amap_api_key()
        url = "https://restapi.amap.com/v3/geocode/geo"
        params = {
            "key": api_key,
            "address": location_name
        }
        
        print(f"请求URL: {url}")
        print(f"请求参数: {params}")
        
        response = requests.get(url, params=params)
        print(f"响应状态码: {response.status_code}")
        
        data = response.json()
        print(f"响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if data["status"] == "1" and data["geocodes"]:
            geocode = data["geocodes"][0]
            location_str = geocode["location"]
            longitude, latitude = location_str.split(",")
            print(f"✅ 成功获取坐标: 经度={longitude}, 纬度={latitude}")
            return float(longitude), float(latitude)
        else:
            print(f"❌ 地理编码失败: {data}")
            return None, None
            
    except Exception as e:
        print(f"❌ 地理编码异常: {e}")
        return None, None

def test_route_planning(start_coords, end_coords, mode="driving"):
    """测试路径规划"""
    print(f"\n=== 测试路径规划：{start_coords} -> {end_coords} ({mode}) ===")
    try:
        # 添加延迟避免QPS限制
        time.sleep(1.0)  # 等待1秒，确保不超过3次/秒
        
        api_key = get_amap_api_key()
        origin = f"{start_coords[0]},{start_coords[1]}"
        destination = f"{end_coords[0]},{end_coords[1]}"
        
        url = f"https://restapi.amap.com/v3/direction/{mode}"
        params = {
            "key": api_key,
            "origin": origin,
            "destination": destination
        }
        
        print(f"请求URL: {url}")
        print(f"请求参数: {params}")
        
        response = requests.get(url, params=params)
        print(f"响应状态码: {response.status_code}")
        
        data = response.json()
        print(f"响应状态: {data.get('status', 'unknown')}")
        print(f"响应信息: {data.get('info', 'unknown')}")
        
        if data.get("status") == "1":
            if mode == "driving" and "route" in data:
                route = data["route"]
                print(f"✅ 路径规划成功")
                print(f"   路径数量: {len(route.get('paths', []))}")
                if route.get('paths'):
                    path = route['paths'][0]
                    print(f"   距离: {path.get('distance', 'unknown')}米")
                    print(f"   预计时间: {path.get('duration', 'unknown')}秒")
                    print(f"   步骤数量: {len(path.get('steps', []))}")
            elif mode == "walking" and "route" in data:
                route = data["route"]
                print(f"✅ 步行路径规划成功")
                print(f"   路径数量: {len(route.get('paths', []))}")
                if route.get('paths'):
                    path = route['paths'][0]
                    print(f"   距离: {path.get('distance', 'unknown')}米")
                    print(f"   预计时间: {path.get('duration', 'unknown')}秒")
            
            return data
        else:
            print(f"❌ 路径规划失败")
            print(f"完整响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return None
            
    except Exception as e:
        print(f"❌ 路径规划异常: {e}")
        return None

def test_api_key_validity():
    """测试API密钥有效性"""
    print("\n=== 测试API密钥有效性 ===")
    try:
        api_key = get_amap_api_key()
        print(f"API密钥: {api_key[:10]}...{api_key[-5:]} (已脱敏)")
        
        # 使用一个简单的IP定位API来测试密钥
        url = "https://restapi.amap.com/v3/ip"
        params = {"key": api_key}
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("status") == "1":
            print("✅ API密钥有效")
            print(f"   当前IP定位: {data.get('city', '未知')}")
            return True
        else:
            print(f"❌ API密钥无效或有问题: {data}")
            return False
            
    except Exception as e:
        print(f"❌ API密钥测试异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试高德地图API...")
    
    # 1. 测试API密钥
    if not test_api_key_validity():
        print("\n❌ API密钥测试失败，请检查.env文件中的AMAP_API_KEY配置")
        return
    
    # 2. 测试地理编码（减少测试地点以避免QPS限制）
    test_locations = [
        "天安门广场",
        "故宫博物院"
        # 暂时只测试2个地点，避免QPS限制
    ]
    
    coordinates = {}
    for location in test_locations:
        lng, lat = test_geocode(location)
        if lng and lat:
            coordinates[location] = (lng, lat)
    
    # 3. 测试路径规划
    if len(coordinates) >= 2:
        locations_list = list(coordinates.items())
        
        # 测试驾车路径规划
        start_name, start_coords = locations_list[0]
        end_name, end_coords = locations_list[1]
        
        print(f"\n🚗 测试驾车路径规划: {start_name} -> {end_name}")
        driving_result = test_route_planning(start_coords, end_coords, "driving")
        
        print(f"\n🚶 测试步行路径规划: {start_name} -> {end_name}")
        walking_result = test_route_planning(start_coords, end_coords, "walking")
        
        # 如果有第三个地点，测试多点路径
        if len(coordinates) >= 3:
            mid_name, mid_coords = locations_list[2]
            print(f"\n🛣️  测试三点路径规划: {start_name} -> {mid_name} -> {end_name}")
            
            # 先测试第一段
            segment1 = test_route_planning(start_coords, mid_coords, "driving")
            # 再测试第二段  
            segment2 = test_route_planning(mid_coords, end_coords, "driving")
    
    print("\n✅ 测试完成！")
    print("\n📊 测试总结:")
    print(f"   - 成功获取坐标的地点数量: {len(coordinates)}")
    print("   - 如果以上测试都成功，说明高德API配置正常")
    print("   - 如果有失败，请检查:")
    print("     1. .env文件中的AMAP_API_KEY是否正确")
    print("     2. API密钥是否开通了相应服务权限")
    print("     3. 网络连接是否正常")

if __name__ == "__main__":
    main()
