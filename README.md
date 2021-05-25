# A concurrent streaming package

<p align="center">
  <a href="https://pypi.python.org/pypi/aiosaber/">
    <img src="https://img.shields.io/pypi/v/aiosaber.svg" alt="Install with PyPi" />
  </a>
  <a href="https://github.com/flowsaber/aiosaber/releases">
  	<img src="https://img.shields.io/github/v/release/aiosaber/aiosaber?include_prereleases&label=github" alt="Github release">
  </a>
  <a href="https://pypi.python.org/pypi/aiosaber">
    <img src="https://img.shields.io/pypi/pyversions/aiosaber.svg" alt="Version">
  </a>
  <a href="https://pepy.tech/project/aiosaber">
    <img src="https://pepy.tech/badge/aiosaber" alt="Downloads">
  </a>
  <a href="https://pepy.tech/project/aiosaber">
    <img src="https://pepy.tech/badge/aiosaber/week" alt="Downloads per week">
  </a>
  <a href="https://github.com/flowsaber/aiosaber/actions/workflows/python-package-conda.yml">
    <img src="https://github.com/flowsaber/aiosaber/actions/workflows/python-package-conda.yml/badge.svg" alt="Build Status">
  </a>
  <a href="https://app.codecov.io/gh/flowsaber/aiosaber">
    <img src="https://codecov.io/gh/flowsaber/aiosaber/branch/dev/graph/badge.svg" alt="codecov">
  </a>
  <a href="https://github.com/flowsaber/aiosaber/blob/master/LICENSE">
    <img src="https://img.shields.io/github/license/flowsaber/aiosaber" alt="license">
  </a>
</p>


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