import argparse
import time

from order_events import OrderProcessor, STATUS_BY_VERSION
from fencing import LockService, Storage


def header(title):
    print("=" * 60)
    print(title)
    print("=" * 60)


def event(order_id, version):
    return {"order_id": order_id, "version": version, "status": STATUS_BY_VERSION[version]}


def scenario_1():
    header("Scenario 1: ordering and duplicates (order o1)")
    p = OrderProcessor()
    for version in [2, 1, 2, 3]:
        p.handle(event("o1", version))
    print("Final: " + p.state("o1"))
    print()


def scenario_2():
    header("Scenario 2: missing event (order o2)")
    p = OrderProcessor()
    p.handle(event("o2", 1))
    p.handle(event("o2", 3))
    print("... version 2 arrives late ...")
    print()
    p.handle(event("o2", 2))
    print("Final: " + p.state("o2"))
    print()


def scenario_3():
    header("Scenario 3: stale worker with fencing tokens (order o3)")
    locks = LockService(lease_seconds=1.0)
    storage = Storage()

    token_a = locks.acquire("worker-A")
    print("[worker-A] got token %d, now pausing (like a long GC pause)" % token_a)
    time.sleep(1.5)
    print("[worker-A] is still paused, its lease has run out")

    token_b = locks.acquire("worker-B")
    storage.write("worker-B", "o3", "PAID", token_b)

    print("[worker-A] wakes up and tries to write with old token %d" % token_a)
    storage.write("worker-A", "o3", "CREATED", token_a)

    print("Final: order=o3 status=%s highest_token=%d"
          % (storage.status["o3"], storage.highest_token["o3"]))
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=int, choices=[1, 2, 3])
    args = parser.parse_args()

    scenarios = {1: scenario_1, 2: scenario_2, 3: scenario_3}
    if args.scenario:
        scenarios[args.scenario]()
    else:
        for n in [1, 2, 3]:
            scenarios[n]()


if __name__ == "__main__":
    main()
