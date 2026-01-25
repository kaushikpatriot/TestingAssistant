from pydantic import BaseModel, Field

from AgentConfig.config import ModelConfig


class ExpectedResultLine(BaseModel):
    """
    Collateral Summary Result Line

    This model represents a single line in the collateral allocation summary.
    Each line represents a unique combination of key fields and shows how
    collateral is distributed across different requirements and purposes.
    **A record will be present for a segment even if it has borrowed collateral without its own total collateral.**

    Key Principle: There will be only one record per unique combination of
    the key fields (step, clearing_member, segment_group, segment, etc.)

    Calculation Flow:
    1. Total collateral amount is the starting point
    2. MLN requirements are calculated and blocked first
    3. Remaining amount flows to compliance and capital cushion
    4. After this, the allocation requirements have to considered based on the priority defined and 
        the requested amounts are allocated.
    5. After the allocation is complete, the remaining amount is the unallocated amount
    6. 
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
        - **MLN borrowed should not be reflected here**
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
        - **This amount is not included in mlnBlockedAmount**

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
        This field will be filled or modified during Allocation events for Cash Allocation or Deposit events for Securities.
        """
    )

    allocatedLent: float = Field(
        description="""
        This is the amount lent by the segment to another segment for allocation purposes. Refer to the allocation priority rules
        to know which segment lends first.
        This will be filled whenever a segment lends Collateral (in respective line) to another segment for Cash Allocation

        """
    )

    allocatedBorrowed: float = Field(
        description="""
        This is the amount borrowed by a segment from segments for the purposes of allocation. On allocation, if the segment
        has its own collateral then the "Allocation" column is filled. If borrowed, then this field is filled with value
        This will be filled whenever a segment borrows Collateral (in respective line) from another segment for Cash Allocation.
        this value will not be filled in the allocated field.
        """
    )

    unallocated: float = Field(
        description="""
        REMAINING BALANCE: Amount not yet allocated and available for future allocation.

        Calculation Logic:
        - Final remainder after MLN Block, MLN Lent, Compliance requirement and Capital cushion blocks if any, allocation and lent for allocation
        - Buffer for unexpected needs or market volatility

       Formula: total_collateral_amount - (block for MLN + Lent for MLN block to other segment + compliance requirements (if any) + capital cusion (if any) + payin adjustment (if any) + allocated + lent for allocation to other segments) 

        Note: Should be ≥ 0. Negative values indicate calculation errors.
        """
    )

class ExpectedResult(BaseModel):
  '''
  Key Principle: There will be only one record per unique combination of the key fields (step, clearing_member, segment_group, segment, etc.)
  Suitable ExpectedResultLine is created for each segment to which Collateral balances are applied.
  '''
  output: list[ExpectedResultLine]
  reason: str = Field(description="Description reason for why this is the expected result")

class TestOutputVerification(BaseModel):
    correctness: bool = Field(default=True, description="Is the output correct?")
    correction: str = Field(default="", description="What needs correction")

generate_model_config = ModelConfig(
                    test_module = '',
                    knowledge_base_path='',
                    role = '''You are senior financial application tester who can write the expected output for a given set of test steps for a test case ''',
                    task_template = '''
                            You are required to carefully understand the requirements, the Test Case and the Test steps given below and do the following
                            Here is the {test_case}
                            "For the given state {current_state} and the given step - {step} and the allocation step - {allocation_steps} - 
                            Firstly think through the impact of the given step on the current state and how that will change. 
                            **Get the list of segments that will be impacted by this step**
                            Base on that, can you generate the expected output in the Collateral summary after the specific step is executed along with the reasoning for the output for Step {step_number} 
                            based on the Blocking Logic and the allocation logic provided. 
                            Pay attention to TR_4.3. **Notes for creating Test Cases and Test Steps for Allocation** especially the *section on Expected output generation process*
                            Steps to be executed will be
                            1. Process the transaction as required
                            2. Apply blocking logic (MLN, Compliance requirements and Capital Cushion as per the blocking logic)
                                Pay ATTENTION to #### **System-Wide MLN Completion:** to ensure ALL segments in the CM-MS-C-Masters_v02.txt that have their MLN requirements are met before Collateal is allocated to other requirements
                                ***MLN Requirements***
                                Segment, Max Non-Cash Limit, Min Cash Limit, Total MLN Requirement
                                FNO,1500000,3500000, 5000000
                                CD,4000000,2000000,6000000
                                SLB,5000000,1000000,6000000

                                #### **System-Wide MLN Completion:**
                                - **MLN is COMPLETE** only when ALL segments have satisfied their full MLN requirements
                                - **MLN is INCOMPLETE** if ANY segment has unmet MLN requirements
                                - **Rule:** If MLN is incomplete, ALL available collateral must go to MLN blocking first
                                - Example even if the steps involve only FNO and CD, if SLB has MLN requirements defined, that has to be considered too.
                            3. If the current step is an **Allocation event, then **TAKE THE PREVIOUS STATE** and apply allocation or de-allocation as per the Allocation Rules provided.
                                **Ensure the collateral borrowed or lent is properly reflected against the correct Collateral type line in the respective segments.
                                **DO NOT perform Cash or Cash equivalent allocation on any event other than Allocation**
                                **Allocate from the respective collateral component that is available and not ONLY CASH**

                            The final result will be the expected output
                            Note: Rows with keys of   step, memberCode,segment_group,segment,purpose_of_deposit,collateral_group, collateral_component,is_fungible,currency 
                            will be aggregated and there will only be one row for a combination of these field. The MLN, Compliance requirements and Capital Cushion requirements are available in the Masters data. 
                            Use those for the calculation. Ensure after the Blocking is done, Allocation is done based on the requested allocation amounts at the individual CM, TM, UCC or CP levels as applicable"
                            Consider Verifier's feedback if available along with the output for correction, if applicable

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
                            Ensure allocation is also done correctly **after the blocking is done**. 
                            Ensure the Allocated amount is equal to the total allocation that is permissible from the requested allocation details. 
                            Note: Rows with keys of   step, memberCode,segment_group,segment,purpose_of_deposit,collateral_group, collateral_component,is_fungible,currency will be aggregated and there will only be one row for a combination of these fields. 
                            **Verify only the current state** and you **DO NOT** have to validate the test case, previous state, step or allocation steps
                            If the output is incorrect record the reasons.
                            ''',
                    task =  '' ,
                    output_format = TestOutputVerification,
                    provider = 'gemini',
                    model = 'gemini-2.5-pro'
                    )
