import asyncio
from typing import Optional, Set, Union, List, TYPE_CHECKING

from aiosaber import context
from aiosaber.channel import Channel
from aiosaber.component import Component
from aiosaber.middleware import DaskExecutorProvider
from aiosaber.utility.typings import ChannelOutput
from aiosaber.utility.utils import class_deco

if TYPE_CHECKING:
    from aiosaber.task import BaseTask, Edge


class Flow(Component):
    def __init__(self, enable_dask: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.edges: Optional[List['Edge']] = None
        self.tasks: Optional[Set['BaseTask']] = None
        self.components: Optional[Set[Component]] = None
        self.enable_dask = enable_dask
        if enable_dask:
            self.executors.append(DaskExecutorProvider)

    def __call__(self, *args, **kwargs) -> Union['Flow', ChannelOutput]:
        new = super().__call__(*args, **kwargs)
        coms = context.context.coms
        if len(coms):
            coms[-1].components.add(new)
            return new.output
        else:
            return new

    def build(self, *args, **kwargs):
        super().build(*args, **kwargs)
        self.edges = []
        self.tasks = set()
        self.components = set()

        context.context.coms.append(self)
        self.output = self.run(*args, **kwargs) or Channel.end()
        context.context.coms.pop(-1)

    def run(self, *args, **kwargs) -> Optional[ChannelOutput]:
        pass

    async def execute(self, **kwargs):
        await super().execute(**kwargs)

        context.context.coms.append(self)
        futures = [asyncio.create_task(com.execute(**kwargs)) for com in self.components]
        context.context.coms.pop(-1)

        await self.wait(futures)


flow = class_deco(Flow, 'run')
