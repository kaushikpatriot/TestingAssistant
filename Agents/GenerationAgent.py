from Agents.Agent import Agent
from pydantic import BaseModel, Field
import json


class TestComboValue(BaseModel):
    dimension: str = Field(description='Dimension applicable. Use consistent naming through out')
    value: str = Field(description = 'Value applicable to the dimension. Use consistent naming through out')

class TestComboSet(BaseModel):
    combo_id: int = Field(description = 'Unique identifier for the combination')
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
    combo_list: list[TestComboSet] = Field(description = 'Consists of all the Test Combination sets. ')

class TestComboVerification(BaseModel):
    overall_score: int = Field(description = 'Provides a score out of 100 in terms of correctness of the test combos')


class TestComboGenerator:
    def __init__(self):
        knowledge_base_path = 'E:\TestingAssistant\KnowledgeBase\CashAllocation' 
        role = '''You are an expert test designer for financial application. You understand the nuances of requirements provided'''
        task = '''
        You required to carefully understand the requirements and the Test dimensions and do the following
        1. Generate 50 combinations of the test dimensions.  
        2. Assign a criticality for the combinations for the purposes of test coverage.
        3. List them in the format required
        ''' 
        output_format = TestComboList 
        test_module = 'Cash Allocation' 
        provider = 'ollama'
        model = 'deepseek-r1:14b'
        self.agent = Agent(knowledge_base_path, role, task, output_format, test_module, provider, model)
    
    def getTestCombo(self):
        #Upload the knowledge base
        #self.agent.upload_files()
        #Generate data
        response = self.agent.generate_content()
        print(response)



class TestComboVerifier:
    def __init__(self):
        with open('E:\TestingAssistant\Output\Output.json', 'r') as f:
            output = json.load(f)
        knowledge_base_path = 'E:\TestingAssistant\KnowledgeBase\CashAllocation' 
        role = '''You are an expert test case verifier for financial application. You understand the nuances of requirements provided'''
        task = '''
        You required to carefully understand the requirements, the Test dimensions and the Test combinations is attached
        1. Verify the {output} and provide a score of the correctness of the output.
        ''' 
        output_format = TestComboVerification
        test_module = 'Cash Allocation' 
        provider = 'gemini'
        model = 'gemini-2.5-flash'
        self.agent = Agent(knowledge_base_path, role, task, output_format, test_module, provider, model)
    
    def verifyTestCombo(self):
        #Upload the knowledge base
        self.agent.upload_files()
        #Generate data
        response = self.agent.generate_content()
        print(response)


class TestCaseGenerator:
    def __init__(self):
        knowledge_base_path = 'E:\TestingAssistant\KnowledgeBase\CashAllocation' 
        role = '''You are an expert test designer for financial application. You understand the nuances of requirements provided'''
        task = '''
        You required to carefully understand the requirements and the Test dimensions and do the following
        1. Generate 50 combinations of the test dimensions.  
        2. Assign a criticality for the combinations for the purposes of test coverage.
        3. List them in the format required
        ''' 
        output_format = TestComboList 
        test_module = 'Cash Allocation' 
        provider = 'ollama'
        model = 'deepseek-r1:14b'
        self.agent = Agent(knowledge_base_path, role, task, output_format, test_module, provider, model)
