import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker
from config import settings
from temporal.workflows import ExtractionWorkflow
from temporal.activities import (
    connect_to_tiktok_live,
    stream_and_extract,
    update_session_status,
    export_csv_activity,
    export_excel_activity
)

logging.basicConfig(level=logging.INFO)

async def main():
    client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[ExtractionWorkflow],
        activities=[
            connect_to_tiktok_live,
            stream_and_extract,
            update_session_status,
            export_csv_activity,
            export_excel_activity
        ],
    )
    logging.info("Starting Temporal Worker...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
