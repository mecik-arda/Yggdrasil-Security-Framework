import uuid
import psutil

ASYNC_TASKS = {}

def get_async_tasks():
    return ASYNC_TASKS

def create_task(tool, target, action):
    task_id = str(uuid.uuid4())
    ASYNC_TASKS[task_id] = {
        'status': 'running',
        'tool': tool,
        'target': target,
        'action': action,
        'process': None
    }
    return task_id

def set_task_process(task_id, process):
    if task_id in ASYNC_TASKS:
        ASYNC_TASKS[task_id]['process'] = process

def kill_task(task_id):
    task = ASYNC_TASKS.get(task_id)
    if not task:
        return False, "Task not found"
        
    process = task.get('process')
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
            
    task['status'] = 'error'
    task['message'] = 'Task aborted by user.'
    if 'output' in task:
        task['output'] += "\n\n[!] PROCESS ABORTED BY USER."
    else:
        task['output'] = "[!] PROCESS ABORTED BY USER."
        
    return True, killed

def kill_all_tasks():
    total_killed = 0
    for task_id, task in list(ASYNC_TASKS.items()):
        if task.get('status') == 'running':
            process = task.get('process')
            if process:
                try:
                    parent = psutil.Process(process.pid)
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
            
            task['status'] = 'error'
            task['message'] = 'Aborted by Global Kill Switch.'
            if 'output' in task:
                task['output'] += "\n\n[!] PROCESS ABORTED BY GLOBAL KILL SWITCH."
            else:
                task['output'] = "[!] PROCESS ABORTED BY GLOBAL KILL SWITCH."
                
    return total_killed
