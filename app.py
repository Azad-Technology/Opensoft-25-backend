from datetime import datetime
from fastapi.responses import HTMLResponse
import pytz
import src.runner
import gradio as gr
from src.chatbot.index import demo


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
from src.routers.chat import router as chat_router
from src.routers.employee import router as employee_router
from src.routers.admin import router as admin_router
from src.routers.common import router as common_router

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(chat_router, prefix="/chat", tags=["Chat"])
app.include_router(employee_router, prefix="/employee", tags=["Employee Analysis"])
app.include_router(admin_router, prefix="/admin", tags=["Admin Analysis"])
app.include_router(common_router, prefix="/common", tags=["Common"])

app = gr.mount_gradio_app(app, demo, path = "/gradio")

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