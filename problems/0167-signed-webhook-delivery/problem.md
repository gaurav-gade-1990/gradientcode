Your agent platform notifies customers' systems with webhooks: `agent_run.completed`, `invoice.paid`, `ticket.escalated`. Customers need to know a request really came from you and wasn't replayed, and your sender must survive their outages without double-processing. Implement both sides of Stripe-style signed webhooks.

**Signature header.** For a Unix timestamp `t` (an int) and the raw request body `body` (a string):

```
v1  = hex(HMAC-SHA256(key=secret, message=f"{t}.{body}"))      # UTF-8 bytes in
header = f"t={t},v1={v1}"
```

**`sign(secret, timestamp, body)`** returns that header.

**`verify(secret, header, body, now, tolerance=300)`** returns one string, checking in this order:

| # | result | when |
|---|---|---|
| 1 | `"malformed"` | Split `header` on `,`. Items without `=` are ignored; the others split on the first `=` into key and value, with no whitespace stripping. Malformed if there isn't exactly one `t` item, its value isn't all ASCII digits, or there is no `v1` item. Other keys (`v0`, `scheme`, …) are ignored. |
| 2 | `"bad_signature"` | none of the `v1` values equals the expected signature for this `t` and the **raw** `body`. Compare with `hmac.compare_digest`; the judge checks that you do. |
| 3 | `"stale"` | `abs(now - t) > tolerance` |
| 4 | `"ok"` | otherwise |

A header can carry several `v1` values while a customer rotates secrets. It is valid if any one matches.

**`Receiver(secret, tolerance=300)`** is the customer's endpoint. `handle(header, body, now)` returns an HTTP status:
- `400` if `verify(...)` isn't `"ok"`;
- otherwise parse `body` as JSON and read its `"id"`. If this receiver has processed that id before, return `200` without processing it again. Else append the id to `self.processed` and return `200`.

**`deliver(event, secret, send, clock, schedule)`** sends one event and returns `{"status", "attempts"}`.
- `body = json.dumps(event, sort_keys=True, separators=(",", ":"))`.
- Each attempt signs with `t = int(clock.now())` **at the time of that attempt**, then calls `status = send(header, body)`. `status` is an HTTP code, or `0` when no response arrived (timeout, dropped connection).
- `200..299`: return `{"status": "delivered", ...}`. `410`: the customer disabled the endpoint, return `{"status": "disabled", ...}` with no more attempts. Anything else: if attempt number `i` (0-based) is less than `len(schedule)`, call `clock.sleep(schedule[i])` and try again; otherwise return `{"status": "failed", ...}`.
- `attempts` is the number of `send` calls made.

The judge wires your `deliver` to your `Receiver` through a faulty network that can return 5xx, drop the response after the receiver processed it, deliver late, or alter the body in transit. It grades every attempt (event, send time, status), the final statuses, `processed`, a set of `verify` probes, and whether `hmac.compare_digest` was used.

**Constraints**

- `0 <= len(schedule) <= 6`, schedule entries are positive seconds.
- Secrets and bodies are ASCII. Timestamps fit in an int.
- Use `clock` for time; don't import `time`.
