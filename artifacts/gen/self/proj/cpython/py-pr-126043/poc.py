import asyncio

class EvilLoop:
    def call_soon(*args):
        # will crash before it actually gets here 
        print(args)

    def get_debug(self):
        return False

    def __getattribute__(self, name):
        global tracker
        if name == "call_soon":
            fut.remove_done_callback(tracker)
            del tracker
            print("returning call_soon method after clearing callback0")
        
        return object.__getattribute__(self, name)

class TrackDel:
    def __del__(self):
        print("deleted", self)

fut = asyncio.Future(loop=EvilLoop())

tracker = TrackDel()
fut.add_done_callback(tracker)
fut.set_result("kaboom")