from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List
import uuid
from datetime import datetime
import base64
from PIL import Image
import io
from rembg import remove
import asyncio
from concurrent.futures import ThreadPoolExecutor

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Thread pool for CPU-intensive tasks
executor = ThreadPoolExecutor(max_workers=2)

# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class BackgroundRemovalRequest(BaseModel):
    image_data: str  # base64 encoded image
    filename: str

class BackgroundRemovalResponse(BaseModel):
    success: bool
    processed_image: str = None  # base64 encoded processed image
    error: str = None
    processing_time: float = None

def remove_background_sync(image_bytes):
    """Synchronous background removal function"""
    try:
        # Open image from bytes
        input_image = Image.open(io.BytesIO(image_bytes))
        
        # Remove background
        output_image = remove(input_image)
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        output_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return img_buffer.getvalue()
    except Exception as e:
        raise Exception(f"Background removal failed: {str(e)}")

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Background Removal API Ready"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

@api_router.post("/remove-background", response_model=BackgroundRemovalResponse)
async def remove_background_endpoint(request: BackgroundRemovalRequest):
    start_time = datetime.now()
    
    try:
        # Decode base64 image
        try:
            # Remove data URL prefix if present
            if ',' in request.image_data:
                image_data = request.image_data.split(',')[1]
            else:
                image_data = request.image_data
                
            image_bytes = base64.b64decode(image_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")
        
        # Validate image
        try:
            test_image = Image.open(io.BytesIO(image_bytes))
            test_image.verify()
            # Reset bytes stream
            image_bytes = base64.b64decode(image_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image format: {str(e)}")
        
        # Process image in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        processed_bytes = await loop.run_in_executor(
            executor, 
            remove_background_sync, 
            image_bytes
        )
        
        # Encode result to base64
        processed_base64 = base64.b64encode(processed_bytes).decode('utf-8')
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return BackgroundRemovalResponse(
            success=True,
            processed_image=processed_base64,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Background removal error: {str(e)}")
        processing_time = (datetime.now() - start_time).total_seconds()
        return BackgroundRemovalResponse(
            success=False,
            error=str(e),
            processing_time=processing_time
        )

@api_router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """Alternative endpoint for file upload"""
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file content
        content = await file.read()
        
        # Encode to base64
        encoded_content = base64.b64encode(content).decode('utf-8')
        
        return {
            "success": True,
            "filename": file.filename,
            "image_data": encoded_content,
            "content_type": file.content_type
        }
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    executor.shutdown(wait=True)