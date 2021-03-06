from aiosaber import *


def test_flow1():
    @task
    def bwa(fasta):
        return str(fasta) + ".bam"

    @task
    def stat(bam):
        return bam + ".bigiwg"

    @task
    def mod(bw1):
        return f"{bw1}.txt"

    @flow
    def flow1(fasta):
        bam = bwa(fasta)
        return stat(bam)

    @flow
    def flow2(bw1):
        return mod(mod(bw1))

    @flow
    def myflow(fasta1, fasta2):
        bw1 = flow1(fasta1)
        bw2 = flow1(fasta2)
        bw12 = merge(bw1, bw2).map(by=lambda bws: '-'.join(bws))
        txt = flow2(bw12).view() \
            .subscribe(on_next=lambda x: print(f"The value is {x}"), on_complete=lambda: print("Now reach the END")) \
            .map(by=lambda x: x + x) \
            .concat(Channel.values('5', '6', '7', 8, 9, 10))
        a = Channel.from_list([1, 2, 3, 4]).mix(txt)
        m = merge(a, a, a)
        outputs = m >> [mod, flow1, flow2, flow1]
        return merge(*outputs) | flatten | [mod, bwa, stat, flow1, flow2, flow1] | split(6) | merge | view

    fasta1 = Channel.values("1", "2", "4")
    fasta2 = Channel.values("A", "B", "x", "a")

    workflow = myflow(fasta1, fasta2)
    asyncio.run(workflow.start())


if __name__ == "__main__":
    test_flow1()
