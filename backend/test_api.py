#!/usr/bin/env python3
"""
Trip Copilot 后端路径规划功能测试脚本
"""

import requests
import json

# 后端服务地址
BASE_URL = "http://localhost:8000"

def test_path_planning():
    """测试路径规划API"""
    print("=== 测试路径规划功能 ===")
    
    # 测试数据
    test_data = {
        "start": "北京天安门",
        "end": "北京大学",
        "mode": "driving"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/trip/path", json=test_data)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                print("✅ 路径规划成功!")
                path_data = result["path_data"]
                print(f"起点: {path_data['start_point']['name']}")
                print(f"起点坐标: ({path_data['start_point']['longitude']}, {path_data['start_point']['latitude']})")
                print(f"终点: {path_data['end_point']['name']}")
                print(f"终点坐标: ({path_data['end_point']['longitude']}, {path_data['end_point']['latitude']})")
                print(f"出行方式: {path_data['mode']}")
                
                # 检查是否有路径信息
                if "route_info" in path_data and "paths" in path_data["route_info"]:
                    paths = path_data["route_info"]["paths"]
                    if paths:
                        path = paths[0]
                        distance = path.get("distance", "未知")
                        duration = path.get("duration", "未知")
                        print(f"距离: {distance}米")
                        print(f"预计时间: {duration}秒")
                
            else:
                print(f"❌ 路径规划失败: {result['error_message']}")
        else:
            print(f"❌ HTTP请求失败: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务，请确保后端服务正在运行")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def test_location_info():
    """测试地点信息API"""
    print("\n=== 测试地点信息功能 ===")
    
    test_data = {
        "location": "北京天安门"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/location/info", json=test_data)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                print("✅ 地点查询成功!")
                location_data = result["location_data"]
                print(f"地点名称: {location_data['name']}")
                print(f"详细地址: {location_data['formatted_address']}")
                print(f"省份: {location_data['province']}")
                print(f"城市: {location_data['city']}")
                print(f"区县: {location_data['district']}")
                print(f"坐标: ({location_data['longitude']}, {location_data['latitude']})")
            else:
                print(f"❌ 地点查询失败: {result['error_message']}")
        else:
            print(f"❌ HTTP请求失败: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务，请确保后端服务正在运行")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def test_health():
    """测试健康检查API"""
    print("\n=== 测试健康检查 ===")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ 后端服务正常运行")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    print("Trip Copilot 后端API测试")
    print("=" * 40)
    
    # 测试健康检查
    test_health()
    
    # 测试地点信息
    test_location_info()
    
    # 测试路径规划
    test_path_planning()
    
    print("\n测试完成!")
