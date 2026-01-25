from pydantic import BaseModel, Field

from AgentConfig.config import ModelConfig


class AllocationDetails(BaseModel):
  step: int = Field(description="This is the same step number as the test case step in which allocation data is generated")
  cmCode: str = Field(description="This is the clearing member code")
  segment: str = Field(description='''Segment in in which the allocation is created.
                                  Use the segment code available in static data such as CM, FNO etc
                                  E.g CM, FNO etc''')
  tmCode: str = Field(description="This is the trading member code")
  cpCode: str = Field(description="This is the custodial participant code. **Do not include any special characters like - or _**. Use the pattern CP001, CP002 etc")
  cliCode: str = Field(description="This is the client code. **Do not include any special characters like - or _**. Use the pattern UCC001, UCC002 etc")
  txn_type: str = Field(description = "This can have only 4 possible values. Allocate, De-allocate and Transfer In and Transfer Out")
  amt: float = Field(description="This is the amount of the transaction. *Allocation and Transfer In are a positive amounts, De-allocation and Transfer Out will be negative.*")
  cum_amt: float = Field(description='''This is the cumulative allocation outstanding after the transaction is performed.
                         Irrespective of whether the request PASS or FAIL, cum_amt is filled as that will be the actual request made''')
  exp_amt: float = Field(description='''This is the expected amount of outstanding allocation after the request is sucessfully processed. It is the same as cum_amt if the transaction *PASS*es. 
                         If the request *FAIL*s then this amount is the same as the last successful request. ''')
  trfToSeg: str = Field(description="This the segment to which allocation will be transfered")
  pass_fail: str = Field(description = '''This indicates if the given allocation step passes or fails. If sufficient collateral is unavailable for allocation, this request is marked as FAIL. 
                                        Otherwise mark it as PASS''')
  reason: str = Field(description = "If the allocation step fails, give a short reason for failure in less than 20 words")
  

class TestCaseStep(BaseModel):
  '''
      Generate steps for the given test case. Generate the steps as described in the transaction_sequence and do not generate anything other than that.
  '''
  test_case_id:str = Field(description = 'This refers to the test case id for which the test steps are being generated. This acts as the traceability')
  step: int = Field(description="This is the step number of the sequence of steps to be executed")
  memberCode: str = Field(description="This should be a running series starting at A001 and go on as A002, A003 etc")
  segment: str = Field(description='''Segment in which the collateral is being transacted.
                                  Use the segment code available in static data such as CM, FNO etc
                                  E.g CM, FNO etc''')
  addReduce: str = Field(description="Whether collateral is being added or reduced")
  collateralType: str = Field(description = '''This is the code pertaining to the type of collateral.  
                              Use only those **Code** values that are defined under Tag ID = 14 in the rd_tag_value in static data as applicable for the test case
                              For **Allocation** event always set this field to CASH''')
  event: str = Field(description = '''The type of transaction e.g Deposit, Withdraw, Invoke, Transfer, Renew, Allocation etc. 
                     Use suitable event in the same format as given here.
                     **For Allocation, De-allocation and Transfer, keep the event as Allocation only**''')
  collateralGroup: str = Field(description = '''The collateral group to which this collateral type belongs to.
                                              Use the code as available in the static data''')
  collateralComponent: str = Field(description ='''The collateral component to which this collateral type belongs to.
                                                 Use the code as available in the static data''')
  isFungible: str = Field(description = '''Indicates if the collaeral is fungible across segments or not.
                                            Cash and FD are always fungible.
                                            'True' for fungible and 'False' for non-fungible''')
  currency: str = Field(description='Always set to INR')
  amount: float = Field(description = '''The amount of the transaction. 
                        Where event is Renew, this is the renewal amount                
                        For securities that have quantity and price, this field will have quantity * price''')
  amountInWords: str = Field(description = "The amount in words for the amount of the transaction")
  bank: str = Field(description='Always set to IDFC. This is applicable for Cash, Fixed Deposit and Bank Guarantees')
  account: str = Field(description='Pick up the suitable bank account from the Masters data (Member Bank Account) based on the MemberCode chosen')
  instrumentNo: int = Field(description='''Random 6 digit number for Fixed Deposit and Bank Guarantee. Keep this unique across test cases and test steps.
                            Keep it empty for Cash. Where the event is renewal, this is the old / existing instrument number''')
  branch: str = Field(description="Applied only to Fixed deposit and Bank Guarantee  transactions. Random city in India. Keept it empty for Cash")
  isElectronic: str = Field(description="Applied only to Fixed deposit and Bank Guarantee  transactions. Set to False always")
  quantity: int = Field(description="Applied only Securities include G-Secs. 0 for others")
  isin: str = Field(description = "Applied only to Securities inclding G-Secs. Empty for others. This will be picked up from the master data provided")
  price: float = Field(description="Applied only to Securities inclding G-Secs. 0 for others. This will be picked up from the master data provided")
  value: float = Field(description="Applied only to Securities inclding G-Secs. 0 for others. This is quantity * price. This is the value used for blocking")
  newInstrumentNo: int = Field(description='''This applies only if the event is **Renewal**. Random 6 digit number for Fixed Deposit and Bank Guarantee. 
                               Keep this unique across test cases and test steps. Keep it empty for Cash''')
  toSegment: str = Field(description='''Segment to which the collateral is being transferred. This is applicable only if the event is transfer
                                  Use the segment code available in static data such as CM, FNO etc
                                  E.g CM, FNO etc **THIS DOES NOT APPLY TO TRANSFER OF ALLOCATION''')  
  allocation: list[AllocationDetails] = Field(description='''Applies only when the event is Allocation. Empty for all other events. This event will hold Allocation, De-allocation and Transfer events. 
                                              The allocation process has to consider every line of this data and use it to allocate Cash where applicable as per the rules given''')
  pass_fail: str = Field(description = "This indicates if the overall transaction step passes or fails. Mark this as FAIL even if one of the Allocation request fails")
  reason: str = Field(description = "If the transaction step fails, give a short reason for failure in less than 20 words")


