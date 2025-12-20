# from Agents.LLMConnector import LLMConnector
# from Agents.GenerationAgent import TestComboGenerator, TestComboVerifier
from dotenv import load_dotenv
# from pydantic import BaseModel, Field
# from Helpers.OutputManager import CsvManager, ExcelManager
# import json
# import pandas as pd
from Agents.TestScenariosAgent import TestScenarioAgent
from Agents.TestDimensionsAgent import TestDimensionAgent
from Agents.TestCasesAgent import TestCaseAgent
from Agents.TestStepsAgent import TestStepAgent
from Agents.TestOutputAgent import TestOutputAgent

# class TestScenario(BaseModel):
#     test_id: int = Field(description = "Unique identifier for a test scenario")
#     test_scenario: str = Field(description = "Test scenario description")

# class TestOutput(BaseModel):
#     output: list[TestScenario]

load_dotenv()

# test_module = "Collateral Blocking"
# new_agent = LLMConnector(test_module)
# prompt = "Can you list a few test scenarios for the given document?"
# # provider='gemini'
# # model = 'gemini-2.5-flash'
# provider = 'ollama'
# model =  'deepseek-r1:14b' #'qwen3-coder:30b' #'gpt-oss:20b'

# def chat(csv_manager:CsvManager):
#     folder_path = 'E:\TestingAssistant\KnowledgeBase\CashAllocation'
#     #new_agent.upload_files(provider, folder_path)
#     response = new_agent.chat(provider, prompt, model, TestOutput)
#     # # csv_manager = CsvManager()
#     # df = pd.DataFrame(json.loads(response)['output'])
#     # csv_manager.writeDfToCsv(df, 'Output/test.csv')
#     print(response)
#     #new_agent.cleanup_files(provider)


# csv_manager = CsvManager()
# chat(csv_manager)

# test_combo = TestComboGenerator()
# test_combo.getTestCombo()

# test_verify = TestComboVerifier()
# test_verify.verifyTestCombo()

# print(f'Generating Test Dimensions \n')
# test_dim_agent = TestDimensionAgent("Cash Allocation")
# test_dim_agent.execute()

# print(f'Generating Test Scenarios \n')
# test_sc_agent = TestScenarioAgent("Cash Allocation")
# test_sc_agent.execute()

# print(f'Generating Test Cases \n')
# test_cs_agent = TestCaseAgent("Cash Allocation")
# test_cs_agent.execute()

print(f'Generating Test Steps \n')
test_st_agent = TestStepAgent("Cash Allocation")
test_st_agent.execute()

# print(f'Generating Test Output \n')
# test_ot_agent = TestOutputAgent("Cash Allocation")
# test_ot_agent.execute()
