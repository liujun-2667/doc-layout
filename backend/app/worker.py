import os
import time
import redis
from rq import Worker, Queue, Connection
from rq.job import Job

from app.config import settings

redis_conn = redis.from_url(settings.redis_url)


def process_task(task_id: str, file_path: str):
    from app.database import SessionLocal
    from app.services.task_service import TaskService

    db = SessionLocal()
    try:
        service = TaskService(db)
        service.process_file(task_id, file_path)
    finally:
        db.close()


def get_queue() -> Queue:
    return Queue(connection=redis_conn, default_timeout=3600)


def enqueue_task(task_id: str, file_path: str) -> Job:
    queue = get_queue()
    job = queue.enqueue(
        process_task,
        task_id,
        file_path,
        job_id=task_id,
        result_ttl=86400,
    )
    return job


def get_job_status(job_id: str):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        return {
            "status": job.get_status(),
            "result": job.result,
            "exc_info": job.exc_info,
        }
    except Exception:
        return None


if __name__ == "__main__":
    with Connection(redis_conn):
        worker = Worker(["default"])
        worker.work()
