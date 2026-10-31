TRIP = ["reserve_hotel", "charge_card", "send_confirmation"]


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"saga_id": "trip-4411", "steps": TRIP},
         "explanation": "Every step succeeds: three do calls, status completed. In each crash run the new worker reads the journal and continues; a crash after charge_card returns makes resume call do with the same key 'trip-4411:charge_card', which returns the same booking instead of charging again."},
        {"name": "Example 2", "hidden": False,
         "args": {"saga_id": "trip-4412", "steps": TRIP, "fail_step": "charge_card"},
         "explanation": "The card is declined, so the hotel is cancelled. The failed charge is never undone because it never happened."},
        {"name": "Example 3", "hidden": False,
         "args": {"saga_id": "trip-4413", "steps": TRIP, "fail_step": "send_confirmation", "flaky_undo": {"charge_card": 1}},
         "explanation": "The email provider rejects the send. Compensation runs newest first: the refund hits one 503, sleeps 2**0 = 1 s and succeeds, then the hotel is cancelled."},
        {"name": "stuck refund", "args": {"saga_id": "trip-5001", "steps": TRIP, "fail_step": "send_confirmation",
                                          "flaky_undo": {"charge_card": 5}}},
        {"name": "first step fails", "args": {"saga_id": "trip-5002", "steps": TRIP, "fail_step": "reserve_hotel"}},
        {"name": "five steps late failure", "args": {"saga_id": "trip-5003",
                                                     "steps": ["reserve_flight", "reserve_hotel", "reserve_car", "charge_card", "send_confirmation"],
                                                     "fail_step": "send_confirmation",
                                                     "flaky_undo": {"reserve_car": 2, "reserve_flight": 1}}},
        {"name": "budget exactly enough", "args": {"saga_id": "trip-5004", "steps": TRIP, "fail_step": "send_confirmation",
                                                   "flaky_undo": {"charge_card": 3, "reserve_hotel": 2}, "max_comp_attempts": 4}},
        {"name": "single attempt", "args": {"saga_id": "trip-5005", "steps": TRIP, "fail_step": "send_confirmation",
                                            "flaky_undo": {"reserve_hotel": 1}, "max_comp_attempts": 1}},
        {"name": "one step saga", "args": {"saga_id": "refund-77", "steps": ["issue_refund"]}},
        {"name": "two flaky undos", "args": {"saga_id": "trip-5006", "steps": ["reserve_flight", "reserve_hotel", "charge_card"],
                                             "fail_step": "charge_card", "flaky_undo": {"reserve_hotel": 2, "reserve_flight": 2},
                                             "max_comp_attempts": 2}},
    ]
