# optimizer/critical_path.py
from models import Task

def compute_critical_paths(tasks: list[Task]) -> dict[str, int]:
    """
    Computes the critical path length for each task using DFS + memoization.
    CPL(task) = task.duration + max(CPL(child))
    """
    task_map: dict[str, Task] = {t.id: t for t in tasks}
    
    # Build reverse adjacency list (children)
    children: dict[str, list[str]] = {t.id: [] for t in tasks}
    for t in tasks:
        for dep in t.deps:
            children[dep].append(t.id)

    cpl: dict[str, int] = {}

    def dfs(task_id: str) -> int:
        if task_id in cpl:
            return cpl[task_id]
        
        task = task_map[task_id]
        max_child_cpl = max((dfs(child_id) for child_id in children[task_id]), default=0)
        
        cpl[task_id] = task.duration + max_child_cpl
        return cpl[task_id]

    for task in tasks:
        if task.id not in cpl:
            dfs(task.id)

    return cpl