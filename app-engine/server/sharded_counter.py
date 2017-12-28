import random

from google.appengine.api import memcache
from google.appengine.ext import ndb

from ndb_util import FancyModel

class _CounterShard(FancyModel):
    """Shards for each named counter."""
    count = ndb.IntegerProperty(default=0)


class ShardedCounter(FancyModel):
    keys = ndb.KeyProperty(kind=_CounterShard, repeated=True)

    @classmethod
    def create(cls, num_shards):
        counter = cls()
        counter.increase_total_shards(num_shards)
        counter.put()
        return counter

    def increase_total_shards(self, num_total_shards):
        while len(self.keys) < num_shards:
            shard = _CounterShard()
            shard_key = shard.put()
            self.keys.append(shard_key)
        self.put()

    def get_count_fast(self):
        total = memcache.get(self._get_memcache_key())
        if total is None:
            total = self.get_count_exact()
        return total

    def get_count_exact(self):
        total = 0
        for shard in ndb.get_multi(self.keys):
            total += shard.count
        memcache.add(self._get_memcache_key(), total, 60)
        return total

    @ndb.transactional
    def increment(self):
        shard = random.choice(self.keys).get()
        shard.count += 1
        shard.put()
        # Memcache increment does nothing if the name is not a key in memcache
        memcache.incr(self._get_memcache_key())

    @ndb.transactional
    def decrement(self):
        shard = random.choice(self.keys).get()
        shard.count -= 1
        shard.put()
        # Memcache increment does nothing if the name is not a key in memcache
        memcache.decr(self._get_memcache_key())

    def _get_memcache_key(self):
        return 'ShardedCounter-{}'.format(self.key.id())

