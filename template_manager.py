# template_manager.py
import json
import os
from typing import Dict, Any, List, Optional

class TemplateManager:
    """
    Manages the templates for different vendors or bill types
    and handles mapping extracted data to these templates
    """
    def __init__(self, templates_dir="templates"):
        self.templates_dir = templates_dir
        os.makedirs(templates_dir, exist_ok=True)
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Any]:
        """Load all saved templates"""
        templates = {}
        
        # If no templates exist yet, create some sample ones
        if not os.listdir(self.templates_dir):
            self._create_sample_templates()
            
        # Load all template files
        for filename in os.listdir(self.templates_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.templates_dir, filename)
                with open(file_path, 'r') as f:
                    template_data = json.load(f)
                    template_id = os.path.splitext(filename)[0]
                    templates[template_id] = template_data
        
        return templates
    
    def _create_sample_templates(self):
        """Create sample templates for demonstration"""
        # Generic bill template
        generic_template = {
            "name": "Generic Bill",
            "description": "Standard template for most bills",
            "fields": {
                "vendor_name": {"required": True, "type": "string"},
                "invoice_number": {"required": True, "type": "string"},
                "date": {"required": True, "type": "date"},
                "due_date": {"required": False, "type": "date"},
                "total_amount": {"required": True, "type": "number"},
                "line_items": {"required": False, "type": "array"},
                "tax_amount": {"required": False, "type": "number"},
                "notes": {"required": False, "type": "string"}
            },
            "identification": {
                "keywords": []
            }
        }
        
        # Utility bill template
        utility_template = {
            "name": "Utility Bill",
            "description": "For electricity, water, gas bills",
            "fields": {
                "vendor_name": {"required": True, "type": "string"},
                "invoice_number": {"required": True, "type": "string"},
                "account_number": {"required": True, "type": "string"},
                "service_address": {"required": True, "type": "string"},
                "service_period": {"required": True, "type": "string"},
                "current_reading": {"required": False, "type": "number"},
                "previous_reading": {"required": False, "type": "number"},
                "usage": {"required": False, "type": "number"},
                "rate": {"required": False, "type": "number"},
                "date": {"required": True, "type": "date"},
                "due_date": {"required": True, "type": "date"},
                "total_amount": {"required": True, "type": "number"}
            },
            "identification": {
                "keywords": ["utility", "electric", "electricity", "water", "gas", "service", "meter"]
            }
        }
        
        # Save sample templates
        with open(os.path.join(self.templates_dir, "generic.json"), 'w') as f:
            json.dump(generic_template, f, indent=2)
            
        with open(os.path.join(self.templates_dir, "utility.json"), 'w') as f:
            json.dump(utility_template, f, indent=2)
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific template by ID"""
        return self.templates.get(template_id)
    
    def get_all_templates(self) -> Dict[str, Any]:
        """Get all available templates"""
        return self.templates
    
    def identify_template(self, extracted_data: Dict[str, Any], ocr_text: str) -> str:
        """
        Identify the most appropriate template for the extracted data
        """
        best_match = "generic"  # Default to generic template
        best_score = 0
        
        # Check each template for keyword matches
        for template_id, template in self.templates.items():
            score = 0
            
            # Check for keywords in OCR text
            keywords = template.get("identification", {}).get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in ocr_text.lower():
                    score += 1
            
            # Check for field matches
            required_fields = [field for field, config in template.get("fields", {}).items() 
                              if config.get("required", False)]
            
            for field in required_fields:
                if field in extracted_data and extracted_data[field]:
                    score += 2  # Give higher weight to matched required fields
            
            if score > best_score:
                best_score = score
                best_match = template_id
        
        return best_match
    
    def map_to_template(self, template_id: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map extracted data to the specified template format
        """
        template = self.get_template(template_id)
        if not template:
            return {'error': f'Template {template_id} not found'}
        
        mapped_data = {
            "template_id": template_id,
            "template_name": template.get("name", "Unknown Template"),
            "data": {}
        }
        
        # Map extracted data to template fields
        for field, config in template.get("fields", {}).items():
            if field in extracted_data:
                mapped_data["data"][field] = extracted_data[field]
            else:
                mapped_data["data"][field] = None
        
        # Validate required fields
        missing_required = []
        for field, config in template.get("fields", {}).items():
            if config.get("required", False) and (field not in mapped_data["data"] or mapped_data["data"][field] is None):
                missing_required.append(field)
        
        if missing_required:
            mapped_data["validation"] = {
                "status": "incomplete",
                "missing_required": missing_required
            }
        else:
            mapped_data["validation"] = {
                "status": "complete"
            }
        
        return mapped_data
    
    def save_template(self, template_id: str, template_data: Dict[str, Any]) -> bool:
        """
        Save a new or updated template
        """
        try:
            file_path = os.path.join(self.templates_dir, f"{template_id}.json")
            with open(file_path, 'w') as f:
                json.dump(template_data, f, indent=2)
            
            # Update in-memory templates
            self.templates[template_id] = template_data
            return True
        except Exception as e:
            print(f"Error saving template: {str(e)}")
            return False