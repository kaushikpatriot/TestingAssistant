from Datamodels.CollateralBlocking import testCases, testSteps, expectedResults

responseSchemaMapper = {"CollateralBlocking":
                        {"TestCases": testCases.testCaseList,
                         "TestSteps": testSteps.testCaseSteps,
                         "ExpectedOutput": expectedResults.expectedResult,
                         "Verification": expectedResults.verificationResult}
                        }

def getResponseSchema(module_name, action):
    return responseSchemaMapper[module_name][action]


folderMapper = {"CollateralBlocking": "KnowledgeBase/CollateralBlocking",
                "CashAllocation": "KnowledgeBase/CashAllocation"}

def getFolderPath(module_name):
    return folderMapper[module_name]

def validateModule(module_name):
    if module_name in ['CollateralBlocking', 'CashAllocation']:
        return True
    return False


def getPrompt(module_name):
    return "Create Test Cases"


