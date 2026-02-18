
from flask import Blueprint, jsonify, request, render_template, current_app
import requests
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template('index.html')

@main_bp.route('/dashboard')
def dashboard():
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "API key not configured", 500

    city = request.args.get('city')
    country = request.args.get('country')

    if not city:
        return render_template('dashboard.html', weather=None)

    # 1. Geocoding
    geo_url = "http://api.openweathermap.org/geo/1.0/direct"
    q_param = f"{city},{country}" if country else city
    
    geo_params = {
        'q': q_param,
        'limit': 1,
        'appid': api_key
    }

    try:
        geo_resp = requests.get(geo_url, params=geo_params)
        if geo_resp.status_code != 200:
             return f"Failed to geocode city: {geo_resp.text}", geo_resp.status_code
        
        geo_data = geo_resp.json()
        if not geo_data:
            return "City not found", 404
            
        lat = geo_data[0]['lat']
        lon = geo_data[0]['lon']
        location_name = geo_data[0]['name']
        if 'country' in geo_data[0]:
            location_name += f", {geo_data[0]['country']}"

        # 2. Weather Data (Current Weather Data 2.5)
        weather_url = "https://api.openweathermap.org/data/2.5/weather"
        weather_params = {
            'lat': lat,
            'lon': lon,
            'appid': api_key,
            'units': 'metric'
        }
        
        weather_resp = requests.get(weather_url, params=weather_params)

        if weather_resp.status_code != 200:
            return f"Failed to fetch weather data: {weather_resp.text}", weather_resp.status_code

        d = weather_resp.json()
        
        # Prepare data for template
        weather_data = {
            'name': location_name,
            'temp': round(d['main']['temp']),
            'feels_like': round(d['main']['feels_like']),
            'description': d['weather'][0]['description'].capitalize(),
            'main': d['weather'][0]['main'],
            'icon': d['weather'][0]['icon'],
            'wind_speed': d['wind']['speed'], 
            'humidity': d['main']['humidity'],
            'visibility': d.get('visibility', 0) / 1000, # convert to km
            'pressure': d['main']['pressure'],
            # Approx dew point
            'dew_point': round(d['main'].get('temp', 0) - ((100 - d['main']['humidity']) / 5)) 
        }

        return render_template('dashboard.html', weather=weather_data)

    except Exception as e:
        return str(e), 500

@main_bp.route('/weather')
def get_weather():
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return jsonify({"error": "API key not configured"}), 500

    city = request.args.get('city')
    country = request.args.get('country')

    if not city:
        return jsonify({"error": "City parameter is required"}), 400

    # 1. Geocoding
    geo_url = "http://api.openweathermap.org/geo/1.0/direct"
    q_param = f"{city},{country}" if country else city
    
    geo_params = {
        'q': q_param,
        'limit': 1,
        'appid': api_key
    }

    try:
        geo_resp = requests.get(geo_url, params=geo_params)
        if geo_resp.status_code != 200:
             return jsonify({"error": "Failed to geocode city", "details": geo_resp.text}), geo_resp.status_code
        
        geo_data = geo_resp.json()
        if not geo_data:
            return jsonify({"error": "City not found"}), 404
            
        lat = geo_data[0]['lat']
        lon = geo_data[0]['lon']
        location_name = geo_data[0]['name']
        if 'country' in geo_data[0]:
            location_name += f", {geo_data[0]['country']}"

        # 2. Weather Data (Current Weather Data 2.5)
        weather_url = "https://api.openweathermap.org/data/2.5/weather"
        weather_params = {
            'lat': lat,
            'lon': lon,
            'appid': api_key
        }
        
        weather_resp = requests.get(weather_url, params=weather_params)

        if weather_resp.status_code != 200:
            return jsonify({"error": "Failed to fetch weather data", "details": weather_resp.text}), weather_resp.status_code

        d = weather_resp.json()
        print(d)
        
        # Transform structure to match what frontend expects
        data = {
            'name': location_name,
            'current': {
                'temp': d['main']['temp'],
                'weather': d['weather']
            }
        }
        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
