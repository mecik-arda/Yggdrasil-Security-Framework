"""
Async Task Manager — ThreadPoolExecutor with bounded concurrency and FIFO queuing.

Replaces the previous unbounded ``threading.Thread``-per-task model with a
configurable worker pool.  When all workers are busy, new tasks are queued
and scheduled automatically as slots free up.

Backward-compatible public API:
    create_task, set_task_process, kill_task, kill_all_tasks, get_async_tasks
"""
import threading
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor, Future

import psutil

from core.logger import emit_log_event

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_CONCURRENT_SCANS = 5  # maximum simultaneous tool executions
MAX_TASK_HISTORY = 1000    # maximum number of completed/errored tasks to retain
TASK_RETENTION_SECONDS = 86400  # 24 hours — completed tasks older than this are purged
TASK_CLEANUP_INTERVAL = 300     # run cleanup every 5 minutes


# ---------------------------------------------------------------------------
# Task data-class
# ---------------------------------------------------------------------------

class Task:
    """Lightweight task record stored in the in-memory registry."""
    __slots__ = (
        'id', 'tool', 'target', 'action', 'status', 'process',
        'output', 'message', 'type', 'created_at', 'completed_at',
        'client_task_id', '_future',
    )

    def __init__(self, task_id, tool, target, action, client_task_id=None):
        self.id = task_id
        self.tool = tool
        self.target = target
        self.action = action
        self.status = 'pending'      # pending → running → success | error
        self.process = None          # subprocess.Popen handle (if any)
        self.output = ''
        self.message = ''
        self.type = 'text'
        self.created_at = time.time()
        self.completed_at = None     # set when task reaches terminal state
        self.client_task_id = client_task_id  # caller-supplied correlation id (never used as primary key)
        self._future = None          # concurrent.futures.Future (internal)


# ---------------------------------------------------------------------------
# Singleton task registry + executor
# ---------------------------------------------------------------------------

