# optimizer/exact_scheduler.py
from ortools.sat.python import cp_model
from models import Task, TaskSchedule

def solve_exact(machines: int, tasks: list[Task]) -> list[TaskSchedule]:
    """
    Finds the mathematically provable global optimal schedule using CP-SAT.
    """
    if not tasks:
        return []

    model = cp_model.CpModel()
    # The absolute maximum possible time is if all tasks run sequentially
    horizon = sum(t.duration for t in tasks)

    starts = {}
    ends = {}
    
    # 1. Create Time Variables
    for task in tasks:
        starts[task.id] = model.NewIntVar(0, horizon, f'start_{task.id}')
        ends[task.id] = model.NewIntVar(0, horizon, f'end_{task.id}')

    # 2. Precedence Constraints (DAG)
    for task in tasks:
        for dep in task.deps:
            model.Add(ends[dep] <= starts[task.id])

    # 3. Machine Assignment & No-Overlap Constraints
    machine_intervals = {m: [] for m in range(machines)}
    task_machine_vars = {} 

    for task in tasks:
        presences = []
        for m in range(machines):
            # Boolean: Is this task assigned to machine m?
            is_present = model.NewBoolVar(f'assign_{task.id}_m{m}')
            presences.append(is_present)
            
            # Optional Interval: Only exists if is_present is True
            opt_interval = model.NewOptionalIntervalVar(
                starts[task.id], 
                task.duration, 
                ends[task.id], 
                is_present, 
                f'interval_{task.id}_m{m}'
            )
            machine_intervals[m].append(opt_interval)
        
        task_machine_vars[task.id] = presences
        
        # A task must be assigned to exactly one machine
        model.AddExactlyOne(presences)

    # Tasks on the same machine cannot overlap
    for m in range(machines):
        model.AddNoOverlap(machine_intervals[m])

    # 4. Objective: Minimize Makespan
    makespan = model.NewIntVar(0, horizon, 'makespan')
    model.AddMaxEquality(makespan, [ends[task.id] for task in tasks])
    model.Minimize(makespan)

    # 5. Solve
    solver = cp_model.CpSolver()
    # Because you don't care about speed, we let it run until it proves optimality.
    # (If you ever get a massive input, you can add: solver.parameters.max_time_in_seconds = 300.0)
    
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("Solver failed to find a solution.")

    # 6. Extract Results
    schedules = []
    for task in tasks:
        start_time = solver.Value(starts[task.id])
        end_time = solver.Value(ends[task.id])
        
        # Find which machine it was assigned to
        assigned_machine = -1
        for m, pres in enumerate(task_machine_vars[task.id]):
            if solver.Value(pres):
                assigned_machine = m + 1 # 1-based indexing for output
                break
                
        schedules.append(TaskSchedule(
            task_id=task.id,
            machine_id=assigned_machine,
            start_time=start_time,
            end_time=end_time
        ))

    return schedules