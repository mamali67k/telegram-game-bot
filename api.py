from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def api_root():
    return {"message": "API endpoint is working"}
