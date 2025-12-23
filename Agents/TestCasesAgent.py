from Agents.Agent import PipelineStepAgent, ModelConfig, LLMClient
from Helpers.KnowledgeBaseProvider import getKnowledgeBasePath
from pydantic import BaseModel, Field
import pandas as pd
import os
from Helpers.OutputManager import CsvManager as csv

class CollateralSteps(BaseModel):
   step: int = Field(description="This is the step number of the sequence of steps to be executed")
   transaction_type: str = Field(description="This describes the transaction type applied e.g Deposit, Allocation etc")
   collateralGroup: list[str] = Field(description = '''The collateral groups to be used for this test case.''')
   collateralComponent: str = Field(description ='''The collateral components which will be used for this test case.''')
   isFungible: list[str] = Field(description = '''Indicates what are the different fungibility of collaterals used for this test case''')

class TestCase(BaseModel):
  test_scenario_id: str = Field(description='This is the reference to the Test Combo Id from the Test Scenarios input. This acts as a trace back to the scenarios')
  test_case_id: str = Field(description='''A unique ID for a test case. This should be of the format Scenario ID + TC-0001, Scenario ID + TC-0002 etc.
                                          ''')
  test_description: str = Field(description='''Describes the test case in detail primarily consisting of
                                               Overall Scenario - Insufficient MLN coverage
                                               MLN Cash and Non - cash coverage
                                               Compliance requirement coverage
                                               Capital cushion coverage''')
  key_validation: str = Field(description = "Lists the key validations for this test case as bullet points prefixed by *")
  segment_scope: str = Field(description="Whether single segment or multiple segments" )
  order: str = Field(description='''State whether Forward (priority order) or Reverse (reverse priority order)''')
  test_steps: list[CollateralSteps] = Field(description='''List the sequence of steps that can truly help verify the test case 
                  Use all applicable Collateral types as per the static data to effectively test the case
                  Refer to the static data for the applicable collateral types. 
                  Generate as many steps as required by the Test Scenarios document.
                  Ensure there is a good coverage of all relevant collateral types''')
  memberCode: str = Field(description="Take the member code from the masters data for whom the test case should be generated. **DO NOT REPEAT MEMBER CODES. EACH TEST CASE SHOULD HAVE A UNIQUE MEMBERCODE")

class TestCaseList(BaseModel):
    output: list[TestCase]

class TestCaseVerification(BaseModel):
    overall_score: int = Field(description = 'Provides a score out of 100 in terms of correctness of the test cases')


class TestCaseAgent(PipelineStepAgent):
    generate_model_config = ModelConfig(
                        test_module = '',
                        knowledge_base_path='',
                        role = '''You are senior financial application tester who can write good test cases given the requirements and the test scenarios ''',
                        task = '''
                                You required to carefully understand the requirements and the Test Scenario in terms of the applicable dimensions and theis values provided as **Input** and do the following
                                1. Create an list of test cases for the given scenario and the dimenstional values provided based on the given requirements 
                                2. Each test case should help test **ONLY** the given set of dimensional values. 
                                3. The Test cases can include variants in Collateral types or Collateral components that can effectively test the given scenario
                                4. Keep each test case comprehensive and independent with necessary steps required to test effectively
                                5. **DO NOT** generate cases for any other Test Scenario or dimensional values that are not provided as **Input**
                                7. There can be more than one test case for a given scenario but only if it is required to test the scenario comprehensively. 
                                6. List them in the format required
                                ''' ,
                        output_format = TestCaseList,
                        provider = 'gemini',
                        model = 'gemini-2.5-pro' #'deepseek-r1:14b' #'qwen-coder:30b'#
                        )
    
    verify_model_config = ModelConfig(
                        test_module = '',
                        knowledge_base_path='',
                        role = '''You are an expert test case verifier for financial application. You understand the nuances of requirements provided''',
                        task = '''
                                You required to carefully understand the requirements, the Test dimensions provided and the Test combinations is attached
                                1. Verify the input given and provide a score of the correctness of the input.
                                '''  ,
                        output_format = TestCaseVerification,
                        provider = 'gemini',
                        model = 'gemini-2.5-pro'
                        )

    def __init__(self, test_module):
        self.generate_model_config.test_module = test_module
        self.generate_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.verify_model_config.test_module = test_module
        self.verify_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)

    def load_input_data(self):
        self.input_df = pd.read_csv(f"{os.getenv('TEST_SCENARIOS_FILE')}")

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
        final_df = pd.DataFrame()
        for record_num in range(len(self.input_df)):
            input_data = self.input_df.iloc[record_num]
            print(f"\n Generating Test Cases for Scenario {record_num+1}")
            for i in range(tries):
                generated_response = self.generate_content(input_data)

                if verify:
                    verify_response = self.verify_content(generated_response)
                    if verify_response['overall_score'] >= 70:
                        break
            output_df = pd.DataFrame(generated_response['output'])
            if final_df.empty:
                final_df = output_df
            else:
                final_df = pd.concat([final_df, output_df], ignore_index = True)
        csv.writeDfToCsv(final_df, os.getenv('TEST_CASES_FILE'))
