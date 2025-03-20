from fastapi import FastAPI
from app.routers import users, items

app = FastAPI(
    title="Deolite",
    description="Problem statement for Deolite",
    version="1.0.0"
)

# Include routers
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(items.router, prefix="/items", tags=["Items"])

@app.get("/")
async def root():
    return {"message": "Welcome to the FastAPI Modular Project!"}
