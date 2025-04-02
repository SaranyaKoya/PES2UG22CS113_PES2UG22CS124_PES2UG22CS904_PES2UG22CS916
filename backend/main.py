from fastapi import FastAPI
from routes.function_routes import router as function_router  # Ensure correct import

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Lambda Function API is running!"}

app.include_router(function_router, prefix="/functions")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

