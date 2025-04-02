import requests

BASE_URL = "http://127.0.0.1:8000"

def test_execute_function():
    response = requests.post(
        f"{BASE_URL}/functions/execute",
        json={"functionCode": "print('Lambda Execution Works!')"}
    )
    assert response.status_code == 200
    assert "output" in response.json()
