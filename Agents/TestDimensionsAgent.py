from Agents.Agent import PipelineStepAgent, ModelConfig, LLMClient
from Helpers.KnowledgeBaseProvider import getKnowledgeBasePath
from pydantic import BaseModel, Field
import pandas as pd
import os


class TestDimension(BaseModel):
    dimension_id: int = Field(description = 'Unique identifier for the dimension. Numbering to be of the format DIM001, DIM002 etc')
    dimension: str = Field(description= 'The dimension name that was extracted from the requirements for which test cases have to be generated. Example: Allocation Level')
    values: list[str] = Field(description = 'The exhaustive list of valid values for this dimension Example CM Level, TM Level, UCC Level, CP Level etc')

class TestDimensionList(BaseModel):
    output: list[TestDimension] = Field(description = 'List of valid dimension extracted from the requirements and their valid list of values')

class TestDimensionVerification(BaseModel):
    overall_score: int = Field(description = 'Provides a score out of 100 in terms of correctness of the test combos')

class TestDimensionAgent(PipelineStepAgent):
    generate_model_config = ModelConfig(
                        test_module = '',
                        knowledge_base_path='',
                        role = '''You are an expert test designer for financial application. You understand the nuances of requirements provided''',
                        task = '''
                                You required to carefully understand the requirements and do the following
                                1. Extract the test dimensions applicable for testing the requirements thoroughly.
                                2. For each of the dimension extract the list of valid values that will be used for generating Test scenarios.
                                3. List them in the format required
                                ''' ,
                        output_format = TestDimensionList,
                        provider = 'ollama',
                        model = 'gpt-oss:20b'
                        )
    
    verify_model_config = ModelConfig(
                        test_module = '',
                        knowledge_base_path='',
                        role = '''You are an expert test case verifier for financial application. You understand the nuances of requirements provided''',
                        task = '''
                                You required to carefully understand the requirements, the test dimensions provided
                                1. Verify the input given and provide a score of the correctness of the input.
                                '''  ,
                        output_format = TestDimensionVerification,
                        provider = 'ollama',
                        model = 'deepseek-r1:14b'
                        )

    def __init__(self, test_module):
        self.generate_model_config.test_module = test_module
        self.generate_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.verify_model_config.test_module = test_module
        self.verify_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)

    def load_input_data(self):
        #No input data from previous step for this Agent
        pass

    def load_knowledge_base(self):
        llm_client = LLMClient(**self.generate_model_config.model_dump())
        llm_client.upload_files()

    def generate_content(self):
        llm_client = LLMClient(**self.generate_model_config.model_dump())
        return llm_client.generate_content()
    
    def verify_content(self, output):
        llm_client = LLMClient(**self.verify_model_config.model_dump())
        return llm_client.generate_content(input = output)
    
    def save_output(self, output):
        df = pd.DataFrame(output)
        output_file = f"{os.getenv('TEST_DIMENSIONS_FILE')}" 
        df.to_csv(output_file)    
    
    def execute(self, verify = True, tries = 1):
        if self.generate_model_config.provider == 'gemini':
            self.load_knowledge_base()
        for i in range(tries):
            generated_response = self.generate_content()

            if verify:
                verify_response = self.verify_content(generated_response)
                if verify_response['overall_score'] >= 70:
                    break
        self.save_output(generated_response['output'])
        #print(generated_response)
