def P(dev, mid, text, show=False):
    op = {"device": dev, "put": [mid, text]}
    if show:
        op["show"] = True
    return op


def D(dev, mid, show=False):
    op = {"device": dev, "delete": mid}
    if show:
        op["show"] = True
    return op


def S(dev, src, show=False):
    op = {"device": dev, "sync_from": src}
    if show:
        op["show"] = True
    return op


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"devices": ["laptop", "phone"],
                  "ops": [P("phone", "m1", "Can you move my 3pm with Dana?"),
                          S("laptop", "phone", True),
                          P("laptop", "m1", "Can you move my 3pm with Dana to 4pm?", True),
                          S("phone", "laptop", True)]},
         "explanation": "The phone writes m1 at [1, phone]. The laptop syncs, so its clock rises to 1, and its edit is stamped [2, laptop], which beats [1, phone]. After the phone syncs back, both show the edited text, and created stays [1, phone]."},
        {"name": "Example 2", "hidden": False,
         "args": {"devices": ["laptop", "phone"],
                  "ops": [P("phone", "m1", "Order 1182 arrived damaged"),
                          P("laptop", "m1", "Order 1182 never arrived"),
                          S("phone", "laptop", True), S("laptop", "phone", True)]},
         "explanation": "Both edits are stamped with lamport 1 while offline. The tie goes to the larger device id, and 'phone' > 'laptop', so both devices keep the phone's text. Neither device prefers its own copy."},
        {"name": "Example 3", "hidden": False,
         "args": {"devices": ["laptop", "phone"],
                  "ops": [P("phone", "m1", "My card ending 4242 was charged twice"),
                          P("phone", "m2", "Ignore that, wrong account"),
                          S("laptop", "phone"), D("laptop", "m1", True),
                          S("phone", "laptop", True), S("laptop", "phone", True)]},
         "explanation": "The laptop deletes m1 with stamp [3, laptop], leaving a tombstone. The phone's copy [1, phone] is older, so the delete wins on both devices, and syncing the phone's state back does not resurrect m1."},
        {"name": "lamport lag", "args": {"devices": ["laptop", "phone"],
                                         "ops": [P("phone", "m%d" % i, "draft %d" % i) for i in range(1, 6)]
                                         + [S("laptop", "phone"), P("laptop", "m3", "final wording", True),
                                            S("phone", "laptop", True)]}},
        {"name": "edit after delete resurrects", "args": {"devices": ["phone", "tablet"],
                                                          "ops": [P("tablet", "m1", "Refund request for order 77"),
                                                                  S("phone", "tablet"), D("tablet", "m1"),
                                                                  P("phone", "m1", "Refund request for order 77, urgent"),
                                                                  P("phone", "m1", "Refund request for order 77, very urgent"),
                                                                  S("tablet", "phone", True), S("phone", "tablet", True)]}},
        {"name": "concurrent delete vs edit tie", "args": {"devices": ["laptop", "phone"],
                                                           "ops": [P("laptop", "m1", "Ship to 12 Elm St"),
                                                                   S("phone", "laptop"),
                                                                   D("phone", "m1"), P("laptop", "m1", "Ship to 14 Elm St"),
                                                                   S("laptop", "phone", True), S("phone", "laptop", True)]}},
        {"name": "three devices ordering", "args": {"devices": ["laptop", "phone", "tablet"],
                                                    "ops": [P("tablet", "t1", "Hi, I need help with SSO"),
                                                            P("laptop", "l1", "Also my invoice is wrong"),
                                                            P("phone", "p1", "Ticket 5521"),
                                                            S("laptop", "tablet"), P("laptop", "l2", "Invoice INV-9", True),
                                                            S("phone", "laptop", True), D("phone", "t1", True),
                                                            S("tablet", "phone", True)]}},
        {"name": "four devices concurrent", "args": {"devices": ["desk", "laptop", "phone", "tablet"],
                                                     "ops": [P("desk", "m1", "a"), P("laptop", "m1", "b"),
                                                             P("phone", "m1", "c"), P("tablet", "m1", "d"),
                                                             D("desk", "m2"), P("phone", "m2", "late"),
                                                             S("desk", "tablet", True), S("laptop", "desk", True),
                                                             P("laptop", "m1", "b2", True)]}},
        {"name": "delete unknown then merge", "args": {"devices": ["laptop", "phone"],
                                                       "ops": [D("laptop", "m9", True), P("phone", "m9", "hello"),
                                                               S("laptop", "phone", True), S("phone", "laptop", True)]}},
        {"name": "stale sync after delete", "args": {"devices": ["laptop", "phone", "tablet"],
                                                     "ops": [P("phone", "m1", "Card 4242"), S("laptop", "phone"),
                                                             S("tablet", "phone"), D("laptop", "m1"),
                                                             S("phone", "laptop", True), S("laptop", "tablet", True),
                                                             S("tablet", "laptop", True)]}},
    ]
