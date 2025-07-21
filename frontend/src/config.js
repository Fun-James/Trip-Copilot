// API 配置
export const API_BASE_URL = 'http://localhost:8000'

// 其他配置项
export const API_ENDPOINTS = {
    weather: location => `${API_BASE_URL}/api/weather/${encodeURIComponent(location)}`,
    tripSuggest: `${API_BASE_URL}/api/trip/suggest`,
    destinations: `${API_BASE_URL}/api/destinations/popular`,
    chat: `${API_BASE_URL}/api/chat`,
    path: `${API_BASE_URL}/api/trip/path`,
    itineraryRoutes: `${API_BASE_URL}/api/trip/itinerary-routes`
}
