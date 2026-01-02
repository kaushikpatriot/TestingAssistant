from Agents.Agent import PipelineStepAgent, ModelConfig, LLMClient
from Helpers.KnowledgeBaseProvider import getKnowledgeBasePath
from pydantic import BaseModel, Field
import pandas as pd
import os
from Helpers.OutputManager import ExcelManager
import json

class ExpectedResultLine(BaseModel):
    """
    Collateral Summary Result Line

    This model represents a single line in the collateral allocation summary.
    Each line represents a unique combination of key fields and shows how
    collateral is distributed across different requirements and purposes.

    Key Principle: There will be only one record per unique combination of
    the key fields (step, clearing_member, segment_group, segment, etc.)

    Calculation Flow:
    1. Total collateral amount is the starting point
    2. MLN requirements are calculated and blocked first
    3. Remaining amount flows to compliance and capital cushion
    4. After this, the allocation requirements have to considered based on the priority defined and 
        the requested amounts are allocated.
    5. After the allocation is complete, the remaining amount is the unallocated amount
    """

    # KEY FIELDS (Unique Combination Identifiers)
    step: int = Field(
        description="""
        KEY FIELD: Processing step number in the collateral allocation workflow.
        Represents the sequential order in which this allocation was processed.
        Used to track the progression of collateral through different stages.
        """
    )

    memberCode: str = Field(
        description="""
        KEY FIELD: Unique identifier of the clearing member who owns this collateral.
        This should be a running series starting at A001 and go on as A002, A003 etc
        This determines which member's account the collateral belongs to.
        """
    )

    segmentGroup: str = Field(
        description="""
        KEY FIELD: High-level grouping of market segments for collateral management.
        Examples: 'Equity', 'Derivatives', 'Currency', etc.
        Used to categorize segments for risk and operational purposes.
        """
    )

    segment: str = Field(
        description="""
        KEY FIELD: Specific market segment where collateral is being utilized.
        Examples: 'Cash Market', 'F&O', 'Currency Derivatives'
        Each segment has its own collateral requirements and rules.
        Use the same code as the static data in rd_tag_value
        """
    )

    purposeOfDeposit: str = Field(
        description="""
        KEY FIELD: Purpose for which the collateral was deposited.
        Always set to 'COLLATERAL' in this context.
        Distinguishes from other types of deposits (margins, fees, etc.)
        """
    )

    collateralGroup: str = Field(
        description="""
        KEY FIELD: High-level classification of the collateral type.
        Examples: 'CASH, SECURITIES, COMMODITIES'
        Used for risk assessment and haircut calculations.
        Determines the collateral's acceptability across segments.
        Use the same code as the static data in rd_tag_value        """
    )

    collateralComponent: str = Field(
        description="""
        KEY FIELD: Specific sub-type or component of the collateral.
        More granular than collateral_group.
        Examples: 'CASH, CASHEQUIVALENT, NONCASH'
        Used for precise valuation and risk calculations.
        Use the same code as the static data in rd_tag_value
        """
    )

    isFungible: str = Field(
        description="""
        KEY FIELD: Indicates whether this collateral can be shared across segments.
        Values: 'True' or 'False'
        'True' = Can be lent/borrowed between segments (Cash, FD always fungible)
        'False' = Segment-specific, cannot be shared
        Affects MLN and allocation calculations.
        """
    )

    currency: str = Field(
        description="""
        KEY FIELD: Currency denomination of the collateral.
        Always set to 'INR' in current implementation.
        Future versions may support multi-currency collateral.
        """
    )

    applicable_limits: str = Field (
       description = '''
        List the applicable limit for MLN, Compliance requirement and Capital cushion relevant
        to this line based on the member and segment applied based on the Master data. This will impact
        the expected result too.
        '''
    )

    # AMOUNT FIELDS (Calculations and Allocations)
    totalCollateralAmount: float = Field(
        description="""
        STARTING AMOUNT: Total collateral available in this line item.

        Calculation: This is the base amount before any allocations.
        Source: Sum of all deposits/transfers for this key combination.

        This amount flows through the allocation waterfall:
        total_collateral_amount = mln_blocked + mln_lent - mln_borrowed +
                                ob_compliance + ob_capital_cushion + ob_payin_adjustment +
                                ob_payin_lent - ob_payin_borrowed + allocated +
                                allocated_lent - allocated_borrowed + unallocated
        """
    )

    mlnBlockedAmount: float = Field(
        description="""
        MLN CALCULATION: Amount blocked to meet Minimum Liquidity Network requirements.

        Calculation Logic:
        - Only covers MLN requirements for THIS specific line item
        - Does NOT represent total MLN blocked for the entire segment
        - Calculated based on segment's MLN requirements and available collateral
        - Takes priority in the allocation waterfall (allocated first)
        - Collateral borrowed from another segment is not added to this item
        - This will reflect mln utilised from this specific line i.e for the set of primary keys.
          It does not reflect the total mln blocked for the entire segment

        Example: If segment needs 7.5M MLN and this line has 1M collateral,
        entire 1M may be blocked if insufficient total collateral available.
        """
    )

    mlnLentAmount: float = Field(
        description="""
        MLN SHARING: Amount lent FROM this line item TO other segments for their MLN needs.

        Calculation Logic:
        - Only applicable when is_fungible = 'Yes'
        - Occurs when this line has excess collateral after meeting own MLN needs
        - Other segments have insufficient collateral for their MLN requirements
        - Reduces available amount in this line but creates MLN coverage elsewhere

        Formula: Available after own MLN needs - lent to segments with shortfalls
        """
    )

    mlnBorrowedAmount: float = Field(
        description="""
        MLN SHARING: Amount borrowed BY this line item FROM other segments for MLN needs.

        Calculation Logic:
        - Only applicable when is_fungible = 'Yes'
        - Occurs when this line has insufficient collateral for MLN requirements
        - Other segments have excess fungible collateral available
        - Increases effective MLN coverage without actual collateral movement
        - This item will reflect under the same primary set of keys as the segment from which it was borrowed.
          For example if Cash Market lends Cash Equivalent to FNO segment, even if FNO segment has no Cash Equivalent
          a new line is created for Cash Equivalent under FNO segment to reflect borrowed amount

        Formula: MLN requirement - own collateral available for MLN
        """
    )

    obComplianceAmount: float = Field(
        description="""
        COMPLIANCE BLOCK: Amount blocked for regulatory compliance obligations.

        Calculation Logic:
        - Applied after MLN requirements are satisfied
        - Based on compliance rules and member's trading activity
        - Only allocated if sufficient collateral remains after MLN allocation
        - Part of the obligation (OB) waterfall: Compliance → Capital Cushion → Payin

        Condition: Only > 0 when MLN requirements are fully met
        """
    )

    obCapitalCushionAmount: float = Field(
        description="""
        CAPITAL CUSHION: Amount blocked for additional capital buffer requirements.

        Calculation Logic:
        - Applied after MLN and Compliance requirements are satisfied
        - Provides extra safety margin beyond minimum requirements
        - Conservative risk management measure
        - Lower priority than compliance in allocation waterfall

        Condition: Only > 0 when MLN and Compliance are fully satisfied
        """
    )

    obPayinAdjustmentAmount: float = Field(
        description="""
        PAYIN ADJUSTMENT: Amount blocked for settlement and payin adjustments.

        Calculation Logic:
        - Applied after MLN, Compliance, and Capital Cushion are satisfied
        - Covers settlement mismatches and timing differences
        - Ensures smooth settlement operations
        - Lowest priority in obligation waterfall

        Condition: Only > 0 when higher priority obligations are met
        """
    )

    obPayinLent: float = Field(
        description="""
        PAYIN SHARING: Amount lent FROM this line TO other segments for payin adjustments.

        Calculation Logic:
        - Occurs when this line has excess after meeting all obligations
        - Other segments need additional payin adjustment coverage
        - Only applicable for fungible collateral
        - Cross-segment support for settlement needs
        """
    )

    obPayinBorrowed: float = Field(
        description="""
        PAYIN SHARING: Amount borrowed BY this line FROM other segments for payin adjustments.

        Calculation Logic:
        - Occurs when this line needs additional payin coverage
        - Other segments have excess fungible collateral after obligations
        - Provides flexibility in settlement management
        - Virtual increase in payin adjustment capability
        """
    )

    allocated: float = Field(
        description="""
        This is filled using the 'allocationDetails' in the test steps and every line is allocated individually
        to the relevant line item, provided it fully satisfies the requirement.
        This amount is filled with the requested allocation provided the requested allocation amount
        is less than the unallocated amount at the time of allocation. No partial allocation is done.
        If allocation succeeds, this is the total allocation requested. This amount will reduce the 
        unallocated amount.
        **The order of priority while allocating should be taken note of**. 
        """
    )

    allocatedLent: float = Field(
        description="""
        ALLOCATION SHARING: Amount lent FROM this line TO other segments for trading allocation.

        Calculation Logic:
        - Excess allocation capacity shared with segments needing more trading limits
        - Optimizes collateral utilization across the member's portfolio
        - Only for fungible collateral types
        - Enhances overall trading capacity without additional deposits
        """
    )

    allocatedBorrowed: float = Field(
        description="""
        ALLOCATION SHARING: Amount borrowed BY this line FROM other segments for trading allocation.

        Calculation Logic:
        - This segment borrows allocation capacity from other segments
        - Other segments have excess allocation after their trading needs
        - Increases this segment's effective trading capacity
        - Virtual enhancement of trading limits
        """
    )

    unallocated: float = Field(
        description="""
        REMAINING BALANCE: Amount not yet allocated and available for future allocation.

        Calculation Logic:
        - Final remainder after all allocations and obligations
        - Available for additional trading limits or future requirements
        - Buffer for unexpected needs or market volatility
        - Can be allocated as trading activity increases

        Formula: total_collateral_amount - (all blocked amounts + all allocations)

        Note: Should be ≥ 0. Negative values indicate calculation errors.
        """
    )

