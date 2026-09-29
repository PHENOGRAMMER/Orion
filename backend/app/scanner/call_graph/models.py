from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class CallSite(BaseModel):
    """
    A single function call encountered inside a function/method.
    """

    caller: str

    callee: str

    file: Path

    line: int

    module: str | None = None

    class_name: str | None = None

    #
    # Receiver object for attribute calls.
    #
    # Example:
    #
    #     builder.build()
    #
    # receiver = "builder"
    #
    receiver: str | None = None

    #
    # Inferred receiver type.
    #
    # Example:
    #
    #     builder = KnowledgeGraphBuilder()
    #
    # receiver_type =
    # app.scanner.knowledge_graph.builder.KnowledgeGraphBuilder
    #
    receiver_type: str | None = None


class FunctionCalls(BaseModel):
    """
    Calls made by one function.
    """

    function: str

    calls: list[CallSite] = Field(default_factory=list)


class ResolvedCall(BaseModel):
    """
    A call whose caller and callee have been resolved
    to project symbols.
    """

    caller_symbol: str

    callee_symbol: str

    file: Path

    line: int