from Agents.Agent import PipelineStepAgent, ModelConfig, LLMClient, TextResponse
from Helpers.KnowledgeBaseProvider import getKnowledgeBasePath
from pydantic import BaseModel, Field
import pandas as pd
import os
from Helpers.OutputManager import CsvManager as csv
import yaml
import time

class TestCase(BaseModel):
  test_scenario_id: str = Field(description='This is the reference to the Test Combo Id from the Test Scenarios input. This acts as a trace back to the scenarios')
  target_scenario: str = Field(description='Briefly describe the scenario for which the test case is generated and list out the dimensions and their values that will constrain the scope of this scenario')
  test_case_id: str = Field(description='''A unique ID for a test case. This should be of the format Scenario ID + TC-0001, Scenario ID + TC-0002 etc.
                                          ''')
  given: str = Field(description = '''This is the initial condition that needs to be there for the test case to be further processed. 
                     This should typically represent the sequence of transactions that should be processed to arrive at the initial state''')
  given_steps: str = Field(description='''This is the list of steps to be executed to arrive at the initial state including the collateral type and the amounts to be used
                           **This HAS to be in a descriptive text format and not a structured format**''')
  when: str = Field(description="This is the event or the set of events that will be processed in order test the given case")
  when_steps: str = Field(description='''This is the step or set of steps that represent the actual event to be tested including the collateral types and the amounts
                          **This HAS to be in a descriptive text format and not a structured format**''')
  then: str = Field(description="This is the expected result after the event is or events are processed")
  memberCode: str = Field(description="Use the same memberCode as that of the Scenario for which the Test Case is generated. **DO NOT CHANGE THE MEMBERCODE**")

class TestCaseList(BaseModel):
    output: list[TestCase]

class TestCaseVerification(BaseModel):
    isCorrect: bool = Field(description = 'Is the output correct or not. Verify the sequence of steps, the collateral types and the amounts used to verify')
    correction: str = Field(description = 'If the output is incorrect, the describe what should be corrected. If the output is correct, this will be blank')

class TestCaseAgent(PipelineStepAgent):
    generate_model_config = ModelConfig(
                        test_module = '',
                        knowledge_base_path='',
                        role = '''You are senior financial application tester who can write good test cases given the requirements and the test scenarios ''',
                        task_template = '''
                                Now that you have the requirements, here is a specific scenario 
                                {scenario_id}
                                {scenario}
                                {dimensions}
                                Refer to the test dimensions: {test_dimensions} for an understanding of the meaning of the dimensions
                                The test cases generated should **STRICTLY** adhere to the criteria defined in this specific Test Scenario.
                                Refer to the background documents for requirements, but **ignore** those that are not relevant
                                for this specific scenario.
                                Do the following
                                1. Create one comprehensive test case for each given specific scenario based on the given requirements. 
                                2. **DO NOT** generate cases for any other Test Scenario or dimensional values that are not provided.
                                3. Generate the sequence of steps for "given" such that the initial state is properly met. 
                                    Appropriate amounts should be used such that the initial state is achieved in accordance
                                    with the scenario
                                4. Generate the when steps to effectively test the scenario    
                                5. Use a different memberCode for each Test Case from the Masters data attached. 
                                Let the memberCode be successive across Test cases. **DO NOT use a different memberCode when the same Test Case is being re-generated 
                                due to a verifier feedback. Keep the same memberCode in such cases**
                                6. Use only those segments available for which MLN requirements are defined in the Masters file. **DO NOT use any other segment
                                7. Refer to the Static Data file for the list of applicable Collateral Groups, Collateral Components and Collateral Types
                                {general_instructions}
                                Refer to the verifier's feedback if available and use it for the output
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
                        task_template = '''
                                Here is the Test Scenario 
                                {scenario_id}
                                {scenario}
                                {dimensions}
                                Please verify the following.
                                1. Verify if the sequence of steps in {given_steps} is correct or not
                                2. Verify if the amounts used in the {given_steps} is correct or not
                                3. Verify if the sequence of steps in {when_steps} is correct or not
                                4. Verify if the amounts used in {when_steps} is correct or not
                                5. Verify if {then} is correct or not
                                If all of these are correct then respond in the format required
                                '''  ,
                        task = '',
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
        with open(os.getenv('TEST_DIMENSIONS_FILE'), 'r') as f:
            self.dimensions = yaml.safe_load(f)
        f.close()


    def load_knowledge_base(self):
        self.generate_llm_client.upload_files()
        #self.verify_llm_client.upload_files()

    def generate_content(self, prompt, response_schema=None):
        return self.generate_llm_client.generate_content(prompt, response_schema)
    
    def verify_content(self, prompt, response_schema=None):
        return self.verify_llm_client.generate_content(prompt, response_schema)
    
    def execute(self, start = 1, end = -1, gen_instruct = '', verify = False, tries = 3, wait = True):
        inCorrectScenarios = []
        if self.generate_model_config.provider == 'gemini':
            self.load_knowledge_base()

        self.load_input_data()
        final_df = pd.DataFrame()
        knowledge_files = os.listdir(self.generate_model_config.knowledge_base_path)
        gen_prompt = f'''I have uploaded the following documents. You required to carefully understand the requirements, processing rules, static data, masters that have already been uploaded. 
        Can you confirm if you have the following documents in your cache?
        {str(knowledge_files)}
        '''
        turn1_response = self.generate_content(gen_prompt)
        print(turn1_response)
        for record_num in range(start-1, (len(self.input_df) if end < 0 else min(end, len(self.input_df)))):
            scenario = self.input_df.iloc[record_num]

            verifier_feedback, verify_response = '', None
            self.generate_model_config.task = self.generate_model_config.task_template.format(scenario_id = str(scenario['scenario_id']),scenario=str(scenario['scenario_description']), 
                                                                                              dimensions = str(scenario['scenario_dimension']),
                                                                                              general_instructions = gen_instruct, test_dimensions = self.dimensions)
            print(f"\n Generating Test Cases for Scenario {record_num+1}")
            for i in range(tries):
                #Generation
                prompt = self.generate_model_config.role + '\n' + self.generate_model_config.task + '\n' + f'Verifier feedback: {verifier_feedback}'
                generated_response = self.generate_content(prompt, self.generate_model_config.output_format)
                output_df = pd.DataFrame(generated_response['output'])
                
                #Verification                
                self.verify_model_config.task = self.verify_model_config.task_template.format(given_steps = output_df['given_steps'], when_steps = output_df['when_steps'], then = output_df['then'],
                                                                                              scenario_id = str(scenario['scenario_id']), scenario=str(scenario['scenario_description']), 
                                                                                              dimensions = str(scenario['scenario_dimension']))    
                prompt = self.verify_model_config.role + '\n' + self.verify_model_config.task
                if verify:
                    # time.sleep(2)
                    print(f'Verifying for the {i+1}th time')
                    verify_response = self.verify_content(prompt,self.verify_model_config.output_format)
                    if verify_response['isCorrect']:
                        break
                    else:
                        verifier_feedback = verify_response['correction']

            if not verify or (verify_response and verify_response['isCorrect']):
                if final_df.empty:
                    final_df = output_df
                else:
                    final_df = pd.concat([final_df, output_df], ignore_index = True)
                csv.writeDfToCsv(final_df, os.getenv('TEST_CASES_FILE'))
            else:
                print(f'Unable to generate correct test case for Scenario {record_num+1} because {verifier_feedback}')
                inCorrectScenarios.append(scenario['scenario_id'])
        
        if len(inCorrectScenarios) > 0:
            print(f'Unable to generate correct test cases for {inCorrectScenarios}')
