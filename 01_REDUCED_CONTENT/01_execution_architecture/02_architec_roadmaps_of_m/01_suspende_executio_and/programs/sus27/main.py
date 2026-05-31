import asyncio


async def fetch_like_task(name, delay):
    print(name, "started")

    await asyncio.sleep(delay)

    print(name, "finished")


async def main():
    await asyncio.gather(
        fetch_like_task("A", 1),
        fetch_like_task("B", 1),
        fetch_like_task("C", 1),
    )


asyncio.run(main())
