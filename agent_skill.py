from langchain_openai import ChatOpenAI 
import os  
from dotenv import load_dotenv 
 
 
load_dotenv() 
 
# A "skill" to handle sensitive data 
class SensitiveDataSkill: 
    """A skill that enforces anonymization and answers based on context.""" 
    def __init__(self, llm): 
        self.llm = llm 
 
    def run(self, context: str, question: str) -> str: 
        # Step 1: Anonymize sensitive info 
        context_safe = context.replace("john@example.com", "[EMAIL REDACTED]") 
 
        # Step 2: Prepare prompt 
        prompt = f""" 
        You are a secure assistant. 
        Answer the question using ONLY the context below. 
        Context: {context_safe} 
        Question: {question} 
        """ 
 
        # Step 3: Ask the model 
        response = self.llm.invoke(prompt)  # Changed from llm(prompt) to llm.invoke(prompt)
        return response.content  # Access the content attribute
 
# Instantiate LLM 
llm = ChatOpenAI( 
    model="gpt-4o-mini", 
    max_tokens=1000, 
    temperature=0.2, 
    timeout=60 
) 

# Create skill 
sensitive_skill = SensitiveDataSkill(llm) 
 
# Use the skill 
context = "The customer's email is john@example.com and the order number is 12345." 
question = "What is the customer's email?" 
print(sensitive_skill.run(context, question))