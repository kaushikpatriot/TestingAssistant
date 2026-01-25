from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class allocationDetails(BaseModel):
  step: int = Field(description="This is the step number of the sequence of steps to be executed")
  tmCode: str = Field(description="This is the trading member code")
  cpCode: str = Field(description="This is the custodial participant code")
  cliCode: str = Field(description="This is the client code")
  amt: float = Field(description="This is the amount allocated")
  trfToSeg: str = Field(description="This the segment to which allocation will be transfered")


class testCaseStep(BaseModel):
  '''
      Generate steps for the given test case. Generate the steps as described in the transaction_sequence and do not generate anything other than that.
  '''
  step: int = Field(description="This is the step number of the sequence of steps to be executed")
  memberCode: str = Field(description="This should be a running series starting at A001 and go on as A002, A003 etc")
  segment: str = Field(description='''Segment in which the collateral is being transacted.
                                  Use the segment code available in static data such as CM, FNO etc
                                  E.g CM, FNO etc''')
  addReduce: str = Field(description="Whether collateral is being added or reduced")
  collateralType: str = Field(description = "This is the code pertaining to the type of collateral.  Use only those **Code** values that are defined under Tag ID = 14 in the rd_tag_value in static data as applicable for the test case")
  event: str = Field(description = "The type of transaction e.g Deposit, Withdraw, Invoke, Transfer, Renew etc. Use suitable event in the same format as given here.")
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
                                  E.g CM, FNO etc''')  
  allocation: list[allocationDetails] = Field(description="Applies only when the event is Allocation. Empty for all other events")


class testCaseSteps(BaseModel):
  steps: list[testCaseStep]
