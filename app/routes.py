
from flask import Blueprint, jsonify, request, render_template, current_app
import requests
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template('index.html')

@main_bp.route('/dashboard')
def dashboard():
    city = request.args.get('city')
    country = request.args.get('country')
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    api_key = os.getenv("OPENWEATHER_API_KEY")

    if (not city and not (lat and lon)) or not api_key:
        return render_template('dashboard.html', weather=None)

    # 1. Geocoding / Location Logic
    location_name = "Your Location"
    
    try:
        if city:
            geo_url = "http://api.openweathermap.org/geo/1.0/direct"
            q_param = f"{city},{country}" if country else city
            geo_params = {'q': q_param, 'limit': 1, 'appid': api_key}
            
            geo_resp = requests.get(geo_url, params=geo_params)
            if geo_resp.status_code != 200 or not geo_resp.json():
                return render_template('dashboard.html', weather=None, error="City not found")
            
            geo_data = geo_resp.json()[0]
            lat, lon = geo_data['lat'], geo_data['lon']
            location_name = geo_data['name']
            if 'country' in geo_data:
                location_name += f", {geo_data['country']}"
        else:
             # Reverse geocoding to get name from coords
             rev_geo_url = "http://api.openweathermap.org/geo/1.0/reverse"
             rev_params = {'lat': lat, 'lon': lon, 'limit': 1, 'appid': api_key}
             rev_resp = requests.get(rev_geo_url, params=rev_params)
             if rev_resp.status_code == 200 and rev_resp.json():
                 rev_data = rev_resp.json()[0]
                 location_name = rev_data['name']
                 if 'country' in rev_data:
                     location_name += f", {rev_data['country']}"

        # 2. Weather Data
        weather_url = "https://api.openweathermap.org/data/2.5/weather"
        weather_params = {'lat': lat, 'lon': lon, 'appid': api_key, 'units': 'metric'}
        weather_resp = requests.get(weather_url, params=weather_params)
        
        if weather_resp.status_code != 200:
             return render_template('dashboard.html', weather=None, error="Failed to fetch weather")

        d = weather_resp.json()
        
        temp = d['main']['temp']
        humidity = d['main']['humidity']
        dew_point = temp - ((100 - humidity) / 5)

        icon_code = d['weather'][0]['icon']
        icon_class = 'fas fa-cloud' # Default
        if icon_code == '01d': icon_class = 'fas fa-sun text-warning'
        elif icon_code == '01n': icon_class = 'fas fa-moon text-warning'
        elif icon_code in ['02d', '02n']: icon_class = 'fas fa-cloud-sun text-warning' if 'd' in icon_code else 'fas fa-cloud-moon text-info'
        elif icon_code in ['03d', '03n', '04d', '04n']: icon_class = 'fas fa-cloud text-info'
        elif icon_code in ['09d', '09n']: icon_class = 'fas fa-cloud-showers-heavy text-info'
        elif icon_code in ['10d', '10n']: icon_class = 'fas fa-cloud-sun-rain text-warning' if 'd' in icon_code else 'fas fa-cloud-moon-rain text-info'
        elif icon_code in ['11d', '11n']: icon_class = 'fas fa-bolt text-danger'
        elif icon_code in ['13d', '13n']: icon_class = 'fas fa-snowflake text-info'
        elif icon_code in ['50d', '50n']: icon_class = 'fas fa-smog text-secondary'

        # 3. Unsplash Image
        unsplash_access_key = os.getenv("UNSPLASH_ACCESS_KEY")
        image_url = None
        if unsplash_access_key:
            unsplash_url = "https://api.unsplash.com/search/photos"
            # Search query: "City weather description" e.g. "London scattered clouds"
            query = f"{location_name} {d['weather'][0]['description']}"
            unsplash_params = {
                'query': query,
                'page': 1,
                'per_page': 1,
                'orientation': 'landscape',
                'client_id': unsplash_access_key
            }
            try:
                unsplash_resp = requests.get(unsplash_url, params=unsplash_params)
                if unsplash_resp.status_code == 200:
                    unsplash_data = unsplash_resp.json()
                    if unsplash_data['results']:
                        image_url = unsplash_data['results'][0]['urls']['regular']
            except Exception:
                # Fallback or log error, but don't crash dashboard
                pass
        
        # Fallback image if Unsplash fails or no key
        if not image_url:
             image_url = "https://images.unsplash.com/photo-1516912481808-3406841bd33c?q=80&w=2544&auto=format&fit=crop" # Generic weather/sky image

        weather_data = {
            'name': location_name,
            'temp': round(temp),
            'feels_like': round(d['main']['feels_like']),
            'temp_min': round(d['main']['temp_min']),
            'description': d['weather'][0]['description'].capitalize(),
            'main': d['weather'][0]['main'],
            'wind_speed': round(d['wind']['speed'] * 3.6), # m/s to km/h
            'humidity': humidity,
            'visibility': round(d.get('visibility', 0) / 1000), # meters to km
            'pressure': d['main']['pressure'],
            'dew_point': round(dew_point),
            'icon_class': icon_class,
            'image_url': image_url
        }
        
        return render_template('dashboard.html', weather=weather_data)

    except Exception as e:
        return render_template('dashboard.html', weather=None, error=str(e))

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