class _TaskManager:
    """Thread-safe singleton that owns the executor, queue, and task dict."""

    def __init__(self):
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=MAX_CONCURRENT_SCANS,
            thread_name_prefix='ygg-task',
        )
        self._queue: deque[Task] = deque()         # explicit pending-task visibility
        self._tasks: dict[str, Task] = {}           # all tasks ever created
        self._active_futures: dict[str, Future] = {}  # currently-running futures
        self._cleanup_started = False

    def _start_cleanup_thread(self):
        """Launch a daemon thread that periodically prunes old completed tasks."""
        if self._cleanup_started:
            return
        self._cleanup_started = True

        def _cleanup_loop():
            while True:
                time.sleep(TASK_CLEANUP_INTERVAL)
                self._prune_old_tasks()

        cleanup_thread = threading.Thread(target=_cleanup_loop, daemon=True, name='ygg-task-cleanup')
        cleanup_thread.start()

    def _prune_old_tasks(self):
        """Remove completed/errored tasks beyond retention limits.

        Applies two policies:
        1. Count-based: keep at most ``MAX_TASK_HISTORY`` terminal tasks.
        2. Time-based: drop terminal tasks older than ``TASK_RETENTION_SECONDS``.
        Active (pending / running) tasks are never pruned.
        """
        cutoff = time.time() - TASK_RETENTION_SECONDS
        with self._lock:
            # Collect terminal task ids with their completed_at timestamps
            terminal_tasks = [
                (tid, t.completed_at or t.created_at)
                for tid, t in self._tasks.items()
                if t.status in ('success', 'error', 'cancelled')
            ]
            # Sort oldest-first
            terminal_tasks.sort(key=lambda x: x[1])

            # Time-based pruning
            for tid, ts in terminal_tasks:
                if ts < cutoff:
                    self._tasks.pop(tid, None)

            # Count-based pruning (re-evaluate after time-based cleanup)
            terminal_tasks = [
                (tid, t.completed_at or t.created_at)
                for tid, t in self._tasks.items()
                if t.status in ('success', 'error', 'cancelled')
            ]
            terminal_tasks.sort(key=lambda x: x[1])

            excess = len(terminal_tasks) - MAX_TASK_HISTORY
            for tid, _ in terminal_tasks[:max(0, excess)]:
                self._tasks.pop(tid, None)

    # -- read-only helpers --------------------------------------------------

    @property
    def active_count(self):
        with self._lock:
            return len(self._active_futures)

    @property
    def queued_count(self):
        with self._lock:
            return len(self._queue)

    def get_stats(self):
        """Return a snapshot of queue / active counts."""
        with self._lock:
            return {
                'active': len(self._active_futures),
                'queued': len(self._queue),
                'total': len(self._tasks),
                'max_workers': MAX_CONCURRENT_SCANS,
            }

    # -- task lifecycle -----------------------------------------------------

    def create_task(self, tool, target, action, task_id=None, client_task_id=None):
        """Create a *pending* task and return a server-generated UUID.

        ``task_id`` is deprecated and ignored (kept for backward-compat).
        ``client_task_id`` is stored for correlation only — it never overrides
        the server-assigned primary key.
        """
        self._start_cleanup_thread()
        server_id = str(uuid.uuid4())
        correlation_id = client_task_id or task_id
        task = Task(server_id, tool, target, action, client_task_id=correlation_id)
        with self._lock:
            self._tasks[server_id] = task
        return server_id

    def submit(self, task_id, func, *args, **kwargs):
        """Run ``func(*args, **kwargs)`` inside the thread pool."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            task.status = 'running'
            self._active_futures[task_id] = None  # placeholder; set inside wrapper

        def _wrapper():
            with self._lock:
                task.status = 'running'
            try:
                func(*args, **kwargs)
            finally:
                with self._lock:
                    task.completed_at = time.time()
                    self._active_futures.pop(task_id, None)

        future = self._executor.submit(_wrapper)
        with self._lock:
            task._future = future
            self._active_futures[task_id] = future
        return True

    def set_task_process(self, task_id, process):
        """Attach a ``subprocess.Popen`` handle so the task can be killed."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.process = process

    def kill_task(self, task_id):
        """Kill a running task (process tree) or cancel a queued one."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False, "Task not found"
            future = task._future

        # Cancel if not yet started
        if future is not None and not future.done():
            cancelled = future.cancel()
            if cancelled:
                with self._lock:
                    task.status = 'error'
                    task.message = 'Task cancelled from queue.'
                    task.output = '[!] TASK CANCELLED FROM QUEUE.'
                    task.completed_at = time.time()
                    self._active_futures.pop(task_id, None)
                return True, 0

        # Kill process tree
        process = task.process
        killed = 0
        if process:
            try:
                parent = psutil.Process(process.pid)
                for child in parent.children(recursive=True):
                    try:
                        child.kill()
                    except psutil.NoSuchProcess:
                        pass
                parent.kill()
                killed += 1
            except psutil.NoSuchProcess:
                pass
            except Exception as e:
                print(f"Error killing process {process.pid}: {e}")

        with self._lock:
            task.status = 'error'
            task.message = 'Task aborted by user.'
            task.completed_at = time.time()
            if task.output:
                task.output += "\n\n[!] PROCESS ABORTED BY USER."
            else:
                task.output = "[!] PROCESS ABORTED BY USER."

        emit_log_event(
            'task_killed',
            f'Task {task_id[:8]}... ({task.tool}) killed by user',
            source='task_manager',
            extra_data={'task_id': task_id, 'tool': task.tool, 'target': task.target},
        )
        return True, killed

    def kill_all_tasks(self):
        """Kill every running task and cancel all queued futures."""
        total_killed = 0
        with self._lock:
            # Cancel all active futures
            for task_id, future in list(self._active_futures.items()):
                if future is not None and not future.done():
                    future.cancel()

            # Kill all tasks that have a process handle and are still active
            for task_id, task in list(self._tasks.items()):
                if task.status in ('pending', 'running') and task.process:
                    try:
                        parent = psutil.Process(task.process.pid)
                        for child in parent.children(recursive=True):
                            try:
                                child.kill()
                            except psutil.NoSuchProcess:
                                pass
                        parent.kill()
                        total_killed += 1
                    except psutil.NoSuchProcess:
                        pass
                    except Exception:
                        pass
                if task.status in ('pending', 'running'):
                    task.status = 'error'
                    task.message = 'Aborted by Global Kill Switch.'
                    task.completed_at = time.time()
                    if task.output:
                        task.output += "\n\n[!] PROCESS ABORTED BY GLOBAL KILL SWITCH."
                    else:
                        task.output = "[!] PROCESS ABORTED BY GLOBAL KILL SWITCH."

            self._active_futures.clear()

        emit_log_event(
            'kill_all',
            f'All tasks killed ({total_killed} process(es) terminated)',
            source='task_manager',
            extra_data={'total_killed': total_killed},
        )
        return total_killed

    def as_dict(self, task_id):
        """Return a JSON-safe dict for a task (strips internal fields)."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            return {
                'status': task.status,
                'tool': task.tool,
                'target': task.target,
                'action': task.action,
                'output': task.output,
                'message': task.message,
                'type': getattr(task, 'type', 'text'),
            }

    def all_dicts(self):
        """Return a JSON-safe dict of all tasks keyed by task_id."""
        with self._lock:
            return {
                tid: {
                    'status': t.status,
                    'tool': t.tool,
                    'target': t.target,
                    'action': t.action,
                    'output': t.output,
                    'message': t.message,
                    'type': getattr(t, 'type', 'text'),
                }
                for tid, t in self._tasks.items()
            }

    def get_task(self, task_id):
        with self._lock:
            return self._tasks.get(task_id)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_manager = _TaskManager()


# ---------------------------------------------------------------------------
# Public API (backward-compatible with v1 task_manager)
# ---------------------------------------------------------------------------

def create_task(tool, target, action, task_id=None, client_task_id=None):
    """Create a pending async task and return a server-generated UUID."""
    return _manager.create_task(tool, target, action, task_id=task_id, client_task_id=client_task_id)


def set_task_process(task_id, process):
    """Attach a subprocess handle to a running task."""
    _manager.set_task_process(task_id, process)


def kill_task(task_id):
    """Kill (or cancel) a task.  Returns ``(success: bool, detail)``."""
    return _manager.kill_task(task_id)


def kill_all_tasks():
    """Kill every running task and cancel all queued futures.  Returns count killed."""
    return _manager.kill_all_tasks()


def get_async_tasks():
    """Return a JSON-safe snapshot of all tasks (backward-compatible)."""
    return _manager.all_dicts()


def get_task_manager():
    """Return the singleton ``_TaskManager`` instance (for advanced use)."""
    return _manager
