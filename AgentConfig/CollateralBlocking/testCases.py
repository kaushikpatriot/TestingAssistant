from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class collateralSteps(BaseModel):
   step: int = Field(description="This is the step number of the sequence of steps to be executed")
   collateralGroup: list[str] = Field(description = '''The collateral groups to be used for this test case.''')
   collateralComponent: str = Field(description ='''The collateral components which will be used for this test case.''')
   isFungible: list[str] = Field(description = '''Indicates what are the different fungibility of collaterals used for this test case''')

class testCase(BaseModel):
  test_case_id: str = Field(description='''A unique ID for a test case. This should be of the format TC-0001, TC-0002 etc.
                                          ''')
  test_description: str = Field(description='''Describes the test case in detail primarily consisting of
                                               Overall Scenario - Insufficient MLN coverage
                                               MLN Cash and Non - cash coverage
                                               Compliance requirement coverage
                                               Capital cushion coverage''')
  key_validation: str = Field(description = "Lists the key validations for this test case as bullet points prefixed by *")
  segment_scope: str = Field(description="Whether single segment or multiple segments" )
  order: str = Field(description='''State whether Forward (priority order) or Reverse (reverse priority order)''')
  test_steps: list[collateralSteps] = Field(description='''List the sequence of steps that can truly help verify the test case 
                  Use all applicable Collateral types as per the static data to effectively test the case
                  Refer to the static data for the applicable collateral types. 
                  Generate as many steps as required by the Test Scenarios document.
                  Ensure there is a good coverage of all relevant collateral types''')
  memberCode: str = Field(description="Take the member code from the masters data for whom the test case should be generated. **DO NOT REPEAT MEMBER CODES. EACH TEST CASE SHOULD HAVE A UNIQUE MEMBERCODE")

class testCaseList(BaseModel):
    test_case_list: list[testCase]
