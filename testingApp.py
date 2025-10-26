from fastapi import FastAPI
import uvicorn
from Helpers.testingAssistant import TestingAssistant
from Helpers.moduleInputs import getFolderPath, getResponseSchema, getPrompt, validateModule


app = FastAPI(
    title="Testing Agent API",
    description="API for generating test cases",
    version="1.0.0"
)
@app.get('/health')
def healthCheck():
    return {"message": "All is well!"}

@app.get('/testcases/{module_name}')
def createTestCases(module_name):
    testAssistant = TestingAssistant()

    if validateModule(module_name):
        folderPath = getFolderPath(module_name)
        response_schema = getResponseSchema(module_name,'TestCases')
        prompt = getPrompt(module_name)
        testAssistant.createTestCases(prompt, folderPath, response_schema)
        return {"message": "Worked!"}
    else:
        return {"error": "This is not a valid module name"}

if __name__ == "__main__":
    uvicorn.run("testingApp:app", host="0.0.0.0", port=8000, reload=True)