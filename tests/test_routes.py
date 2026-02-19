
import pytest
from unittest.mock import patch, MagicMock
import os
import requests

# Helper to mock successful response
def mock_response(json_data, status_code=200):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.status_code = status_code
    mock.text = str(json_data) # Set text for error handling access
    return mock

# Data fixtures
@pytest.fixture
def mock_env():
    return {
        "OPENWEATHER_API_KEY": "test_weather_key",
        "UNSPLASH_ACCESS_KEY": "test_unsplash_key"
    }

@pytest.fixture
def weather_response_data():
    return {
        "coord": {"lon": -0.1257, "lat": 51.5085},
        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
        "base": "stations",
        "main": {
            "temp": 15.0,
            "feels_like": 14.5,
            "temp_min": 13.0,
            "temp_max": 17.0,
            "pressure": 1012,
            "humidity": 56
        },
        "visibility": 10000,
        "wind": {"speed": 4.1, "deg": 80},
        "clouds": {"all": 0},
        "dt": 1625574323,
        "sys": {"type": 2, "id": 2019646, "country": "GB", "sunrise": 1625544607, "sunset": 1625604082},
        "timezone": 3600,
        "id": 2643743,
        "name": "London",
        "cod": 200
    }

@pytest.fixture
def geo_response_data():
    return [{"name": "London", "lat": 51.5074, "lon": -0.1278, "country": "GB"}]

@pytest.fixture
def unsplash_response_data():
    return {
        "total": 1,
        "total_pages": 1,
        "results": [{
            "id": "test_id",
            "urls": {"regular": "http://example.com/image.jpg"}
        }]
    }

# --- Tests for Home Route ---

def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Check Weather" in response.data

# --- Tests for Dashboard Route ---

def test_dashboard_no_params(client):
    with patch.dict(os.environ, {"OPENWEATHER_API_KEY": "key"}):
        response = client.get("/dashboard")
        # Should render template with weather=None (default prompt)
        assert response.status_code == 200
        assert b"Please enter a city" in response.data

def test_dashboard_missing_api_key(client):
    with patch.dict(os.environ, {}, clear=True):
        response = client.get("/dashboard?city=London")
        assert response.status_code == 200
        # Without key, logic returns render_template('dashboard.html', weather=None)
        assert b"Please enter a city" in response.data 

def test_dashboard_city_not_found(client, mock_env):
    with patch.dict(os.environ, mock_env):
        with patch("requests.get") as mock_get:
            # Mock geocoding returning empty list
            mock_get.return_value = mock_response([], 200)
            
            response = client.get("/dashboard?city=UnknownCity")
            assert response.status_code == 200
            assert b"City not found" in response.data

def test_dashboard_geocoding_failure(client, mock_env):
    with patch.dict(os.environ, mock_env):
        with patch("requests.get") as mock_get:
            # Mock geocoding failing (non-200)
            mock_get.return_value = mock_response({"cod": 401, "message": "Invalid API key"}, 401)
            
            response = client.get("/dashboard?city=London")
            assert response.status_code == 200
            assert b"City not found" in response.data

def test_dashboard_weather_fetch_failure(client, mock_env, geo_response_data):
    with patch.dict(os.environ, mock_env):
        with patch("requests.get") as mock_get:
            # 1. Geo success
            # 2. Weather failure
            mock_get.side_effect = [
                mock_response(geo_response_data),
                mock_response({"cod": 500}, 500)
            ]
            
            response = client.get("/dashboard?city=London")
            assert response.status_code == 200
            assert b"Failed to fetch weather" in response.data

def test_dashboard_success_with_city(client, mock_env, geo_response_data, weather_response_data, unsplash_response_data):
    with patch.dict(os.environ, mock_env):
        with patch("requests.get") as mock_get:
            # 1. Geo success
            # 2. Weather success
            # 3. Unsplash success
            mock_get.side_effect = [
                mock_response(geo_response_data),
                mock_response(weather_response_data),
                mock_response(unsplash_response_data)
            ]
            
            response = client.get("/dashboard?city=London")
            assert response.status_code == 200
            
            # Check for key data in response
            assert b"London, GB" in response.data
            assert b"15" in response.data # Temp
            assert b"http://example.com/image.jpg" in response.data
            assert b"Clear" in response.data
            assert b"fas fa-sun text-warning" in response.data # Icon mapping for 01d

