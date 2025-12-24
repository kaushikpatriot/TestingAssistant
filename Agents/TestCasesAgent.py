from Agents.Agent import PipelineStepAgent, ModelConfig, LLMClient, TextResponse
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

# class TestPlan(BaseModel):
#     plan_description: str = Field(description = "Describe how this Test case should be tested step by step. Keep the description to not more than 50 words")
#     test_steps_outline: list[CollateralSteps] = Field(description = "This lists the steps that will be required to be generated inorder to test this test case")

class TestCase(BaseModel):
  test_scenario_id: str = Field(description='This is the reference to the Test Combo Id from the Test Scenarios input. This acts as a trace back to the scenarios')
  test_case_id: str = Field(description='''A unique ID for a test case. This should be of the format Scenario ID + TC-0001, Scenario ID + TC-0002 etc.
                                          ''')
  given: str = Field(description = '''This is the initial condition that needs to be there for the test case to be further processed. 
                     This should typically represent the sequence of transactions that should be processed to arrive at the initial state''')
  given_steps: list[CollateralSteps] = Field(description='''This is the list of steps to be executed to get to the initial state''')
  when: str = Field(description="This is the event or the set of events that will be processed in order test the given case")
  when_steps: list[CollateralSteps] = Field(description='''This is the step or the set of steps that represent the actual event to be tested''')
  then: str = Field(description="This is the expected result after the event is or events are processed")
#   test_description: str = Field(description='''Describes the test case in detail using the scenario given as input.''')
#   key_validation: str = Field(description = "Lists the key validations for this test case as bullet points prefixed by *")
#   segment_scope: str = Field(description="Whether single segment or multiple segments" )
#   order: str = Field(description='''State whether Forward (priority order) or Reverse (reverse priority order)''')
#   test_plan: TestPlan = Field(description='''List the sequence of steps that can truly help verify the test case 
#                   Use all applicable Collateral types as per the static data to effectively test the case
#                   Refer to the static data for the applicable collateral types. 
#                   Generate as many steps as required by the Test Scenarios document.
#                   Ensure there is a good coverage of all relevant collateral types''')
  memberCode: str = Field(description="Use the same memberCode as that of the Scenario for which the Test Case is generated. **DO NOT CHANGE THE MEMBERCODE**")

class TestCaseList(BaseModel):
    output: list[TestCase]

class TestCaseVerification(BaseModel):
    overall_score: int = Field(description = 'Provides a score out of 100 in terms of correctness of the test cases')


class TestCaseAgent(PipelineStepAgent):
    generate_model_config = ModelConfig(
                        test_module = '',
                        knowledge_base_path='',
                        role = '''You are senior financial application tester who can write good test cases given the requirements and the test scenarios ''',
                        task_template = '''
                                Now that you have the requirements, here is a specific scenario {input}. 
                                The test cases generated should STRICTLY adhere to the criteria defined in this specific Test Scenario.
                                Do the following
                                1. Create test cases for the given specific scenario based on the given requirements. 
                                2. Each test case should help test **ONLY** the given scenario. 
                                3. Keep each test case comprehensive and independent with necessary steps required to test effectively
                                4. **DO NOT** generate cases for any other Test Scenario or dimensional values that are not provided.
                                5. List them in the format required
                                ''' ,
                        task = '',
                        output_format = TestCaseList,
                        provider = 'gemini',
                        model = 'gemini-2.5-pro' #'deepseek-r1:14b' #'qwen-coder:30b'#
                        )
    
    verify_model_config = ModelConfig(
                        test_module = '',
                        knowledge_base_path='',
                        role = '''You are an expert test case verifier for financial application. You understand the nuances of requirements provided''',
                        task_template = '',
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
        self.generate_llm_client = LLMClient(self.generate_model_config.provider, self.generate_model_config.model, self.generate_model_config.knowledge_base_path, test_module) #**self.generate_model_config.model_dump())
        self.verify_llm_client = LLMClient(self.verify_model_config.provider, self.verify_model_config.model, self.verify_model_config.knowledge_base_path, test_module) #**self.verify_model_config.model_dump())


    def load_input_data(self):
        self.input_df = pd.read_csv(f"{os.getenv('TEST_SCENARIOS_FILE')}")
        self.test_dim = pd.read_csv(f"{os.getenv('TEST_DIMENSIONS_FILE')}")

    def load_knowledge_base(self):
        self.generate_llm_client.upload_files()
        #self.verify_llm_client.upload_files()

    def generate_content(self, prompt, response_schema=None):
        return self.generate_llm_client.generate_content(prompt, response_schema)
    
    def verify_content(self, output):
        return self.verify_llm_client.generate_content(input = output)
    
    def execute(self, verify = False, tries = 1):
        if self.generate_model_config.provider == 'gemini':
            self.load_knowledge_base()

        self.load_input_data()
        final_df = pd.DataFrame()
        # gen_prompt = '''I have uploaded the following documents. You required to carefully understand the requirements, processing rules, static data, masters that have already been uploaded. 
        # Can you confirm if you have the following documents in your cache?
        # - CM-CA-Allocation-SS-Overview_v01.txt
        # - CM-MLN_Blocks-Business_v01.txt
        # - CM-SS-C-Masters_v02.txt
        # - CM-StaticData_v01.txt
        # - CM-Testing-Overview_v03.txt
        # '''
        gen_prompt = '''When given this scenario 
        Test for First Time Allocation at CM level Allocation only with Collateral deposited being from Collateral Group "CASH" and Collateral Component "CASH" only. The Collateral Deposited will be sufficient to fulfil allocation request

        What is your understanding of the Scenario that is given to you? What are the collateral groups, collateral components and collateral types
        applicable to generate test cases for this scenario alone?
        '''
        turn1_response = self.generate_content(gen_prompt)

        print(turn1_response)
        # for record_num in range(3):#len(self.input_df)):
        #     scenario = self.input_df.iloc[record_num]
        #     self.generate_model_config.task = self.generate_model_config.task_template.format(input=str(scenario))
        #     print(f"\n Generating Test Cases for Scenario {record_num+1}")
        #     for i in range(tries):
        #         prompt = self.generate_model_config.role + '\n' + self.generate_model_config.task
        #         generated_response = self.generate_content(prompt, self.generate_model_config.output_format)
        #         if verify:
        #             verify_response = self.verify_content(generated_response)
        #             if verify_response['overall_score'] >= 70:
        #                 break
        #     output_df = pd.DataFrame(generated_response['output'])
        #     if final_df.empty:
        #         final_df = output_df
        #     else:
        #         final_df = pd.concat([final_df, output_df], ignore_index = True)
        # csv.writeDfToCsv(final_df, os.getenv('TEST_CASES_FILE'))
