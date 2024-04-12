from redis.asyncio import Redis


TRIGRAM_FACTOR = 10


class MarkovBotRedis:
    def __init__(self, host: str, port: int, db: int):
        self._host = host
        self._port = port
        self._db = db
        self._redis = None

    async def connect(self):
        self._redis = await Redis(host=self._host, port=self._port, db=self._db)

    async def add_bigram(self, prev: str, next_: str) -> None:
        await self._redis.sadd(prev, next_)
        await self._redis.incr(f"{prev}__{next_}")

    async def add_trigram(self, pprev: str, prev: str, next_: str) -> None:
        await self._redis.sadd(f"{pprev}--{prev}", next_)
        await self._redis.incr(f"{pprev}--{prev}--{next_}")

    async def get_bigram(self, prev: str) -> tuple[list[str], list[int]]:
        bi_words = await self._redis.smembers(prev)
        bi_words = [str(word, "utf-8") for word in bi_words]
        bi_counts = await self._redis.mget(f"{prev}__{next_}" for next_ in bi_words)
        bi_counts = [int(i) for i in bi_counts]
        assert len(bi_words) == len(bi_counts)
        return bi_words, bi_counts

    async def get_trigram(self, pprev: str, prev: str, factor: int = TRIGRAM_FACTOR) -> tuple[list[str], list[int]]:
        tri_words = await self._redis.smembers(f"{pprev}--{prev}")
        tri_words = [str(word, "utf-8") for word in tri_words]
        tri_counts = await self._redis.mget(f"{pprev}--{prev}--{next_}" for next_ in tri_words)
        tri_counts = [int(i) * factor for i in tri_counts]
        assert len(tri_words) == len(tri_counts)
        return tri_words, tri_counts
