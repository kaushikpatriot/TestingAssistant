from Agents.Agent import PipelineStepAgent, LLMClient
from AgentConfig.config import ModelConfig
from Helpers.KnowledgeBaseProvider import getKnowledgeBasePath, getConfigPath, getModule
import pandas as pd
import os
from Helpers.OutputManager import CsvManager as csv
import yaml
import importlib.util


class TestScenarioAgent(PipelineStepAgent):
    def __init__(self, test_module):
        file_path = os.path.join(getConfigPath(test_module=test_module), "TestScenarioConfig.py")
        moduleObj = getModule("TestScenarioConfig", file_path)
        self.generate_model_config = moduleObj.generate_model_config
        self.verify_model_config = moduleObj.verify_model_config
        self.generate_model_config.test_module = test_module
        self.generate_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.verify_model_config.test_module = test_module
        self.verify_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.generate_llm_client = LLMClient(self.generate_model_config.provider, self.generate_model_config.model, self.generate_model_config.knowledge_base_path, test_module,'generator') #**self.generate_model_config.model_dump())
        self.verify_llm_client = LLMClient(self.verify_model_config.provider, self.verify_model_config.model, self.verify_model_config.knowledge_base_path, test_module,'verifier') #**self.verify_model_config.model_dump())


    def load_input_data(self):
        with open(os.getenv('TEST_DIMENSIONS_FILE'), 'r') as f:
            self.dimensions = yaml.safe_load(f)
        f.close()
        # self.input_df = pd.read_csv(f"{os.getenv('TEST_DIMENSIONS_FILE')}")         

    def load_generator_knowledge_base(self):
        self.generate_llm_client.upload_files()

    def load_verifier_knowledge_base(self):
        self.verify_llm_client.upload_files()

    def generate_content(self, prompt, response_schema=None):
        return self.generate_llm_client.generate_content(prompt, response_schema)
    
    def verify_content(self, prompt, response_schema=None):
        return self.verify_llm_client.generate_content(prompt, response_schema)
    
    def execute(self, verify = True, tries = 1):
        if self.generate_model_config.provider == 'gemini':
            self.load_generator_knowledge_base()
        
        if verify and self.verify_model_config.provider == 'gemini':
            self.load_verifier_knowledge_base()

        self.load_input_data()

        knowledge_files = os.listdir(self.generate_model_config.knowledge_base_path)
        gen_prompt = f'''I have uploaded the following documents. You required to carefully understand the requirements, processing rules, static data, masters that have already been uploaded. 
        Can you confirm if you have the following documents in your cache?
        {str(knowledge_files)}
        '''
        turn1_response = self.generate_content(gen_prompt)
        print(turn1_response)
        
        scenarios_df = pd.DataFrame()

        # for step_num in range(iterations):
        for i in range(tries):
            self.generate_model_config.task = self.generate_model_config.task_template.format(dimensions = str(self.dimensions))
            prompt = self.generate_model_config.role + '\n' + self.generate_model_config.task
            generated_response = self.generate_content(prompt, self.generate_model_config.output_format)
            response_df = pd.DataFrame(generated_response['output'])
            if verify:
                self.verify_model_config.task = self.verify_model_config.task_template.format(dimensions = str(self.dimensions), test_scenarios = str(generated_response['output']))
                verify_prompt = self.verify_model_config.role + '\n' + self.verify_model_config.task
                verify_response = self.verify_content(verify_prompt, self.verify_model_config.output_format)
                if verify_response:
                    verify_df = pd.DataFrame(verify_response['output'])
                # if verify_response['overall_score'] >= 70:
                #     break
        if scenarios_df.empty:
            scenarios_df = response_df
        else:
            scenarios_df = pd.concat([scenarios_df, response_df], ignore_index=True)
        
        scenarios_df = pd.concat([scenarios_df, verify_df], ignore_index=True)
        
        csv.writeDfToCsv(scenarios_df,os.getenv('TEST_SCENARIOS_FILE'))
        #print(generated_response)
