# optimizer/scheduler.py
from models import ScheduleResult
from parser import parse_input
from exact_scheduler import solve_exact

def run_scheduler(filepath: str) -> ScheduleResult:
    """Orchestrates the pipeline using the Exact CP-SAT solver."""
    machines, tasks = parse_input(filepath)
    
    if not tasks:
        return ScheduleResult(makespan=0, task_schedules=[], tasks=[])

    # Call the exact solver instead of the heuristic simulator
    task_schedules = solve_exact(machines, tasks)
    
    makespan = max(ts.end_time for ts in task_schedules)
    
    return ScheduleResult(
        makespan=makespan,
        task_schedules=task_schedules,
        tasks=tasks
    )