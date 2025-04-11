# llm_extractor.py
import os
from langchain.llms import HuggingFaceHub
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import json
from typing import Dict, Any

class LLMDataExtractor:
    """
    Use a language model to extract structured data from OCR text
    """
    def __init__(self):
        # Use HuggingFaceHub for accessing open source models
        # You'll need to set HUGGINGFACEHUB_API_TOKEN in your environment
        # or use a local model instead
        self.llm = HuggingFaceHub(
            repo_id="mistralai/Mistral-7B-Instruct-v0.2",
            model_kwargs={"temperature": 0.1, "max_length": 2048}
        )
        
        # Create a prompt template for extracting bill information
        self.prompt_template = PromptTemplate(
            input_variables=["bill_text"],
            template="""
            Extract the following information from this bill text. 
            Return the results in JSON format with these keys:
            - invoice_number
            - date
            - due_date
            - total_amount (as a number without currency symbols)
            - vendor_name
            - vendor_address
            - bill_to_name
            - bill_to_address
            - line_items (as an array of objects with description, quantity, unit_price, and total)
            
            If any field is not found, use null.
            
            BILL TEXT:
            {bill_text}
            
            JSON RESULT:
            """
        )
        
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt_template)
    
    def extract_data(self, text: str) -> Dict[str, Any]:
        """
        Use the LLM to extract structured data from OCR text
        """
        try:
            # Get the LLM response
            response = self.chain.run(bill_text=text)
            
            # Parse the JSON response
            # This might need error handling for real-world use
            # as the LLM output format isn't guaranteed
            parsed_data = json.loads(response)
            return parsed_data
        except Exception as e:
            print(f"Error extracting data with LLM: {str(e)}")
            # Return a basic structure in case of error
            return {
                'invoice_number': None,
                'date': None,
                'due_date': None,
                'total_amount': None,
                'vendor_name': None,
                'error': str(e)
            }

# Alternative implementation using a local model
class LocalLLMDataExtractor:
    """
    Use a locally hosted language model for data extraction
    """
    def __init__(self, model_path="llama-3-8b"):
        try:
            from langchain.llms import LlamaCpp
            
            # Initialize local LLM
            self.llm = LlamaCpp(
                model_path=model_path,
                temperature=0.1,
                max_tokens=2048,
                top_p=1
            )
            
            # Create prompt template
            self.prompt_template = PromptTemplate(
                input_variables=["bill_text"],
                template="""
                Extract the following information from this bill text. 
                Return the results in JSON format with these keys:
                - invoice_number
                - date
                - due_date
                - total_amount (as a number without currency symbols)
                - vendor_name
                - vendor_address
                - bill_to_name
                - bill_to_address
                - line_items (as an array of objects with description, quantity, unit_price, and total)
                
                If any field is not found, use null.
                
                BILL TEXT:
                {bill_text}
                
                JSON RESULT:
                """
            )
            
            self.chain = LLMChain(llm=self.llm, prompt=self.prompt_template)
        except ImportError:
            print("LlamaCpp not available. Install with: pip install llama-cpp-python")
            self.llm = None
    
    def extract_data(self, text: str) -> Dict[str, Any]:
        """Use the local LLM to extract data"""
        if not self.llm:
            return {'error': 'Local LLM not initialized'}
        
        try:
            response = self.chain.run(bill_text=text)
            parsed_data = json.loads(response)
            return parsed_data
        except Exception as e:
            return {
                'invoice_number': None,
                'date': None,
                'due_date': None,
                'total_amount': None,
                'vendor_name': None,
                'error': str(e)
            }