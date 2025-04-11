# main.py
import os
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime

from processor import DocumentProcessor
from template_manager import TemplateManager
from llm_extractor import LLMDataExtractor  # Or use LocalLLMDataExtractor

# Create necessary directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("processed", exist_ok=True)
os.makedirs("templates", exist_ok=True)
os.makedirs("output", exist_ok=True)

# Initialize components
document_processor = DocumentProcessor()
template_manager = TemplateManager()

# Try to initialize LLM extractor, but have a fallback if not available
try:
    data_extractor = LLMDataExtractor()
except Exception as e:
    print(f"Warning: LLM extractor not available: {str(e)}")
    print("Using basic extraction only")
    data_extractor = None

# Create FastAPI application
app = FastAPI(title="Bill Processing System")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define Pydantic models for request/response validation
class ProcessingResult(BaseModel):
    bill_id: str
    status: str
    extracted_data: Dict[str, Any]
    template_id: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None

class ProcessingRequest(BaseModel):
    bill_id: str
    template_id: Optional[str] = None

class TemplateData(BaseModel):
    name: str
    description: str
    fields: Dict[str, Any]
    identification: Optional[Dict[str, Any]] = None

# Background task for processing documents
def process_document_task(filename: str, bill_id: str, template_id: Optional[str] = None):
    try:
        # Step 1: Extract data using OCR
        basic_data = document_processor.process_document(filename)
        
        # Get the full text from the document for better extraction
        file_path = os.path.join("uploads", filename)
        ocr_text = ""
        
        # This is a simplified version - in reality you'd reuse the OCR from process_document
        if file_path.endswith('.pdf'):
            from pdf2image import convert_from_path
            import pytesseract
            
            pages = convert_from_path(file_path, 300)
            for page in pages:
                ocr_text += pytesseract.image_to_string(page) + "\n"
        
        # Step 2: Use LLM for enhanced extraction if available
        if data_extractor:
            extracted_data = data_extractor.extract_data(ocr_text)
        else:
            extracted_data = basic_data
        
        # Step 3: Identify the best template if none specified
        if not template_id:
            template_id = template_manager.identify_template(extracted_data, ocr_text)
        
        # Step 4: Map the data to the template
        template_mapped = template_manager.map_to_template(template_id, extracted_data)
        
        # Step 5: Save the results
        result = {
            "bill_id": bill_id,
            "filename": filename,
            "processed_date": datetime.now().isoformat(),
            "status": "completed",
            "extracted_data": extracted_data,
            "template_id": template_id,
            "template_data": template_mapped,
            "validation": template_mapped.get("validation", {})
        }
        
        result_path = os.path.join("processed", f"{bill_id}.json")
        with open(result_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        return result
    
    except Exception as e:
        # Log the error
        error_result = {
            "bill_id": bill_id,
            "status": "error",
            "error": str(e)
        }
        
        result_path = os.path.join("processed", f"{bill_id}.json")
        with open(result_path, 'w') as f:
            json.dump(error_result, f, indent=2)
        
        return error_result

# API Endpoints
@app.post("/upload-bill/", response_model=dict)
async def upload_bill(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    template_id: str = Form(None),
    notes: str = Form(None)
):
    """
    Upload a bill for processing
    """
    # Generate unique identifiers
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bill_id = str(uuid.uuid4())[:8]
    extension = os.path.splitext(file.filename)[1]
    
    # Save the file
    filename = f"{timestamp}_{bill_id}{extension}"
    file_path = os.path.join("uploads", filename)
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Queue processing in background
    background_tasks.add_task(process_document_task, filename, bill_id, template_id)
    
    return {
        "status": "processing",
        "message": "Bill uploaded and queued for processing",
        "bill_id": bill_id,
        "filename": filename
    }

@app.get("/bill/{bill_id}", response_model=dict)
async def get_bill_status(bill_id: str):
    """
    Get the status and data for a processed bill
    """
    result_path = os.path.join("processed", f"{bill_id}.json")
    
    if not os.path.exists(result_path):
        return {
            "status": "processing",
            "message": "Bill is still being processed"
        }
    
    with open(result_path, 'r') as f:
        result = json.load(f)
    
    return result

@app.post("/reprocess-bill/", response_model=dict)
async def reprocess_bill(
    background_tasks: BackgroundTasks,
    request: ProcessingRequest
):
    """
    Reprocess a bill with a specific template
    """
    # Find the original file
    bill_id = request.bill_id
    result_path = os.path.join("processed", f"{bill_id}.json")
    
    if not os.path.exists(result_path):
        raise HTTPException(status_code=404, detail="Bill not found")
    
    with open(result_path, 'r') as f:
        result = json.load(f)
    
    filename = result.get("filename")
    if not filename or not os.path.exists(os.path.join("uploads", filename)):
        raise HTTPException(status_code=404, detail="Original bill file not found")
    
    # Queue reprocessing with specified template
    background_tasks.add_task(
        process_document_task, 
        filename, 
        bill_id, 
        request.template_id
    )
    
    return {
        "status": "reprocessing",
        "message": "Bill queued for reprocessing",
        "bill_id": bill_id
    }

@app.get("/templates/", response_model=Dict[str, Any])
async def get_templates():
    """
    Get all available templates
    """
    return template_manager.get_all_templates()

@app.get("/template/{template_id}", response_model=Dict[str, Any])
async def get_template(template_id: str):
    """
    Get a specific template
    """
    template = template_manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template

@app.post("/template/{template_id}", response_model=Dict[str, str])
async def save_template(template_id: str, template_data: TemplateData):
    """
    Save a new or update an existing template
    """
    success = template_manager.save_template(template_id, template_data.dict())
    
    if success:
        return {
            "status": "success",
            "message": f"Template {template_id} saved successfully"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to save template")

@app.get("/")
async def root():
    return {
        "app": "Bill Processing System",
        "version": "1.0.0",
        "status": "running"
    }

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)