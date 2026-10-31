## 1. What the problem is really asking

Your platform tells customers' systems about events (`invoice.paid`, `agent_run.completed`) by POSTing to their webhook URL. The customer needs two guarantees: the request really came from you, and it isn't an old request being replayed. You need a third: if their endpoint is down, you keep trying without making them process the event twice.

You're writing four small pieces, and each one is a well-known pattern:

| piece | pattern |
|---|---|
| `sign` | an HMAC over `"{t}.{body}"`, so the timestamp and body are bound together |
| `verify` | parse a header, constant-time compare, then a time window in both directions |
| `Receiver.handle` | an idempotent consumer: remember event ids, answer 200 to repeats |
| `deliver` | a retry loop over a fixed schedule, **signing fresh on every attempt** |

The judge connects your `deliver` to your `Receiver` through a fake network that can return 5xx, lose the response after the receiver processed it, add delay, or alter the body. It grades every attempt (event, send time, status), each delivery's final status, the receiver's `processed` list, the results of a set of `verify` probes, and whether `hmac.compare_digest` was called at all.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `secret` | the shared signing key, like `"whsec_acme_7f3a"` | the HMAC key, UTF-8 encoded |
| `timestamp` / `t` | integer Unix seconds | the first half of the signed message |
| `body` | the **raw** request body string | the second half; never re-serialize it |
| `header` | `"t=...,v1=..."`, maybe with extra items | parsed by `verify` |
| `now`, `tolerance` | the receiver's clock and the allowed skew (300 s by default) | `abs(now - t) > tolerance` is stale |
| `send(header, body)` | the network; returns an HTTP code, or `0` for no response | one call per attempt |
| `clock` | virtual time: `now()` and `sleep(s)` | signing time and backoff |
| `schedule` | sleeps between attempts, e.g. `[60, 300, 1800, 7200]` | `len(schedule) + 1` attempts at most |

Three details are easy to miss:

- **`clock.now()` can be fractional.** "custom schedule and tolerance" starts at `1712345678.75`. The spec says `t = int(clock.now())`, and the signed message must use that integer.
- **The header parser does no whitespace stripping.** `"t=1700000000, v1=..."` has a key `" v1"`, which is not `"v1"`, so the header has no `v1` and is `"malformed"`.
- **The checks run in a fixed order: malformed, then signature, then staleness.** A header with a bad signature *and* an old timestamp is `"bad_signature"`, not `"stale"`.

## 3. Trace Example 1 by hand

One event, `PAID`. The network's faults are `["503", "ok"]`, and the clock starts at `1700000000`.

**The body.** `json.dumps(event, sort_keys=True, separators=(",", ":"))` gives:

```
{"data":{"amount":4200,"invoice":"in_88"},"id":"evt_1001","tenant":"acme","type":"invoice.paid"}
```

**Attempt 1 at t = 1700000000.** Sign and send:

```
t=1700000000,v1=4e8e1b8f25338b21d1d98620f9d395775465778e810d5b194498d44626f18143
```

The network returns `503` without reaching the receiver. That's neither 2xx nor 410, and attempt 0 is less than `len(schedule) = 4`, so you `clock.sleep(60)`.

**Attempt 2 at t = 1700000060.** Sign again with the new time. The header changes completely:

```
t=1700000060,v1=0592f5f3372179da01684927e266ced502129e591b7167c20f51190d8d2e1146
```

The receiver verifies it (`abs(now - t) = 0`), sees `evt_1001` for the first time, processes it and returns `200`. Result: `{"status": "delivered", "attempts": 2}`, and `processed` is `['evt_1001']`.

**The three probes.** A valid header checked 10 s after `t` is `"ok"`. The same header 301 s later is `"stale"`. A header signed over the body with `4200` but checked against a body with `420000` is `"bad_signature"`.

**The trickiest hidden case, "custom schedule and tolerance".** Secret `whsec_globex_19`, schedule `[5, 50]`, tolerance 60, start `1712345678.75`, faults `["503", "late:100", "lost", "ok"]`.

| attempt | signed `t` | what happens | status |
|---|---|---|---|
| 1 | 1712345678 | 503 | 503, sleep 5 |
| 2 | 1712345683 | arrives 100 s late, `abs(now - t) > 60` | 400, sleep 50 |
| 3 | 1712345833 | the receiver processes `evt_1001`, but the response is lost | 0 |

That was attempt index 2, and `2 < len(schedule)` is false, so `evt_1001` is `"failed"` after 3 attempts, even though the receiver did process it. `evt_1002` then goes through in one attempt at `1712345833`. Both ids end up in `processed`. "Failed" from the sender's side means "I never got a 2xx", not "it never arrived". That's exactly why the receiver must dedupe.

