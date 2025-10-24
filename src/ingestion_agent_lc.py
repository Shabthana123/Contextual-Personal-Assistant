# src/ingestion_agent_lc.py

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.llms import HuggingFacePipeline
from transformers import pipeline
import json
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
    template="""
You are a personal assistant. For the following note, extract key entities:

- assignee (person or team, e.g., Vimal, Sam, Kamal, Marketing Team, Team 1)
- date_text (explicit or relative date)
- context_keywords (main nouns/proper nouns, 3-6 words max)

Return output in strict JSON format ONLY:
{{
    "assignee": "...",
    "date_text": "...",
    "context_keywords": ["...", "..."]
}}

Note:
{note_text}
"""
)

# --- Core agent logic (existing) ---
core_agent = IngestionAgent()

class LangChainIngestionAgent:
    def __init__(self):
        self.chain = LLMChain(llm=llm, prompt=PROMPT)
        self.core_agent = core_agent

    # def process_note(self, note: str):
    #     """
    #     LangChain integration: run note through LLMChain (stub)
    #     but processing is handled by existing IngestionAgent.
    #     """
    #     _ = self.chain.run(note_text=note)  # satisfy framework requirement
    #     card = self.core_agent.process_note(note)
    #     return card
    
    def process_note(self, note: str):
        """
        LangChain integration: run note through LLMChain to extract assignee/date/keywords,
        then feed into core IngestionAgent for Card creation.
        """
        try:
            # Run the LLM to get JSON output
            llm_output = self.chain.run(note_text=note)
            data = json.loads(llm_output)  # parse JSON
        except Exception as e:
            print(f"LLM JSON parse failed, using default extractor: {e}")
            data = {"assignee": None, "date_text": None, "context_keywords": []}

        # Use LangChain output to update core agent processing
        card = self.core_agent.process_note(
            note,
            assignee_override=data.get("assignee"),
            date_override=data.get("date_text"),
            keywords_override=data.get("context_keywords")
        )
        return card
