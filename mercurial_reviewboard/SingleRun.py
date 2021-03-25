import os


class SingleRun():
    class InstanceRunningException(Exception):
        pass

    def __init__(self, lock_file):
        # define the lock file name
        self.lock_file = "%s.pid" % lock_file

    def __call__(self, func):
        def f(*args, **kwargs):
            if os.path.exists(self.lock_file):
                # get process id, if lock file exists
                pid = open(self.lock_file, "rt").read()
                if not os.path.exists("/proc/%s" % pid):
                    # if process is not alive remove the lock file
                    os.unlink(self.lock_file)
                else:
                    # process is running
                    print(("Other process is running, pid: " + str(pid)))
                    raise self.InstanceRunningException(pid)
            try:
                # store process id
                open(self.lock_file, "wt").write(str(os.getpid()))
                # execute wrapped function
                func(*args, **kwargs)
            finally:
                if os.path.exists(self.lock_file):
                    os.unlink(self.lock_file)

        return f
