import asyncio


async def main():
    loop = asyncio.get_running_loop()
    loop.set_task_factory(asyncio.eager_task_factory)

    async def foo(): ...

    task = asyncio.create_task(foo())
    await task
    print(task.get_coro())


asyncio.run(main())