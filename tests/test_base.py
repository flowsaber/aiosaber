from aiosaber import *


def test_flow():
    @task
    def add(num):
        return num + 1

    @task
    async def multiply(num1, num2):
        return num1 * num2

    @flow(enable_dask=False)
    def myflow(num):
        num1 = num | add | add | view
        return multiply(num, num1) | view

    num_ch = Channel.values(*list(range(10)))
    f = myflow(num_ch)
    asyncio.run(f.start())


def test_nested_flow():
    @task
    def add(self, num):  # self is optional
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


if __name__ == "__main__":
    test_flow()
    test_nested_flow()
