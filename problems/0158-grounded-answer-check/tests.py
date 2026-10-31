REFUND = ("Refund Policy (rev. 2026-03)\n"
          "Customers on annual plans may request a prorated refund within 30 days of renewal. "
          "Refunds are issued to the original payment method within 5–7 business days.")
TICKET = ("INC-48213: Northwind Traders reports an SSO login loop after rotating the SAML signing certificate. "
          "Workaround: upload the new certificate under Settings > SSO > Certificates.")
# Extracted from a PDF: hard line wraps, a non-breaking space and a curly apostrophe.
EXPENSE_PDF = ("Expense Policy\n\nSubmit receipts in Expensify within\n30 days of the purchase. Meals with\nclients are capped at $75 per person.\n"
               "Alcohol isn’t reimbursed unless a client is present.")
SOURCES = [REFUND, TICKET]


def cases():
    good = ('Annual customers can get "a prorated refund within 30 days of renewal" [1]. '
            'The money goes back "to the original payment method" [1].')
    mixed = ('Annual customers can get "a prorated refund within 30 days of renewal" [1]. '
             'Refunds usually arrive in about a week [1]. '
             'You can also get store credit instead.')
    repaired = ('Annual customers can get “a prorated refund within 30 days of renewal” [1]. '
                'Refunds arrive “within 5-7 business days” [1].')
    return [
        {"name": "Example 1", "hidden": False,
         "args": {"answer": good, "sources": SOURCES, "min_groundedness": 0.8, "script": []},
         "explanation": "Both sentences cite [1] and quote it word for word, so groundedness is 1.0 and the model is never called."},
        {"name": "Example 2", "hidden": False,
         "args": {"answer": mixed, "sources": SOURCES, "min_groundedness": 0.8, "script": [{"content": repaired}]},
         "explanation": "Only the first of three sentences is supported (0.33 < 0.80): the second cites [1] with no quote, and the third cites nothing. "
                        "The repair prompt lists both failures and the sources. The rewrite uses curly quotes and an ASCII hyphen where the source has an en dash. "
                        "After normalization both quotes match [1], so the answer is repaired."},
        {"name": "Example 3", "hidden": False,
         "args": {"answer": 'Upload the new certificate "under Settings > SSO > Certificates" [1].', "sources": SOURCES, "min_groundedness": 1.0,
                  "script": [{"content": 'Upload it "under Settings > SSO > Certificates" [2]. This fixes it permanently [2].'}]},
         "explanation": "The quote is real, but it is in source [2], not the cited [1], so it is unsupported. The rewrite cites [2] correctly, "
                        "but its second sentence has no quote, so 0.5 < 1.0 and the answer is rejected."},
        {"name": "pdf line wraps and nbsp", "args": {"answer": 'Submit receipts "within 30 days of the purchase" [1]. Client meals are "capped at $75 per person" [1]. '
                                                               'Alcohol "isn\'t reimbursed unless a client is present" [1].',
                                                     "sources": [EXPENSE_PDF], "min_groundedness": 1.0, "script": []}},
        {"name": "out of range citation", "args": {"answer": 'Refunds are prorated "within 30 days of renewal" [1][3]. See the ticket [2].',
                                                   "sources": SOURCES, "min_groundedness": 0.5, "script": [{"content": ""}]}},
        {"name": "misattributed quote", "args": {"answer": 'Northwind reports "an SSO login loop" [1]. Refunds take "5-7 business days" [1].',
                                                 "sources": SOURCES, "min_groundedness": 0.5, "script": []}},
        {"name": "multi-source sentence", "args": {"answer": 'The customer sees "an SSO login loop" and wants "a prorated refund" [2][1]! Is that allowed [1]?',
                                                   "sources": SOURCES, "min_groundedness": 0.4, "script": []}},
        {"name": "one bad quote of two", "args": {"answer": 'Refunds go "to the original payment method" within "3 business days" [1].',
                                                  "sources": SOURCES, "min_groundedness": 1.0,
                                                  "script": [{"content": 'Refunds go “to the original payment method” “within 5–7 business days” [1].'}]}},
        {"name": "empty answer", "args": {"answer": "   ", "sources": SOURCES, "min_groundedness": 0.0, "script": []}},
        {"name": "threshold equality", "args": {"answer": mixed + ' Refunds go "to the original payment method" [1].', "sources": SOURCES, "min_groundedness": 0.5, "script": []}},
        {"name": "rewrite still bad", "args": {"answer": "We always refund in full.", "sources": SOURCES, "min_groundedness": 0.5,
                                               "script": [{"content": "We always refund in full [1]. Trust me [0]."}]}},
        {"name": "case and spacing in quote", "args": {"answer": 'Use   "UPLOAD THE NEW CERTIFICATE  under settings" [2].', "sources": SOURCES, "min_groundedness": 1.0, "script": []}},
    ]
