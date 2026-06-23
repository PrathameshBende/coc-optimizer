# optimizer/exact_scheduler.py
from ortools.sat.python import cp_model
from models import Task, TaskSchedule, ResourceType
import time
from collections import defaultdict

class ProgressCallback(cp_model.CpSolverSolutionCallback):
    def __init__(self, target_gap: float = 0.5):
        super().__init__()
        self.start_time = time.time()
        self.last_update = 0
        self.solution_count = 0
        self.target_gap = target_gap
        
    def on_solution_callback(self):
        self.solution_count += 1
        upper_bound = self.ObjectiveValue()
        lower_bound = self.BestObjectiveBound()
        
        if upper_bound > 0:
            gap = ((upper_bound - lower_bound) / upper_bound) * 100
        else:
            gap = 0.0
            
        if gap <= self.target_gap:
            print(f"\n✅ Target reached! Gap is {gap:.2f}% (<= {self.target_gap}%). Stopping early.")
            self.StopSearch()
            return

        current_time = time.time()
        if current_time - self.last_update < 1.0: return
        self.last_update = current_time
        elapsed = current_time - self.start_time
        
        print(f"\r⏳ {elapsed:5.1f}s | Best: {upper_bound/86400:7.1f}d | Min: {lower_bound/86400:7.1f}d | Gap: {gap:5.2f}% | Solutions: {self.solution_count}", end='', flush=True)

def solve_exact(machine_counts: dict[ResourceType, int], tasks: list[Task], time_limit_seconds: int = 300) -> list[TaskSchedule]:
    if not tasks: return []

    model = cp_model.CpModel()
    horizon = sum(t.duration for t in tasks)
    starts = {}; ends = {}
    
    for task in tasks:
        starts[task.id] = model.NewIntVar(0, horizon, f'start_{task.id}')
        ends[task.id] = model.NewIntVar(0, horizon, f'end_{task.id}')

    for task in tasks:
        for dep in task.deps:
            model.Add(ends[dep] <= starts[task.id])
        if task.release_time > 0:
            model.Add(starts[task.id] >= task.release_time)

    # Group intervals by (ResourceType, MachineIndex)
    machine_intervals = defaultdict(list)
    task_machine_vars = {} 

    for task in tasks:
        num_machines = machine_counts.get(task.resource, 1)
        presences = []
        for m in range(num_machines):
            is_present = model.NewBoolVar(f'assign_{task.id}_m{m}')
            presences.append(is_present)
            opt_interval = model.NewOptionalIntervalVar(
                starts[task.id], task.duration, ends[task.id], is_present, f'interval_{task.id}_m{m}'
            )
            machine_intervals[(task.resource, m)].append(opt_interval)
        
        task_machine_vars[task.id] = presences
        model.AddExactlyOne(presences)

    # Add NoOverlap for each machine in each resource pool
    for key, intervals in machine_intervals.items():
        model.AddNoOverlap(intervals)

    makespan = model.NewIntVar(0, horizon, 'makespan')
    model.AddMaxEquality(makespan, [ends[task.id] for task in tasks])
    model.Minimize(makespan)

    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = False
    solver.parameters.num_search_workers = 8
    solver.parameters.max_time_in_seconds = time_limit_seconds
    
    callback = ProgressCallback()
    status = solver.Solve(model, callback)
    print()

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("Solver failed to find a solution.")

    schedules = []
    for task in tasks:
        start_time = solver.Value(starts[task.id])
        end_time = solver.Value(ends[task.id])
        assigned_machine = -1
        for m, pres in enumerate(task_machine_vars[task.id]):
            if solver.Value(pres):
                assigned_machine = m + 1; break
        schedules.append(TaskSchedule(task_id=task.id, machine_id=assigned_machine, start_time=start_time, end_time=end_time))

    return schedules