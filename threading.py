import threading
import concurrent.futures
import multiprocessing
import time
import queue

class ThreadManager:
    """
    A simple thread manager for running tasks in background threads.
    Supports pausing, resuming, and cancelling tasks.
    """
    
    def __init__(self, max_workers=None):
        """
        Initialize the ThreadManager.
        
        Args:
            max_workers (int, optional): Number of worker threads. 
                                         Defaults to number of CPU cores.
        """
        if max_workers is None:
            try:
                max_workers = multiprocessing.cpu_count()
            except NotImplementedError:
                max_workers = 1
                
        self.max_workers = max_workers
        self.executor = None
        self.futures = []
        self.is_paused = False
        self.pause_condition = threading.Condition()
        self._shutdown = False

    def start(self):
        """Start the thread pool executor."""
        if self.executor is None:
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
            self._shutdown = False

    def stop(self, wait=True):
        """
        Stop the thread manager and shutdown the executor.
        
        Args:
            wait (bool): If True, wait for pending futures to complete.
        """
        self._shutdown = True
        self.cancel_all()
        if self.executor:
            self.executor.shutdown(wait=wait)
            self.executor = None

    def pause(self):
        """Pause execution of new tasks."""
        self.is_paused = True

    def resume(self):
        """Resume execution of tasks."""
        with self.pause_condition:
            self.is_paused = False
            self.pause_condition.notify_all()

    def cancel_all(self):
        """Cancel all pending futures."""
        for future in self.futures:
            if not future.done():
                future.cancel()
        self.futures = [f for f in self.futures if not f.done()]

    def submit(self, fn, *args, **kwargs):
        """
        Submit a task to be executed.
        
        Args:
            fn (callable): The function to execute.
            *args: Arguments for the function.
            **kwargs: Keyword arguments for the function.
            
        Returns:
            concurrent.futures.Future: The future object representing the task.
        """
        if self.executor is None:
            self.start()

        def wrapped_fn(*args, **kwargs):
            # Check for pause
            with self.pause_condition:
                while self.is_paused and not self._shutdown:
                    self.pause_condition.wait()
            
            if self._shutdown:
                return None
                
            return fn(*args, **kwargs)

        future = self.executor.submit(wrapped_fn, *args, **kwargs)
        self.futures.append(future)
        
        # Clean up finished futures periodically
        self.futures = [f for f in self.futures if not f.done()]
        
        return future

    def shutdown(self):
        """Alias for stop."""
        self.stop()
