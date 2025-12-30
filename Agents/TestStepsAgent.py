from Agents.Agent import PipelineStepAgent, ModelConfig, LLMClient
from Helpers.KnowledgeBaseProvider import getKnowledgeBasePath
from pydantic import BaseModel, Field
import pandas as pd
import os
from Helpers.OutputManager import ExcelManager

class AllocationDetails(BaseModel):
  step: int = Field(description="This is the same step number as the test case step in which allocation data is generated")
  cmCode: str = Field(description="This is the clearing member code")
  segment: str = Field(description='''Segment in in which the allocation is created.
                                  Use the segment code available in static data such as CM, FNO etc
                                  E.g CM, FNO etc''')
  tmCode: str = Field(description="This is the trading member code")
  cpCode: str = Field(description="This is the custodial participant code")
  cliCode: str = Field(description="This is the client code")
  txn_type: str = Field(description = "This can have only 4 possible values. Allocate, De-allocate and Transfer In and Transfer Out")
  amt: float = Field(description="This is the amount of the transaction. Allocation and Transfer In are a positive amounts, De-allocation and Transfer Out will be negative.")
  cum_amt: float = Field(description="This is the cumulative allocation outstanding after the transaction is performed. This will take into account the allocation transactions in the previous steps too ")
  exp_amt: float = Field(description='''This is the expected amount of allocation after the request is processed. It is the same as cum_amt if the transaction succeeds. 
                         If the request fails then this amount is the same as the last successful request''')
  trfToSeg: str = Field(description="This the segment to which allocation will be transfered")
  pass_fail: str = Field(description = "This indicates if the given allocation step passes or fails")
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
  pass_fail: str = Field(description = "This indicates if the overall transaction step passes or fails")
  reason: str = Field(description = "If the transaction step fails, give a short reason for failure in less than 20 words")


class TestCaseSteps(BaseModel):
  output: list[TestCaseStep]

class TestStepVerification(BaseModel):
    isCorrect: bool = Field(description = 'Reports True if the output is correct, False if wrong')
    correction: str = Field(description = 'Describe what needs correction')

class TestStepAgent(PipelineStepAgent):
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
                                and also consider the verifier's feedback {feedback} if available
                                and do the following
                                1. Create the necessary and relevant test steps required to effectively test the given test case. 
                                2. Keep each test step comprehensive and independent to test effectively
                                3. **DO NOT** generate steps for any other Test cases other than the Test case provided as **Input**
                                3. List them in the format required
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
                                You required to carefully understand the requirements, the Test case provided and the Test steps is attached
                                {test_steps}
                                1. Verify the output primarily the steps, collateral types used and the amounts. If these are correct, you can report the steps as correct.
                                ''',
                        task =  '',
                        output_format = TestStepVerification,
                        provider = 'gemini',
                        model = 'gemini-2.5-pro'
                        )

    def __init__(self, test_module):
        self.generate_model_config.test_module = test_module
        self.generate_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.verify_model_config.test_module = test_module
        self.verify_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.excel_handler = ExcelManager(mode = 'new', filepath = os.getenv('TEST_DATA_FILE'))
        self.generate_llm_client = LLMClient(self.generate_model_config.provider, self.generate_model_config.model, self.generate_model_config.knowledge_base_path, test_module) #**self.generate_model_config.model_dump())
        self.verify_llm_client = LLMClient(self.verify_model_config.provider, self.verify_model_config.model, self.verify_model_config.knowledge_base_path, test_module) #**self.verify_model_config.model_dump())

    def load_input_data(self):
        self.input_df = pd.read_csv(f"{os.getenv('TEST_CASES_FILE')}")

    def load_knowledge_base(self):
        self.generate_llm_client.upload_files()

    def generate_content(self, prompt, response_schema=None):
        return self.generate_llm_client.generate_content(prompt, response_schema)
    
    def verify_content(self, prompt, response_schema=None):
        return self.verify_llm_client.generate_content(prompt, response_schema)
    
    def execute(self, start=1, end=-1, verify = True, tries = 3):
        if self.generate_model_config.provider == 'gemini':
            self.load_knowledge_base()

        self.load_input_data()
        knowledge_files = os.listdir(self.generate_model_config.knowledge_base_path)
        gen_prompt = f'''I have uploaded the following documents. You required to carefully understand the requirements, processing rules, static data, masters that have already been uploaded. 
        Can you confirm if you have the following documents in your cache?
        {str(knowledge_files)}
        '''
        turn1_response = self.generate_content(gen_prompt)
        print(turn1_response)

        feedback = ''
        for record_num in range(start-1, (len(self.input_df) if end < 0 else end)):#len(self.input_df)):
            input_data = self.input_df.iloc[record_num]
            self.generate_model_config.task = self.generate_model_config.task_template.format(target_scenario = str(input_data["target_scenario"]),
                                                                                              test_case_id = str(input_data["test_case_id"]), 
                                                                                              given = str(input_data["given"]) + '\n' + str(input_data["given_steps"]),
                                                                                              when = str(input_data["when"]) + '\n' + str(input_data["when_steps"]),
                                                                                              then = str(input_data["then"]),
                                                                                              memberCode = str(input_data['memberCode']),
                                                                                              feedback = feedback)
            prompt = self.generate_model_config.role + '\n' + self.generate_model_config.task
            for i in range(tries):
                generated_response = self.generate_content(prompt, self.generate_model_config.output_format)
                output_df = pd.DataFrame(generated_response['output'])
                if verify:
                    self.verify_model_config.task = self.verify_model_config.task_template.format(test_steps = str(output_df))
                    prompt = self.verify_model_config.role + '\n' + self.verify_model_config.task
                    verify_response = self.verify_content(prompt, self.verify_model_config.output_format)
                    if verify_response['isCorrect']:
                        break
                    else:
                        feedback = verify_response['correction']
            if verify_response['isCorrect']:
                self.excel_handler.createWorksheet(sheetName=input_data['test_case_id'])
                #Identify columns that have lists as its value. They will be written out separately on Excel
                list_cols = [
                            c for c in output_df.columns
                            if output_df[c].apply(lambda x: isinstance(x, list)).any()
                    ]
                # print(f'Writing Test Steps to File for {record_num+1}')
                curr_row = self.excel_handler.writeDfToSheet(sheetName = input_data['test_case_id'], dfToWrite=output_df.drop(columns=list_cols),
                                                startRow=1, startMarker="##Test Steps - Start", endMarker="##Test Steps - End")
                print(f'Written Test Steps to File for {record_num+1}')
                #Writing Sub steps in a separate set of rows. E.g. Allocation Steps
                # print(f'Writing Allocation Steps to File for {record_num+1}')
                for col in list_cols:
                    filtered_series = output_df.loc[output_df[col].str.len() > 0, col]
                    print(filtered_series)
                    sub_df = pd.DataFrame(filtered_series.explode().to_list())
                    # print(sub_df)
                    curr_row = self.excel_handler.writeDfToSheet(sheetName = input_data['test_case_id'], dfToWrite=sub_df,
                                                startRow=curr_row+1, startMarker=f"##{col} Steps - Start", endMarker=f"##{col} Steps - End")
                print(f'Written Allocation Steps to File for {record_num+1}')        
                self.excel_handler.save_wb()
            else:
                print(f"Unable to generate test steps correctly for {input_data['test_case_id']} because of {feedback}")