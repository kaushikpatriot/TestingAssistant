import json
from Agents.Agent import PipelineStepAgent, LLMClient
from Helpers.KnowledgeBaseProvider import getConfigPath, getKnowledgeBasePath, getModule
import pandas as pd
import os
from Helpers.OutputManager import CsvManager as csv
import yaml


class TestCaseAgent(PipelineStepAgent):
    def __init__(self, test_module):
        file_path = os.path.join(getConfigPath(test_module=test_module), "TestCaseConfig.py")
        moduleObj = getModule("TestCaseConfig", file_path)
        self.generate_model_config = moduleObj.generate_model_config
        self.verify_model_config = moduleObj.verify_model_config
        self.generate_model_config.test_module = test_module
        self.generate_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.verify_model_config.test_module = test_module
        self.verify_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.generate_llm_client = LLMClient(self.generate_model_config.provider, self.generate_model_config.model, self.generate_model_config.knowledge_base_path, test_module, 'generator') #**self.generate_model_config.model_dump())
        self.verify_llm_client = LLMClient(self.verify_model_config.provider, self.verify_model_config.model, self.verify_model_config.knowledge_base_path, test_module, 'verifier') #**self.verify_model_config.model_dump())


    def load_input_data(self):
        self.input_df = pd.read_csv(f"{os.getenv('TEST_SCENARIOS_FILE')}")
        with open(os.getenv('TEST_DIMENSIONS_FILE'), 'r') as f:
            self.dimensions = yaml.safe_load(f)
        f.close()


    def load_generator_knowledge_base(self):
        self.generate_llm_client.upload_files()

    def load_verifier_knowledge_base(self):
        self.verify_llm_client.upload_files()

    def generate_content(self, prompt, response_schema=None):
        return self.generate_llm_client.generate_content(prompt, response_schema)
    
    def verify_content(self, prompt, response_schema=None):
        return self.verify_llm_client.generate_content(prompt, response_schema)
    
    def execute(self, start = 1, end = -1, gen_instruct = '', verify = True, tries = 2, wait = True):
        inCorrectScenarios = []
        if self.generate_model_config.provider == 'gemini':
            self.load_generator_knowledge_base()

        if verify and self.verify_model_config.provider == 'gemini':
            self.load_verifier_knowledge_base()

        self.load_input_data()
        final_df = pd.DataFrame()
        knowledge_files = os.listdir(self.generate_model_config.knowledge_base_path)
        gen_prompt = f'''I have uploaded the following documents. You required to carefully understand the requirements, processing rules, static data, masters that have already been uploaded. 
        Can you confirm if you have the following documents in your cache?
        {str(knowledge_files)}
        '''
        turn1_response = self.generate_content(gen_prompt)
        print(turn1_response)
        for record_num in range(start-1, (len(self.input_df) if end < 0 else min(end, len(self.input_df)))):
            scenario = self.input_df.iloc[record_num]

            verifier_feedback, current_output, verify_response = '', '', None
            self.generate_model_config.task = self.generate_model_config.task_template.format(scenario_id = str(scenario['scenario_id']),scenario=str(scenario['scenario_description']), 
                                                                                              dimensions = str(scenario['scenario_dimension']), memberCode = str(scenario['member_code']),
                                                                                              general_instructions = gen_instruct, test_dimensions = self.dimensions)
            print(f"\n Generating Test Cases for Scenario {record_num+1}")
            for i in range(tries):
                #Generation
                prompt = self.generate_model_config.role + '\n' + self.generate_model_config.task + '\n' + f'Verifier feedback: {verifier_feedback} , Previous output: {current_output}'
                generated_response = self.generate_content(prompt, self.generate_model_config.output_format)
                output_df = pd.DataFrame(generated_response['output'])
                
                #Verification                
                self.verify_model_config.task = self.verify_model_config.task_template.format(given_steps = output_df['given_steps'].to_json(), when_steps = output_df['when_steps'].to_json(), then = output_df['then'].to_json(),
                                                                                              scenario_id = str(scenario['scenario_id']), scenario=str(scenario['scenario_description']), memberCode = str(scenario['member_code']),
                                                                                              dimensions = str(scenario['scenario_dimension']))    
                prompt = self.verify_model_config.role + '\n' + self.verify_model_config.task
                if verify:
                    # time.sleep(2)
                    print(f'Verifying for the {i+1}th time')
                    verify_response = self.verify_content(prompt,self.verify_model_config.output_format)
                    if verify_response['isCorrect']:
                        break
                    else:
                        verifier_feedback = verify_response['correction']
                        current_output = json.dumps({'given_steps': output_df['given_steps'].to_json(), 'when_steps': output_df['when_steps'].to_json(), 'then': output_df['then'].to_json()}, indent = 2)

            if not verify or (verify_response and verify_response['isCorrect']):
                if final_df.empty:
                    final_df = output_df
                else:
                    final_df = pd.concat([final_df, output_df], ignore_index = True)
                csv.writeDfToCsv(final_df, os.getenv('TEST_CASES_FILE'))
            else:
                print(f'Unable to generate correct test case for Scenario {record_num+1} because {verifier_feedback}')
                inCorrectScenarios.append(scenario['scenario_id'])
        
        if len(inCorrectScenarios) > 0:
            print(f'Unable to generate correct test cases for {inCorrectScenarios}')