class TestCaseSteps(BaseModel):
  output: list[TestCaseStep]

class TestStepVerification(BaseModel):
    correctness: bool = Field(default=True, description="Is the output correct?")
    correction: str = Field(default="", description="What needs correction")

generate_model_config = ModelConfig(
                    test_module = '',
                    knowledge_base_path='',
                    role = '''You are senior financial application tester who can write test steps required to the execute the test case given the requirements and the test case ''',
                    task_template = '''
                            You required to carefully understand the requirements and the Test Case provided here 
                            {target_scenario}
                            {test_case_id}
                            {given}
                            {when}
                            {then} 
                            {memberCode}
                            and do the following
                            1. Create the necessary and relevant test steps required to effectively test the given test case. 
                            2. Keep each test step comprehensive and independent to test effectively
                            3. **DO NOT** generate steps for any other Test cases other than the Test case provided as **Input**
                            4. Consider verifier's feed back if available
                            ''',
                    task = '' ,
                    output_format = TestCaseSteps,
                    provider = 'gemini',
                    model = 'gemini-2.5-pro' #'deepseek-r1:14b' #'qwen-coder:30b'#
                    )

verify_model_config = ModelConfig(
                    test_module = '',
                    knowledge_base_path='',
                    role = '''You are an expert test data verifier for financial application. You understand the nuances of requirements provided''',
                    task_template = '''
                            Here is the test case for which test steps are being generated. 
                            {target_scenario}
                            {test_case_id}
                            {given}
                            {when}
                            {then} 
                            {memberCode}
                            You required to carefully understand the requirements and the test case provided. 
                            Here are the Test steps generated. 
                            {test_steps}
                            1. The Test case including given when then are already verified
                            2. What you need to verify now is whether the test steps generated correspond to the steps 
                                laid out in the given and when steps. 
                            3. If the steps correspond to the given when steps, then the output is Correct. If not, it is incorrect
                            4. **NOTE: For Allocation Event, the Collateral Type will always be marked as CASH. This can be ignored**
                            ''',
                    task =  '',
                    output_format = TestStepVerification,
                    provider = 'gemini',
                    model = 'gemini-2.5-pro'
                    )
