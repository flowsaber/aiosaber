from aiosaber import *


def test_middleware():
    class NameBuilder(BaseBuilder):
        def __call__(self, com, *args, **kwargs):
            super().__call__(com, *args, **kwargs)
            com.context['name'] = type(com).__name__ + str(id(com))

    class ClientProvider(BaseExecutor):
        async def __call__(self, com, **kwargs):
            if not context.context.get('client'):
                context.context['client'] = 'client'
            return await super().__call__(com, **kwargs)

    class Filter(BaseHandler):
        async def __call__(self, com, get, put, **kwargs):
            async def filter_put(data):
                if data is END or data > 3:
                    await put(data)

            return await super().__call__(com, get, filter_put, **kwargs)

    @task
    async def add(self, num):
        print(self.context['name'])
        print(context.context['client'])
        return num + 1

    @flow
    def myflow(num_ch):
        return num_ch | add | view

    context.context.update({
        'builders': [NameBuilder],
        'executors': [ClientProvider],
        'handlers': [Filter]
    })
    f = myflow(Channel.values(1, 2, 3, 4, 5))
    context.context.clear()
    asyncio.run(f.start())


if __name__ == "__main__":
    test_middleware()
