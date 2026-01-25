import importlib


def getKnowledgeBasePath(test_module):
    if test_module == 'Collateral Blocking':
        return 'KnowledgeBase/CollateralBlocking'
    elif test_module == 'Cash Allocation':
        return 'KnowledgeBase/CashAllocation'
    else:
        raise Exception(f'Cannot find the Knowledge Base Path for module {test_module}')

def getConfigPath(test_module):
    if test_module == 'Collateral Blocking':
        return 'AgentConfig/CollateralBlocking'
    elif test_module == 'Cash Allocation':
        return 'AgentConfig/CashAllocation'
    else:
        raise Exception(f'Cannot find the Knowledge Base Path for module {test_module}')

def getModule(module_name, file_path):
    """Import a module given its name and file path."""
    # 1. Create the module specification
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    
    # 2. Create a new module object from the specification
    module = importlib.util.module_from_spec(spec)
    
    # 3. (Optional) Register the module in sys.modules
    # This allows other modules to import it normally later
    # sys.modules[module_name] = module
    
    # 4. Execute the module's code
    # This runs the code in the file, populating the module's attributes
    spec.loader.exec_module(module)
    
    return module
