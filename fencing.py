import time


class LockService:
    def __init__(self, lease_seconds):
        self.lease_seconds = lease_seconds
        self.next_token = 1
        self.holder = None
        self.expires_at = 0.0

    def log(self, msg):
        print("[lock] " + msg)

    def acquire(self, worker):
        now = time.monotonic()
        if self.holder is not None and now < self.expires_at:
            self.log("%s could not get the lock, %s still holds it" % (worker, self.holder))
            return None
        if self.holder is not None:
            self.log("lease of %s has expired" % self.holder)
        token = self.next_token
        self.next_token += 1
        self.holder = worker
        self.expires_at = now + self.lease_seconds
        self.log("lock given to %s with fencing token %d (lease %.1fs)" % (worker, token, self.lease_seconds))
        return token


class Storage:
    def __init__(self):
        self.status = {}
        self.highest_token = {}

    def log(self, msg):
        print("[storage] " + msg)

    def write(self, worker, order_id, status, token):
        highest = self.highest_token.get(order_id, 0)
        if token < highest:
            self.log("REJECTED write from %s: order=%s status=%s token=%d (highest seen=%d)"
                     % (worker, order_id, status, token, highest))
            return False
        self.highest_token[order_id] = token
        self.status[order_id] = status
        self.log("ACCEPTED write from %s: order=%s status=%s token=%d"
                 % (worker, order_id, status, token))
        return True
