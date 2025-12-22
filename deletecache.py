from Agents.LLMConnector import LLMConnector
from dotenv import load_dotenv

load_dotenv()

connector = LLMConnector('Cash Allocation')
connector.cleanup_files('gemini')