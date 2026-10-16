"""Exp96 — answer guard for react agents (shared by exp85_mcq_rag_task.py and exp87_heldout_task.py).

guard_continue(n): react on_continue hook. After n tool calls (submit not counted) it tells the model once per turn
that its tool budget is used up and to submit; the loop ends after n + 2 calls, or as soon as the model replies
without a tool call once the budget is spent, or after its third reply without a tool call. Before that it keeps
react's default behavior of urging the model on when it replies without calling a tool.
force_answer(): solver run after the agent (react must use AgentSubmit(keep_in_messages=True) so a submit call
stays visible). If the agent never called submit(), it asks for one letter with no
tools and marks the sample metadata forced=True (scored like any other answer).
"""
from inspect_ai.agent import AgentState
from inspect_ai.model import ChatMessageUser, get_model
from inspect_ai.solver import Generate, TaskState, solver

NUDGE = "You have used your tool budget. Do not call any more lookup tools. Call submit() now with exactly one letter: A, B, C, D or E."
URGE = "Please proceed to the next step using your best judgement. When you have the answer, call submit() with exactly one letter."
FORCE = "Stop using tools. Based on what you have found so far, answer now with EXACTLY one letter: A, B, C, D or E. Nothing else."


def _tool_calls(messages):
    return sum(1 for m in messages if m.role == "assistant" for tc in (m.tool_calls or []) if tc.function != "submit")


def guard_continue(n: int):
    async def cont(state: AgentState):
        calls = _tool_calls(state.messages)
        last = state.messages[-1]
        replied_without_tool = last.role == "assistant" and not last.tool_calls
        text_replies = sum(1 for m in state.messages if m.role == "assistant" and not m.tool_calls)
        if calls >= n + 2 or (calls >= n and replied_without_tool) or text_replies >= 3:
            return False  # budget spent and the model kept looking or answered in text: go to force_answer
        if calls >= n:
            return NUDGE
        if replied_without_tool:
            return URGE
        return True
    return cont


def _submitted(messages):
    return any(m.role == "tool" and getattr(m, "function", "") == "submit" for m in messages)


@solver
def force_answer():
    async def solve(state: TaskState, generate: Generate):
        state.metadata["tool_calls"] = _tool_calls(state.messages)
        if _submitted(state.messages):
            state.metadata["forced"] = False
            return state
        state.metadata["forced"] = True
        state.messages.append(ChatMessageUser(content=FORCE))
        out = await get_model().generate(state.messages, tools=[])
        state.messages.append(out.message)
        state.output = out
        return state
    return solve
