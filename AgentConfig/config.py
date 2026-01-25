from typing import Type
from pydantic import BaseModel

class ModelConfig(BaseModel):
    test_module: str
    knowledge_base_path: str
    role: str
    task_template: str
    task: str
    output_format: Type[BaseModel]
    provider: str
    model: str