## 4. Key idea: sign inside the retry loop

The schedule is 60 s, 5 min, 30 min, 2 h. The tolerance is 5 minutes. A signature made once, before the loop, is fine for the first two attempts and stale after that.

Example 3 shows it. Three 503s, then the endpoint is healthy:

| attempt | send time | sign once (wrong) | sign per attempt |
|---|---|---|---|
| 1 | 1700000000 | 503 | 503 |
| 2 | 1700000060 | 503 | 503 |
| 3 | 1700000360 | 503 | 503 |
| 4 | 1700002160 | `t` is 2160 s old: 400 | fresh: 200 |

With the signature reused, attempts 4 and 5 both get 400 and the event is `"failed"` after 5 attempts. A short customer outage becomes a permanently lost event. With a fresh signature, attempt 4 is accepted. Moving one line into the loop is the whole fix.

## 5. Key idea: why each verify rule exists

Each rule in `verify` blocks a specific attack or outage. The "all probes" case runs 20 headers through it:

| probe | result | the rule it tests |
|---|---|---|
| valid, `now = t + 300` / `t - 300` | ok | the window is inclusive |
| valid, `now = t + 301` / `t - 301` | stale | the window applies in **both** directions |
| only the old secret's `v1` | bad_signature | the key matters |
| old `v1` then current `v1` | ok | any `v1` may match (secret rotation) |
| current `v1` then 64 zeros | ok | a bad extra `v1` doesn't hurt |
| only `v0` | malformed | other keys are ignored, so there's no `v1` |
| no `t`, two `t`s, `t=17e8` | malformed | exactly one all-digit `t` |
| `t=...,` then ` v1=...` (a space) | malformed | no whitespace stripping |
| body changed after signing | bad_signature | the body is signed |
| header `t` is `T0 + 5`, signature over `T0` | bad_signature | the timestamp is signed |
| header `t` is `T0 - 9999`, signature over `T0` | bad_signature | the signature check runs before staleness |
| raw body with extra spaces, signed as sent | ok | verify the raw bytes |
| extra `scheme=test` and a bare `junk` | ok | unknown keys and items with no `=` are ignored |
| wrong secret | bad_signature | |
| empty header | malformed | |

Two of these deserve a sentence. **Future timestamps.** If you only check `now - t > tolerance`, a timestamp far in the future passes forever, and a captured request can be replayed indefinitely. `abs` closes it. **Constant time.** `==` on strings returns at the first differing byte, which leaks how many leading bytes were right. Over many requests an attacker can learn a valid signature byte by byte. `hmac.compare_digest` takes the same time either way, and the judge checks that you call it.

## 6. Plan before you code

```
sign: hex HMAC-SHA256(secret, "{t}.{body}") -> "t={t},v1={hex}"

verify:
    collect t values and v1 values from "k=v" items (split on first "=", no strip)
    exactly one t, all ASCII digits, at least one v1?   else "malformed"
    expected = HMAC over "{t}.{raw body}"
    any v1 matches with compare_digest?               else "bad_signature"
    abs(now - t) <= tolerance?                         else "stale"
    "ok"

Receiver.handle:
    verify != ok -> 400
    id seen -> 200 (do nothing)
    remember id, append to processed -> 200

deliver:
    body = canonical JSON
    for attempt in 0 .. len(schedule):
        sign with int(clock.now()), send
        2xx -> delivered; 410 -> disabled
        attempt < len(schedule) -> sleep(schedule[attempt])
    failed
```

## 7. Build it one piece at a time

**Step 1: sign.** `"%d.%s"` both formats the message and guarantees `t` is printed as an integer:

```python
def sign(secret, timestamp, body):
    mac = hmac.new(secret.encode(), ("%d.%s" % (timestamp, body)).encode(), hashlib.sha256).hexdigest()
    return "t=%d,v1=%s" % (timestamp, mac)
```

**Step 2: parse the header.** Collect lists instead of a dict, so you can tell "two `t` items" apart from one, and keep every `v1`:

```python
    ts, sigs = [], []
    for item in header.split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        if key == "t":
            ts.append(value)
        elif key == "v1":
            sigs.append(value)
    if len(ts) != 1 or not re.fullmatch(r"[0-9]+", ts[0]) or not sigs:
        return "malformed"
```

`split("=", 1)` matters because a value could contain `=`. `re.fullmatch(r"[0-9]+", ...)` rejects `17e8`, `-5` and the empty string. Don't use `int()` in a `try`: `int(" 17")` and `int("+17")` both succeed.

