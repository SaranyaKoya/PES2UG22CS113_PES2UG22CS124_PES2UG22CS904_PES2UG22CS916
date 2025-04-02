from fastapi import APIRouter
import subprocess

router = APIRouter()

@router.post("/execute")  
def execute_function(data: dict):
    function_code = data.get("functionCode", "")

    if not function_code:
        return {"error": "No function code provided"}

    try:
        result = subprocess.run(["python3", "-c", function_code], capture_output=True, text=True)
        return {"output": result.stdout.strip()}
    except Exception as e:
        return {"error": str(e)}

