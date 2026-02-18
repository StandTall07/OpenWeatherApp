
from unittest.mock import patch

def test_dashboard_city_not_found(client):
    """Test dashboard route with non-existent city returns 404."""
    with patch("os.getenv", return_value="fake_api_key"):
        with patch("requests.get") as mock_get:
            # Mock geocoding returning empty list (city not found)
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = []
            
            response = client.get("/dashboard?city=UnknownCity")
            assert response.status_code == 404
            assert b"City not found" in response.data

def test_dashboard_api_key_missing(client):
    """Test dashboard route without API key configured returns 500."""
    with patch("os.getenv", return_value=None):
        response = client.get("/dashboard?city=London")
        assert response.status_code == 500
        assert b"API key not configured" in response.data
