STOP = ["a", "an", "the", "is", "are", "of", "for", "to", "up", "at", "per", "you", "your", "can", "and", "or",
        "in", "on", "with", "be", "must", "within", "it", "this", "that", "i", "we", "as", "by", "see", "do", "if",
        "thanks", "hope", "helps", "happy", "help"]

PTO = ("Employees accrue 1.5 days of paid time off per month, up to a maximum balance of 30 days. "
       "Unused PTO above the cap is forfeited on January 1.")
PARENTAL = ("Parental leave is 16 weeks at full pay for birthing and non-birthing parents. "
            "Leave must start within 12 months of the birth or adoption.")
REMOTE = ("Remote work outside the home country is allowed for up to 30 days per calendar year with manager approval. "
          "Longer stays require a tax review by People Ops.")
EXPENSES = ("Expense reports must be submitted within 60 days of purchase. "
            "Meals are reimbursed up to $75 per day while travelling.")
POLICIES = [PTO, PARENTAL, REMOTE, EXPENSES]


def case(answer, passages=POLICIES, tau=0.6):
    return {"answer": answer, "passages": passages, "stopwords": STOP, "tau": tau}


def cases():
    return [
        {"name": "Example 1", "hidden": False,
         "args": case("You accrue 1.5 days of PTO per month [1]. The balance is capped at 30 days [1]. "
                      "Parental leave is 16 weeks at full pay [2]."),
         "explanation": "Sentence 0's claim set is {accrue, 1, 5, days, pto, month}; all 6 are in passage 1, overlap 1.0. Sentence 1 is "
                        "{balance, capped, 30, days}; 'capped' is not in the passage (it says 'cap'), so 3/4 = 0.75, still >= 0.6. "
                        "Sentence 2 is fully in passage 2. Every sentence is supported."},
        {"name": "Example 2", "hidden": False,
         "args": case("Parental leave is 26 weeks for all parents [2]. You can work remotely abroad for 90 days without approval [3]. "
                      "Meals are reimbursed up to $75 per day [4][7]. Contact People Ops for exceptions. Thanks!"),
         "explanation": "Sentence 0 changed 16 to 26 and added 'all': {parental, leave, 26, weeks, all, parents} has 4/6 = 0.67 in passage 2, so it "
                        "passes. Token overlap cannot see a wrong number; that is the known limit of this check. Sentence 1 shares only work, days "
                        "and approval with passage 3: 3/7, unsupported. Sentence 2 is supported by [4]; [7] does not exist (out_of_range). "
                        "Sentence 3 makes a claim with no citation (missing). 'Thanks!' is all stopwords, so it is no_claim and not graded: rate 2/4."},
        {"name": "Example 3", "hidden": False,
         "args": case("Unused PTO is forfeited on January 1. [1] Remote stays longer than 30 days need a tax review [3]."),
         "explanation": "The model put [1] after the period. The splitter breaks on the space after '1.', so sentence 0 has no citation "
                        "(missing), and '[1]' lands at the start of sentence 1, which now cites [1] and [3]. Its 9 claim tokens share 2 with "
                        "passage 1 (unsupported) and 7 with passage 3 (supported), so the sentence is supported."},
        {"name": "citation zero is out of range",
         "args": case("Meals are reimbursed up to $75 per day [0]. Expense reports are due within 60 days of purchase [4].")},
        {"name": "lowercase acronym from the model",
         "args": case("Unused pto above the cap is forfeited on january 1 [1].", tau=0.9)},
        {"name": "repeated words do not count twice",
         "args": case("Remote work and remote travel need manager approval [3].", tau=0.7)},
        {"name": "supported by a passage it did not cite",
         "args": case("Parental leave is 16 weeks at full pay [1]. Expense reports must be submitted within 60 days [3].")},
        {"name": "duplicate and mixed citations",
         "args": case("Leave must start within 12 months of the birth [1][2][2]. Meals are reimbursed while travelling [4][1].")},
        {"name": "overlap exactly at tau",
         "args": case("Expense reports go to finance [4]. Remote approval comes from HR [3].", tau=0.5)},
        {"name": "no passages retrieved",
         "args": case("You accrue 1.5 days of PTO per month [1]. Is that right?", passages=[])},
        {"name": "only pleasantries",
         "args": case("Thanks! Hope this helps.")},
        {"name": "questions and exclamations split",
         "args": case("Can I work from Lisbon for 30 days? Yes, with manager approval [3]! Longer stays require a tax review [3].")},
    ]
