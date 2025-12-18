from google import genai
from google.genai import types
import os
import requests
from datetime import datetime
import json

class LLMConnector:
    def __init__(self, test_module = "General Knowledge"):
        self.ollama_url = os.getenv('OLLAMA_BASE_URL')
        self.ollama_api_key= os.getenv('OLLAMA_API_KEY')
        self.gemini_api_key = os.getenv('GOOGLE_API_KEY')
        self.gemini_client = genai.Client(api_key = self.gemini_api_key)
        self.ollama_knowledge_id = self._find_or_create_knowledge(test_module) 

#---------------------------------------Main Chat and file management functions-------------------------
    def chat(self, provider, prompt, model, response_schema, folder_path=None):
        if provider == 'ollama':
            self.files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) 
                if os.path.isfile(os.path.join(folder_path, f))]
            response = self._chat_ollama(prompt, model, response_schema)
        elif provider == 'gemini':
            response = self._chat_gemini(prompt, model, response_schema)
        else:
            raise Exception(f"{provider} is an invalid provider. It can only be ollama or gemini")
        return response

    def upload_files(self, provider, folder_path):

        self.files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) 
                if os.path.isfile(os.path.join(folder_path, f))]
        self.uploaded_files = []
        if provider == 'ollama':
            results = self._upload_files_ollama(self.files)
            # print(results)
        elif provider == 'gemini':
            self._upload_files_gemini(self.files)
        else:
            raise Exception(f"{provider} is an invalid provider. It can only be ollama or gemini")


    def cleanup_files(self, provider):
        if provider == 'ollama':
            self._cleanup_knowledge_files()
        elif provider == 'gemini':
            self._delete_files_gemini()
        else:
            raise Exception(f"{provider} is an invalid provider. It can only be ollama or gemini")


