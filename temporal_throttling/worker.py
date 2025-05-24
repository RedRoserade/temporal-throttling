import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from temporal_throttling.defs import SomeWorkflow, SomeActivity


async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="hello-activity-task-queue",
        workflows=[SomeWorkflow],
        activities=[SomeActivity().run],
    )

    print("Starting worker")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
