# CMPE 273 Module 7: Event Ordering and Fencing Tokens

This project shows how a system can handle order updates that arrive out of order, arrive twice, or go missing. It also shows how fencing tokens stop an old worker from writing after its lock has expired. Everything runs in memory with plain Python.

## How to run

No packages are needed. You only need Python 3.

Run all three scenarios:

```
python main.py
```

Run only one scenario:

```
python main.py --scenario 1
python main.py --scenario 2
python main.py --scenario 3
```

## How it works

Versions and the pending buffer (`order_events.py`):

- Each order goes through versions: 1 = CREATED, 2 = PAID, 3 = SHIPPED.
- If the next version arrives, the program applies it.
- If a version arrives too early, it waits in the pending buffer. The program also says which version is missing.
- When the missing version arrives, the program applies it and checks the pending buffer again.
- If a version was already applied, the program ignores it as a duplicate.

Fencing tokens (`fencing.py`):

- Every new lock gets a higher token number (1, 2, 3, ...). Each lock has a lease that runs out after a while.
- The storage remembers the highest token it has seen for each order.
- If a worker tries to write with an older token, the storage rejects it. So a worker that held an old lock cannot overwrite newer data.

## Evidence: correct event ordering (Scenario 1)

The updates for order o1 arrive as version 2, then 1, then 2 again, then 3. Version 2 waits as pending until version 1 shows up. Then both are applied in the right order.

```
============================================================
Scenario 1: ordering and duplicates (order o1)
============================================================
[processor] received order=o1 version=2 status=PAID
[processor] version 2 arrived too early, waiting as pending
[processor] missing version(s): [1]
[processor] state: order=o1 applied_version=0 status=NONE pending=[2]

[processor] received order=o1 version=1 status=CREATED
[processor] applied version 1 -> status=CREATED
[processor] version 2 was pending, now it is next in line
[processor] applied version 2 -> status=PAID
[processor] state: order=o1 applied_version=2 status=PAID pending=[]

[processor] received order=o1 version=2 status=PAID
[processor] duplicate ignored (version 2 already applied)
[processor] state: order=o1 applied_version=2 status=PAID pending=[]

[processor] received order=o1 version=3 status=SHIPPED
[processor] applied version 3 -> status=SHIPPED
[processor] state: order=o1 applied_version=3 status=SHIPPED pending=[]

Final: order=o1 applied_version=3 status=SHIPPED pending=[]
```

## Evidence: duplicate handling

In Scenario 1, version 2 arrives a second time after it was already applied. The program does not apply it again. It prints this line and the state stays the same:

```
[processor] duplicate ignored (version 2 already applied)
[processor] state: order=o1 applied_version=2 status=PAID pending=[]
```

## Evidence: missing event (Scenario 2)

For order o2, version 1 arrives, then version 3, but version 2 is missing. The order stays at CREATED and version 3 waits. When version 2 finally arrives, versions 2 and 3 are applied in order.

```
============================================================
Scenario 2: missing event (order o2)
============================================================
[processor] received order=o2 version=1 status=CREATED
[processor] applied version 1 -> status=CREATED
[processor] state: order=o2 applied_version=1 status=CREATED pending=[]

[processor] received order=o2 version=3 status=SHIPPED
[processor] version 3 arrived too early, waiting as pending
[processor] missing version(s): [2]
[processor] state: order=o2 applied_version=1 status=CREATED pending=[3]

... version 2 arrives late ...

[processor] received order=o2 version=2 status=PAID
[processor] applied version 2 -> status=PAID
[processor] version 3 was pending, now it is next in line
[processor] applied version 3 -> status=SHIPPED
[processor] state: order=o2 applied_version=3 status=SHIPPED pending=[]

Final: order=o2 applied_version=3 status=SHIPPED pending=[]
```

## Evidence: stale worker rejection (Scenario 3)

worker-A gets token 1 and pauses for 1.5 seconds. Its lease is only 1 second, so it expires. Then worker-B gets token 2 and writes PAID. When worker-A tries to write again with its old token, the storage rejects it. The final status is the one from worker-B.

```
============================================================
Scenario 3: stale worker with fencing tokens (order o3)
============================================================
[lock] lock given to worker-A with fencing token 1 (lease 1.0s)
[worker-A] got token 1, now pausing (like a long GC pause)
[worker-A] is still paused, its lease has run out
[lock] lease of worker-A has expired
[lock] lock given to worker-B with fencing token 2 (lease 1.0s)
[storage] ACCEPTED write from worker-B: order=o3 status=PAID token=2
[worker-A] wakes up and tries to write with old token 1
[storage] REJECTED write from worker-A: order=o3 status=CREATED token=1 (highest seen=2)
Final: order=o3 status=PAID highest_token=2
```

## Reflection

I learned that timestamps are not always enough to decide the order of events. Different machines can have slightly different times, and a clock can even jump backward when it gets fixed, so the timestamps may not show the real order.

In this project, I used version numbers instead. If an update arrives too early, it waits until the missing version arrives. I also used fencing tokens so that a worker with an old lock cannot overwrite newer data.