# -----------------------------------Ollama helper functions-------------------------------------------

    def _chat_ollama(self, prompt, model = 'gpt-oss:20b', response_schema = None, folder_path = None, tries = 3):

        response_schema_json = response_schema.model_json_schema()

        knowledge = "Here is the knowledge base to refer to do your task \n"
        
        for file_path in self.files:
            with open(file_path, 'r', encoding='utf-8') as f:
                knowledge += f.read() + '\n'
        
        if response_schema:
            json_instruction = (
            f"\n\nYou must respond ONLY with valid JSON matching the given schema {response_schema_json}"
            "Do not include any explanatory text, markdown formatting, or code blocks. "
            "Return raw JSON only. Do not even have any preceding json markdown"
        )
    
        prompt = prompt + knowledge + json_instruction
        headers = {
            'Authorization': f'Bearer {self.ollama_api_key}',
            'Content-Type': 'application/json'
        }

        data = {
        "model": f"{model}", #"gpt-oss:20b" , qwen3-coder:30b
        "messages": [
            {
            "role": "user",
            "content": f"{prompt}"
            }
        ],
        'files': [{'type': 'collection', 'id': self.ollama_knowledge_id}],
        'temperature': 0.7,
        'max_tokens': 25000
        }
        success = False
        for i in range(tries):
            print(f'Run #{i+1} to generate content')
            response = requests.post(self.ollama_url+'chat/completions', headers=headers, json=data)
            # print(response.json())
            if response.status_code == 200:
                result = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                # print(result)
                try:
                    if response_schema:
                        result = self._cleanup_json(result)
                    validated_model = response_schema.model_validate_json(result)
                    success = True
                    return validated_model.model_dump_json(indent=2)
                except:
                    success = False
            # else:
            #     raise Exception("Invalid response status from model")
        if not success:
            raise Exception('Ollama response: LLM unable to produce the necessary output')


    def _upload_files_ollama(self, files):
        results = []
        for file_path in files:
            with open(file_path, 'rb') as f:
                response = requests.post(
                    self.ollama_url + 'v1/files/',
                    headers={
                        'Authorization': f'Bearer {self.ollama_api_key}',
                        'Accept': 'application/json'
                    },
                    files={'file': f}
                )
                result = response.json()
                results.append(result)
                response_knowledge = self._add_file_to_knowledge(
                        file_id=result['id']
                    )
        return results

    def _add_file_to_knowledge(self, file_id):
        url = f'{self.ollama_url}v1/knowledge/{self.ollama_knowledge_id}/file/add'
        print(url)
        headers = {
            'Authorization': f'Bearer {self.ollama_api_key}',
            'Content-Type': 'application/json'
        }
        data = {'file_id': file_id}
        response = requests.post(url, headers=headers, json=data)
        print(f'Adding to knowledge - {response.json()}')
        return response.json()

    def _create_knowledge_collection(self, name, description=""):
        url = f'{self.ollama_url}v1/knowledge/create'
        headers = {
            'Authorization': f'Bearer {self.ollama_api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'name': name,
            'description': description
            # Optional: embedding settings, chunk settings, etc.
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result['id']  # This is your knowledge_id
    
    def _get_knowledge_collections(self):
        url = f'{self.ollama_url}v1/knowledge/'
        headers = {
            'Authorization': f'Bearer {self.ollama_api_key}',
        }
        response = requests.get(url, headers=headers)
        return response.json()  # List of collections

    def _find_or_create_knowledge(self, name):
        collections = self._get_knowledge_collections()
        
        # Check if exists
        for collection in collections:
            if collection['name'] == name:
                return collection['id']
        
        # Create if doesn't exist
        return self._create_knowledge_collection(name)     

    def _cleanup_knowledge_files(self):
        """
        Removes the knowledge collection entirely along with its files
      
        """
        self._delete_knowledge_collection()

    def _delete_knowledge_collection(self):
        url = f'{self.ollama_url}v1/knowledge/{self.ollama_knowledge_id}/delete'
        headers = {
            'Authorization': f'Bearer {self.ollama_api_key}',
        }
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        return response.json()    
    
# -----------------------------------Gemini helper functions-------------------------------------------

    def _chat_gemini(self, prompt, model = 'gemini-2.5-flash', response_schema = None):
        self._load_cache_gemini()
        response = self.gemini_client.models.generate_content(
            model=model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                cached_content=self.cache.name,
                response_mime_type='application/json',
                response_schema=response_schema if response_schema else str 
            )
        )
        return response.text
    

    def _upload_files_gemini(self, files, model = 'gemini-2.5-flash'):
        for file_path in files:
            print(f"Uploading file: {file_path}...")
            # mime_type = 'application/text-plain'

            file_obj = self.gemini_client.files.upload(
                file=file_path
            )
            self.uploaded_files.append(file_obj)
            print(f"Uploaded: {file_obj.display_name} ({file_obj.name})")

        cache_contents = [f for f in self.uploaded_files]
        # 5. Define system instructions for the combined document analysis
        SYSTEM_INSTRUCTION = "You are an expert tester who must analyze the provided documents and help generate test cases, test steps, test data and expected output"

        # 6. Create the single cache containing all uploaded files
        print("\nCreating context cache for all documents...")
        self.cache = self.gemini_client.caches.create(
            model=model,
            config=types.CreateCachedContentConfig(
                display_name="Requirements documents",
                system_instruction=SYSTEM_INSTRUCTION,
                contents=cache_contents,  # Pass the list of all uploaded File objects
                ttl='1800s',  # E.g., cache for 30 minutes
            )
        )
        self._save_cache_gemini()

        print(f"Cache created: {self.cache.name}")
        print(f"Total cached tokens: {self.cache.usage_metadata.total_token_count}")

    def _save_cache_gemini(self):
        # Save cache name to file
        cache_info = {
            'cache_name': self.cache.name,  # e.g., "cachedContents/abc123"
            'created_at': datetime.now().isoformat(),
            'ttl': '1800s'
        }

        with open('Cache/cache_info.json', 'w') as f:
            json.dump(cache_info, f)
        
        file_metadata = [{'name': f.name, 'display_name': f.display_name} 
                 for f in self.uploaded_files]
        json.dump(file_metadata, open('Cache/uploaded_files.json', 'w'))

    def _load_cache_gemini(self):
        with open('Cache/cache_info.json', 'r') as f:
            cache_info = json.load(f)
        self.cache = self.gemini_client.caches.get(name=cache_info['cache_name'])

    def _delete_files_gemini(self):
        # 8. Clean up (Important for cost management)
        try:
            self._load_cache_gemini()
            file_metadata = json.load(open('Cache/uploaded_files.json', 'r'))
            self.gemini_client.caches.delete(name=self.cache.name)
            for file_info in file_metadata:
                self.gemini_client.files.delete(name=file_info['name'])
        except Exception as e:
            print(e)
        finally:
            os.remove('Cache/uploaded_files.json')
            os.remove('Cache/cache_info.json')
            print("\nClean-up complete. Cache and individual files deleted.")
   
#------------------------------General helper functions-------------------------
    def _cleanup_json(self, result):
        # Clean markdown artifacts
            result = result.strip()
            if result.startswith('```json'):
                result = result.split('```json')[1].split('```')[0].strip()
            elif result.startswith('```'):
                result = result.split('```')[1].split('```')[0].strip()
            return result


    
