import asyncio

async def main():
    loop = asyncio.get_running_loop()
    loop.set_task_factory(asyncio.eager_task_factory)

    async def foo(): ...

    task = asyncio.create_task(foo())
    await task
    assert task.get_coro() is None, f"Expected None, got {task.get_coro()}"

asyncio.run(main())