class ExpectedResult(BaseModel):
  output: list[ExpectedResultLine]
  reason: str = Field(description="Description reason for why this is the expected result")

class TestOutputVerification(BaseModel):
  correctness: bool = Field(description = "Indicates if the output is correct or not")
  correction: str = Field(description="If incorrect, explain what is wrong. Keep it empty if the result is correct")

class TestOutputAgent(PipelineStepAgent):
    generate_model_config = ModelConfig(
                        test_module = '',
                        knowledge_base_path='',
                        role = '''You are senior financial application tester who can write the expected output for a given set of test steps for a test case ''',
                        task_template = '''
                                You are required to carefully understand the requirements, the Test Case and the Test steps given below and do the following
                                Here is the {test_case}
                                "For the given state {current_state} and the given step - {step} and the allocation step - {allocation_steps} - 
                                Can you generate the expected output in the Collateral summary along with the reasoning for the output for Step {step_number} 
                                based on the Blocking Logic and the allocation logic provided. 
                                Note: Rows with keys of   step, memberCode,segment_group,segment,purpose_of_deposit,collateral_group, collateral_component,is_fungible,currency 
                                will be aggregated and there will only be one row for a combination of these field. The MLN, Compliance requirements and Capital Cushion requirements are available in the Masters data. 
                                Use those for the calculation. Ensure after the Blocking is done, Allocation is done based on the requested allocation amounts at the individual CM, TM, UCC or CP levels as applicable"
                                Here is the feedback from the verifier if applicable: {feedback}. Consider this too when generating the output
                                3. List them in the format required
                                ''',
                        task = '' ,
                        output_format = ExpectedResult,
                        provider = 'gemini',
                        model = 'gemini-2.5-pro' #'deepseek-r1:14b' #'qwen-coder:30b'#
                        )
    
    verify_model_config = ModelConfig(
                        test_module = '',
                        knowledge_base_path='',
                        role = '''You are an expert test case verifier for financial application. You understand the nuances of requirements provided''',
                        task_template = '''
                                For the given Test Case: {test_case},  previous state: {previous_state}, current state {current_state} and the given {step} and {allocation_steps} - 
                                Can you verify if the current state is correctly computed as per the Blocking rules and the allocation rules given from the previous state and the step taken? 
                                Ensure allocation is also done correctly after the blocking is done. 
                                Ensure the Allocated amount is equal to the total allocation that is permissible from the requested allocation details. 
                                Note: Rows with keys of   step, memberCode,segment_group,segment,purpose_of_deposit,collateral_group, collateral_component,is_fungible,currency will be aggregated and there will only be one row for a combination of these fields. 
                                If the output is incorrect record the reasons.
                                ''',
                        task =  '' ,
                        output_format = TestOutputVerification,
                        provider = 'gemini',
                        model = 'gemini-2.5-pro'
                        )

    def __init__(self, test_module):
        self.generate_model_config.test_module = test_module
        self.generate_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.verify_model_config.test_module = test_module
        self.verify_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.excel_handler = ExcelManager(mode = 'modify', filepath = os.getenv('TEST_DATA_FILE'))
        self.generate_llm_client = LLMClient(self.generate_model_config.provider, self.generate_model_config.model, self.generate_model_config.knowledge_base_path, test_module) #**self.generate_model_config.model_dump())
        self.verify_llm_client = LLMClient(self.verify_model_config.provider, self.verify_model_config.model, self.verify_model_config.knowledge_base_path, test_module) #**self.verify_model_config.model_dump())
        self.inCorrectSheetList = []

    def load_input_data(self, sheetName):
        test_cases_df = pd.read_csv(os.getenv('TEST_CASES_FILE'))
        test_case_for_id = test_cases_df[test_cases_df['test_case_id'] == sheetName]
        test_step_end_row, steps_df = self.excel_handler.excelToDfConverter(sheetName, "##Test Steps - Start", "##Test Steps - End")
        allocation_end_row, allocation_df = self.excel_handler.excelToDfConverter(sheetName, "##allocation Steps - Start", "##allocation Steps - End")
        end_row = allocation_end_row if allocation_end_row else test_step_end_row
        return test_case_for_id, end_row, steps_df, allocation_df

    def load_knowledge_base(self):
        self.generate_llm_client.upload_files()

    def generate_content(self, prompt, response_schema = None):
        return self.generate_llm_client.generate_content(prompt, response_schema)
    
    def verify_content(self, prompt, response_schema = None):
        return self.verify_llm_client.generate_content(prompt, response_schema)
    
    def execute(self, sheets, verify = True, tries = 3, startMarker = '##Expected Output - Start', endMarker = '##Expected Output - End'):
        if self.generate_model_config.provider == 'gemini':
            self.load_knowledge_base()

        knowledge_files = os.listdir(self.generate_model_config.knowledge_base_path)
        gen_prompt = f'''I have uploaded the following documents. You required to carefully understand the requirements, processing rules, static data, masters that have already been uploaded. 
        Can you confirm if you have the following documents in your cache?
        {str(knowledge_files)}
        '''
        turn1_response = self.generate_content(gen_prompt)
        print(turn1_response)

        sheetNames = sheets if sheets else self.excel_handler.sheetnames #specific sheets if given as input, if not all sheets
        #For each sheet
        for sheetName in sheetNames:

            # if (sheets is None) or (sheets is not None and sheetName in sheets):
            # Correct Output indicator
            isOutputCorrect = False
            # Delete the range from Excel
            self.excel_handler.deleteRange(sheetName, startMarker, endMarker)
            # Convert to Dataframe
            output_df = pd.DataFrame()
            test_case, end_row, steps_df, allocation_df = self.load_input_data(sheetName)
            # Generate output given the current state and the transaction
            step_count, current_state, previous_state = len(steps_df), {}, {}

            gen_prompt = f'''No focus on this specific Test Case sheet. Here ae the details of the test case
            {test_case}.
            Here are the {steps_df} and the {allocation_df}
            **DO NOT use details of any other test case other than the one given here**
            Can you confirm if you have understood the test case?
            '''
            turn1_response = self.generate_content(gen_prompt)
            print(turn1_response)


            for step in range(1, step_count+1):
                feedback = ''
                actual_step = steps_df[steps_df['step'] == step ]
                if len(allocation_df) > 0:
                    allocation_steps = allocation_df[allocation_df['step'] == step]
                    if len(allocation_steps) > 0:
                        allocation_steps_json = allocation_steps.to_json()
                    else:
                        allocation_steps_json = ''
                
                step_number = str(actual_step['step'].item()),
                #Format Prompt
                self.generate_model_config.task = self.generate_model_config.task_template.format(test_case = test_case.to_json(),
                                                                                                    step = actual_step.to_json(),
                                                                                                    allocation_steps = allocation_steps_json,
                                                                                                    step_number = str(step_number),
                                                                                                    current_state = str(current_state), 
                                                                                                    feedback = feedback
                                                                                                    )
                prompt = self.generate_model_config.role + '\n' + self.generate_model_config.task
                # print(f'here is the {prompt} for {step_number}')
                #Generate output
                print(f"\nExpected Output being generated for {sheetName} - {step_number}")
                for i in range(tries):
                    generated_response = self.generate_content(prompt,self.generate_model_config.output_format)
                    current_state = generated_response['output']
                    # print(f'This is the current_state after Step {step_number} - {current_state}')
                    if verify:
                        print(f"\nVerifying Expected Output being generated for {sheetName} - {step_number}")
                        self.verify_model_config.task = self.verify_model_config.task_template.format(test_case = test_case.to_json(),
                                                                                                        previous_state = str(previous_state),
                                                                                                        current_state = str(current_state),
                                                                                                        step = actual_step.to_json(),
                                                                                                        allocation_steps = allocation_steps_json
                                                                                                        )
                        prompt = self.verify_model_config.role + '\n' + self.verify_model_config.task
                        verify_response = self.verify_content(prompt, self.verify_model_config.output_format)
                        feedback = verify_response['correction']
                        if verify_response['correctness'] == True:
                            previous_state = current_state
                            break

                #State update for next iteration
                if verify_response['correctness'] == True:
                    isOutputCorrect = True
                    if output_df.empty:
                        output_df = pd.DataFrame(generated_response['output'])
                    else:
                        output_df = pd.concat([output_df, pd.DataFrame(generated_response['output'])], ignore_index=True)
                else:
                    print(f'Unable to generate correct expected output for {sheetName}. Reason: {feedback}')
                    self.inCorrectSheetList.append(sheetName)
                    isOutputCorrect = False
                    break               

            # Write the output to the sheet
            if isOutputCorrect:
                curr_row = self.excel_handler.writeDfToSheet(sheetName = sheetName, dfToWrite=output_df,
                                    startRow=end_row+2, startMarker="##Expected Output - Start", endMarker="##Expected Output - End")

                # Save the workbook
                self.excel_handler.save_wb()
        print(f'Here are the list of sheets for which correct output could not be produced: {self.inCorrectSheetList}')
        

