import json
import os
import re
from typing import List, Dict, Any
import pandas as pd
from bs4 import BeautifulSoup
import html2text
from sentence_transformers import SentenceTransformer

class DataProcessor:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.data_path = os.getenv('DATA_PATH', './patent_jsons_ML Assignment/patent_jsons/')
        
    def clean_html_content(self, content: str) -> str:
        """Clean HTML markup from text content."""
        if not content:
            return ""
        
        # Use BeautifulSoup to parse and clean HTML
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove all HTML tags and get text
        clean_text = soup.get_text()
        
        # Clean up extra whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        return clean_text
    
    def extract_patent_data(self, patent_json: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant data from a patent JSON object."""
        try:
            # Extract basic information
            patent_number = patent_json.get('patent_number', '')
            
            # Extract title
            titles = patent_json.get('titles', [])
            title = titles[0].get('text', '') if titles else ''
            
            # Extract and clean abstracts
            abstracts = patent_json.get('abstracts', [])
            abstract_text = ""
            if abstracts:
                abstract_content = abstracts[0].get('paragraph_markup', '')
                abstract_text = self.clean_html_content(abstract_content)
            
            # Extract and clean claims
            claims = patent_json.get('claims', [])
            claims_text = ""
            if claims:
                claims_list = claims[0].get('claims', [])
                claims_texts = []
                for claim in claims_list[:5]:  # Take first 5 claims to avoid too much text
                    claim_content = claim.get('paragraph_markup', '')
                    clean_claim = self.clean_html_content(claim_content)
                    claims_texts.append(clean_claim)
                claims_text = " ".join(claims_texts)
            
            # Extract and clean descriptions
            descriptions = patent_json.get('descriptions', [])
            description_text = ""
            if descriptions:
                desc_content = descriptions[0].get('paragraph_markup', '')
                description_text = self.clean_html_content(desc_content)
                # Limit description length to avoid overwhelming the model
                description_text = description_text[:2000] + "..." if len(description_text) > 2000 else description_text
            
            # Combine abstract and claims for searchable text
            searchable_text = f"{abstract_text} {claims_text}".strip()
            
            return {
                'patent_number': patent_number,
                'title': title,
                'abstract': abstract_text,
                'claims': claims_text,
                'description': description_text,
                'searchable_text': searchable_text
            }
            
        except Exception as e:
            print(f"Error processing patent {patent_json.get('patent_number', 'unknown')}: {e}")
            return None
    
    def load_and_process_documents(self) -> List[Dict[str, Any]]:
        """Load all patent JSON files and process them."""
        documents = []
        
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Data path not found: {self.data_path}")
        
        json_files = [f for f in os.listdir(self.data_path) if f.endswith('.json')]
        
        print(f"Found {len(json_files)} JSON files to process...")
        
        for i, filename in enumerate(json_files):
            try:
                file_path = os.path.join(self.data_path, filename)
                
                with open(file_path, 'r', encoding='utf-8') as file:
                    patent_data = json.load(file)
                
                processed_doc = self.extract_patent_data(patent_data)
                
                if processed_doc and processed_doc['searchable_text']:
                    # Generate embeddings for the searchable text
                    embedding = self.model.encode(processed_doc['searchable_text'])
                    processed_doc['embedding'] = embedding.tolist()
                    
                    documents.append(processed_doc)
                
                if (i + 1) % 50 == 0:
                    print(f"Processed {i + 1}/{len(json_files)} files...")
                    
            except Exception as e:
                print(f"Error loading file {filename}: {e}")
                continue
        
        print(f"Successfully processed {len(documents)} documents.")
        return documents
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a given text."""
        embedding = self.model.encode(text)
        return embedding.tolist()