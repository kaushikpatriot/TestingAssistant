from Agents.LLMConnector import LLMConnector
import json
from pydantic import BaseModel
from abc import ABC, abstractmethod
from typing import Type
from Helpers.KnowledgeBaseProvider import getKnowledgeBasePath


class LLMClient:
    '''
    This class acts as a common Client to connect with LLMs using LLMConnector for perform content generation or upload of files
    '''
    def __init__(self, **params):
        self.params = params
        self.llm_connector = LLMConnector(self.params.get('test_module'))

    def upload_files(self):
        self.llm_connector.upload_files(provider = self.params.get('provider'), folder_path = self.params.get('knowledge_base_path'))

    def generate_content(self, input=''):
        prompt = f"Role: {self.params.get('role')}. Task: {self.params.get('task')}. **Input**: {input}"
        response = self.llm_connector.chat(provider = self.params.get('provider'), prompt = prompt, model = self.params.get('model'), 
                                           response_schema = self.params.get('output_format'), folder_path = self.params.get('knowledge_base_path'))
        return json.loads(response)


class ModelConfig(BaseModel):
    test_module: str
    knowledge_base_path: str
    role: str
    task: str
    output_format: Type[BaseModel]
    provider: str
    model: str


class PipelineStepAgent(ABC):
    '''
    This is a template Class for defining an Agent to perform a given task and produce an output
    '''
    generate_model_config:ModelConfig
    verify_model_config:ModelConfig

    @abstractmethod
    def __init__(self, test_module):
        pass

    @abstractmethod
    def load_input_data(self):
        pass

    @abstractmethod
    def load_knowledge_base(self):
        pass

    @abstractmethod
    def generate_content(self):
        pass
    
    @abstractmethod
    def verify_content(self):
        pass

    @abstractmethod
    def save_output(self):
        pass    
    
    @abstractmethod
    def execute(self):
        pass

    