def test_dashboard_success_with_coords(client, mock_env, weather_response_data, unsplash_response_data):
    with patch.dict(os.environ, mock_env):
        with patch("requests.get") as mock_get:
            # 1. Reverse Geo success
            rev_geo_data = [{"name": "Westminster", "country": "GB"}]
            # 2. Weather success
            # 3. Unsplash success
            mock_get.side_effect = [
                mock_response(rev_geo_data),
                mock_response(weather_response_data),
                mock_response(unsplash_response_data)
            ]
            
            response = client.get("/dashboard?lat=51.5&lon=-0.1")
            assert response.status_code == 200
            assert b"Westminster, GB" in response.data

def test_dashboard_unsplash_failure(client, mock_env, geo_response_data, weather_response_data):
    with patch.dict(os.environ, mock_env):
        with patch("requests.get") as mock_get:
            # 1. Geo success
            # 2. Weather success
            # 3. Unsplash failure (exception or non-200)
            mock_get.side_effect = [
                mock_response(geo_response_data),
                mock_response(weather_response_data),
                Exception("Unsplash Error") 
            ]
            
            response = client.get("/dashboard?city=London")
            assert response.status_code == 200
            # Should have fallback image
            assert b"https://images.unsplash.com/photo" in response.data

def test_dashboard_icon_mapping(client, mock_env, geo_response_data, weather_response_data):
    # Test a different icon code branch
    weather_data_rain = weather_response_data.copy()
    weather_data_rain["weather"][0]["icon"] = "09d" # Shower rain
    
    with patch.dict(os.environ, mock_env):
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                mock_response(geo_response_data),
                mock_response(weather_data_rain),
                Exception("Skip Unsplash") # Skip image to save mocks
            ]
            
            response = client.get("/dashboard?city=London")
            assert b"fas fa-cloud-showers-heavy text-info" in response.data

def test_dashboard_exception_handling(client, mock_env):
    with patch.dict(os.environ, mock_env):
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Unexpected Error")
            
            response = client.get("/dashboard?city=London")
            assert response.status_code == 200
            assert b"Unexpected Error" in response.data

# --- Tests for Get Weather Route (JSON API) ---

def test_get_weather_no_api_key(client):
    with patch.dict(os.environ, {}, clear=True):
        response = client.get("/weather")
        assert response.status_code == 500
        assert response.json == {"error": "API key not configured"}

def test_get_weather_missing_city(client, mock_env):
    with patch.dict(os.environ, mock_env):
        response = client.get("/weather") # No city param
        assert response.status_code == 400
        assert response.json == {"error": "City parameter is required"}

def test_get_weather_geo_failure(client, mock_env):
    with patch.dict(os.environ, mock_env):
        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_response({"message": "error"}, 401)
            
            response = client.get("/weather?city=London")
            assert response.status_code == 401
            assert "Failed to geocode city" in response.json["error"]

def test_get_weather_city_not_found(client, mock_env):
    with patch.dict(os.environ, mock_env):
        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_response([], 200) # Empty list
            
            response = client.get("/weather?city=Unknown")
            assert response.status_code == 404
            assert response.json == {"error": "City not found"}

def test_get_weather_fetch_failure(client, mock_env, geo_response_data):
    with patch.dict(os.environ, mock_env):
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                mock_response(geo_response_data),
                mock_response({"message": "error"}, 500)
            ]
            
            response = client.get("/weather?city=London")
            assert response.status_code == 500
            assert "Failed to fetch weather data" in response.json["error"]

def test_get_weather_success(client, mock_env, geo_response_data, weather_response_data):
    with patch.dict(os.environ, mock_env):
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                mock_response(geo_response_data),
                mock_response(weather_response_data)
            ]
            
            response = client.get("/weather?city=London")
            assert response.status_code == 200
            data = response.json
            assert data["name"] == "London, GB"
            assert data["current"]["temp"] == 15.0

def test_get_weather_exception(client, mock_env):
    with patch.dict(os.environ, mock_env):
        with patch("requests.get", side_effect=Exception("Severe Error")):
            response = client.get("/weather?city=London")
            assert response.status_code == 500
            assert response.json == {"error": "Severe Error"}
