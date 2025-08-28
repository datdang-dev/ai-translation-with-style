import asyncio
import time
import pytest

from services.infrastructure import JobScheduler


async def _sleep_job(duration: float):
    await asyncio.sleep(duration)
    return duration


@pytest.mark.asyncio
async def test_scheduler_starts_jobs_by_timer_independent_of_completion():
    """Job2 must start ~1s after Job1 start, even if Job1 still runs.
    - Job1: delay=0s, duration=3s
    - Job2: delay=1s, duration=0.1s
    Assertions:
      - job2.started_at - job1.started_at in [0.8s, 1.8s]
      - job2.started_at < job1.completed_at (i.e., overlapped)
    """
    scheduler = JobScheduler(default_delay=0.0)
    await scheduler.start()

    # Add two jobs: job1 starts immediately, job2 should start ~1s later regardless of job1 running
    job1 = scheduler.add_job(
        "job1",
        _sleep_job,
        3.0,  # 3 seconds work
        priority=0,
        delay=0.0,
    )
    job2 = scheduler.add_job(
        "job2",
        _sleep_job,
        0.1,  # quick
        priority=1,
        delay=1.0,
    )

    # Wait for both to complete
    await scheduler.wait_for_completion(timeout=10.0)

    # Fetch updated job records
    j1 = scheduler.jobs[job1.job_id]
    j2 = scheduler.jobs[job2.job_id]

    # Ensure the scheduler recorded timestamps
    assert j1.started_at is not None and j1.completed_at is not None
    assert j2.started_at is not None and j2.completed_at is not None

    # Check that job2 was fired by the timer around 1s after job1 started
    start_gap = j2.started_at - j1.started_at
    assert 0.8 <= start_gap <= 1.8, f"job2 start gap {start_gap:.2f}s not ~1s"

    # And that job2 began before job1 completed (overlap)
    assert j2.started_at < j1.completed_at, (
        f"job2 started at {j2.started_at:.2f} but job1 completed at {j1.completed_at:.2f}"
    )

    await scheduler.stop()