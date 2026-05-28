import asyncio


async def worker(name, delay):
    print(name, "start")

    await asyncio.sleep(delay)

    print(name, "done")


async def main():
    await asyncio.gather(
        worker("A", 1),
        worker("B", 1),
    )


asyncio.run(main())
