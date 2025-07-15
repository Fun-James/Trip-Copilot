#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前后端集成测试脚本
模拟前端对后端的调用，检查数据格式和坐标处理
"""

import requests
import json
import time

# 后端服务地址
BASE_URL = "http://localhost:8000"

def test_coordinate_validation():
    """测试坐标验证功能"""
    print("\n=== 测试坐标数据格式 ===")
    
    # 测试地点信息API返回的坐标格式
    locations = ["天安门广场", "故宫博物院", "颐和园"]
    
    for location in locations:
        try:
            response = requests.post(f"{BASE_URL}/api/location/info", 
                                   json={"location": location})
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    location_data = data.get("location_data", {})
                    
                    # 检查坐标类型
                    lng = location_data.get("longitude")
                    lat = location_data.get("latitude")
                    
                    print(f"\n地点: {location}")
                    print(f"  经度: {lng} (类型: {type(lng)})")
                    print(f"  纬度: {lat} (类型: {type(lat)})")
                    
                    # 验证坐标转换
                    try:
                        lng_float = float(lng)
                        lat_float = float(lat)
                        
                        # 检查有效性
                        if not (isinstance(lng_float, float) and isinstance(lat_float, float)):
                            print(f"  ❌ 坐标类型错误")
                        elif lng_float != lng_float or lat_float != lat_float:  # NaN检查
                            print(f"  ❌ 坐标为NaN")
                        elif not (-180 <= lng_float <= 180 and -90 <= lat_float <= 90):
                            print(f"  ❌ 坐标超出范围")
                        else:
                            print(f"  ✅ 坐标有效: ({lng_float}, {lat_float})")
                            
                    except (ValueError, TypeError) as e:
                        print(f"  ❌ 坐标转换失败: {e}")
                        
                else:
                    print(f"❌ {location}: API调用失败 - {data.get('error_message')}")
            else:
                print(f"❌ {location}: HTTP错误 {response.status_code}")
                
        except Exception as e:
            print(f"❌ {location}: 异常 - {e}")
        
        time.sleep(0.5)  # 避免QPS限制

def test_itinerary_coordinates():
    """测试行程规划中的坐标数据"""
    print("\n=== 测试行程规划坐标格式 ===")
    
    try:
        response = requests.post(f"{BASE_URL}/api/trip/plan", 
                               json={"destination": "北京", "duration": 2})
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                plan_data = data.get("plan_data", {})
                itinerary = plan_data.get("itinerary", [])
                
                print(f"行程规划成功，共 {len(itinerary)} 天")
                
                total_places = 0
                valid_places = 0
                invalid_places = 0
                
                for day_plan in itinerary:
                    day = day_plan.get("day")
                    places = day_plan.get("places", [])
                    
                    print(f"\n第{day}天，共 {len(places)} 个地点:")
                    
                    for place in places:
                        total_places += 1
                        name = place.get("name", "未知地点")
                        lng = place.get("longitude")
                        lat = place.get("latitude")
                        
                        print(f"  地点: {name}")
                        print(f"    坐标: ({lng}, {lat})")
                        print(f"    类型: 经度={type(lng)}, 纬度={type(lat)}")
                        
                        # 验证坐标
                        try:
                            lng_float = float(lng) if lng is not None else None
                            lat_float = float(lat) if lat is not None else None
                            
                            if lng_float is None or lat_float is None:
                                print(f"    ❌ 坐标缺失")
                                invalid_places += 1
                            elif lng_float != lng_float or lat_float != lat_float:
                                print(f"    ❌ 坐标为NaN")
                                invalid_places += 1
                            elif not (-180 <= lng_float <= 180 and -90 <= lat_float <= 90):
                                print(f"    ❌ 坐标超出范围")
                                invalid_places += 1
                            else:
                                print(f"    ✅ 坐标有效")
                                valid_places += 1
                                
                        except (ValueError, TypeError):
                            print(f"    ❌ 坐标转换失败")
                            invalid_places += 1
                
                print(f"\n📊 坐标统计:")
                print(f"  总地点数: {total_places}")
                print(f"  有效坐标: {valid_places}")
                print(f"  无效坐标: {invalid_places}")
                print(f"  有效率: {valid_places/total_places*100:.1f}%" if total_places > 0 else "  有效率: N/A")
                
            else:
                print(f"❌ 行程规划失败: {data.get('error_message')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 异常: {e}")

def test_path_planning_coordinates():
    """测试路径规划中的坐标数据"""
    print("\n=== 测试路径规划坐标格式 ===")
    
    try:
        response = requests.post(f"{BASE_URL}/api/trip/path", 
                               json={
                                   "start": "天安门广场", 
                                   "end": "故宫博物院", 
                                   "mode": "walking"
                               })
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                path_data = data.get("path_data", {})
                
                print("路径规划成功")
                
                # 检查起点坐标
                start_point = path_data.get("start_point", {})
                start_lng = start_point.get("longitude")
                start_lat = start_point.get("latitude")
                
                print(f"\n起点: {start_point.get('name')}")
                print(f"  坐标: ({start_lng}, {start_lat})")
                print(f"  类型: 经度={type(start_lng)}, 纬度={type(start_lat)}")
                
                # 检查终点坐标
                end_point = path_data.get("end_point", {})
                end_lng = end_point.get("longitude")
                end_lat = end_point.get("latitude")
                
                print(f"\n终点: {end_point.get('name')}")
                print(f"  坐标: ({end_lng}, {end_lat})")
                print(f"  类型: 经度={type(end_lng)}, 纬度={type(end_lat)}")
                
                # 验证坐标有效性
                coordinates_to_check = [
                    ("起点", start_lng, start_lat),
                    ("终点", end_lng, end_lat)
                ]
                
                for label, lng, lat in coordinates_to_check:
                    try:
                        lng_float = float(lng) if lng is not None else None
                        lat_float = float(lat) if lat is not None else None
                        
                        if lng_float is None or lat_float is None:
                            print(f"  {label}: ❌ 坐标缺失")
                        elif lng_float != lng_float or lat_float != lat_float:
                            print(f"  {label}: ❌ 坐标为NaN")
                        elif not (-180 <= lng_float <= 180 and -90 <= lat_float <= 90):
                            print(f"  {label}: ❌ 坐标超出范围")
                        else:
                            print(f"  {label}: ✅ 坐标有效 ({lng_float}, {lat_float})")
                            
                    except (ValueError, TypeError):
                        print(f"  {label}: ❌ 坐标转换失败")
                
            else:
                print(f"❌ 路径规划失败: {data.get('error_message')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 异常: {e}")

def main():
    """主测试函数"""
    print("🔍 开始前后端集成坐标测试...")
    
    # 检查后端服务状态
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ 后端服务不可用，请先启动后端服务")
            return
    except Exception as e:
        print(f"❌ 无法连接后端服务: {e}")
        print("请确保后端服务已启动: cd backend && python main.py")
        return
    
    print("✅ 后端服务连接正常")
    
    # 执行各项测试
    test_coordinate_validation()
    test_itinerary_coordinates()
    test_path_planning_coordinates()
    
    print("\n🎯 测试总结:")
    print("1. 如果所有坐标都显示'有效'，说明后端数据格式正确")
    print("2. 如果出现'NaN'或'坐标转换失败'，说明需要修复坐标处理")
    print("3. 前端应该加强坐标验证，确保传递给地图的都是有效数值")
    print("\n💡 建议:")
    print("- 前端收到后端数据后立即进行坐标类型转换和验证")
    print("- 使用 parseFloat() 转换坐标，并检查 isNaN() 和 isFinite()")
    print("- 对无效坐标进行过滤，避免传递给地图组件")

if __name__ == "__main__":
    main()
