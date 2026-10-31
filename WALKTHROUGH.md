# Writing a walkthrough.md

`walkthrough.md` is the long-form guide shown in a problem's **Detailed Explanation** tab. The editorial is the 3-minute version. The walkthrough is the 10-minute version for someone who couldn't solve the problem and wants to understand it well enough to solve the next one alone.

The models are `problems/0101-react-tool-loop/walkthrough.md` and `problems/0102-agent-loop-detection/walkthrough.md`. Read both before writing one. The user reviewed them and liked them; match their depth, tone and shape.

`python3 scripts/check.py <id>` checks every walkthrough: the section numbering, the required sections, the word count, that the Full solution code is **Accepted** by the real judge, and that every row of the test-case table names a real test case.

## Facts come from running code, never from memory

Every number, step, shape, output and test-case result you quote must come from running it:

```
python3 scripts/trace.py <id>                 # every case: args and the reference output
python3 scripts/trace.py <id> "case name"     # one case
python3 scripts/trace.py <id> --code f.py     # your own code (e.g. a wrong version) next to the expected output
```

For hand traces of intermediate values (a transcript after step 2, a matrix after one iteration), write a scratch script in `/tmp` and run it. If you claim "this mistake makes test X fail", run the mistake with `--code` and check it does. The `wrong_*.py` files are ready-made mistakes, and each has a comment naming the bug.

Read every file in the problem folder first: `problem.md`, `meta.json` (hints, signature), `starter.py`, `solution.py`, `tests.py`, `driver.py` and `checker.py` if present, `editorial.md` and the `wrong_*.py` files. Read `harness/gc_runtime.py` for any fake the problem uses.

## Shape for coding problems (Applied tracks and ML)

No `# ` title: the tab supplies one. Sections are `## N. Title`, numbered from 1 in order. Use these, adapting titles where it reads better, but keep the words the checker looks for (marked **required**):

1. **What the problem is really asking** (required: "really asking"). Strip the story. Name the underlying pattern (a state machine, a string match on a list's tail, a weighted sum, a priority queue...). Say what the judge actually records and grades.
2. **Understand the inputs.** A table: name, what it is, how you use it. Then the two or three details that are easy to miss.
3. **Trace an example by hand.** Pick the visible example that teaches the most. Show the actual intermediate state: a step table, the messages appended, the array values or shapes. Then trace the trickiest hidden case if there is one.
4. **Key ideas, if any.** One `## N. Key idea: ...` section per non-obvious idea (why to append before checking, why keys are sorted, why the log-sum-exp trick). Skip this when there isn't one.
5. **Plan before you code.** Pseudocode or commented steps, then any decision table.
6. **Build it one piece at a time.** Three to five steps, each a small code block plus why it's written that way, including the reason behind any line a beginner would get wrong.
7. **Full solution** (required: "full solution"). One ```python block holding the complete solution, which the checker submits to the judge. Usually `solution.py`'s logic, made Accepted.
   **Every line of code gets a comment saying what it does and why**, as an end-of-line comment or a comment line directly above it. That includes imports, `def`/`class` lines, `return`, `else:` and `break`. The checker enforces this on every statement. Explain intent, not syntax: write `# the model answered, so we're done`, not `# return content`. Where an end-of-line comment would push past ~100 characters, put the comment on its own line above the code. A multi-line statement needs only one comment.
8. **How the test cases map to the code** (required: "test case"). A table whose first column is the test-case name exactly as in `tests.py`, one case or a comma-joined group per row. Then the expected result (from trace.py) and what the case checks. Cover the cases that each test a distinct idea; skip near-duplicates.
9. **Complexity** (required). Time and memory, plus what it means in production or at scale.
10. **If you got Wrong Answer** (required: "wrong answer"). Symptom first ("`stopped_at` is one later than expected"), then the bug. Draw these from the `wrong_*.py` files and the editorial's common mistakes.
11. **Follow-ups an interviewer might ask** (required: "follow-up"). Three to five, in the form *question?* then a concrete answer, with problem numbers where another problem covers it.

At least 900 words of prose outside code blocks; 1,200–1,800 is typical.

### Extra for the ML track (ids 1–99)

- Add a **The math** section after the inputs: the equations from the definition, derived step by step in KaTeX (`$...$`, `$$...$$`), with every symbol named. Derive gradients, don't just state them.
- **Track shapes everywhere.** In the trace and the build steps, annotate arrays with their shapes, e.g. `# (batch, d_model)`. Shape bugs are the most common ML failure.
- Cover numerical stability where it matters (overflow, log of 0, division by a near-zero norm), and what NumPy broadcasting does on each line that relies on it.
- Complexity in terms of the problem's dimensions (n, d, k, T...).

## Shape for design problems (ids 201–215)

These have no code. The model answer is `solution.md` and the grading is `rubric.json`. The walkthrough teaches *how to get to* that answer. Sections:

1. **What the problem is really asking** (required). The core tension, plus the two or three decisions that carry the design.
2. **The numbers that drive the design.** Do the back-of-envelope arithmetic from `problem.md` step by step (volumes, peak rate, tokens, cost), with the results the model answer uses.
3. **How to spend your time.** A minute-by-minute plan for the session, by pillar.
4. **Pillar A: Frame**, then 5. **Pillar B: Build the core**, 6. **Pillar C: Serve and store**, 7. **Pillar D: Run it safely**, with a `### Section name` subsection for each of the 15 sections inside its pillar. Use the exact titles: Scenario, Single View, Data Sources, Processing, Agents, Memory, MCP Tool Servers, Endpoints, Caching, Data Stores, Output, Guardrails, Key Impact, Failure Modes, Build Order. The checker requires a heading for each. For each one: the question it answers, how to reason to the decision (the alternatives and why the model answer picks what it does), the trap, and which rubric criteria it earns.
8. **The decisions that separate strong answers.** Two or three head-to-head comparisons.
9. **Common mistakes.**
10. **Follow-ups an interviewer might ask** (required: "follow-up").

Every number and price must agree with `solution.md`; never introduce new ones. Don't restate the model answer wholesale: explain the reasoning and point to it ("reveal the model answer for the full table").

## Style

- Plain, direct sentences. Second person ("you"). No filler, no "Let's dive in", no emoji.
- Tables for anything compared across rows, code blocks for code, `inline code` for names and values.
- Use the problem's own vocabulary and case names so the reader can match them to the page.
- Refer to related problems by number and name, e.g. "problem 107 (memory-under-token-budget)".
