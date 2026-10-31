"""gc_runtime: deterministic stand-ins for the things production AI code talks to.

Applied AI problems are graded against these fakes, so there are no real API calls, no wall-clock
sleeps and no flakiness. Your code may import from here:

    from gc_runtime import Clock, FakeLLM, Response, ToolCall, RateLimitError, count_tokens, embed

Everything is deterministic given the scenario the judge builds. Keep this file Python 3.9
compatible and dependency-free apart from NumPy.
"""

import hashlib
import heapq
import json
import math
import re

import numpy as np


# ---------------------------------------------------------------- errors

class GCError(Exception):
    """Base class for every simulated failure."""


class RateLimitError(GCError):
    """HTTP 429. `retry_after` is in seconds, or None when the server sent no header."""

    def __init__(self, message="rate limited", retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class ServerError(GCError):
    """HTTP 5xx: retryable."""


class TimeoutError_(GCError):
    """The call did not finish in time: retryable."""


class BadRequestError(GCError):
    """HTTP 400: not retryable."""


class ToolError(GCError):
    """A tool failed while running."""


ERRORS = {
    "rate_limit": RateLimitError,
    "server": ServerError,
    "timeout": TimeoutError_,
    "bad_request": BadRequestError,
    "tool": ToolError,
}


# ---------------------------------------------------------------- time

class Clock:
    """Virtual time in seconds. `sleep` advances it instantly and records the sleep."""

    def __init__(self, start=0.0):
        self._t = float(start)
        self.sleeps = []

    def now(self):
        return self._t

    def sleep(self, seconds):
        if seconds < 0:
            raise ValueError("cannot sleep a negative duration")
        self.sleeps.append(float(seconds))
        self._t += float(seconds)

    def advance(self, seconds):
        """Used by fakes to model latency; not recorded as a sleep."""
        self._t += float(seconds)


# ---------------------------------------------------------------- tokens and embeddings

_TOKEN_RE = re.compile(r"\w+|[^\w\s]")


def tokenize(text):
    """The judge's tokenizer: words and individual punctuation marks."""
    return _TOKEN_RE.findall(text or "")


def count_tokens(text):
    """Token count used by every budget in GradientCode. 'Hello, world!' -> 4."""
    if isinstance(text, (dict, list)):
        text = json.dumps(text, sort_keys=True)
    return len(tokenize(text))


def message_tokens(messages):
    """Tokens for a chat transcript: content tokens plus 3 per message for role framing."""
    total = 0
    for m in messages:
        total += 3 + count_tokens(m.get("content") or "")
        for tc in m.get("tool_calls") or []:
            total += count_tokens(tc["name"]) + count_tokens(tc.get("arguments") or {})
    return total


def embed(text, dim=32):
    """Deterministic bag-of-words embedding, L2-normalized. Texts sharing words are similar."""
    v = np.zeros(dim)
    for tok in tokenize((text or "").lower()):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        v[h % dim] += 1.0 if (h >> 64) % 2 else -1.0
    n = np.linalg.norm(v)
    return v / n if n else v


def stable_hash(s, mod=None):
    """sha256-based integer hash: the same on every machine and every run (unlike hash())."""
    h = int(hashlib.sha256(str(s).encode()).hexdigest(), 16)
    return h % mod if mod else h


# ---------------------------------------------------------------- LLM

class ToolCall:
    def __init__(self, id, name, arguments):
        self.id = id
        self.name = name
        self.arguments = arguments

    def to_dict(self):
        return {"id": self.id, "name": self.name, "arguments": self.arguments}

    def __repr__(self):
        return "ToolCall(%r, %r, %r)" % (self.id, self.name, self.arguments)


class Response:
    """What FakeLLM.complete returns. `stop_reason` is "end_turn" or "tool_use"."""

    def __init__(self, content=None, tool_calls=None, input_tokens=0, output_tokens=0, model=""):
        self.content = content
        self.tool_calls = tool_calls or []
        self.stop_reason = "tool_use" if self.tool_calls else "end_turn"
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.model = model

    def __repr__(self):
        return "Response(content=%r, tool_calls=%r)" % (self.content, self.tool_calls)


class FakeLLM:
    """A scripted model.

    `script` is a list of turns, consumed in order, one per complete() call. A turn is:
      {"content": "text"}                                  -> a final answer
      {"tool_calls": [{"name": "search", "arguments": {...}}], "content": optional}
      {"error": "rate_limit", "retry_after": 2.0}          -> raises (see ERRORS)
    Or pass `responder(messages, tools, model) -> turn` to decide turns from the input.

    Every call is recorded in `.calls` (a deep copy of messages, the tool names, the model), and
    takes `latency` seconds of virtual time on `clock` when one is given.
    """

    def __init__(self, script=None, responder=None, clock=None, latency=0.0, model="fake-model"):
        self.script = list(script or [])
        self.responder = responder
        self.clock = clock
        self.latency = latency
        self.model = model
        self.calls = []
        self._i = 0
        self._ids = 0

    def complete(self, messages, tools=None, model=None, max_tokens=None):
        model = model or self.model
        self.calls.append({
            "messages": json.loads(json.dumps(messages, default=_jsonable)),
            "tools": [t["name"] if isinstance(t, dict) else str(t) for t in (tools or [])],
            "model": model,
            "t": self.clock.now() if self.clock else None,
        })
        if self.clock and self.latency:
            self.clock.advance(self.latency)
        if self.responder is not None:
            turn = self.responder(messages, tools, model)
        else:
            if self._i >= len(self.script):
                raise GCError("FakeLLM script exhausted after %d calls" % self._i)
            turn = self.script[self._i]
            self._i += 1
        if "error" in turn:
            cls = ERRORS[turn["error"]]
            if cls is RateLimitError:
                raise RateLimitError(turn.get("message", "rate limited"), turn.get("retry_after"))
            raise cls(turn.get("message", turn["error"]))
        calls = []
        for tc in turn.get("tool_calls") or []:
            self._ids += 1
            calls.append(ToolCall(tc.get("id", "call_%d" % self._ids), tc["name"], tc.get("arguments", {})))
        out_tokens = turn.get("output_tokens", count_tokens(turn.get("content") or "") + sum(count_tokens(c.arguments) + 1 for c in calls))
        return Response(turn.get("content"), calls, message_tokens(messages), out_tokens, model)


def _jsonable(o):
    if isinstance(o, ToolCall):
        return o.to_dict()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.integer, np.floating)):
        return o.item()
    return str(o)


