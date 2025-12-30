from dotenv import load_dotenv
from Agents.TestScenariosAgent import TestScenarioAgent
from Agents.TestDimensionsAgent import TestDimensionAgent
from Agents.TestCasesAgent import TestCaseAgent
from Agents.TestStepsAgent import TestStepAgent
from Agents.TestOutputAgent import TestOutputAgent
from Helpers.TestScenarioGenerator import TestScenarioGenerator
import sys
import os

load_dotenv()

def generateDimensions():
    print(f'Generating Test Dimensions \n')
    test_dim_agent = TestDimensionAgent("Cash Allocation")
    test_dim_agent.execute()

def generateScenarios():
    print(f'Generating Test Scenarios \n')
    # scenario_gen = TestScenarioGenerator()
    # scenario_gen.generateScenarios()
    test_sc_agent = TestScenarioAgent("Cash Allocation")
    test_sc_agent.execute()

def generateTestCases():
    print(f'Generating Test Cases \n')
    test_cs_agent = TestCaseAgent("Cash Allocation")
    test_cs_agent.execute()

def generateTestSteps():
    print(f'Generating Test Steps \n')
    test_st_agent = TestStepAgent("Cash Allocation")
    test_st_agent.execute()

def generateTestOutput(sheets=None):
    print(f'Generating Test Output \n')
    test_ot_agent = TestOutputAgent("Cash Allocation")
    test_ot_agent.execute(sheets=sheets)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        arg1 = sys.argv[1]
        match arg1:
            case 'dim':
                generateDimensions()
            case 'sen':
                generateScenarios()
            case 'cas':
                generateTestCases()
            case 'stp':
                generateTestSteps()
            case 'out':
                if len(sys.argv) > 2:
                    sheets = sys.argv[2].split(',')
                    generateTestOutput(sheets)
                else:
                    generateTestOutput()
    else:
        print('Invalid set of parameters passed')