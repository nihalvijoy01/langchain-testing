import asyncio, re, subprocess
from pathlib import Path
from typing import TypedDict

import yaml
from langchain.agents import create_agent
from langchain_aws import ChatBedrockConverse
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessageChunk, ToolMessage

ROOT = Path(__file__).parent.resolve()
MAX_HEAL_ATTEMPTS = 3
MODEL_ID = "mistral.mistral-large-3-675b-instruct"  # use your Bedrock model / inference profile ID

llm = ChatBedrockConverse(
    model=MODEL_ID,
    region_name="ap-south-1",
    temperature=0,
    max_tokens=8192,
)

# ---- Playwright MCP ---------------------------------------------------------
mcp_client = MultiServerMCPClient({
    "playwright": {
        "transport": "stdio",
        "command": "npx",
        "args": ["playwright", "run-test-mcp-server"],
        "cwd": str(ROOT),
    }
})

def _safe(path: str) -> Path:
    """Resolve a path and refuse anything outside the project root."""
    p = (ROOT / path).resolve()
    if ROOT not in p.parents and p != ROOT:
        raise ValueError(f"Path escapes project root: {path}")
    return p


@tool
def read_file(file_path: str) -> str:
    """Read a text file, path relative to the project root."""
    return _safe(file_path).read_text()


@tool
def write_file(file_path: str, text: str) -> str:
    """Write text to a file (creates parent folders, overwrites if it exists)."""
    p = _safe(file_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return f"Wrote {len(text)} chars to {file_path}"


@tool
def list_directory(dir_path: str = ".") -> str:
    """List files and folders in a directory, path relative to the project root."""
    return "\n".join(sorted(x.name + ("/" if x.is_dir() else "") for x in _safe(dir_path).iterdir()))


fs_tools = [read_file, write_file, list_directory]


# ---- Load your existing agent definitions -----------------------------------
def load_agent_def(name: str) -> tuple[dict, str]:
    text = (ROOT / ".github/agents" / f"{name}.agent.md").read_text()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    meta, body = (yaml.safe_load(m.group(1)), m.group(2)) if m else ({}, text)
    return meta, body.strip()


def _text(content) -> str:
    """Bedrock Converse returns content as a list of blocks; flatten to text."""
    if isinstance(content, str):
        return content
    return "".join(
        b.get("text", "") for b in content
        if isinstance(b, dict) and b.get("type") == "text"
    )


async def run_agent(name: str, task: str) -> str:
    """Spin up an agent with its own persistent Playwright MCP session, streaming output."""
    meta, system_prompt = load_agent_def(name)
    print(f"\n=== {name} started ===", flush=True)

    async with mcp_client.session("playwright") as session:
        pw_tools = await load_mcp_tools(session)

        allowed = {t.split("/")[-1] for t in meta.get("tools", [])}
        if allowed & {t.name for t in pw_tools}:
            pw_tools = [t for t in pw_tools if t.name in allowed]

        agent = create_agent(llm, tools=pw_tools + fs_tools, system_prompt=system_prompt)

        last_turn: list[str] = []
        async for chunk, _meta in agent.astream(
            {"messages": [{"role": "user", "content": task}]},
            config={"recursion_limit": 100},
            stream_mode="messages",
        ):
            if isinstance(chunk, AIMessageChunk):
                # Show tool calls as soon as the model starts emitting them
                for tc in chunk.tool_call_chunks:
                    if tc.get("name"):
                        print(f"\n🔧 [{name}] -> {tc['name']}", flush=True)
                text = _text(chunk.content)
                if text:
                    print(text, end="", flush=True)
                    last_turn.append(text)
            elif isinstance(chunk, ToolMessage):
                preview = str(chunk.content).replace("\n", " ")[:200]
                print(f"\n   ↳ {chunk.name}: {preview}", flush=True)
                last_turn = []  # the final answer is whatever comes after the last tool result

        print(f"\n=== {name} done ===\n", flush=True)
        return "".join(last_turn)


# ---- Graph state & nodes ----------------------------------------------------
class State(TypedDict):
    requirements_path: str
    base_url: str
    plan_path: str
    run_output: str
    passed: bool
    heal_attempts: int


async def planner_node(state: State):
    await run_agent("playwright-test-planner", f"""
Read the requirements document at {state['requirements_path']}.
Explore the application at {state['base_url']} using the browser tools.
Write a test plan with only 1 scenario as markdown to {state['plan_path']}.""")
    return {}


async def generator_node(state: State):
    await run_agent("playwright-test-generator", f"""
Read the test plan at {state['plan_path']}.
For each scenario, execute the steps in the browser to verify selectors and
behavior, then write a Playwright test to tests/<feature>.spec.ts.""")
    return {}


async def run_tests_node(state: State):
    print("\n=== running playwright tests ===", flush=True)
    proc = await asyncio.create_subprocess_exec(
        "npx", "playwright", "test", "--reporter=line", "--project=chromium", "--headed",
        cwd=ROOT,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,  # merge stderr into stdout
    )
    lines: list[str] = []
    async for raw in proc.stdout:
        line = raw.decode(errors="replace")
        print(line, end="", flush=True)
        lines.append(line)
    await proc.wait()
    out = "".join(lines)[-12000:]
    return {"passed": proc.returncode == 0, "run_output": out}


async def healer_node(state: State):
    attempt = state["heal_attempts"] + 1
    await run_agent("playwright-test-healer", f"""
Playwright tests failed (heal attempt {attempt}/{MAX_HEAL_ATTEMPTS}).
Failure output:

{state['run_output']}

Reproduce the failing steps in the browser, find the root cause, and edit the
failing spec files under tests/. Do not weaken or remove assertions to force a
pass. If the app itself is genuinely broken, mark the test with test.fixme and
explain why in a comment.""")
    return {"heal_attempts": attempt}


def after_run(state: State) -> str:
    if state["passed"] or state["heal_attempts"] >= MAX_HEAL_ATTEMPTS:
        return END
    return "healer"

async def check_mcp():
    async with mcp_client.session("playwright") as session:
        init = await session.initialize()
        print("MCP server:", init.serverInfo.name, init.serverInfo.version, flush=True)

        tools = await load_mcp_tools(session)
        print(f"MCP tools: {len(tools)}", [t.name for t in tools], flush=True)

        if not tools:
            raise RuntimeError("Playwright MCP started but exposed no tools")


# ---- Wire it up ---------------------------------------------------------------
g = StateGraph(State)
g.add_node("planner", planner_node)
g.add_node("generator", generator_node)
g.add_node("run_tests", run_tests_node)
g.add_node("healer", healer_node)

g.add_edge(START, "planner")
g.add_edge("planner", "generator")
g.add_edge("generator", "run_tests")
g.add_conditional_edges("run_tests", after_run, {"healer": "healer", END: END})
g.add_edge("healer", "run_tests")
graph = g.compile()


async def main():
    await check_mcp()
    final = await graph.ainvoke({
        "requirements_path": "requirements/todo.md",
        "base_url": "https://automationexercise.com/",
        "plan_path": "specs/test-plan.md",
        "run_output": "",
        "passed": False,
        "heal_attempts": 0,
    })
    print("Passed:", final["passed"], "| heal attempts:", final["heal_attempts"])
    if not final["passed"]:
        print(final["run_output"])

if __name__ == "__main__":
    asyncio.run(main())