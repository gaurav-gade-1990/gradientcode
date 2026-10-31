## Approach

Treat the model's reply as **untrusted text that probably contains JSON**. Run three deterministic passes over it: extract, parse with a narrow repair, and validate. Only if those fail, spend exactly one more model call, and show the model its own mistake.

```python
cand = fence.group(1) if fence else text[text.find("{"): text.rfind("}") + 1]
try:
    obj = json.loads(cand)
except ValueError:
    cand = re.sub(r",\s*([}\]])", r"\1", cand)          # trailing commas
    cand = re.sub(r"'([^'\"]*)'\s*:", r'"\1":', cand)   # 'key': -> "key":
    obj = json.loads(cand)                                # failure -> invalid_json
```

The **last** `}` matters. JSON objects nest, so the first `}` usually closes an inner object such as `"ship_to": {...}`. A fence takes priority because it's the model's explicit statement of where the payload is.

Validation is `isinstance` per type name, with one Python trap: `bool` is a subclass of `int`, so `isinstance(True, int)` is `True`. Exclude bools from `integer` and `number`.

The re-ask is `messages + [assistant: bad reply, user: errors]`. Including the bad reply lets the model fix its own output instead of regenerating from scratch, and the concrete error list (`type:amount_cents; missing:reason`) tells it exactly what to change.

## Common mistakes

- **Retrying until valid.** A loop with no cap turns one confused model into a cost spike and a latency tail. Bound it: here, one re-ask.
- **The first closing brace.** `text[:text.find("}")+1]` truncates any nested object and turns valid JSON into `invalid_json`.
- **`bool` counted as `integer`.** `"amount_cents": true` passes, and you refund 1 cent.
- **Re-asking without the previous reply.** The model sees an error message about a reply it can't see, so it often repeats the same mistake.
- **Mutating the caller's `messages`.** `messages += [...]` leaks the failed exchange into the conversation history the rest of the app stores and replays.
- **Repairing too aggressively.** Swapping every `'` for `"` corrupts values like `"Can't log in"`. Keep repairs narrow and targeted.

## Production notes

- Prefer constrained decoding where you can. OpenAI's `response_format: json_schema` with `strict: true`, Anthropic's structured outputs and tool-use with an `input_schema`, and vLLM's guided decoding (outlines, xgrammar) make most of this repair code unnecessary. Keep a validator anyway, because schemas drift and providers change.
- Libraries like Instructor and Pydantic AI implement this exact loop: they validate with Pydantic, send the validation error back, and cap `max_retries`. Use a full JSON Schema validator (problem 113) instead of this type-name subset.
- Log every repair and re-ask with the prompt version. A rising repair rate is an early regression signal for a prompt change (problem 149).
- Pairs with **streaming tool-call assembly** (problem 115), where malformed JSON is reported rather than repaired, and **retry with backoff** (problem 124), which handles transport errors, not content errors.
