from Agents.Agent import PipelineStepAgent, ModelConfig, LLMClient
from Helpers.KnowledgeBaseProvider import getConfigPath, getKnowledgeBasePath, getModule
from pydantic import BaseModel, Field
import pandas as pd
import os
from Helpers.OutputManager import ExcelManager
import time
import sys


class TestStepAgent(PipelineStepAgent):
    def __init__(self, test_module):
        file_path = os.path.join(getConfigPath(test_module=test_module), "TestStepConfig.py")
        moduleObj = getModule("TestStepConfig", file_path)
        self.generate_model_config = moduleObj.generate_model_config
        self.verify_model_config = moduleObj.verify_model_config
        self.generate_model_config.test_module = test_module
        self.generate_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.verify_model_config.test_module = test_module
        self.verify_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.excel_handler = ExcelManager(mode = 'new', filepath = os.getenv('TEST_DATA_FILE'))
        self.generate_llm_client = LLMClient(self.generate_model_config.provider, self.generate_model_config.model, self.generate_model_config.knowledge_base_path, test_module, 'generator') #**self.generate_model_config.model_dump())
        self.verify_llm_client = LLMClient(self.verify_model_config.provider, self.verify_model_config.model, self.verify_model_config.knowledge_base_path, test_module, 'verifier') #**self.verify_model_config.model_dump())

    def load_input_data(self):
        self.input_df = pd.read_csv(f"{os.getenv('TEST_CASES_FILE')}")

    def load_generator_knowledge_base(self):
        self.generate_llm_client.upload_files()

    def load_verifier_knowledge_base(self):
        self.verify_llm_client.upload_files()

    def generate_content(self, prompt, response_schema=None):
        return self.generate_llm_client.generate_content(prompt, response_schema)
    
    def verify_content(self, prompt, response_schema=None):
        return self.verify_llm_client.generate_content(prompt, response_schema)
    
    def execute(self, start=1, end=-1, verify = True, tries = 2, cleanup = False):
        if self.generate_model_config.provider == 'gemini':
            self.load_generator_knowledge_base()

        if self.verify_model_config.provider == 'gemini':
            self.load_verifier_knowledge_base()

        self.load_input_data()
        knowledge_files = os.listdir(self.generate_model_config.knowledge_base_path)
        gen_prompt = f'''I have uploaded the following documents. You required to carefully understand the requirements, processing rules, static data, masters that have already been uploaded. 
        Can you confirm if you have the following documents in your cache?
        {str(knowledge_files)}
        '''
        turn1_response = self.generate_content(gen_prompt)
        print(f'Generator: {turn1_response}')

        gen_prompt = f'''I have uploaded the following documents. You required to carefully understand the requirements, processing rules, static data, masters that have already been uploaded. 
        Can you confirm if you have the following documents in your cache?
        {str(knowledge_files)}
        '''
        turn1_response = self.verify_content(gen_prompt)
        print(f'Verifier: {turn1_response}')

        feedback = ''
        for record_num in range(start-1, (len(self.input_df) if end < 0 else min(end, len(self.input_df)))):#len(self.input_df)):
            input_data = self.input_df.iloc[record_num]
            self.generate_model_config.task = self.generate_model_config.task_template.format(target_scenario = str(input_data["target_scenario"]),
                                                                                              test_case_id = str(input_data["test_case_id"]), 
                                                                                              given = str(input_data["given"]) + '\n' + str(input_data["given_steps"]),
                                                                                              when = str(input_data["when"]) + '\n' + str(input_data["when_steps"]),
                                                                                              then = str(input_data["then"]),
                                                                                              memberCode = str(input_data['memberCode'])
                                                                                             )
            for i in range(tries):
                prompt = self.generate_model_config.role + '\n' + self.generate_model_config.task + f'\nVerifier feedback:{feedback}'
                generated_response = self.generate_content(prompt, self.generate_model_config.output_format)
                output_df = pd.DataFrame(generated_response['output'])
                output_df_json = output_df.to_json()
                if verify:
                    time.sleep(2)
                    self.verify_model_config.task = self.verify_model_config.task_template.format(target_scenario = str(input_data["target_scenario"]),
                                                                                              test_case_id = str(input_data["test_case_id"]), 
                                                                                              given = str(input_data["given"]) + '\n' + str(input_data["given_steps"]),
                                                                                              when = str(input_data["when"]) + '\n' + str(input_data["when_steps"]),
                                                                                              then = str(input_data["then"]),
                                                                                              memberCode = str(input_data['memberCode']),
                                                                                              test_steps = str(output_df_json))
                    prompt = self.verify_model_config.role + '\n' + self.verify_model_config.task  #if feedback != '' else ''
                    verify_response = self.verify_content(prompt, self.verify_model_config.output_format)

                    if verify_response['correctness']:
                        # print(verify_response)
                        break
                    else:
                        feedback = verify_response['correction']
                else:
                    break

            if not verify or verify_response['correctness']:
                self.excel_handler.createWorksheet(sheetName=input_data['test_case_id'])
                objectToWrite = {'Test Case ID': (1,1),
                                 str(input_data['test_case_id']): (1,2),
                                 'Test Case description': (2,1),
                                 str(input_data['target_scenario']): (2,2)
                                 }
                self.excel_handler.writeTextToSheet(input_data['test_case_id'],objectToWrite)
                #Identify columns that have lists as its value. They will be written out separately on Excel
                list_cols = [
                            c for c in output_df.columns
                            if output_df[c].apply(lambda x: isinstance(x, list)).any()
                    ]
                # print(f'Writing Test Steps to File for {record_num+1}')
                curr_row = self.excel_handler.writeDfToSheet(sheetName = input_data['test_case_id'], dfToWrite=output_df.drop(columns=list_cols),
                                                startRow=4, startMarker="##Test Steps - Start", endMarker="##Test Steps - End")
                print(f'Written Test Steps to File for {record_num+1}')
                #Writing Sub steps in a separate set of rows. E.g. Allocation Steps
                # print(f'Writing Allocation Steps to File for {record_num+1}')
                for col in list_cols:
                    filtered_series = output_df.loc[output_df[col].str.len() > 0, col]
                    print(filtered_series)
                    sub_df = pd.DataFrame(filtered_series.explode().to_list())
                    # print(sub_df)
                    curr_row = self.excel_handler.writeDfToSheet(sheetName = input_data['test_case_id'], dfToWrite=sub_df,
                                                startRow=curr_row+1, startMarker=f"##{col} Steps - Start", endMarker=f"##{col} Steps - End")
                print(f'Written Allocation Steps to File for {record_num+1}')        
                self.excel_handler.save_wb()
            else:
                print(f"Unable to generate test steps correctly for {input_data['test_case_id']} because of {feedback}")
        
        #Clean up uploaded files and delete cache
        if cleanup:
            self.generate_llm_client.cleanup_files()
            self.verify_llm_client.cleanup_files()