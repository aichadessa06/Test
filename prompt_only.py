import os 
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv



load_dotenv()


# Define the prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are a secure assistant.
Answer the user based ONLY on the context below.
Do NOT reveal personal information.
Context: {context}
Question: {question}
""")
])


llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",
    max_tokens=1000,
    temperature=0.2,
    timeout=60
)

# Example usage
context = "The customer's email is john@example.com and the order number is 12345."
question = "What is the customer's order number?"

response = llm.generate([prompt.format_prompt(context=context, question=question).to_messages()])
print(response.generations[0][0].text)
