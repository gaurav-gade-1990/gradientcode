import base64
import json

import numpy as np


def cur(created_at, id):
    return base64.urlsafe_b64encode(json.dumps([created_at, id], separators=(",", ":")).encode()).decode()


def raw(obj):
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode()


def conv(i, t, title):
    return {"id": "conv_%04d" % i, "created_at": t, "title": title}


SIDEBAR = [
    conv(1, 1730000000, "Refund for order 1182"),
    conv(2, 1730000300, "Draft Q3 board memo"),
    conv(3, 1730000600, "Debug flaky CI job"),
    conv(4, 1730000900, "Summarize vendor contract"),
    conv(5, 1730001200, "Plan Austin offsite"),
]

TIES = [
    conv(10, 1730005000, "Import: ticket 1"),
    conv(11, 1730005000, "Import: ticket 2"),
    conv(12, 1730005000, "Import: ticket 3"),
    conv(9, 1730004000, "Older chat"),
]


def big_table():
    rng = np.random.default_rng(170)
    times = 1730000000 + rng.integers(0, 40, size=120) * 60
    order = rng.permutation(120)
    return [conv(int(i) + 100, int(times[i]), "chat %d" % i) for i in order]


def walk(direction, n, limit):
    return [{"op": "page", "limit": limit, "follow": direction} for _ in range(n)]


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"table": SIDEBAR, "ops": [{"op": "page", "limit": 2}] + walk("next", 2, 2)},
         "explanation": "Newest first: conv_0005, conv_0004 | conv_0003, conv_0002 | conv_0001. Each next_cursor is the "
                        "last item's [created_at, id] in base64. The last page has nothing older, so next_cursor is None. "
                        "Every page after the first has a prev_cursor."},
        {"name": "Example 2", "hidden": False,
         "args": {"table": SIDEBAR, "ops": [{"op": "page", "limit": 2},
                                            {"op": "insert", "row": conv(6, 1730001500, "New: rotate API keys")},
                                            {"op": "page", "limit": 2, "follow": "next"},
                                            {"op": "page", "limit": 2, "follow": "prev"}]},
         "explanation": "A new conversation appears while the user scrolls. An offset cursor would repeat conv_0004. The "
                        "keyset cursor continues after conv_0004 at conv_0003. Going back returns the two rows just above "
                        "conv_0003 (conv_0005, conv_0004), and that page's prev_cursor is set because conv_0006 is newer."},
        {"name": "Example 3", "hidden": False,
         "args": {"table": TIES, "ops": [{"op": "page", "limit": 2}, {"op": "page", "limit": 2, "follow": "next"}]},
         "explanation": "Three conversations were imported in the same second. Ties order by id descending, and the "
                        "cursor holds (created_at, id), so conv_0010 is not skipped on the second page."},
        {"name": "exact multiple: last full page has no next",
         "args": {"table": SIDEBAR[:4], "ops": [{"op": "page", "limit": 2}] + walk("next", 1, 2)}},
        {"name": "limit larger than table", "args": {"table": SIDEBAR, "ops": [{"op": "page", "limit": 50}]}},
        {"name": "empty table", "args": {"table": [], "ops": [{"op": "page", "limit": 10}]}},
        {"name": "before-page takes rows closest to cursor",
         "args": {"table": SIDEBAR, "ops": [{"op": "page", "limit": 2, "before": cur(1730000000, "conv_0001")},
                                            {"op": "page", "limit": 2, "follow": "prev"}]}},
        {"name": "before the newest row is empty",
         "args": {"table": SIDEBAR, "ops": [{"op": "page", "limit": 3, "before": cur(1730001200, "conv_0005")}]}},
        {"name": "cursor of a deleted row still works",
         "args": {"table": SIDEBAR, "ops": [{"op": "page", "limit": 2}, {"op": "delete", "id": "conv_0004"},
                                            {"op": "delete", "id": "conv_0003"},
                                            {"op": "page", "limit": 2, "follow": "next"},
                                            {"op": "page", "limit": 2, "follow": "prev"}]}},
        {"name": "ties straddling every boundary",
         "args": {"table": TIES + [conv(13, 1730005000, "Import: ticket 4"), conv(8, 1730004000, "Old 2")],
                  "ops": [{"op": "page", "limit": 1}] + walk("next", 5, 1) + walk("prev", 5, 1)}},
        {"name": "insert with a tied timestamp mid-scroll",
         "args": {"table": TIES, "ops": [{"op": "page", "limit": 2},
                                         {"op": "insert", "row": conv(15, 1730005000, "Import: late ticket")},
                                         {"op": "insert", "row": conv(7, 1730005000, "Import: low id")},
                                         {"op": "page", "limit": 2, "follow": "next"},
                                         {"op": "page", "limit": 2, "follow": "next"},
                                         {"op": "page", "limit": 3, "follow": "prev"}]}},
        {"name": "invalid cursors are 400",
         "args": {"table": SIDEBAR, "ops": [
             {"op": "page", "limit": 2, "after": "not base64!!"},
             {"op": "page", "limit": 2, "after": raw({"offset": 2})},
             {"op": "page", "limit": 2, "after": raw([True, "conv_0003"])},
             {"op": "page", "limit": 2, "before": raw(["1730000600", "conv_0003"])},
             {"op": "page", "limit": 2, "after": raw([1730000600])},
             {"op": "page", "limit": 2, "after": base64.urlsafe_b64encode(b"[1730000600, conv_0003]").decode()},
             {"op": "page", "limit": 2, "after": cur(1730000600, "conv_0003"), "before": cur(1730001200, "conv_0005")},
             {"op": "page", "limit": 2, "after": cur(1730000600, "conv_0003")}]}},
        {"name": "big table walk forward then back",
         "args": {"table": big_table(), "ops": [{"op": "page", "limit": 7}] + walk("next", 17, 7) + walk("prev", 17, 7)}},
        {"name": "big table with inserts while scrolling",
         "args": {"table": big_table(), "ops": [{"op": "page", "limit": 9}] + walk("next", 3, 9)
                  + [{"op": "insert", "row": conv(900 + k, 1730000000 + 60 * (k * 7 % 40), "late %d" % k)} for k in range(12)]
                  + walk("next", 11, 9) + walk("prev", 4, 9)}},
    ]
