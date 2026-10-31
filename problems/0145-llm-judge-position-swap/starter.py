SYSTEM = "You are a strict evaluator. Compare two responses to the same customer question."
TEMPLATE = (
    "Question: {question}\n\n"
    "[Response 1]\n{first}\n\n"
    "[Response 2]\n{second}\n\n"
    "Which response is better? Reply with exactly one of: 1, 2, tie."
)


def evaluate_with_judge(judge, pairs, human, policy):
    # Write your code here
    pass
