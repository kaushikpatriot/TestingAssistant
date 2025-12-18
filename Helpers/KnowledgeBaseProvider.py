def getKnowledgeBasePath(test_module):
    if test_module == 'Collateral Blocking':
        return 'KnowledgeBase/CollateralBlocking'
    elif test_module == 'Cash Allocation':
        return 'KnowledgeBase/CashAllocation'
    else:
        raise Exception(f'Cannot find the Knowledge Base Path for module {test_module}')