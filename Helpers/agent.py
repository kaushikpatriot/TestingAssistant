import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import json
from datetime import datetime
from Datamodels.CollateralBlocking import testCases, testSteps, expectedResults


class AgentManager:
    def __init__(self):
        load_dotenv('.env')  # Specify your custom filename
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.client = genai.Client(api_key = self.api_key)
        self.model = os.getenv('MODEL')

    def uploadFilesAndCache(self, folderPath, ttl='1800s'):
        self.uploaded_files = []
        files = [os.path.join(folderPath, f) for f in os.listdir(folderPath) 
                if os.path.isfile(os.path.join(folderPath, f))]
        for file_path in files:
            print(f"Uploading file: {file_path}...")
            file_obj = self.client.files.upload(
                file=file_path
            )
            self.uploaded_files.append(file_obj)
            print(f"Uploaded: {file_obj.display_name} ({file_obj.name})")

        # 4. Create the final list of content to be cached
        cache_contents = [f for f in self.uploaded_files]
        # 5. Define system instructions for the combined document analysis
        SYSTEM_INSTRUCTION = "You are an expert tester who must analyze the provided documents and help generate test cases, test steps, test data and expected output"

        # 6. Create the single cache containing all uploaded files
        print("\nCreating context cache for all documents...")
        self.cache = self.client.caches.create(
            model=self.model,
            config=types.CreateCachedContentConfig(
                display_name="Test requirements documents",
                system_instruction=SYSTEM_INSTRUCTION,
                contents=cache_contents,  # Pass the list of all uploaded File objects
                ttl=ttl,  # E.g., cache for 30 minutes
            )
        )
        self.saveCache()

        print(f"Cache created: {self.cache.name}")
        print(f"Total cached tokens: {self.cache.usage_metadata.total_token_count}")

    def saveCache(self):
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


    def loadCache(self, folderPath):
        try: 
            with open('Cache/cache_info.json', 'r') as f:
                cache_info = json.load(f)
            self.cache = self.client.caches.get(name=cache_info['cache_name'])
        except Exception as e:
            self.uploadFilesAndCache(folderPath)

    def generateResponse(self, prompt, folderPath, response_schema=None):
        # Load Cache or Upload files as applicable
        self.loadCache(folderPath)
        
        #Generate response with response schema
        if response_schema:
            print(f'Im here- {response_schema}')
            response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                cached_content=self.cache.name,
                response_mime_type='application/json',
                response_schema=response_schema
                )
            )
        #Generate response as a general text
        else:
            response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                cached_content=self.cache.name
                )
            )
        return json.loads(response.text)


 