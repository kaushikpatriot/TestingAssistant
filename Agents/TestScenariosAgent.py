from Agents.Agent import PipelineStepAgent, ModelConfig, LLMClient
from Helpers.KnowledgeBaseProvider import getKnowledgeBasePath
from pydantic import BaseModel, Field
import pandas as pd
import os
from Helpers.OutputManager import CsvManager as csv
import yaml


class TestComboValue(BaseModel):
    dimension: str = Field(description='Dimension applicable. Use consistent naming through out')
    value: str = Field(description = 'Value applicable to the dimension. Use consistent naming through out')

class TestComboSet(BaseModel):
    scenario_id: str = Field(description = 'Unique identifier for the combination. The numbering follows SC-001, SC-002 pattern')
    scenario_description: str = Field (description = 'Comprehensive description of the scenario using the dimensions provided.')
    scenario_dimension: list[TestComboValue] = Field(description= 'The list of combination values of dimensions')

class TestComboList(BaseModel):
    output: list[TestComboSet] = Field(description = 'Consists of all the Test Combination sets. ')

class TestComboVerification(BaseModel):
    overall_score: int = Field(description = 'Provides a score out of 100 in terms of correctness of the test combos')


class TestScenarioAgent(PipelineStepAgent):
    generate_model_config = ModelConfig(
                        test_module = '',
                        knowledge_base_path='',
                        role = '''You are an expert test designer for financial application. You understand the nuances of requirements provided''',
                        task_template='''
                                You required to carefully understand the requirements and the Test dimensions provided here 
                                {dimensions}
                             and do the following
                                1. Create an exhaustive list of dimensions from which test cases can be generated. **DO NOT** miss any valid combinations.
                                2. Use only the dimensions and the respective values available in the **Input**. **DO NOT** use any other dimensions.
                                3. **DO NOT GENERATE DUPLICATE COMBINATIONS**
                                4. combine_strategy for each dimension means
                                    a. cartesian - means every value has to be combined with every value from other dimensions to create an exhaustive list
                                    b. coverage - means there should atleast one combination that covers the given value. It doesnt have to be combined to every value
                                    c. independent - means these values form their own scenarios and do not combine with values of other dimensions
                                5. List them in the format required
                                ''',
                        task =  '',
                        output_format = TestComboList,
                        provider = 'gemini',
                        model = 'gemini-2.5-pro' #'qwen-coder:30b'#'gpt-oss:20b'
                        )
    
    verify_model_config = ModelConfig(
                        test_module = '',
                        knowledge_base_path='',
                        role = '''You are an expert test case verifier for financial application. You understand the nuances of requirements provided''',
                        task_template='',
                        task = '''
                                You required to carefully understand the requirements, the Test dimensions provided and the Test combinations is attached
                                1. Verify the input given and provide a score of the correctness of the input.
                                '''  ,
                        output_format = TestComboVerification,
                        provider = 'gemini',
                        model = 'gemini-2.5-pro'
                        )

    def __init__(self, test_module):
        self.generate_model_config.test_module = test_module
        self.generate_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.verify_model_config.test_module = test_module
        self.verify_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.generate_llm_client = LLMClient(self.generate_model_config.provider, self.generate_model_config.model, self.generate_model_config.knowledge_base_path, test_module) #**self.generate_model_config.model_dump())
        self.verify_llm_client = LLMClient(self.verify_model_config.provider, self.verify_model_config.model, self.verify_model_config.knowledge_base_path, test_module) #**self.verify_model_config.model_dump())


    def load_input_data(self):
        with open(os.getenv('TEST_DIMENSIONS_FILE'), 'r') as f:
            self.dimensions = yaml.safe_load(f)
        f.close()
        # self.input_df = pd.read_csv(f"{os.getenv('TEST_DIMENSIONS_FILE')}")         

    def load_knowledge_base(self):
        self.generate_llm_client.upload_files()

    def generate_content(self, prompt, response_schema=None):
        return self.generate_llm_client.generate_content(prompt, response_schema)
    
    def verify_content(self, output):
        return self.verify_llm_client.generate_content(input = output)
    
    def execute(self, verify = False, tries = 1):
        if self.generate_model_config.provider == 'gemini':
            self.load_knowledge_base()

        self.load_input_data()

        knowledge_files = os.listdir(self.generate_model_config.knowledge_base_path)
        gen_prompt = f'''I have uploaded the following documents. You required to carefully understand the requirements, processing rules, static data, masters that have already been uploaded. 
        Can you confirm if you have the following documents in your cache?
        {str(knowledge_files)}
        '''
        turn1_response = self.generate_content(gen_prompt)
        print(turn1_response)
        
        scenarios_df = pd.DataFrame()

        # for step_num in range(iterations):
        for i in range(tries):
            self.generate_model_config.task = self.generate_model_config.task_template.format(dimensions = str(self.dimensions))
            prompt = self.generate_model_config.role + '\n' + self.generate_model_config.task
            generated_response = self.generate_content(prompt, self.generate_model_config.output_format)
            response_df = pd.DataFrame(generated_response['output'])
            # print(f'Number of Scenarios generated in step {step_num+1} is {len(response_df)}')
            if verify:
                verify_response = self.verify_content(generated_response)
                if verify_response['overall_score'] >= 70:
                    break
        if scenarios_df.empty:
            scenarios_df = response_df
        else:
            scenarios_df = pd.concat([scenarios_df, response_df], ignore_index=True)
        # if len(response_df) < 50: #Maximum of 50 combinations being generated at a time
        #     break

        csv.writeDfToCsv(scenarios_df,os.getenv('TEST_SCENARIOS_FILE'))
        #print(generated_response)
