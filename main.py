import asyncio
import os
import random
import re
from collections import deque
from typing import Optional

from aiohttp import ClientWebSocketResponse
from janome.tokenizer import Tokenizer
from mipac import Note

from misskey_bot.bot_base import MisskeyBot
from misskey_bot.bot_redis import MarkovBotRedis
from misskey_bot.constants import RE_ENGLISH_ONLY, RE_REACTION, END_TOKEN


class MarkovMisskeyBot(MisskeyBot):
    def __init__(self, redis_host: str, redis_port: int, redis_db: int):
        super().__init__(channels=["local"])
        self.tokenizer = Tokenizer("./dictionary.csv", udic_type="simpledic", udic_enc="utf8")
        self.db = MarkovBotRedis(redis_host, redis_port, redis_db)
        self.recent_topics = deque(maxlen=100)

    async def on_ready(self, ws: ClientWebSocketResponse) -> None:
        await self.db.connect()
        await super().on_ready(ws)

    async def on_note(self, note: Note) -> None:
        if self._should_ignore(note):
            return
        words, nouns = self._parse(note.text)
        await self._learn_words(words)
        for n in set(nouns):
            self.recent_topics.append(n)

    def _choose_topic(self) -> Optional[str]:
        topics = list(set(self.recent_topics))
        if not topics:
            return
        return random.choice(topics)

    async def _speak(self) -> None:
        topic = self._choose_topic()
        if not topic:
            return
        msg = await self._generate_message(topic, max_words=20)
        self.logger.debug(f"Create note: {msg}")
        await self._create_note(msg)

    async def speak_loop(self, interval: int) -> None:
        while True:
            await asyncio.sleep(interval)
            await self._speak()

    def _parse(self, msg: str) -> tuple[list[str], list[str]]:
        def tokenize(text):
            words_, nouns_ = [], []
            for token in self.tokenizer.tokenize(text):
                surface = token.surface
                if not re.match(RE_ENGLISH_ONLY, surface):
                    words_.append(surface)
                    if token.part_of_speech.startswith("名詞"):
                        nouns_.append(surface)
            return words_, nouns_

        words, nouns = [], []
        cursor = 0
        for line in msg.splitlines():
            for match in re.finditer(RE_REACTION, line):
                w, n = tokenize(line[cursor:match.start(0)])
                words.extend(w)
                nouns.extend(n)
                reaction = match.group(0)
                words.append(reaction)
                cursor = match.end(0)
            w, n = tokenize(line[cursor:])
            words.extend(w)
            nouns.extend(n)
        return words, nouns

    async def _learn_words(self, words: list[str]) -> None:
        words = words + [END_TOKEN]
        for i in range(len(words) - 1):
            prev, next_ = words[i], words[i + 1]
            await self.db.add_bigram(prev, next_)
            if i >= 1:
                pprev = words[i - 1]
                await self.db.add_trigram(pprev, prev, next_)

    async def _choose_next_word(self, prev: str, pprev: str) -> Optional[str]:
        bi_words, bi_counts = await self.db.get_bigram(prev)
        if pprev:
            tri_words, tri_counts = await self.db.get_trigram(pprev, prev)
        else:
            tri_words, tri_counts = [], []
        if not (bi_words or tri_words):
            return
        counts = tri_counts + bi_counts
        sum_ = sum(counts)
        dcr = random.randrange(0, sum_)
        for i, c in enumerate(counts):
            dcr -= c
            if dcr < 0:
                if i < len(tri_counts):
                    return tri_words[i]
                return bi_words[i - len(tri_counts)]

    async def _generate_message(self, initial_word: str, max_words: int) -> str:
        words = ["", initial_word]
        for _ in range(max_words):
            next_ = await self._choose_next_word(words[-1], words[-2])
            if not next_ or next_ == END_TOKEN:
                break
            words.append(next_)
        msg = "".join(words)
        return re.sub(r':([a-z0-9_]+):([0-9])', r':\1: \2', msg)

    async def start_wrapper(self, url: str, token: str, interval: int) -> None:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.start(url, token))
            tg.create_task(self.speak_loop(interval))


def main():
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_db = int(os.getenv("REDIS_DB", "0"))

    url = os.getenv("SERVER_URL")
    token = os.getenv("API_TOKEN")

    interval = int(os.getenv("SPEAK_INTERVAL", "1800"))

    bot = MarkovMisskeyBot(redis_host, redis_port, redis_db)
    asyncio.run(bot.start_wrapper(url, token, interval))


if __name__ == '__main__':
    main()
