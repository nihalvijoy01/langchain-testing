"""
Open a website with Playwright MCP, take an accessibility snapshot,
and have an Amazon Bedrock model explain it.

Setup:
    pip install langchain-aws langchain-mcp-adapters langgraph
    # Node.js must be installed (the MCP server is launched via npx)
    # AWS credentials must be configured (aws configure / env vars / IAM role),
    # and model access enabled in the Bedrock console.

Run:
    python playwright_snapshot_agent.py https://example.com
"""
import asyncio
import os
import sys

from langchain_aws import ChatBedrockConverse
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

URL = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"

# Change to any Bedrock model/inference profile you have access to
MODEL_ID = "mistral.mistral-large-3-675b-instruct"
REGION = "ap-south-1"  # or your preferred region


async def main():
    # 1. Start the Playwright MCP server and load its tools
    client = MultiServerMCPClient(
        {
            "playwright": {
                "command": "npx",
                "args": ["@playwright/mcp@latest", "--headless"],
                "transport": "stdio",
            }
        }
    )
    all_tools = await client.get_tools()

    # Keep only what we need: navigate + snapshot
    tools = [t for t in all_tools if t.name in ("browser_navigate", "browser_snapshot")]

    # 2. Bedrock model
    llm = ChatBedrockConverse(model=MODEL_ID, region_name=REGION, temperature=0)

    # 3. Agent that can call the tools
    agent = create_react_agent(llm, tools)

    result = await agent.ainvoke(
        {
            "messages": [
                (
                    "user",
                    f"Open {URL} using the browser, take a snapshot of the page, "
                    "and then explain what the page contains: its purpose, main "
                    "sections, and key interactive elements.",
                )
            ]
        }
    )

    print(result["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())