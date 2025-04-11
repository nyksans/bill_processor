# app.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import uuid
from datetime import datetime
from typing import List

# Initialize FastAPI
app = FastAPI(title="Bill Processor API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create necessary directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("processed", exist_ok=True)

@app.post("/upload-bill/")
async def upload_bill(
    file: UploadFile = File(...),
    company_name: str = Form(None),
    notes: str = Form(None)
):
    """
    Upload a bill file (PDF, JPG, PNG) for processing
    """
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_id = str(uuid.uuid4())[:8]
    extension = os.path.splitext(file.filename)[1]
    
    # Save the file
    filename = f"{timestamp}_{file_id}{extension}"
    file_path = os.path.join("uploads", filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Queue for processing (in a real app, this would use Celery or similar)
    # For now, just return success
    return {
        "status": "success",
        "message": "Bill uploaded successfully",
        "file_id": file_id,
        "filename": filename,
        "company_name": company_name,
        "notes": notes
    }

@app.get("/")
async def root():
    return {"message": "Bill Processing API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)