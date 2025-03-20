from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_items():
    return [{"item_name": "Laptop"}, {"item_name": "Phone"}]

@router.get("/{item_id}")
async def get_item(item_id: int):
    return {"item_name": f"Item {item_id}"}

@router.post("/")
async def create_item(item: dict):
    return {"message": "Item created successfully", "item": item}
