import inspect
from typing import Callable, Any, Union, Sequence, Awaitable, TYPE_CHECKING, Protocol

from aiosaber.channel import Channel
from aiosaber.utility.target import End, Target

if TYPE_CHECKING:
    from aiosaber.component import Component
    from aiosaber.task import BaseTask


def get_signatures():
    def func(*args: Union[object, Channel]) -> ChannelOutput:
        pass

    return {
        'args': list(inspect.signature(func).parameters.values())[0],
        'return': inspect.signature(func).return_annotation
    }


def get_self_sig():
    def _self_func(self):
        pass

    self_sig = list(inspect.signature(_self_func).parameters.values())[0]

    return self_sig


POS_INF = float("inf")
NEG_INF = float("-inf")
ChannelOutput = Union[Sequence[Channel], Channel]
SELF_SIG = get_self_sig()
ARGS_SIG = get_signatures()['args']
ChannelOutput_RETURN_SIG = get_signatures()['return']

Predicate = Callable[[Any], bool]
Getter = Callable[[], Awaitable[Any]]
Putter = Callable[..., Awaitable[Any]]
AsyncFunc = Callable[..., Awaitable[Any]]


class Builder(Protocol):
    def __call__(self, com: "Component", *args, **kwargs) -> None: ...


class Executor(Protocol):
    async def __call__(self, com: "Component", **kwargs): ...


class Handler(Protocol):
    async def __call__(self, task: "BaseTask", get: Getter, put: Putter, **kwargs): ...


ChannelData = Union[Any, End, Target]
