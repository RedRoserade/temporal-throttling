import asyncio
import redis.asyncio as redis

from dataclasses import dataclass
from datetime import datetime, timedelta

from temporalio import activity, workflow


@dataclass(kw_only=True)
class Input:
    base_id: str


class SomeActivity:
    def __init__(self) -> None:
        self.redis = redis.Redis(encoding="utf-8", decode_responses=True)

    @activity.defn
    async def run(self, input: Input) -> str:
        now = datetime.now()

        version: str = await self.redis.get(f"item.{input.base_id}.version")

        print(
            f"[{now.isoformat()}] Running activity with base_id={input.base_id} and version={version}"
        )

        await asyncio.sleep(1.5)

        return version


@workflow.defn
class SomeWorkflow:
    @workflow.run
    async def run(self, base_id: str) -> str:
        result = await workflow.execute_activity(
            SomeActivity.run,
            Input(base_id=base_id),
            start_to_close_timeout=timedelta(seconds=10),
        )

        return result
