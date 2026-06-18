# optimizer/main.py
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import from the orchestrator, NOT the exact solver directly
from scheduler import run_scheduler
from models import ScheduleResult

def print_schedule(result: ScheduleResult) -> None:
    print(f"Makespan: {result.makespan} hours\n")

    machine_tasks: dict[int, list] = {}
    for ts in result.task_schedules:
        machine_tasks.setdefault(ts.machine_id, []).append(ts)

    for m_id in sorted(machine_tasks.keys()):
        print(f"Machine {m_id}")
        tasks = sorted(machine_tasks[m_id], key=lambda x: x.start_time)
        for ts in tasks:
            print(f"{ts.start_time} -> {ts.end_time} : {ts.task_id}")
        print()

def verify_schedule(result: ScheduleResult) -> None:
    task_ids = {t.id for t in result.tasks}
    scheduled_ids = {ts.task_id for ts in result.task_schedules}

    if task_ids != scheduled_ids:
        raise ValueError(f"Task execution mismatch. Missing: {task_ids - scheduled_ids}")

    end_times = {ts.task_id: ts.end_time for ts in result.task_schedules}
    start_times = {ts.task_id: ts.start_time for ts in result.task_schedules}

    for task in result.tasks:
        for dep in task.deps:
            if end_times[dep] > start_times[task.id]:
                raise ValueError(f"Dependency violated: {task.id} starts before {dep} ends")

    machine_tasks: dict[int, list] = {}
    for ts in result.task_schedules:
        machine_tasks.setdefault(ts.machine_id, []).append(ts)

    for m_id, m_tasks in machine_tasks.items():
        m_tasks.sort(key=lambda x: x.start_time)
        for i in range(len(m_tasks) - 1):
            if m_tasks[i].end_time > m_tasks[i+1].start_time:
                raise ValueError(f"Overlap on machine {m_id}")

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_json>")
        sys.exit(1)

    try:
        result = run_scheduler(sys.argv[1])
        print_schedule(result)
        verify_schedule(result)
        print("Verification passed: All constraints satisfied.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()