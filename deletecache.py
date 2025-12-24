from Agents.LLMConnector import LLMConnector
from dotenv import load_dotenv

load_dotenv()

connector = LLMConnector('gemini', 'gemini-2.5-pro', "", 'Cash Allocation')
connector.cleanup_files()