# Trip Copilot 后端路径规划API文档

## 概述

本文档描述了Trip Copilot后端新增的路径规划功能，该功能集成了高德地图Web服务，可以为前端提供起点到终点的路径规划信息。

## 环境配置

### 1. 安装依赖

确保安装了所有必要的Python包：

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置API密钥

复制环境变量示例文件并配置你的API密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的API密钥：

```
# 通义千问API密钥
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# 高德地图API密钥  
AMAP_API_KEY=your_amap_api_key_here
```

**获取高德地图API密钥的步骤：**
1. 访问 [高德开放平台](https://lbs.amap.com/)
2. 注册账号并登录
3. 进入控制台，创建新应用
4. 获取Web服务API的Key

## API接口

### 1. 路径规划接口

**接口地址：** `POST /api/trip/path`

**功能：** 获取起点到终点的路径规划信息

**请求参数：**
```json
{
    "start": "起点名称",
    "end": "终点名称", 
    "mode": "出行方式"  // 可选，默认"driving"
}
```

**mode参数说明：**
- `driving`: 驾车路径规划
- `walking`: 步行路径规划  
- `transit`: 公交路径规划

**响应示例：**
```json
{
    "success": true,
    "path_data": {
        "start_point": {
            "name": "北京天安门",
            "longitude": 116.397128,
            "latitude": 39.916527
        },
        "end_point": {
            "name": "北京大学",
            "longitude": 116.275463,
            "latitude": 39.992801
        },
        "mode": "driving",
        "route_info": {
            "paths": [
                {
                    "distance": "15420",
                    "duration": "2340",
                    "steps": [...],
                    // 更多路径详细信息
                }
            ]
        },
        "raw_data": {
            // 高德地图API的完整原始响应数据
        }
    },
    "error_message": null
}
```

### 2. 地点信息查询接口

**接口地址：** `POST /api/location/info`

**功能：** 获取地点的详细信息和坐标

**请求参数：**
```json
{
    "location": "地点名称"
}
```

**响应示例：**
```json
{
    "success": true,
    "location_data": {
        "name": "北京天安门",
        "formatted_address": "北京市东城区东长安街",
        "province": "北京市",
        "city": "北京市", 
        "district": "东城区",
        "location": "116.397128,39.916527",
        "longitude": 116.397128,
        "latitude": 39.916527,
        "level": "兴趣点"
    },
    "error_message": null
}
```

## 前端集成示例

### JavaScript/Vue.js示例

```javascript
// 获取路径规划
async function getRoutePath(start, end, mode = 'driving') {
    try {
        const response = await fetch('/api/trip/path', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                start: start,
                end: end, 
                mode: mode
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 成功获取路径数据
            const pathData = result.path_data;
            console.log('起点:', pathData.start_point);
            console.log('终点:', pathData.end_point);
            
            // 可以使用raw_data中的完整路径信息在地图上绘制
            return pathData;
        } else {
            console.error('获取路径失败:', result.error_message);
            return null;
        }
    } catch (error) {
        console.error('请求失败:', error);
        return null;
    }
}

// 使用示例
getRoutePath('北京天安门', '北京大学', 'driving').then(pathData => {
    if (pathData) {
        // 在地图上绘制路径
        drawRouteOnMap(pathData);
    }
});
```

## 测试

运行测试脚本来验证API功能：

```bash
# 确保后端服务正在运行
python main.py

# 在另一个终端运行测试
python test_api.py
```

## 错误处理

API会返回详细的错误信息：

1. **API密钥错误：** `AMAP_API_KEY not found in environment variables`
2. **地点无效：** `无法获取起点/终点的坐标信息`
3. **路径规划失败：** `获取路径规划失败，请检查起点和终点是否正确`
4. **服务器错误：** `服务器内部错误: [具体错误信息]`

## 注意事项

1. 确保高德地图API密钥有效且有足够的调用次数
2. 地点名称尽量使用具体的地址或知名地标
3. 不同的`mode`参数会返回不同类型的路径规划结果
4. `raw_data`字段包含了高德地图API的完整响应，可根据需要提取更多信息
5. 坐标系统使用的是高德地图的GCJ02坐标系

## 下一步开发建议

1. 添加路径优化选项（如避开拥堵、高速优先等）
2. 支持多个途经点的路径规划
3. 添加实时交通信息
4. 缓存常用路径以提高响应速度
5. 添加路径分享功能
