from Agents.Agent import PipelineStepAgent, ModelConfig, LLMClient
from Helpers.KnowledgeBaseProvider import getKnowledgeBasePath
from pydantic import BaseModel, Field
import pandas as pd
import os
from Helpers.OutputManager import CsvManager as csv


class TestComboValue(BaseModel):
    dimension: str = Field(description='Dimension applicable. Use consistent naming through out')
    value: str = Field(description = 'Value applicable to the dimension. Use consistent naming through out')

class TestComboSet(BaseModel):
    combo_id: str = Field(description = 'Unique identifier for the combination. The numbering follows SC-001, SC-002 pattern')
    combo_description: list[TestComboValue] = Field(description= 'The list of combination values of dimensions')
    criticality: str = Field(description = '''This is the criticality level of the combination in terms importance 
                             for test coverage. The values can only be HIGH, MEDIUM and LOW. **No other value should be 
                             provided**
                             HIGH - refers to those combinations that are absolutely critical to test failing which the application 
                             cannot be considered as tested
                             MEDIUM - refers to those combinations that are important but less critical. 
                             LOW - refers to those combinations that are low in importance for the general functioning of the 
                             application. 
                             ''')
    traceability: str = Field(description = '''This gives the references (comma separated) to the requirements from which the combination is derived''')


class TestComboList(BaseModel):
    output: list[TestComboSet] = Field(description = 'Consists of all the Test Combination sets. ')

class TestComboVerification(BaseModel):
    overall_score: int = Field(description = 'Provides a score out of 100 in terms of correctness of the test combos')


class TestScenarioAgent(PipelineStepAgent):
    generate_model_config = ModelConfig(
                        test_module = '',
                        knowledge_base_path='',
                        role = '''You are an expert test designer for financial application. You understand the nuances of requirements provided''',
                        task = '''
                                You required to carefully understand the requirements and the Test dimensions provided as **Input** and do the following
                                1. Create an exhaustive list of combinations of dimensions from which test cases can be generated. **DO NOT** miss any valid combinations.
                                2. Use only the dimensions and the respective values available in the **Input**. **DO NOT** use any other dimensions.
                                3. Assign a criticality for the combinations for the purposes of test coverage.
                                4. List them in the format required
                                ''' ,
                        output_format = TestComboList,
                        provider = 'ollama',
                        model = 'deepseek-r1:14b' #'qwen-coder:30b'#'gpt-oss:20b'
                        )
    
    verify_model_config = ModelConfig(
                        test_module = '',
                        knowledge_base_path='',
                        role = '''You are an expert test case verifier for financial application. You understand the nuances of requirements provided''',
                        task = '''
                                You required to carefully understand the requirements, the Test dimensions provided and the Test combinations is attached
                                1. Verify the input given and provide a score of the correctness of the input.
                                '''  ,
                        output_format = TestComboVerification,
                        provider = 'ollama',
                        model = 'deepseek-r1:14b'
                        )

    def __init__(self, test_module):
        self.generate_model_config.test_module = test_module
        self.generate_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.verify_model_config.test_module = test_module
        self.verify_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)

    def load_input_data(self):
        self.input_df = pd.read_csv(f"{os.getenv('TEST_DIMENSIONS_FILE')}")

    def load_knowledge_base(self):
        llm_client = LLMClient(**self.generate_model_config.model_dump())
        llm_client.upload_files()

    def generate_content(self, input):
        llm_client = LLMClient(**self.generate_model_config.model_dump())
        return llm_client.generate_content(input)
    
    def verify_content(self, output):
        llm_client = LLMClient(**self.verify_model_config.model_dump())
        return llm_client.generate_content(input = output)
    
    def execute(self, verify = True, tries = 1):
        if self.generate_model_config.provider == 'gemini':
            self.load_knowledge_base()

        self.load_input_data()
        
        for i in range(tries):
            generated_response = self.generate_content(self.input_df)

            if verify:
                verify_response = self.verify_content(generated_response)
                if verify_response['overall_score'] >= 70:
                    break
        csv.writeDfToCsv(pd.DataFrame(generated_response['output']),os.getenv('TEST_SCENARIOS_FILE'))
        #print(generated_response)
