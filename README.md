# A concurrent streaming package

- Dataflow based functional syntax.
- Implicitly parallelism for both async and non-async functions.
- Composable for both flows and tasks.
- Extensible with middlewares.

## Example

```python
from aiosaber import *
@task
def add(self, num):
    for i in range(100000):
        num += 1
    return num

@task
async def multiply(num1, num2):
    return num1 * num2

@flow
def sub_flow(num):
    return add(num) | map_(lambda x: x ** 2) | add

@flow
def my_flow(num):
    [sub_flow(num), sub_flow(num)] | multiply | view

num_ch = Channel.values(*list(range(100)))
f = my_flow(num_ch)
asyncio.run(f.start())
```