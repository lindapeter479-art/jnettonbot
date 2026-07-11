import os
import requests
import json
import logging

logger = logging.getLogger(__name__)

class DictionaryAPI:
    """Helper class for dictionary API calls."""
    
    def __init__(self):
        # Using the free Dictionary API
        self.base_url = "https://api.dictionaryapi.dev/api/v2/entries/en"
        self.wordnik_url = "https://api.wordnik.com/v4/word.json"
        # You can get a free Wordnik API key at https://www.wordnik.com/signup
        self.wordnik_key = os.environ.get("WORDNIK_API_KEY", "")  # FIXED: Correct spelling
    
    def get_definition(self, word):
        """Get definition of a word."""
        try:
            url = f"{self.base_url}/{word}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0]
            return {"error": "Word not found"}
        except Exception as e:
            logger.error(f"Error fetching definition: {e}")
            return {"error": "API error"}
    
    def get_synonyms(self, word):
        """Get synonyms for a word."""
        try:
            url = f"{self.base_url}/{word}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                synonyms = []
                
                if data and len(data) > 0:
                    for meaning in data[0].get("meanings", []):
                        for definition in meaning.get("definitions", []):
                            synonyms.extend(definition.get("synonyms", []))
                
                # Remove duplicates
                synonyms = list(set(synonyms))
                return {"synonyms": synonyms}
            
            return {"error": "Word not found", "synonyms": []}
        except Exception as e:
            logger.error(f"Error fetching synonyms: {e}")
            return {"error": "API error", "synonyms": []}
    
    def get_examples(self, word):
        """Get example sentences for a word."""
        try:
            url = f"{self.base_url}/{word}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                examples = []
                
                if data and len(data) > 0:
                    for meaning in data[0].get("meanings", []):
                        for definition in meaning.get("definitions", []):
                            if definition.get("example"):
                                examples.append(definition.get("example"))
                
                return {"examples": examples}
            
            return {"error": "Word not found", "examples": []}
        except Exception as e:
            logger.error(f"Error fetching examples: {e}")
            return {"error": "API error", "examples": []}
