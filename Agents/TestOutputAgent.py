from Agents.Agent import PipelineStepAgent, ModelConfig, LLMClient
from Helpers.KnowledgeBaseProvider import getKnowledgeBasePath
from pydantic import BaseModel, Field
import pandas as pd
import os

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
        to the relevant line item, provided it is fully satisfies the requirement.
        This amount is filled with the requested allocation provided the requested allocation amount
        is less than the unallocated amount at the time of allocation. No partial allocation is done.
        If allocation succeeds, this is the total allocation requested. This amount will reduce the 
        unallocated amount.
        The order of priority while allocating should be taken note of. 
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
                        role = '''You are senior financial application tester who can write test steps required to the execute the test case given the requirements and the test case ''',
                        task = '''
                                You required to carefully understand the requirements and the Test Case provided as **Input** and do the following
                                1. Create the necessary and relevant test steps required to effectively test the given test case. 
                                2. Keep each test step comprehensive and independent to test effectively
                                3. **DO NOT** generate steps for any other Test cases other than the Test case provided as **Input**
                                3. List them in the format required
                                ''' ,
                        output_format = ExpectedResult,
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
                        output_format = TestOutputVerification,
                        provider = 'ollama',
                        model = 'deepseek-r1:14b'
                        )

    def __init__(self, test_module):
        self.generate_model_config.test_module = test_module
        self.generate_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.verify_model_config.test_module = test_module
        self.verify_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)

    def load_input_data(self):
        self.input_df = pd.read_csv(f"{os.getenv('TEST_DATA_DIR')}/teststeps_TC-0001.csv")

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
        for record_num in range(len(self.input_df)):
            input_data = self.input_df.iloc[record_num]
            for i in range(tries):
                generated_response = self.generate_content(input_data)

                if verify:
                    verify_response = self.verify_content(generated_response)
                    if verify_response['correctness'] == True:
                        break
            output_df = pd.DataFrame(generated_response['output'])
            # print(f'Input Data {input_data}')
            # print(f'Output Data {output_df}')
            # print(f'Final Data {final_df}')
            self.save_output(output_df, input_data['step'])
        #print(generated_response)
