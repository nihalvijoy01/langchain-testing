from langchain_google_genai import ChatGoogleGenerativeAI  

def get_llm(temperature: float = 0.1):
    return ChatGoogleGenerativeAI(
        model="gemini-3.8-flash",
        temperature=temperature,
        max_output_tokens=16384
    )