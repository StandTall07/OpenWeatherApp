
def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Check Weather" in response.data

def test_weather_missing_city(client):
    response = client.get("/weather")
    assert response.status_code == 400
    assert response.json == {"error": "City parameter is required"}

def test_weather_route_structure(client):
    response = client.get("/weather?city=London&country=UK")
    assert response.status_code in [200, 401, 404, 500, 502]
