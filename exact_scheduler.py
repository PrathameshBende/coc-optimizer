# optimizer/exact_scheduler.py
from ortools.sat.python import cp_model
from models import Task, TaskSchedule
import time

class ProgressCallback(cp_model.CpSolverSolutionCallback):
    """Monitor solver progress and display a clean progress bar."""
    
    def __init__(self):
        super().__init__()
        self.start_time = time.time()
        self.last_update = 0
        self.solution_count = 0
        
    def on_solution_callback(self):
        """Called whenever the solver finds a new, better schedule."""
        self.solution_count += 1
        current_time = time.time()
        
        # Update display every 1 second
        if current_time - self.last_update < 1.0:
            return
            
        self.last_update = current_time
        elapsed = current_time - self.start_time
        
        # Convert seconds to days for readability
        upper_bound_days = self.ObjectiveValue() / 86400 
        lower_bound_days = self.BestObjectiveBound() / 86400
        
        # Calculate optimality gap
        if upper_bound_days > 0:
            gap = ((upper_bound_days - lower_bound_days) / upper_bound_days) * 100
        else:
            gap = 100.0
            
        print(f"\r⏳ {elapsed:5.1f}s | Best Schedule: {upper_bound_days:7.1f}d | Theoretical Min: {lower_bound_days:7.1f}d | Gap: {gap:5.2f}% | Solutions found: {self.solution_count}", end='', flush=True)

def solve_exact(machines: int, tasks: list[Task], time_limit_seconds: int = 120) -> list[TaskSchedule]:
    """
    Finds the global optimal schedule using CP-SAT.
    """
    if not tasks:
        return []

    model = cp_model.CpModel()
    horizon = sum(t.duration for t in tasks)

    starts = {}
    ends = {}
    
    for task in tasks:
        starts[task.id] = model.NewIntVar(0, horizon, f'start_{task.id}')
        ends[task.id] = model.NewIntVar(0, horizon, f'end_{task.id}')

    for task in tasks:
        for dep in task.deps:
            model.Add(ends[dep] <= starts[task.id])

    for task in tasks:
        if task.release_time > 0:
            model.Add(starts[task.id] >= task.release_time)

    machine_intervals = {m: [] for m in range(machines)}
    task_machine_vars = {} 

    for task in tasks:
        presences = []
        for m in range(machines):
            is_present = model.NewBoolVar(f'assign_{task.id}_m{m}')
            presences.append(is_present)
            
            opt_interval = model.NewOptionalIntervalVar(
                starts[task.id], task.duration, ends[task.id], is_present, f'interval_{task.id}_m{m}'
            )
            machine_intervals[m].append(opt_interval)
        
        task_machine_vars[task.id] = presences
        model.AddExactlyOne(presences)

    for m in range(machines):
        model.AddNoOverlap(machine_intervals[m])

    makespan = model.NewIntVar(0, horizon, 'makespan')
    model.AddMaxEquality(makespan, [ends[task.id] for task in tasks])
    model.Minimize(makespan)

    solver = cp_model.CpSolver()
    
    # CRITICAL: Turn off the wall of text
    solver.parameters.log_search_progress = False 
    solver.parameters.num_search_workers = 8
    
    # Stop searching after X seconds and return the best schedule found so far
    solver.parameters.max_time_in_seconds = time_limit_seconds 
    
    callback = ProgressCallback()
    status = solver.Solve(model, callback)
    print() # Newline after progress bar

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("Solver failed to find a solution.")

    status_name = "OPTIMAL (Proven)" if status == cp_model.OPTIMAL else "FEASIBLE (Time Limit Reached)"
    print(f"🏁 Solver finished with status: {status_name}")

    schedules = []
    for task in tasks:
        start_time = solver.Value(starts[task.id])
        end_time = solver.Value(ends[task.id])
        
        assigned_machine = -1
        for m, pres in enumerate(task_machine_vars[task.id]):
            if solver.Value(pres):
                assigned_machine = m + 1
                break
                
        schedules.append(TaskSchedule(
            task_id=task.id,
            machine_id=assigned_machine,
            start_time=start_time,
            end_time=end_time
        ))

    return schedules