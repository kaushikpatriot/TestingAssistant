from Agents.LLMConnector import LLMConnector
from dotenv import load_dotenv

load_dotenv()

connector = LLMConnector('gemini', 'gemini-2.5-pro', "", 'Cash Allocation', 'generator')
connector.cleanup_files()

connector = LLMConnector('gemini', 'gemini-2.5-pro', "", 'Cash Allocation', 'verifier')
connector.cleanup_files()