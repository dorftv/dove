import sys
import traceback
from gi.repository import GLib


def run_on_master_when_idle(func, **func_args):
    def function_runner(args):
        if args['func'] is None:
            raise RuntimeError("Missing function to run in master thread")

        try:
            f = args["func"]
            func_args = args["func_args"]
            f(**func_args)
        except Exception as e:
            print('------------ UNCAUGHT EXCEPTION ON MASTER THREAD: %s ------------' % e, file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
        return False
    if func is None:
        raise RuntimeError("Missing function to run in master thread")
    GLib.idle_add(function_runner, {"func": func, "func_args": func_args})
