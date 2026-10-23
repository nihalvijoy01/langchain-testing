"""
Minimal LangChain + Amazon Bedrock example.

Setup:
    pip install langchain-aws langchain-core boto3

Credentials (any standard AWS method works):
    aws configure            # or set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
                             # or AWS_PROFILE for SSO profiles

Environment variables used here:
    AWS_REGION        e.g. ap-south-1, us-east-1
    BEDROCK_MODEL_ID  copy the exact Model ID or Inference Profile ID
                      from the Bedrock console
"""

import os

from langchain_aws import ChatBedrockConverse
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

REGION = "ap-south-1"  # or your preferred region
MODEL_ID = "mistral.mistral-large-3-675b-instruct"  # fail early if not set

# 1. The model
llm = ChatBedrockConverse(
    model=MODEL_ID,
    region_name=REGION,
    temperature=0.3,
    max_tokens=500,
)

# 2. A prompt template
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a concise, friendly assistant."),
        ("human", "Explain {topic} in three sentences."),
    ]
)

# 3. Chain: prompt -> model -> plain string
chain = prompt | llm | StrOutputParser()

if __name__ == "__main__":
    print(chain.invoke({"topic": "vector databases"}))

    # Streaming example
    print("\n--- streaming ---")
    for chunk in chain.stream({"topic": "retrieval-augmented generation"}):
        print(chunk, end="", flush=True)
    print()