# ---------------------------------------------------------------- concurrency

class Task:
    def __init__(self, loop, gen, name):
        self.loop, self.gen, self.name = loop, gen, name
        self.done, self.result, self.error = False, None, None
        self.waiters = []
        self.started_at = loop.now()
        self.finished_at = None


class EventLoop:
    """A deterministic, single-threaded scheduler over virtual time.

    A task is a generator. Inside it:
      yield 1.5            -> sleep 1.5 virtual seconds
      r = yield other_task -> wait for another Task and get its result (its exception is re-raised)
      yield None           -> yield control and resume at the same time
    loop.spawn(gen, name) returns a Task; loop.run() runs until no task is runnable.
    Ties at the same time resume in spawn/wake order, so every run is identical.
    """

    def __init__(self, clock=None):
        self.clock = clock or Clock()
        self._q = []
        self._seq = 0
        self.tasks = []

    def now(self):
        return self.clock.now()

    def spawn(self, gen, name=None):
        t = Task(self, gen, name or "task-%d" % len(self.tasks))
        self.tasks.append(t)
        self._schedule(t, self.now(), None)
        return t

    def _schedule(self, task, when, value, error=None):
        self._seq += 1
        heapq.heappush(self._q, (when, self._seq, task, value, error))

    def run(self, until=None):
        while self._q:
            when, _, task, value, error = heapq.heappop(self._q)
            if until is not None and when > until:
                heapq.heappush(self._q, (when, 0, task, value, error))
                break
            if when > self.clock.now():
                self.clock.advance(when - self.clock.now())
            self._step(task, value, error)

    def _step(self, task, value, error):
        try:
            y = task.gen.throw(error) if error is not None else task.gen.send(value)
        except StopIteration as s:
            self._finish(task, s.value, None)
            return
        except Exception as e:
            self._finish(task, None, e)
            return
        if y is None:
            self._schedule(task, self.now(), None)
        elif isinstance(y, (int, float)):
            if y < 0:
                self._schedule(task, self.now(), None, ValueError("negative sleep"))
            else:
                self._schedule(task, self.now() + y, None)
        elif isinstance(y, Task):
            if y.done:
                self._schedule(task, self.now(), y.result, y.error)
            else:
                y.waiters.append(task)
        else:
            self._schedule(task, self.now(), None, TypeError("tasks may yield a number, a Task or None, got %r" % (y,)))

    def _finish(self, task, result, error):
        task.done, task.result, task.error = True, result, error
        task.finished_at = self.now()
        for w in task.waiters:
            self._schedule(w, self.now(), result, error)
        task.waiters = []


# ---------------------------------------------------------------- logs

class EventLog:
    """An append-only list of (t, kind, fields) records the judge can grade."""

    def __init__(self, clock=None):
        self.clock = clock
        self.entries = []

    def append(self, kind, **fields):
        e = {"t": self.clock.now() if self.clock else len(self.entries), "kind": kind}
        e.update(fields)
        self.entries.append(e)
        return e

    def kinds(self):
        return [e["kind"] for e in self.entries]
