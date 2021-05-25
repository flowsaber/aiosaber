import asyncio
import inspect
from collections import abc
from functools import partial
from inspect import BoundArguments, Signature
from typing import Sequence, TYPE_CHECKING, Optional, Callable

from aiosaber import context
from aiosaber.channel import Channel, Consumer
from aiosaber.component import Component
from aiosaber.utility.target import END
from aiosaber.utility.typings import ChannelOutput, Getter, Putter, Handler
from aiosaber.utility.utils import bounded_create_task, async_getter, is_coroutine_function, class_deco

if TYPE_CHECKING:
    from aiosaber.utility.scheduler import Scheduler


class BaseTask(Component):
    default_handlers = []

    def __init__(self, num_out: int = 1, handlers=None, **kwargs):
        super().__init__(**kwargs)
        self.num_out = num_out
        handlers = self.default_handlers + (handlers or [])
        self.handle_plugins = handlers + context.context.get('handlers', [])
        self._handler: Optional[Handler] = None

    def resolve_plugins(self, *args, **kwargs):
        super().resolve_plugins(*args, **kwargs)
        handler = type(self).handle
        handlers = self.handle_plugins + context.context.get('handlers', [])
        for cls in handlers:
            handler = cls(handler=handler)
        self._handler = handler

    @property
    def handler(self) -> Handler:
        return self._handler

    def build(self, *args, **kwargs):
        super().build(*args, **kwargs)
        self.initialize_input(*args, **kwargs)
        self.initialize_output(*args, **kwargs)
        # register to top flow for serializing
        flows = context.context.coms
        if flows:
            flows[0].tasks.add(self)
            flows[-1].tasks.add(self)
            flows[-1].components.add(self)

    def __call__(self, *args, **kwargs) -> ChannelOutput:
        new = super().__call__(*args, **kwargs)
        return new.output

    def initialize_input(self, *args, **kwargs):
        """Wrap all _input channels into a consumer object for simultaneous data ferching,

        Parameters
        ----------
        args
        kwargs
        """
        channels = list(args) + list(kwargs.values())
        self.input = Consumer.from_channels(*channels, task=self)
        # register edges into the up-most flow
        coms = context.context.coms
        if coms:
            for input_q in self.input.queues:
                edge = Edge(channel=input_q.ch, task=self)
                coms[0].edges.append(edge)
                if coms[-1] is not coms[0]:
                    coms[-1].edges.append(edge)

    def initialize_output(self, *args, **kwargs):
        """Create _output channels according to self.num_output
        """
        self.output = tuple(Channel(task=self) for _ in range(self.num_out))
        if self.num_out == 1:
            self.output = self.output[0]

    async def execute(self, **kwargs):
        await super().execute(**kwargs)
        return await self.handle_stream(self.input, **kwargs)

    async def handle_stream(self, consumer: Consumer, **kwargs):
        async for data in consumer:
            res = await self.handler(self, async_getter(data), self.put, **kwargs)
            # a signal to pre-exit, for example to exit from a constant channel
            if res is END:
                break
        # always handle END
        await self.handler(self, async_getter(END), self.put)

    async def handle(self, get: Getter, put: Putter, **kwargs):
        data = await get()
        return await put(data)

    async def put(self, data, index=None):
        # enqueue data into the _output channel
        if self.num_out != 1:
            assert isinstance(self.output, Sequence), "num_out != 1, with output not being a sequence of Channel"
            try:
                if data is END:
                    data = [END] * self.num_out
                if index is None:
                    for ch, _res in zip(self.output, data):
                        await ch.put(_res)
                else:
                    await self.output[index].put(data)
            except TypeError as e:
                raise RuntimeError(f"The output: {data} can't be split into {self.num_out} channels."
                                   f"The error is {e}")
        else:
            await self.output.put(data)

    def __ror__(self, chs) -> ChannelOutput:
        """
        ch | task               -> task(ch)
        [ch1, ch2, ch3] | task  -> task(ch1, ch2, ch3)
        """
        if not isinstance(chs, abc.Sequence):
            chs = [chs]
        assert all(isinstance(ch, Channel) for ch in chs)
        return self(*chs)

    def __rrshift__(self, chs):
        """
        ch >> task              -> task(ch)
        [ch1, ch2, ch3] >> task -> [task(ch1), task(ch2), task(ch3)]
        """
        if isinstance(chs, abc.Sequence):
            assert all(isinstance(ch, Channel) for ch in chs)
            output_chs = [self(ch) for ch in chs]
            if isinstance(chs, tuple):
                output_chs = tuple(output_chs)
            return output_chs
        else:
            assert isinstance(chs, Channel)
            return self(chs)

    def __lshift__(self, chs):
        """
        task << ch
        task << [ch1, ch2, ch3]
        """
        return chs >> self

    def copy_clean(self):
        from copy import copy
        new = copy(self)
        new.build_plugins = None
        new.execute_plugins = None
        new.handle_plugins = None
        return new


