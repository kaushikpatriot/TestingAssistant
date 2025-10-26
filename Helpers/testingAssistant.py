from Helpers.agent import AgentManager

class TestingAssistant:
    def __init__(self):
        self.agent = AgentManager()

    def createTestCases(self, prompt, folderPath, response_schema):
        print(response_schema)
        response = self.agent.generateResponse(prompt, folderPath, response_schema)

    def createTestSteps(self):
        pass

    def createTestOutput(self):
        pass

