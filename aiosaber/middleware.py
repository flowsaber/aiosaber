"""
Inspired by starlette
"""

from typing import TYPE_CHECKING

from aiosaber import context
from aiosaber.utility.typings import Getter, Putter, Builder, Executor, Handler

if TYPE_CHECKING:
    from .flow import Flow
    from .task import Component


class BaseBuilder(Builder):
    def __init__(self, builder: Builder):
        self.next_builder: Builder = builder

    def __call__(self, com: "Component", *args, **kwargs):
        self.next_builder(com, *args, **kwargs)


class BaseExecutor(Executor):
    def __init__(self, executor: Executor):
        self.next_executor: Executor = executor

    async def __call__(self, com: "Component", **kwargs):
        return await self.next_executor(com, **kwargs)


class BaseHandler(Handler):
    def __init__(self, handler: Handler):
        self.next_handler: Handler = handler

    async def __call__(self, task, get: Getter, put: Putter, **kwargs):
        return await self.next_handler(task, get, put)


class ContextExecutor(BaseExecutor):
    """Should be used as the outermost ExecutePlugin
    """

    async def __call__(self, com: "Component", *args, **kwargs):
        from copy import copy
        context_token = context.context_var.set(copy(dict(context.context)))
        try:
            return await super().__call__(com, **kwargs)
        finally:
            context.context_var.reset(context_token)


class DaskExecutorProvider(BaseExecutor):
    """Dask is used for executing computing-bounded function. Disable this plugin if needed.
    """

    async def __call__(self, flow: "Flow", **kwargs):
        from aiosaber.flow import Flow
        is_top_flow = not context.context.coms and isinstance(flow, Flow)
        executor = None
        if is_top_flow and not context.context.get('executor'):
            from aiosaber.utility.dask_executor import DaskExecutor
            executor = DaskExecutor(**context.context.get("dask_executor_kwargs", {}))
            context.context['executor'] = executor
            await executor.start()

        try:
            return await super().__call__(flow, **kwargs)
        finally:
            if executor:
                del context.context['executor']
                await executor.shutdown()
