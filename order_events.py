STATUS_BY_VERSION = {1: "CREATED", 2: "PAID", 3: "SHIPPED"}


class OrderProcessor:
    def __init__(self):
        # order_id -> {"version": int, "status": str, "pending": {version: update}}
        self.orders = {}

    def log(self, msg):
        print("[processor] " + msg)

    def get_order(self, order_id):
        if order_id not in self.orders:
            self.orders[order_id] = {"version": 0, "status": "NONE", "pending": {}}
        return self.orders[order_id]

    def state(self, order_id):
        order = self.get_order(order_id)
        pending = sorted(order["pending"].keys())
        return "order=%s applied_version=%d status=%s pending=%s" % (
            order_id, order["version"], order["status"], pending)

    def apply(self, order, update):
        order["version"] = update["version"]
        order["status"] = update["status"]
        self.log("applied version %d -> status=%s" % (update["version"], update["status"]))

    def handle(self, update):
        order_id = update["order_id"]
        version = update["version"]
        order = self.get_order(order_id)
        self.log("received order=%s version=%d status=%s" % (order_id, version, update["status"]))

        if version <= order["version"]:
            self.log("duplicate ignored (version %d already applied)" % version)
        elif version == order["version"] + 1:
            self.apply(order, update)
            # apply any buffered versions that are now next in line
            while order["version"] + 1 in order["pending"]:
                next_update = order["pending"].pop(order["version"] + 1)
                self.log("version %d was pending, now it is next in line" % next_update["version"])
                self.apply(order, next_update)
        elif version in order["pending"]:
            self.log("version %d is already pending, not stored again" % version)
        else:
            order["pending"][version] = update
            self.log("version %d arrived too early, waiting as pending" % version)
            missing = [v for v in range(order["version"] + 1, version) if v not in order["pending"]]
            self.log("missing version(s): %s" % missing)

        self.log("state: " + self.state(order_id))
        print()
