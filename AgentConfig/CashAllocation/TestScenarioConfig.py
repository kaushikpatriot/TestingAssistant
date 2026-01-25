from pydantic import BaseModel, Field
from AgentConfig.config import ModelConfig

#-----------------------------------Output Models-------------------------------------
class TestComboValue(BaseModel):
    dimension: str = Field(description='Dimension applicable. Use consistent naming through out')
    value: str = Field(description = 'Value applicable to the dimension. Use consistent naming through out')

class TestComboSet(BaseModel):
    scenario_id: str = Field(description = 'Unique identifier for the combination. The numbering follows SC-001, SC-002 pattern')
    scenario_description: str = Field (description = 'Comprehensive description of the scenario using the dimensions provided.')
    scenario_dimension: list[TestComboValue] = Field(description= 'The list of combination values of dimensions')
    member_code: str = Field(description='member code to be used for this scenario')


class TestComboList(BaseModel):
    output: list[TestComboSet] = Field(description = 'Consists of all the Test Combination sets. ')

class TestComboVerification(BaseModel):
    overall_score: int = Field(description = 'Provides a score out of 100 in terms of correctness of the test combos')


#---------------------------------------Agent Config--------------------------------------
generate_model_config = ModelConfig(
                    test_module = '',
                    knowledge_base_path='',
                    role = '''You are an expert test designer for financial application. You understand the nuances of requirements provided''',
                    task_template='''
                            You required to carefully understand the requirements and the Test dimensions provided here 
                            {dimensions}
                            and do the following
                            1. Create an exhaustive list of scenarios from which test cases can be generated from the dimensions provided. **DO NOT** miss any valid combinations.
                            2. Use only the dimensions provided. **DO NOT** use any other dimensions.
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
                            You required to carefully understand the requirements, the Test dimensions provided and the Test combinations is attached.
                            Test Dimensions are given below:
                            {dimensions}
                            Test Scenarios generated so far:
                            {test_scenarios} 
                            Verify the test scenarios carefully and do the following
                            1. Provide the corrected scenarios where the scenario is incorrect
                            2. Provide a list of scenarios that are missed out from the initial set
                            '''  ,
                    output_format = TestComboList,
                    provider = 'gemini',
                    model = 'gemini-2.5-pro'
                    )
