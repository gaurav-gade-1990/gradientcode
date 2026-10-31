SECRET = "whsec_acme_7f3a"
T0 = 1700000000

PAID = {"id": "evt_1001", "type": "invoice.paid", "tenant": "acme", "data": {"invoice": "in_88", "amount": 4200}}
RUN_DONE = {"id": "evt_1002", "type": "agent_run.completed", "tenant": "acme", "data": {"run": "run_51", "tokens": 18234}}
ESCALATED = {"id": "evt_1003", "type": "ticket.escalated", "tenant": "acme", "data": {"ticket": "T-1182", "to": "human"}}

RAW = '{"id": "evt_2001", "type": "invoice.paid",  "data": {"amount": 4200}}'
CANON = '{"data":{"amount":4200},"id":"evt_2001","type":"invoice.paid"}'


def probe(header, now, body=CANON, **kw):
    p = {"header": header, "body": body, "now": now}
    p.update(kw)
    return p


GOOD = "t=%d,v1={sig:%s:%d}" % (T0, SECRET, T0)

PROBES = [
    probe(GOOD, T0 + 10),
    probe(GOOD, T0 + 300),
    probe(GOOD, T0 + 301),
    probe(GOOD, T0 - 301),
    probe(GOOD, T0 - 300),
    probe("t=%d,v1={sig:whsec_old_secret:%d}" % (T0, T0), T0),
    probe("t=%d,v1={sig:whsec_old_secret:%d},v1={sig:%s:%d}" % (T0, T0, SECRET, T0), T0),
    probe("t=%d,v1={sig:%s:%d},v1=%s" % (T0, SECRET, T0, "0" * 64), T0),
    probe("t=%d,v0={sig:%s:%d}" % (T0, SECRET, T0), T0),
    probe("v1={sig:%s:%d}" % (SECRET, T0), T0),
    probe("t=%d,t=%d,v1={sig:%s:%d}" % (T0, T0, SECRET, T0), T0),
    probe("t=17e8,v1={sig:%s:%d}" % (SECRET, T0), T0),
    probe("t=%d, v1={sig:%s:%d}" % (T0, SECRET, T0), T0),
    probe(GOOD, T0, body=CANON.replace("4200", "420000"), signed_body=CANON),
    probe("t=%d,v1={sig:%s:%d}" % (T0 + 5, SECRET, T0), T0),
    probe("t=%d,v1={sig:%s:%d}" % (T0 - 9999, SECRET, T0), T0),
    probe("t=%d,v1={sig:%s:%d}" % (T0, SECRET, T0), T0, body=RAW),
    probe("t=%d,v1={sig:%s:%d},scheme=test,junk" % (T0, SECRET, T0), T0),
    probe("t=%d,v1={sig:%s:%d}" % (T0, SECRET, T0), T0, secret="whsec_other"),
    probe("", T0),
]


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"secret": SECRET, "events": [PAID], "faults": ["503", "ok"],
                  "probes": [probe(GOOD, T0 + 10), probe(GOOD, T0 + 301), probe(GOOD, T0, body=CANON.replace("4200", "420000"), signed_body=CANON)]},
         "explanation": "The endpoint returns 503, so the sender sleeps 60 s and retries with a fresh timestamp and signature; the receiver verifies and processes evt_1001. "
                        "The probes: a valid header 10 s later is ok, 301 s later it is stale, and a body edited in transit fails the signature."},
        {"name": "Example 2", "hidden": False,
         "args": {"secret": SECRET, "events": [RUN_DONE], "faults": ["lost", "ok"],
                  "probes": [probe("t=%d,v1={sig:whsec_old_secret:%d},v1={sig:%s:%d}" % (T0, T0, SECRET, T0), T0)]},
         "explanation": "The receiver processes evt_1002 but the response is lost, so the sender retries. The receiver sees the same event id and returns 200 without processing it again. "
                        "During secret rotation a header carries two v1 signatures; it is valid if either one matches."},
        {"name": "Example 3", "hidden": False,
         "args": {"secret": SECRET, "events": [ESCALATED], "faults": ["503", "503", "503", "ok"]},
         "explanation": "Three failures mean sleeps of 60, 300 and 1800 s. The fourth attempt is 2160 s after the first. It is signed at send time, so it is fresh and accepted."},
        {"name": "all probes", "args": {"secret": SECRET, "probes": PROBES}},
        {"name": "long outage then success", "args": {"secret": SECRET, "events": [PAID], "faults": ["500", "502", "503", "504", "ok"]}},
        {"name": "gives up after the schedule", "args": {"secret": SECRET, "events": [PAID, RUN_DONE], "faults": ["503"] * 5 + ["ok"]}},
        {"name": "endpoint gone", "args": {"secret": SECRET, "events": [PAID, ESCALATED], "faults": ["503", "410", "ok"]}},
        {"name": "lost twice", "args": {"secret": SECRET, "events": [PAID, RUN_DONE, ESCALATED], "faults": ["lost", "lost", "ok", "ok", "lost", "503", "ok"]}},
        {"name": "slow network", "args": {"secret": SECRET, "events": [PAID, RUN_DONE], "faults": ["late:400", "late:299", "ok"]}},
        {"name": "tampered in transit", "args": {"secret": SECRET, "events": [PAID], "faults": ["tamper", "ok"]}},
        {"name": "custom schedule and tolerance", "args": {"secret": "whsec_globex_19", "events": [dict(PAID, tenant="globex"), dict(RUN_DONE, tenant="globex")],
                                                           "faults": ["503", "late:100", "lost", "ok"], "schedule": [5, 50], "tolerance": 60, "start": 1712345678.75}},
        {"name": "same event sent twice by the app", "args": {"secret": SECRET, "events": [PAID, PAID, RUN_DONE], "faults": []}},
        {"name": "tampered resend of a seen id", "args": {"secret": SECRET, "events": [PAID, PAID], "faults": ["ok", "tamper", "ok"]}},
    ]
