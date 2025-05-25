# Same as caller.py, but it uses Client#count_workflows to check if there's an existing workflow already

import asyncio
import redis.asyncio as redis
from datetime import datetime, timedelta
from datetime import timezone
from math import ceil
import time
import uuid

from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError


from temporal_throttling.defs import SomeWorkflow


# Tune these as you wish
message_count = 97
input_rps = 120
target_rps = 1
delay = 2

if delay < (1 / target_rps):
    raise ValueError(
        "please set delay >= (1 / target_rps) to eliminate the risk of lost events"
    )


async def main():
    client = await Client.connect("localhost:7233")

    r = redis.Redis(encoding="utf-8", decode_responses=True)

    sleep_s = 1 / input_rps

    schedule_delay = timedelta(seconds=delay)

    base_id = str(uuid.uuid4())

    workflow_id: str = ""

    for i in range(1, message_count + 1):
        await asyncio.sleep(sleep_s)

        await r.set(f"item.{base_id}.version", str(i))

        bucket = ceil(target_rps * time.time()) / target_rps

        workflow_id = f"{base_id}_{bucket}"

        now = datetime.now(tz=timezone.utc)

        # Count the number of workflows before scheduling, prevents so many scheduling attempts
        count_result = await client.count_workflows(f'WorkflowId = "{workflow_id}"')

        if count_result.count > 0:
            print(f"Workflow with id={workflow_id} already exists")
            continue

        print(
            f"scheduling workflow with id={workflow_id}, version={i}, start={(now + schedule_delay).isoformat()}"
        )

        try:
            handle = await client.start_workflow(
                SomeWorkflow.run,
                base_id,
                id=workflow_id,
                task_queue="hello-activity-task-queue",
                start_delay=schedule_delay,
            )

            description = await handle.describe()

            print(f"scheduled, run_id={description.run_id}")

        except WorkflowAlreadyStartedError as e:
            print(f"already started: run_id={e.run_id}")

    print(f"getting result for {workflow_id=!r}, expected_version={message_count}")

    last_handle = client.get_workflow_handle_for(
        SomeWorkflow.run,
        workflow_id,
    )

    result = await last_handle.result()

    print(f"{result=}")

    assert result == str(message_count)


if __name__ == "__main__":
    asyncio.run(main())
