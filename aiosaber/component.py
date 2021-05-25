import asyncio
import traceback
from copy import deepcopy
from enum import IntEnum
from typing import Union, List, Optional, TYPE_CHECKING

from aiosaber import context
from aiosaber.channel import Consumer
from aiosaber.plugins import ContextExecutor
from aiosaber.utility.typings import ChannelOutput, Builder, Executor

if TYPE_CHECKING:
    pass


class ComponentExecuteError(RuntimeError):
    def __init__(self, *args, futures=None, trace_back=None):
        super().__init__(*args)
        self.futures = futures or []
        self.trace_back = trace_back


class ComponentCallError(RuntimeError):
    def __init__(self, *args, trace_back=None):
        super().__init__(*args)
        self.trace_back = trace_back


def check_future_exceptions(futures: List[asyncio.Future]):
    # wrap into a ComponentExecuteError with record of all futures
    first_exception = next((fut.exception() for fut in futures if fut.exception()), None)
    if first_exception:
        raise ComponentExecuteError(str(first_exception), futures=futures) from first_exception


class Component(object):
    """Base class of Flow and Task
    """

    class State(IntEnum):
        CREATED = 1
        INITIALIZED = 2
        EXECUTED = 3

    CREATED = State.CREATED
    INITIALIZED = State.INITIALIZED
    EXECUTED = State.EXECUTED

    default_builders = []
    default_executors = []

    def __init__(self, copy_context: bool = True, builders=None, executors=None, **kwargs):
        self.com_state: Component.State = self.CREATED
        self.rest_kwargs: dict = kwargs
        self.context: Optional[dict] = None
        self.copy_context: bool = copy_context
        # builders, executors plugin
        builders = self.default_builders + (builders or [])
        self.builders: Optional[List] = builders + context.context.get('builders', [])
        executors = self.default_executors + (executors or [])
        self.executors: Optional[List] = executors + context.context.get('executors', [])

        self._builder: Optional[Builder] = None
        self._executor: Optional[Executor] = None

        self._input_args: Optional[tuple] = None
        self._input_kwargs: Optional[dict] = None
        self._input: Optional[Consumer] = None
        self._output: Optional[ChannelOutput] = None

    def __call__(self, *args, **kwargs) -> Union['Component', ChannelOutput]:
        """ This is where the flow/task build dependency graph
        """
        try:
            from copy import copy
            new = copy(self)
            new.resolve_plugins(*args, **kwargs)
            new._builder(new, *args, **kwargs)
            return new
        except BaseException as e:
            tb = traceback.format_exc()
            raise ComponentCallError(str(e), trace_back=tb) from e

    @property
    def executor(self):
        if self.copy_context and not isinstance(self._executor, ContextExecutor):
            self._executor = ContextExecutor(executor=self._executor)
        return self._executor

    async def start(self, **kwargs):
        try:
            executor = self._executor
            if self.copy_context:
                executor = ContextExecutor(executor=executor)
            return await executor(self, **kwargs)
        except BaseException as e:
            tb = traceback.format_exc()
            raise ComponentExecuteError(str(e), trace_back=tb) from e

    def resolve_plugins(self, *args, **kwargs):
        builder = type(self).build
        builders: List[type] = self.builders + context.context.get('builders', [])
        for cls in builders:
            builder = cls(builder=builder)
        self._builder = builder

        executor = type(self).execute
        executors: List[type] = self.executors + context.context.get('executors', [])
        for cls in executors:
            executor = cls(executor=executor)
        self._executor = executor

    def build(self, *args, **kwargs):
        """Copy rest_kwargs to context
        """
        from copy import deepcopy
        self.state = self.INITIALIZED
        self.context = deepcopy(self.rest_kwargs)
        self._input_args = args
        self._input_kwargs = kwargs

    async def execute(self, **kwargs):
        if self.state == self.CREATED:
            raise ValueError("The Task/Flow object is not initialized, "
                             "please use task()/flow() to initialize it.")
        elif self.state == self.EXECUTED:
            raise ValueError("The Task/Flow has already been executed once before.")

        self.state = self.EXECUTED

    @staticmethod
    async def wait(futures):

        done, pending = await asyncio.wait(futures, return_when=asyncio.FIRST_EXCEPTION)
        for fut in pending:
            fut.cancel()

        res_futures = list(done) + list(pending)
        check_future_exceptions(res_futures)
        return res_futures

    @property
    def input(self) -> Optional[Consumer]:
        return self._input

    @input.setter
    def input(self, value: Consumer):
        self._input = value

    @property
    def output(self) -> Optional[ChannelOutput]:
        return self._output

    @output.setter
    def output(self, value: ChannelOutput):
        self._output = value

    @property
    def state(self):
        return self.com_state

    @state.setter
    def state(self, new_state: State):
        assert new_state > self.com_state
        self.com_state = new_state

    @property
    def initialized(self):
        return self.state != Component.State.CREATED

    def __copy__(self):
        cls = type(self)
        new = cls.__new__(cls)
        for k, v in self.__dict__.items():
            new.__dict__[k] = None if k.startswith('_') else deepcopy(v)
        return new

# TODO copy signature of run method to __call__
