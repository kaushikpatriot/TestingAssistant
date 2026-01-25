
from pydantic import BaseModel, Field

from AgentConfig.config import ModelConfig


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


generate_model_config = ModelConfig(
                    test_module = '',
                    knowledge_base_path='',
                    role = '''You are senior financial application tester who can write good test cases given the requirements and the test scenarios ''',
                    task_template = '''
                            Now that you have the requirements, here is a specific scenario 
                            {scenario_id}
                            {scenario}
                            {dimensions}
                            {memberCode}
                            Refer to the test dimensions: {test_dimensions} for an understanding of the meaning of the dimensions
                            The test cases generated should **STRICTLY** adhere to the criteria defined in this specific Test Scenario.
                            Refer to the background documents for requirements, but **ignore** those that are not relevant
                            for this specific scenario.
                            Pay attention to TR_4.3. **Notes for creating Test Cases and Test Steps for Allocation**
                            Do the following
                            1. Create one comprehensive test case for each given specific scenario based on the given requirements. 
                            2. **DO NOT** generate cases for any other Test Scenario or dimensional values that are not provided.
                            3. Generate the sequence of steps for "given" such that the initial state is properly met. 
                                Appropriate amounts should be used such that the initial state is achieved in accordance
                                with the scenario
                            4. Generate the when steps to effectively test the scenario    
                            5. Use the memberCode in the scenario
                            6. Use only those segments available for which MLN requirements are defined in the Masters file. **DO NOT use any other segment
                                ***MLN Requirements***
                                Segment, Max Non-Cash Limit, Min Cash Limit, Total MLN Requirement
                                FNO,1500000,3500000, 5000000
                                CD,4000000,2000000,6000000
                                SLB,5000000,1000000,6000000

                            7. Refer to the Static Data file for the list of applicable Collateral Groups, Collateral Components and Collateral Types
                            {general_instructions}
                            Refer to the verifier's feedback and the output generated last time, if available and use it for the new output.
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
                            {memberCode}
                            Please verify the following.
                            1. Verify if the sequence of steps in {given_steps} is correct or not
                            2. Verify if the amounts used in the {given_steps} is correct or not.
                                **Ensure there is enough amount needed for Total MLN Blocks for all segments before applying it for other blocking and allocation**
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
