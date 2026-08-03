"""Free weather query service backed by Open-Meteo (no API key required).

- Geocoding: https://geocoding-api.open-meteo.com/v1/search
- Forecast:  https://api.open-meteo.com/v1/forecast

Works from mainland China without a proxy.
"""

import json
import time
from urllib import error, parse, request

from app.config import settings

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_TIMEOUT = 15

# WMO weather interpretation codes -> Chinese descriptions
WMO_CODES: dict[int, str] = {
    0: "晴",
    1: "基本晴朗",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "雾凇",
    51: "毛毛雨",
    53: "毛毛雨",
    55: "毛毛雨",
    56: "冻毛毛雨",
    57: "冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "阵雨",
    81: "阵雨",
    82: "强阵雨",
    85: "阵雪",
    86: "阵雪",
    95: "雷暴",
    96: "雷暴伴冰雹",
    99: "雷暴伴冰雹",
}


class WeatherService:
    def __init__(self, timeout: int | None = None):
        self.timeout = int(timeout if timeout is not None else DEFAULT_TIMEOUT)

    def search(self, city: str, *, days: int = 1) -> dict:
        """Query current + daily weather for a city name (Chinese or pinyin)."""
        name = city.strip()
        if not name:
            raise ValueError("Weather query city cannot be empty")

        started = time.perf_counter()
        location = self._geocode(name)
        if not location:
            raise ValueError(f"City not found: {name}")

        forecast = self._forecast(location["latitude"], location["longitude"], days)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        daily = forecast.get("daily") or {}
        dates = (daily.get("time") or [])[:days]
        max_temps = (daily.get("temperature_2m_max") or [])[:days]
        min_temps = (daily.get("temperature_2m_min") or [])[:days]
        weather_codes = (daily.get("weather_code") or [])[:days]

        current = forecast.get("current") or {}
        current_code = current.get("weather_code")
        current_wind = current.get("wind_speed_10m")

        return {
            "provider": "open-meteo",
            "status": 200,
            "city": location["name"],
            "region": location.get("admin1"),
            "country": location.get("country"),
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "elapsedMs": elapsed_ms,
            "current": {
                "time": current.get("time"),
                "temperatureC": current.get("temperature_2m"),
                "apparentTemperatureC": current.get("apparent_temperature"),
                "condition": WMO_CODES.get(current_code, f"未知({current_code})"),
                "windSpeedKmh": current_wind,
            },
            "daily": [
                {
                    "date": dates[i] if i < len(dates) else None,
                    "maxTempC": max_temps[i] if i < len(max_temps) else None,
                    "minTempC": min_temps[i] if i < len(min_temps) else None,
                    "condition": WMO_CODES.get(weather_codes[i], "未知"),
                }
                for i in range(min(days, len(dates)))
            ],
        }

    def _geocode(self, name: str) -> dict | None:
        url = f"{GEOCODING_URL}?{parse.urlencode({'name': name, 'count': 1, 'language': 'zh', 'format': 'json'})}"
        data = self._get_json(url)
        results = data.get("results") if isinstance(data, dict) else None
        if not results:
            return None
        row = results[0]
        return {
            "name": row.get("name"),
            "latitude": row.get("latitude"),
            "longitude": row.get("longitude"),
            "admin1": row.get("admin1"),
            "country": row.get("country"),
        }

    def _forecast(self, latitude: float, longitude: float, days: int) -> dict:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "forecast_days": max(1, min(int(days), 7)),
            "timezone": "Asia/Shanghai",
        }
        url = f"{FORECAST_URL}?{parse.urlencode(params)}"
        return self._get_json(url)

    def _get_json(self, url: str) -> dict:
        req = request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
                "Accept": "application/json",
            },
            method="GET",
        )
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with request.urlopen(req, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except (error.HTTPError, error.URLError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(0.8 * (attempt + 1))
        if isinstance(last_error, error.HTTPError):
            raise RuntimeError(f"Weather API failed ({last_error.code})") from last_error
        if isinstance(last_error, error.URLError):
            raise ConnectionError("Unable to reach weather API") from last_error
        raise RuntimeError("Weather API returned invalid JSON") from last_error
