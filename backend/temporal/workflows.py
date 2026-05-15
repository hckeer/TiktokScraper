from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from temporal.activities import (
        connect_to_tiktok_live,
        stream_and_extract,
        update_session_status
    )

retry_policy = RetryPolicy(
    maximum_attempts=5,
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=30)
)

@workflow.defn
class ExtractionWorkflow:
    def __init__(self):
        self._stop_requested = False
        self._status = "connecting"
        self._stats = {"total_comments": 0, "total_numbers": 0}

    @workflow.signal
    def stop(self):
        self._stop_requested = True

    @workflow.query
    def get_status(self) -> dict:
        return {"status": self._status, **self._stats}

    @workflow.run
    async def run(self, username: str, session_id: str) -> dict:
        self._status = "connecting"
        
        await workflow.execute_activity(
            connect_to_tiktok_live,
            username,
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=retry_policy,
            heartbeat_timeout=timedelta(seconds=10)
        )
        
        self._status = "live"
        await workflow.execute_activity(
            update_session_status,
            args=[session_id, "live", 0, 0],
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=retry_policy,
            heartbeat_timeout=timedelta(seconds=10)
        )
        
        # We start the stream and extract activity
        # Since it runs until stopped or errored, we run it and wait
        # To handle stop signals, we must wrap it in a wait or cancel it
        # Unfortunately stream_and_extract is an activity that runs forever.
        # We can start it in the background and wait for the stop signal.
        
        import asyncio
        stream_task = asyncio.create_task(
            workflow.execute_activity(
                stream_and_extract,
                args=[username, session_id],
                start_to_close_timeout=timedelta(hours=4),
                retry_policy=retry_policy,
                heartbeat_timeout=timedelta(seconds=15),
                cancellation_type=workflow.ActivityCancellationType.TRY_CANCEL
            )
        )
        
        # Wait for either a stop signal, or for the extraction activity to finish naturally (or fail)
        await workflow.wait_condition(lambda: self._stop_requested or stream_task.done())
        
        if self._stop_requested and not stream_task.done():
            # Stop requested, cancel the activity
            stream_task.cancel()
        
        try:
            result = await stream_task
            self._stats = result
        except Exception:
            # Activity was cancelled
            pass
            
        self._status = "ended"
        await workflow.execute_activity(
            update_session_status,
            args=[session_id, "ended", self._stats["total_comments"], self._stats["total_numbers"]],
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=retry_policy,
            heartbeat_timeout=timedelta(seconds=10)
        )
        
        return {"status": "ended", **self._stats}