**Step 3: signature, then time.** Compute the expected signature for the header's `t` and the body exactly as received:

```python
    expected = hmac.new(secret.encode(), ("%d.%s" % (t, body)).encode(), hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected.encode(), s.encode()) for s in sigs):
        return "bad_signature"
    if abs(now - t) > tolerance:
        return "stale"
```

**Step 4: the receiver.** Verify first, then dedupe. A set gives O(1) lookups, and `processed` keeps the order the judge compares. Note that a 400 doesn't mark the id as seen: in "tampered in transit" the altered first attempt gets 400, and the clean retry is processed normally.

**Step 5: deliver.** `range(len(schedule) + 1)` is the attempt budget. The sleep happens only when another attempt follows, so a failing event doesn't push the clock forward for the next one. In "gives up after the schedule", `evt_1001` fails after 5 attempts and `evt_1002` is sent at `1700009360`, the same time as `evt_1001`'s last attempt.

## 8. Full solution

```python
import hashlib  # SHA-256 for the HMAC
import hmac  # HMAC and the constant-time compare_digest
import json  # canonical body on the sender, event id on the receiver
import re  # strict all-digits check for the timestamp


def sign(secret, timestamp, body):  # the header the sender attaches to one attempt
    # HMAC binds the timestamp to the body, so neither can be changed alone
    mac = hmac.new(secret.encode(), ("%d.%s" % (timestamp, body)).encode(), hashlib.sha256).hexdigest()
    return "t=%d,v1=%s" % (timestamp, mac)  # Stripe-style header


def verify(secret, header, body, now, tolerance=300):  # malformed, then signature, then staleness
    ts, sigs = [], []  # lists, so duplicate t items and several v1 items are visible
    for item in header.split(","):  # header items are comma-separated
        if "=" not in item:  # bare items like "junk" carry no key
            continue  # ignore them
        key, value = item.split("=", 1)  # split on the first "=" only, with no whitespace stripping
        if key == "t":  # the timestamp item
            ts.append(value)  # keep it to count and validate later
        elif key == "v1":  # one signature; rotation can send several
            sigs.append(value)  # any of them may match
    if len(ts) != 1 or not re.fullmatch(r"[0-9]+", ts[0]) or not sigs:  # exactly one numeric t, at least one v1
        return "malformed"  # the header can't even be checked
    t = int(ts[0])  # safe now that it's all digits
    # what the signature must be for this t and the raw body we received
    expected = hmac.new(secret.encode(), ("%d.%s" % (t, body)).encode(), hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected.encode(), s.encode()) for s in sigs):  # constant time, any v1 may match
        return "bad_signature"  # forged, tampered, or signed with another secret
    if abs(now - t) > tolerance:  # too old or too far in the future
        return "stale"  # a replay, or a badly skewed clock
    return "ok"  # authentic and fresh


class Receiver:  # the customer's webhook endpoint
    def __init__(self, secret, tolerance=300):  # one receiver per endpoint
        self.secret = secret  # the shared signing key
        self.tolerance = tolerance  # allowed clock skew in seconds
        self.processed = []  # event ids processed, in order, which the judge reads
        self._seen = set()  # fast lookup for the same ids

    def handle(self, header, body, now):  # returns an HTTP status code
        if verify(self.secret, header, body, now, self.tolerance) != "ok":  # authenticate before anything else
            return 400  # reject; the id is not marked seen, so a clean retry still works
        event_id = json.loads(body)["id"]  # the idempotency key
        if event_id in self._seen:  # a retry after a lost response, or a resend by the app
            return 200  # acknowledge it so the sender stops, but don't process it twice
        self._seen.add(event_id)  # remember it for future duplicates
        self.processed.append(event_id)  # "process" the event
        return 200  # success


def deliver(event, secret, send, clock, schedule):  # send one event with retries
    body = json.dumps(event, sort_keys=True, separators=(",", ":"))  # one canonical body for every attempt
    for attempt in range(len(schedule) + 1):  # the first try plus one retry per schedule entry
        header = sign(secret, int(clock.now()), body)  # sign fresh, so a late retry isn't stale
        status = send(header, body)  # one network call; 0 means no response arrived
        if 200 <= status < 300:  # the receiver accepted it
            return {"status": "delivered", "attempts": attempt + 1}  # done
        if status == 410:  # the customer disabled the endpoint
            return {"status": "disabled", "attempts": attempt + 1}  # never retry a 410
        if attempt < len(schedule):  # another attempt is allowed
            clock.sleep(schedule[attempt])  # back off before it
    return {"status": "failed", "attempts": len(schedule) + 1}  # the schedule ran out without a 2xx
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | delivered in 2; attempts at `T0` and `T0 + 60`; probes ok, stale, bad_signature | a retry after 503, the window, the signed body |
| Example 2 | delivered in 2, `processed: ['evt_1002']` | a lost response is retried and deduped; rotation probe is ok |
| Example 3 | delivered on attempt 4 at `1700002160` | signing per attempt |
| all probes | 20 results, from `ok` to `malformed` | every rule of `verify` (section 5) |
| long outage then success | delivered in 5, last at `1700009360` | the whole schedule, 60 + 300 + 1800 + 7200 |
| gives up after the schedule | `evt_1001` failed in 5, `evt_1002` delivered at `1700009360` | the attempt budget, and no sleep after the last attempt |
| endpoint gone | `evt_1001` disabled in 2, `evt_1003` delivered | stop on 410 |
| lost twice | all three delivered, `processed` has each id once | dedupe across several lost responses |
| slow network | first attempt 400 (arrived 400 s late), retry 200 at 299 s late | the receiver's staleness check; 299 is inside the window |
| tampered in transit | 400, then 200 | a body changed in transit fails the signature |
| custom schedule and tolerance | `evt_1001` failed in 3 but processed | a fractional clock, `int(clock.now())`, custom schedule and tolerance |
| same event sent twice by the app | both sends 200, `processed: ['evt_1001', 'evt_1002']` | dedupe isn't only for retries |
| tampered resend of a seen id | second send 400 then 200 at `1700000060`, `processed: ['evt_1001']` | verify runs before the dedupe lookup |

## 10. Complexity

`sign` and `verify` are O(b + h) for a body of b bytes and a header of h bytes, with one HMAC per call. `handle` adds a JSON parse and an O(1) set lookup. `deliver` makes at most `len(schedule) + 1` sends. All of it is trivially cheap.

What matters in production is outside the function. The receiver's seen-id set grows forever unless you expire ids after the sender's maximum retry window (a few days). The sender should persist its attempt log and send from an outbox, so an event committed in the database is never lost before its first attempt (problem 172, transactional-outbox). Real schedules add jitter (problem 124, retry-with-backoff) so thousands of retries don't hit a recovering endpoint at the same second.

## 11. If you got Wrong Answer

- **`compare_digest_used` is `False` on every case.** You compared with `==` or `in`. Use `hmac.compare_digest`.
- **Example 3 ends `"failed"` after 5 attempts, with 400 on attempts 4 and 5.** You signed once before the loop. Sign inside it.
- **Example 2's `processed` is `['evt_1002', 'evt_1002']`.** The receiver doesn't dedupe. "lost twice" and "same event sent twice by the app" fail for the same reason.
- **"endpoint gone" shows a third attempt for `evt_1001`.** You retried a 410. Return `"disabled"` right away.
- **"all probes": the 4th result (`now = t - 301`) is `ok`.** You checked `now - t > tolerance` without `abs`.
- **"all probes": the 7th result (old secret, then current) is `bad_signature`.** You checked only the first `v1`. Example 2's probe fails too.
- **"all probes": the 17th result (the raw body with extra spaces) is `bad_signature`.** You re-serialized the body before verifying. Verify the string you received.
- **"all probes": the 16th result is `stale` instead of `bad_signature`.** You checked the time before the signature.
- **"all probes": the 13th result (a space before `v1`) is `ok`.** You stripped whitespace from keys. The spec says not to.
- **"gives up after the schedule" sends `evt_1002` too late.** You slept after the final attempt.
- **"tampered resend of a seen id": the tampered attempt gets 200.** You looked up the event id before verifying. A forged request with a known id must still get 400, so verify first.

## 12. Follow-ups an interviewer might ask

- *Why put the timestamp inside the signature instead of just sending it?* An unsigned timestamp can be changed to "now" by whoever captured the request, which defeats the window. Signing `"{t}.{body}"` binds them.
- *How does secret rotation work end to end?* For a while the sender signs with both the old and new secret and sends two `v1` values. Receivers that have either secret verify. Once every customer has moved over, the old one is dropped.
- *Why does the receiver return 200 for a duplicate instead of 409?* Any non-2xx makes the sender retry. A duplicate means the work is already done, so the right answer is "success, stop sending".
- *What's the standard beyond Stripe?* The Standard Webhooks spec (used by Svix, Clerk and others) has the same design with `webhook-id`, `webhook-timestamp` and `webhook-signature` headers, and it signs the id as well.
- *How should the receiver handle slow work?* Verify, dedupe and enqueue, then return 2xx immediately. A slow handler causes sender timeouts, and timeouts cause duplicates. This is the same idempotency idea as problem 119 (idempotent-tool-execution).
