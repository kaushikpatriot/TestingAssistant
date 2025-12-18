from Agents.Agent import PipelineStepAgent, ModelConfig, LLMClient
from Helpers.KnowledgeBaseProvider import getKnowledgeBasePath
from pydantic import BaseModel, Field
import pandas as pd
import os

class AllocationDetails(BaseModel):
  step: int = Field(description="This is the same step number as the test case step in which allocation data is generated")
  cmCode: str = Field(description="This is the clearing member code")
  segment: str = Field(description='''Segment in in which the allocation is created.
                                  Use the segment code available in static data such as CM, FNO etc
                                  E.g CM, FNO etc''')
  tmCode: str = Field(description="This is the trading member code")
  cpCode: str = Field(description="This is the custodial participant code")
  cliCode: str = Field(description="This is the client code")
  txn_type: str = Field(description = "This can 4 possible values. Allocate, De-allocate and Transfer In and Transfer Out")
  amt: float = Field(description="This is the amount of the transaction. Allocation and Transfer In are a positive amounts, De-allocation and Transfer Out will be negative.")
  cum_amt: float = Field(description="This is the cumulative allocation outstanding after the transaction is performed. This will take into account the allocation transactions in the previous steps too ")
  trfToSeg: str = Field(description="This the segment to which allocation will be transfered")
  pass_fail: str = Field(description = "This indicates if the given allocation passes or fails")
  reason: str = Field(description = "If the allocation fails, give a short reason for failure in less than 20 words")
  

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
  collateralType: str = Field(description = "This is the code pertaining to the type of collateral.  Use only those **Code** values that are defined under Tag ID = 14 in the rd_tag_value in static data as applicable for the test case")
  event: str = Field(description = "The type of transaction e.g Deposit, Withdraw, Invoke, Transfer, Renew, Allocation etc. Use suitable event in the same format as given here.")
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
  instrumentNo: int = Field(description='''Random 6 digit number for Fixed Deposit and Bank Guarantee. Keep it empty for Cash
                                        Where the event is renewal, this is the old / existing instrument number''')
  branch: str = Field(description="Applied only to Fixed deposit and Bank Guarantee  transactions. Random city in India. Keept it empty for Cash")
  isElectronic: str = Field(description="Applied only to Fixed deposit and Bank Guarantee  transactions. Set to False always")
  quantity: int = Field(description="Applied only Securities include G-Secs. 0 for others")
  isin: str = Field(description = "Applied only to Securities inclding G-Secs. Empty for others. This will be picked up from the master data provided")
  price: float = Field(description="Applied only to Securities inclding G-Secs. 0 for others. This will be picked up from the master data provided")
  value: float = Field(description="Applied only to Securities inclding G-Secs. 0 for others. This is quantity * price. This is the value used for blocking")
  newInstrumentNo: int = Field(description='''This applies only if the event is **Renewal**. Random 6 digit number for Fixed Deposit and Bank Guarantee. Keep it empty for Cash''')
  toSegment: str = Field(description='''Segment to which the collateral is being transferred. This is applicable only if the event is transfer
                                  Use the segment code available in static data such as CM, FNO etc
                                  E.g CM, FNO etc **THIS DOES NOT APPLY TO TRANSFER OF ALLOCATION''')  
  allocation: list[AllocationDetails] = Field(description='''Applies only when the event is Allocation. Empty for all other events. This event will hold Allocation, De-allocation and Transfer events. 
                                              The allocation process has to consider every line of this data and use it to allocate Cash where applicable as per the rules given''')
  pass_fail: str = Field(description = "This indicates if the overall allocation passes or fails")
  reason: str = Field(description = "If the allocation fails, give a short reason for failure in less than 20 words")


class TestCaseSteps(BaseModel):
  output: list[TestCaseStep]

class TestStepVerification(BaseModel):
    overall_score: int = Field(description = 'Provides a score out of 100 in terms of correctness of the test steps')

class TestStepAgent(PipelineStepAgent):
    generate_model_config = ModelConfig(
                        test_module = '',
                        knowledge_base_path='',
                        role = '''You are senior financial application tester who can write test steps required to the execute the test case given the requirements and the test case ''',
                        task = '''
                                You required to carefully understand the requirements and the Test Case provided as **Input** and do the following
                                1. Create the necessary and relevant test steps required to effectively test the given test case. 
                                2. Keep each test step comprehensive and independent to test effectively
                                3. **DO NOT** generate steps for any other Test cases other than the Test case provided as **Input**
                                3. List them in the format required
                                ''' ,
                        output_format = TestCaseSteps,
                        provider = 'ollama',
                        model = 'gpt-oss:20b' #'deepseek-r1:14b' #'qwen-coder:30b'#
                        )
    
    verify_model_config = ModelConfig(
                        test_module = '',
                        knowledge_base_path='',
                        role = '''You are an expert test case verifier for financial application. You understand the nuances of requirements provided''',
                        task = '''
                                You required to carefully understand the requirements, the Test case provided and the Test steps is attached
                                1. Verify the input given and provide a score of the correctness of the input.
                                '''  ,
                        output_format = TestStepVerification,
                        provider = 'ollama',
                        model = 'deepseek-r1:14b'
                        )

    def __init__(self, test_module):
        self.generate_model_config.test_module = test_module
        self.generate_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.verify_model_config.test_module = test_module
        self.verify_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)

    def load_input_data(self):
        self.input_df = pd.read_csv(f"{os.getenv('TEST_CASES_FILE')}")

    def load_knowledge_base(self):
        llm_client = LLMClient(**self.generate_model_config.model_dump())
        llm_client.upload_files()

    def generate_content(self, input):
        llm_client = LLMClient(**self.generate_model_config.model_dump())
        return llm_client.generate_content(input)
    
    def verify_content(self, output):
        llm_client = LLMClient(**self.verify_model_config.model_dump())
        return llm_client.generate_content(input = output)
    
    def save_output(self, output:pd.DataFrame, test_case):
        #df = pd.DataFrame(output)
        output_file = f"{os.getenv('TEST_DATA_DIR')}/teststeps_{test_case}.csv" 
        output.to_csv(output_file)    
    
    def execute(self, verify = True, tries = 1):
        if self.generate_model_config.provider == 'gemini':
            self.load_knowledge_base()

        self.load_input_data()
        for record_num in range(3):#len(self.input_df)):
            input_data = self.input_df.iloc[record_num]
            for i in range(tries):
                generated_response = self.generate_content(input_data)

                if verify:
                    verify_response = self.verify_content(generated_response)
                    if verify_response['overall_score'] >= 70:
                        break
            output_df = pd.DataFrame(generated_response['output'])
            # print(f'Input Data {input_data}')
            # print(f'Output Data {output_df}')
            # print(f'Final Data {final_df}')
            self.save_output(output_df, input_data['test_case_id'])
        #print(generated_response)
