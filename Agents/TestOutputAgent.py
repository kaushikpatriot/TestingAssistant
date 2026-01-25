from Agents.Agent import PipelineStepAgent, ModelConfig, LLMClient
from Helpers.KnowledgeBaseProvider import getConfigPath, getKnowledgeBasePath, getModule
from pydantic import BaseModel, Field
import pandas as pd
import os
from Helpers.OutputManager import ExcelManager
import json
import sys

class TestOutputAgent(PipelineStepAgent):
    def __init__(self, test_module):
        file_path = os.path.join(getConfigPath(test_module=test_module), "TestOutputConfig.py")
        moduleObj = getModule("TestOutputConfig", file_path)
        self.generate_model_config = moduleObj.generate_model_config
        self.verify_model_config = moduleObj.verify_model_config
        self.generate_model_config.test_module = test_module
        self.generate_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.verify_model_config.test_module = test_module
        self.verify_model_config.knowledge_base_path = getKnowledgeBasePath(test_module)
        self.excel_handler = ExcelManager(mode = 'modify', filepath = os.getenv('TEST_DATA_FILE'))
        self.generate_llm_client = LLMClient(self.generate_model_config.provider, self.generate_model_config.model, self.generate_model_config.knowledge_base_path, test_module, 'generator') #**self.generate_model_config.model_dump())
        self.verify_llm_client = LLMClient(self.verify_model_config.provider, self.verify_model_config.model, self.verify_model_config.knowledge_base_path, test_module, 'verifier') #**self.verify_model_config.model_dump())
        self.inCorrectSheetList = []

    def load_input_data(self, sheetName):
        test_cases_df = pd.read_csv(os.getenv('TEST_CASES_FILE'))
        test_case_for_id = test_cases_df[test_cases_df['test_case_id'] == sheetName]
        test_step_end_row, steps_df = self.excel_handler.excelToDfConverter(sheetName, "##Test Steps - Start", "##Test Steps - End")
        allocation_end_row, allocation_df = self.excel_handler.excelToDfConverter(sheetName, "##allocation Steps - Start", "##allocation Steps - End")
        end_row = allocation_end_row if allocation_end_row else test_step_end_row
        return test_case_for_id, end_row, steps_df, allocation_df

    def load_generator_knowledge_base(self):
        self.generate_llm_client.upload_files()

    def load_verifier_knowledge_base(self):
        self.verify_llm_client.upload_files()

    def generate_content(self, prompt, response_schema = None, session = 'new'):
        return self.generate_llm_client.generate_content(prompt, response_schema, session)
    
    def verify_content(self, prompt, response_schema = None, session = 'new'):
        return self.verify_llm_client.generate_content(prompt, response_schema, session)
    
    def execute(self, sheets, verify = False, tries = 3, startMarker = '##Expected Output - Start', endMarker = '##Expected Output - End', cleanup = False):
        if self.generate_model_config.provider == 'gemini':
            self.load_generator_knowledge_base()

        if verify and self.verify_model_config.provider == 'gemini':
            self.load_verifier_knowledge_base()

        knowledge_files = os.listdir(self.generate_model_config.knowledge_base_path)
        gen_prompt = f'''I have uploaded the following documents. You required to carefully understand the requirements, processing rules, static data, masters that have already been uploaded. 
        Can you confirm if you have the following documents in your cache?
        {str(knowledge_files)}
        '''
        turn1_response = self.generate_content(prompt = gen_prompt, session = 'new')
        print(f'Generator: {turn1_response}')
        
        if verify:
            gen_prompt = f'''I have uploaded the following documents. You required to carefully understand the requirements, processing rules, static data, masters that have already been uploaded. 
            Can you confirm if you have the following documents in your cache?
            {str(knowledge_files)}
            '''
            turn1_response = self.verify_content(prompt = gen_prompt, session = 'new')
            print(f'Verifier: {turn1_response}')

        sheetNames = sheets if sheets else self.excel_handler.sheetnames #specific sheets if given as input, if not all sheets
        #For each sheet
        for sheetName in sheetNames:

            # if (sheets is None) or (sheets is not None and sheetName in sheets):
            # Correct Output indicator
            isOutputCorrect = False
            # Delete the range from Excel
            self.excel_handler.deleteRange(sheetName, startMarker, endMarker)
            # Convert to Dataframe
            output_df = pd.DataFrame()
            test_case, end_row, steps_df, allocation_df = self.load_input_data(sheetName)
            # Generate output given the current state and the transaction
            step_count, current_state, previous_state = len(steps_df), {}, {}

            gen_prompt = f'''Now focus on this specific Test Case sheet. Here are the details of the test case
            {test_case}.
            Here are the {steps_df} and the {allocation_df}
            **DO NOT use details of any other test case other than the one given here**
            Can you confirm if you have understood the test case?
            '''
            turn1_response = self.generate_content(prompt = gen_prompt, session = 'new')
            print(turn1_response)

            for step in range(1, step_count+1):
                feedback = ''
                actual_step = steps_df[steps_df['step'] == step ]
                if len(allocation_df) > 0:
                    allocation_steps = allocation_df[allocation_df['step'] == step]
                    if len(allocation_steps) > 0:
                        allocation_steps_json = allocation_steps.to_json()
                    else:
                        allocation_steps_json = ''
              
                step_number = str(actual_step['step'].item()),
                #Format Prompt
                self.generate_model_config.task = self.generate_model_config.task_template.format(test_case = test_case.to_json(),
                                                                                                    step = actual_step.to_json(),
                                                                                                    allocation_steps = allocation_steps_json,
                                                                                                    step_number = str(step),
                                                                                                    current_state = str(current_state)
                                                                                                    )
                #Generate output
                print(f"\nExpected Output being generated for {sheetName} - {step_number}")
                gen_prompt = f'''
                Before generating output in a structured format, can you very briefly state (in less than 20 words totally)
                1. Will you apply allocation in this step or not? Just say yes or no.
                2. If it impacts allocation, can you refer to the rationale or rule, on why you apply it in this step?
                3. Are there other segments to which lending will be done either for Blocking or allocation purposes? Just say yes or no
                4. Do you remember that Non-fungible Cash Equivalent can be used towards satisfying Compliance Requirements and Capital Cushion? Just say yes or no
                Input:
                test_case = {test_case.to_json()}
                step = {actual_step.to_json()}
                allocation_steps = {allocation_steps_json},
                step_number = {str(step)},
                current_state = {str(current_state)}
                **DO NOT GIVE ANY OTHER OUTPUT OTHER THAN ANSWERS TO THE QUESTIONS ABOVE**  
                '''
                turn1_response = self.generate_content(prompt = gen_prompt)
                print(f'Articulating Step {str(step)} and my response is \n {turn1_response}')

                for i in range(tries):
                    prompt = self.generate_model_config.role + '\n' + self.generate_model_config.task + f'\n Verifier feedback: {feedback} Output: {str(current_state)}'
                    # print(f'here is the {prompt} for {step_number}')
                    generated_response = self.generate_content(prompt,self.generate_model_config.output_format)
                    current_state = generated_response['output']
                    # print(f'This is the current_state after Step {step_number} - {current_state}')
                    if verify:
                        print(f"\nVerifying Expected Output being generated for {sheetName} - {step_number}")
                        self.verify_model_config.task = self.verify_model_config.task_template.format(test_case = test_case.to_json(),
                                                                                                        previous_state = str(previous_state),
                                                                                                        current_state = str(current_state),
                                                                                                        step = actual_step.to_json(),
                                                                                                        allocation_steps = allocation_steps_json
                                                                                                        )
                        prompt = self.verify_model_config.role + '\n' + self.verify_model_config.task
                        verify_response = self.verify_content(prompt, self.verify_model_config.output_format, session = 'new')
                        feedback = verify_response['correction']
                        if verify_response['correctness'] == True:
                            previous_state = current_state
                            break
                    else: 
                        break

                #State update for next iteration
                if not verify or (verify_response['correctness'] == True):
                    isOutputCorrect = True
                    if output_df.empty:
                        output_df = pd.DataFrame(generated_response['output'])
                    else:
                        output_df = pd.concat([output_df, pd.DataFrame(generated_response['output'])], ignore_index=True)
                else:
                    print(f'Unable to generate correct expected output for {sheetName}. Reason: {feedback}')
                    self.inCorrectSheetList.append(sheetName)
                    isOutputCorrect = False
                    break               

            # Write the output to the sheet
            if isOutputCorrect:
                curr_row = self.excel_handler.writeDfToSheet(sheetName = sheetName, dfToWrite=output_df,
                                    startRow=end_row+2, startMarker="##Expected Output - Start", endMarker="##Expected Output - End")

                # Save the workbook
                self.excel_handler.save_wb()
        print(f'Here are the list of sheets for which correct output could not be produced: {self.inCorrectSheetList}')

        #Clean up uploaded files and delete cache
        if cleanup:
            self.generate_llm_client.cleanup_files()
            self.verify_llm_client.cleanup_files()
        