class Task(BaseTask):
    """TaskRuns of multiple inputs from input stream will be scheduled parallel.
    """

    def __init__(self, maxsize=200, **kwargs):
        super().__init__(**kwargs)
        self.maxsize = maxsize
        # run_func is the real function being called for stream input, the first argument is task/self
        self.run_func: Optional[Callable] = None
        # run_sig is used for bounding steam input with run_func's arguments, with out the first task/self argument
        self.run_sig: Optional[Signature] = None

    def build(self, *args, **kwargs):
        super().build(*args, **kwargs)
        #  run_sig is signature with out the first self argument
        self.run_func = type(self).run
        self.run_sig = inspect.signature(self.run)

    async def handle_stream(self, consumer: Consumer, **kwargs):
        # get the custom scheduler and pop it, do not pass into task runner
        scheduler: "Scheduler" = context.context.get('scheduler', None)
        create_task = partial(scheduler.create_task, data=self) if scheduler else asyncio.create_task

        def return_when(fut: asyncio.Future):
            # when meet END, it means we need pre-exit the data fetching loop
            return fut.cancelled() or fut.exception() or fut.result() is END

        waiter, schedule = bounded_create_task(self.maxsize, create_task=create_task, return_when=return_when)
        try:
            async for data in consumer:
                # pre bound the data
                data: BoundArguments = self.create_run_data(data)
                coro = self.handler(self, async_getter(data), self.put, **kwargs)
                await schedule(coro)
            await waiter
        finally:
            # always handle END at last
            await create_task(self.handler(self, async_getter(END), self.put, **kwargs))

    async def handle(self, get: Getter, put: Putter, **kwargs):
        data = await get()
        if data is END:
            return await put(data)

        # create a clean task and update context
        task = self.copy_clean()
        task.context.update(kwargs)
        run_func = task.run_func
        # for non-async function, run in executor(user supplied or default ThreadPoolExecutor)
        if is_coroutine_function(run_func):
            res = await run_func(task, *data.args, **data.kwargs)
        else:
            res = await self.run_in_executor(partial(run_func, task, *data.args, **data.kwargs))
        return await put(res)

    def create_run_data(self, data) -> BoundArguments:
        """Wrap consumer fetched data tuple into a BoundArgument paired with self.run's signature.
        """
        data = (data,) if self.input.single else data
        len_args = len(self._input_args)
        args = data[:len_args]
        kwargs = {k: data[len_args + i] for i, k in enumerate(self._input_kwargs.keys())}

        try:
            run_data = self.run_sig.bind(*args, **kwargs)
        except TypeError as exc:
            raise ValueError(f"The input data: {data} can not be passed "
                             f"to {self.run_func} with signature of {self.run_sig}") from exc
        run_data.apply_defaults()
        return run_data

    @staticmethod
    async def run_in_executor(func: Callable):
        # run in user supplied executor or ThreadPoolExecutor, The context may be invalid anymore
        executor = context.context.get('executor')
        if executor:
            return await executor.submit(func)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func)

    async def run(self, *args, **kwargs):
        return tuple(list(args) + list(kwargs.values()))


class Edge(object):
    """A edge represents a dependency between a channel and a task. the Task consumes data emited by the channel.
    """

    def __init__(self, channel: Channel, task: BaseTask):
        self.channel: Channel = channel
        self.task: BaseTask = task


task = class_deco(Task, 'run')
