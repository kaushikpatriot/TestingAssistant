from Agents.Agent import PipelineStepAgent, ModelConfig, LLMClient
from Helpers.KnowledgeBaseProvider import getKnowledgeBasePath
from pydantic import BaseModel, Field
import pandas as pd
from Helpers.OutputManager import CsvManager as csv
import os


class DimensionValues(BaseModel):
    dim_val_id: str = Field(description='''Unique Id for the value within the Dimension. Value Id should have the Dimension Id followed 
                                by an id. For example Value for Dim Id TD-001 should be TD-001-001 , TD-001-002 and so on''')
    dim_value: str = Field(description = '''The allowed value for the dimension. Use consistent naming pattern''')

class TestConstraints(BaseModel):
    const_id: str = Field(description='''Unique Id for the constraint. Use Dim id and add -C-001, -C-002 etc to it''')
    constraint: str = Field(description='''The constraint to be applied when generating combinations using this dimension's values''')

class TestDimension(BaseModel):
    dim_id: str = Field(description = 'Unique identifier for the dimension. Numbering to be of the format TD-001, TD-002 etc')
    dimension: str = Field(description= 'The dimension name that was extracted from the requirements for which test cases have to be generated. Example: Allocation Level')
    description: str = Field(description='Description of the dimension and what it means')
    dim_type: str = Field(description='The type of dimension for testing purposes. Values can only be **Core**, **Independent**, **Ancillary**')
    values: list[DimensionValues] = Field(description='The list of allowed values for this dimension')
    constraints: list[TestConstraints] = Field(description='The list of constraints to be applied to this dimension when combining its values with other dimensions to generate scenarios')
    note: str = Field(description = 'Any notes that will be useful for Test Combination generation process later')

class TestDimensionList(BaseModel):
    output: list[TestDimension] = Field(description = 'List of valid dimension extracted from the requirements and their valid list of values')

class TestDimensionVerification(BaseModel):
    overall_score: int = Field(description = 'Provides a score out of 100 in terms of correctness of the test combinations')
    rationale: str = Field(description = 'List the reasons for providing this score. What are the reasons that reduced the score')

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
                        provider = 'gemini',
                        model = 'gemini-2.5-flash'
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
                        provider = 'gemini',
                        model = 'gemini-2.5-flash'
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
    
    def execute(self, verify = True, tries = 1):
        if self.generate_model_config.provider == 'gemini':
            self.load_knowledge_base()
        for i in range(tries):
            generated_response = self.generate_content()

            if verify:
                verify_response = self.verify_content(generated_response)
                if verify_response['overall_score'] >= 70:
                    break
        csv.writeDfToCsv(pd.DataFrame(generated_response['output']), os.getenv('TEST_DIMENSIONS_FILE'))
        #print(generated_response)
