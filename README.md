# Throttling and delaying Temporal workflow executions

A proof of concept/demo for delaying and throttling Temporal workflow executions.

## Requirements

- Temporal server (for running the workflows and activities)
- Redis (for some shared state)

## Usage

- Start a Temporal server (e.g., `temporal server start-dev`)
- Start a Redis instance listening on `localhost:6379`
- Run the worker: `uv run -m temporal_throttling.worker`
- Run the calling code: `uv run -m temporal_throttling.caller`

You can play around with the parameters in [caller.py](./temporal_throttling/caller.py). You can set:

- The input rate of events (in events/second)
- The throttled rate of workflow executions (in workflows/sec)
- The delay (in seconds)

## How this works

(You can see the logic in [caller.py](./temporal_throttling/caller.py).)

The throttling is done by calculating the workflow IDs using time-based bucketing, and using collisions to our advantage. To ensure a monotonically-increasing ID, we use the UNIX timestamp, and calculate a bucket using the throttle rate:

```python
time_bucket = ceil(time.time() * throttled_rps) / throttled_rps
```

Assuming that `throttled_rps = 2`, for every second, the `time_bucket` will end in `.0` or `.5`. Any event in the timestamp `[0..0.5[` will be assigned bucket `.5` and any event with timestamp `[0.5..1[` will be assigned bucket `.0` of the next second.

If we combine this with some base ID, then we will get something in the format: `{base_id}_{time_bucket}`:

```python
base_id = "hello"

timestamp = 1234.56
throttled_rps = 2

time_bucket = ceil(timestamp * throttled_rps) / throttled_rps  # 1235.0

bucketed_id = f"{base_id}_{time_bucket}"  # hello_1235.0
```

Then, we run `Client#start_workflow(workflow_id=bucketed_id, ...)` to schedule it.

Because Temporal does not allow two workflows with the same ID to be running, scheduling a second execution while one is already running will cause the second scheduling operation to raise `WorkflowAlreadyStartedError`. Alternatively, we could use `Client#count_workflows(query="WorkflowId = 'hello_1235.0'")` and checking the result, but this requires one extra call to the Temporal API.

## Important caveat

Using only bucketing can cause events to be lost, depending on factors such as:

- How many events at the end of the input stream land into the final bucket
- The throughput of the worker consuming the workflows and activities

Therefore, this is not ideal if the last event of a sequence must be considered at all times (for that, debouncing is required, not throttling), but for activities that work on the _current state_ of some object, this can work, but a delay is essential.

This delay (in seconds) must be greater than or equal to the size of the bucket. Since the bucket's size (in seconds) is `1 / throttled_rps`, this means that, if `throttled_rps = 2`, then `delay >= (1 / 2)` or, `delay >= 0.5`.
