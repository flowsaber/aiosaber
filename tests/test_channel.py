import time

from aiosaber import *


def test_event_channel():
    def check_if_passed(interval):
        import time
        last = cur = time.time()
        check = 3
        while check > 0:
            if cur - last >= interval:
                yield True
                check -= 1
                last = cur
            else:
                yield False
            cur = time.time()

    @flow
    def myflow():
        event = Channel.event(check_if_passed(0.5), check_if_passed(1), interval=0.1)
        event | subscribe(lambda x: print(time.time()))

    asyncio.run(myflow().start())


if __name__ == "__main__":
    test_event_channel()
