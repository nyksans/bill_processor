# processor.py
import os
import cv2
import pytesseract
from pdf2image import convert_from_path
import numpy as np
from PIL import Image
import re
from typing import Dict, List, Tuple, Any

# Configuration
pytesseract.pytesseract.tesseract_cmd = r'tesseract'  # Update this path if needed

class DocumentProcessor:
    """
    Handles the processing of bill documents, including OCR and data extraction
    """
    def __init__(self, uploads_dir="uploads", processed_dir="processed"):
        self.uploads_dir = uploads_dir
        self.processed_dir = processed_dir
        os.makedirs(processed_dir, exist_ok=True)
    
    def process_document(self, filename: str) -> Dict[str, Any]:
        """
        Process a document and extract key information
        """
        file_path = os.path.join(self.uploads_dir, filename)
        extension = os.path.splitext(filename)[1].lower()
        
        # Convert document to images
        if extension == '.pdf':
            images = self._pdf_to_images(file_path)
        elif extension in ['.jpg', '.jpeg', '.png']:
            images = [cv2.imread(file_path)]
        else:
            raise ValueError(f"Unsupported file format: {extension}")
        
        # Process each image
        extracted_text = ""
        for img in images:
            # Preprocess image for better OCR
            preprocessed = self._preprocess_image(img)
            
            # Perform OCR
            text = pytesseract.image_to_string(preprocessed)
            extracted_text += text + "\n"
        
        # Extract structured data
        bill_data = self._extract_bill_data(extracted_text)
        
        # Save processed results
        processed_path = os.path.join(self.processed_dir, f"processed_{filename}.json")
        # In a real implementation, save the bill_data to JSON here
        
        return bill_data
    
    def _pdf_to_images(self, pdf_path: str) -> List[np.ndarray]:
        """Convert PDF to a list of images"""
        pages = convert_from_path(pdf_path, 300)  # DPI=300
        images = []
        
        for page in pages:
            # Convert PIL Image to OpenCV format
            img = np.array(page)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            images.append(img)
            
        return images
    
    def _preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR results"""
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding
        _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Optional: Apply noise reduction
        denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)
        
        return denoised
    
    def _extract_bill_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from OCR text"""
        bill_data = {
            'invoice_number': None,
            'date': None,
            'due_date': None,
            'total_amount': None,
            'vendor_name': None,
            'line_items': []
        }
        
        # Extract invoice number (typical formats: INV-12345, #12345, etc.)
        inv_match = re.search(r'(?:invoice|inv|invoice number|inv no)[\s#:]*([a-z0-9\-]+)', 
                             text, re.IGNORECASE)
        if inv_match:
            bill_data['invoice_number'] = inv_match.group(1)
        
        # Extract date (common formats: MM/DD/YYYY, DD-MM-YYYY, etc.)
        date_match = re.search(r'(?:date|invoice date)[\s:]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})', 
                              text, re.IGNORECASE)
        if date_match:
            bill_data['date'] = date_match.group(1)
        
        # Extract total amount (look for patterns like "Total: $123.45")
        amount_match = re.search(r'(?:total|amount due|balance due)[\s:]*[\$£€]?(\d+(?:,\d+)*(?:\.\d+)?)', 
                                text, re.IGNORECASE)
        if amount_match:
            # Remove commas and convert to float
            amount_str = amount_match.group(1).replace(',', '')
            bill_data['total_amount'] = float(amount_str)
        
        # Extract vendor name (typically at the top of the invoice)
        # This is simplified and might need enhancement for real invoices
        lines = text.strip().split('\n')
        if lines:
            potential_vendor = lines[0].strip()
            if len(potential_vendor) > 1 and len(potential_vendor) < 50:  # Reasonable length for a company name
                bill_data['vendor_name'] = potential_vendor
        
        return bill_data

# Usage example
if __name__ == "__main__":
    processor = DocumentProcessor()
    # Test with a sample file
    if os.path.exists("uploads/sample_bill.pdf"):
        result = processor.process_document("sample_bill.pdf")
        print(result)
    else:
        print("Please upload a test file to the uploads directory")