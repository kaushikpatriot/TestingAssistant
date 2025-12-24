from Agents.LLMConnector import LLMConnector
import json
from pydantic import BaseModel
from abc import ABC, abstractmethod
from typing import Optional, Type
import pandas as pd
import os


class LLMClient:
    '''
    This class acts as a common Client to connect with LLMs using LLMConnector for perform content generation or upload of files
    '''
    def __init__(self, provider, model, knowledge_base_path, test_module):
        self.llm_connector = LLMConnector(provider, model, knowledge_base_path, test_module)

    def upload_files(self):
        self.llm_connector.upload_files()

    def generate_content(self, prompt, response_schema=None):
        response = self.llm_connector.chat(prompt, response_schema)
        if response_schema:
            return json.loads(response)
        else:
            return response        


class ModelConfig(BaseModel):
    test_module: str
    knowledge_base_path: str
    role: str
    task_template: str
    task: str
    output_format: Type[BaseModel]
    provider: str
    model: str

class TextResponse(BaseModel):
    text: str
    proceed: bool

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
    def execute(self):
        pass

    



