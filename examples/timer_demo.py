import asyncio
import time

from services.infrastructure import JobScheduler


def ts():
	return time.strftime("%H:%M:%S")


async def long_job(name: str, duration: float):
	print(f"[{ts()}] {name}: START (duration={duration}s)")
	await asyncio.sleep(duration)
	print(f"[{ts()}] {name}: END")
	return name


async def short_job(name: str, duration: float):
	print(f"[{ts()}] {name}: START (duration={duration}s)")
	await asyncio.sleep(duration)
	print(f"[{ts()}] {name}: END")
	return name


async def main():
	print(f"[{ts()}] App start -> init scheduler")
	scheduler = JobScheduler(default_delay=0.0)
	await scheduler.start()

	print(f"[{ts()}] Job scheduling: queue job1 now, and job2 with 10s timer")
	# job1 starts immediately and runs for 30s
	scheduler.add_job(
		"job1",
		long_job,
		"job1",
		30.0,
		priority=0,
		delay=0.0,
	)
	# job2 starts exactly 10s after job1 was queued, even if job1 is still running
	scheduler.add_job(
		"job2",
		short_job,
		"job2",
		0.5,
		priority=1,
		delay=10.0,
	)

	print(f"[{ts()}] Timer interval (10s) counting... scheduler will trigger job2 independently")
	await scheduler.wait_for_completion(timeout=60.0)

	j1 = scheduler.jobs["job1"]
	j2 = scheduler.jobs["job2"]

	gap = j2.started_at - j1.started_at if j1.started_at and j2.started_at else None
	print(f"[{ts()}] Results:\n  job1: started_at={j1.started_at}, completed_at={j1.completed_at}\n  job2: started_at={j2.started_at}, completed_at={j2.completed_at}\n  start_gap(job2-job1)={gap:.2f}s")

	await scheduler.stop()
	print(f"[{ts()}] Scheduler stopped. Demo done.")


if __name__ == "__main__":
	asyncio.run(main())