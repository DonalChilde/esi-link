"""An example of using contextlib.ExitStack to manage multiple context managers in a single class.

This might be used to have a single EsiLink class manage the resources needed to make a request to ESI, such as a session, an async session, and a cache.
"""

from contextlib import ExitStack


class ManagedPipeline:
    def __init__(self, file_path_1, file_path_2):
        self.path_1 = file_path_1
        self.path_2 = file_path_2
        # Initialize the stack container
        self.stack = ExitStack()

    def __enter__(self):
        try:
            # Enter the inner context managers and save references to their outputs
            self.file_1 = self.stack.enter_context(open(self.path_1, "w"))
            self.file_2 = self.stack.enter_context(open(self.path_2, "w"))
            return self
        except Exception:
            # Clean up anything already opened if an error happens during __enter__
            self.stack.close()
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        # This automatically calls __exit__ on all contained context managers
        # and forwards any exceptions correctly
        return self.stack.__exit__(exc_type, exc_val, exc_tb)


# Usage
with ManagedPipeline("log1.txt", "log2.txt") as pipeline:
    pipeline.file_1.write("Writing to file 1\n")
    pipeline.file_2.write("Writing to file 2\n")
