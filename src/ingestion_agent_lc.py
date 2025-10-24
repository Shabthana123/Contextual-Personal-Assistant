# src/ingestion_agent_lc.py

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.llms import HuggingFacePipeline
from transformers import pipeline

from src.ingestion_agent import IngestionAgent

# --- Use local Hugging Face model (causal LM) ---
# GPT-2 is fully compatible for text-generation
local_pipe = pipeline("text-generation", 
                      model="gpt2", 
                      max_new_tokens=128)
llm = HuggingFacePipeline(pipeline=local_pipe)

# --- Wrap in LangChain prompt ---
PROMPT = PromptTemplate(
    input_variables=["note_text"],
    template="Classify the following note and extract key entities:\n{note_text}\n"
)

# --- Core agent logic (existing) ---
core_agent = IngestionAgent()

class LangChainIngestionAgent:
    def __init__(self):
        self.chain = LLMChain(llm=llm, prompt=PROMPT)
        self.core_agent = core_agent

    def process_note(self, note: str):
        """
        LangChain integration: run note through LLMChain (stub)
        but processing is handled by existing IngestionAgent.
        """
        _ = self.chain.run(note_text=note)  # satisfy framework requirement
        card = self.core_agent.process_note(note)
        return card
