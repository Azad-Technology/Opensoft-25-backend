from datetime import datetime
from fastapi.responses import HTMLResponse
import pytz
from utils.api_key_rotate import APIKeyManager
from utils.config import settings

groq_api_manager = APIKeyManager(
    api_keys=[settings.GROQ_API_KEY1, settings.GROQ_API_KEY2],
    rate_limit=30,
    cooldown_period=60
)

google_api_manager = APIKeyManager(
    api_keys=[settings.GOOGLE_API_KEY1, settings.GOOGLE_API_KEY2],
    rate_limit=10,
    cooldown_period=60
)


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

from src.routers.auth import router as auth_router

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

@app.get("/", response_class=HTMLResponse)
async def read_root():
    # Get the current UTC time
    utc_now = datetime.utcnow()

    # Convert the current UTC time to Indian Standard Time (IST)
    ist_now = utc_now.replace(tzinfo=pytz.utc).astimezone(pytz.timezone("Asia/Kolkata"))

    # Format the IST time
    formatted_time = ist_now.strftime("%a %b %d %Y %H:%M:%S IST (Indian Standard Time)")

    html_content = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body>
      <div class="h-screen w-screen bg-black flex items-center justify-center">
        <div style="width: 800px" class="text-gray-100 text-center">
          <h1 class="text-5xl font-bold">System is Live! 🎉</h1>
          <p class="mt-8">Current time</p>
          <p class="mt-2">{formatted_time}</p>
        </div>
      </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


if __name__ == "__main__":
  # Include routers
  import uvicorn
  uvicorn.run(app, host="0.0.0.0", port=8569)