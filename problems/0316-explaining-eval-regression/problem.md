### Context

You are the director of claims AI at a regional auto insurer: $1.4B of written premium and 50,000 claims a month. A model reads every new claim file and flags the likely fraudulent ones to the Special Investigations Unit (SIU), which investigates them before payment. On October 1 a state privacy rule took effect, and the team shipped a step that strips claimants' phone numbers, emails and street addresses before the claim reaches the model. This week the quarterly eval report says fraud "recall" fell from 82.5 to 72.5 percent. The SIU director has emailed the COO that "the AI now misses 1 in 10 more frauds, so roll it back". The ops dashboard, meanwhile, shows "accuracy" rising from 96.6 to 97.2 percent. The COO wants you to explain what happened at Thursday's exec ops review, in 3 days, and to say what you are doing about it.

### What you have

- **The eval set.** Each quarter SIU investigates 1,000 randomly chosen claims, whether flagged or not; 40 of this quarter's were confirmed fraud. Both versions of the model were run on the same 1,000:
  - **Before redaction:** flagged 60 claims, of which 33 were fraud.
  - **After redaction:** flagged 46 claims, of which 29 were fraud.
  - **On the 40 frauds:** 27 were caught by both versions, 6 only by the old one and 2 only by the new one.
  - **At a lower flag threshold:** the redacted version flags 58 claims and catches 31 of the 40 frauds.
- **Fraud in production.** The confirmed fraud rate is 4 percent of claims, which matches the audit sample. Finance estimates that a fraudulent claim that isn't flagged pays out $6,500 on average.
- **SIU.** 40 investigators can work 3,000 flagged claims a month. They now receive about 2,300.
- **Labels.** The random audit labels only 1,000 claims a quarter. Contract auditors could label more at an assumed $45 a claim. Separately, 1,200 confirmed-fraud claims were closed in the last 12 months, with full files.
- **Legal.** Re-running historical claims through either version for internal testing is permitted. Sending the stripped fields to the model in production is not.
- **A fix.** The team can compute link signals in-house, such as "this phone number appears on 3 other claims this year", and send the model only the count, never the number. Compliance has approved the approach. It takes 2 engineers 6 weeks (fully loaded cost assumed at $240k a year).
- **Model cost.** Sonnet 5.5 at about 20,000 input and 400 output tokens a claim, at $2 and $10 per million tokens.

### The constraint

Rolling back is not an option: the old version sends data the rule now forbids. And the audit sample holds only 40 frauds a quarter, so on its own it can't tell a real 10-point drop from noise for many quarters. The executives need an answer on Thursday.

### What a strong answer covers

- Recall, precision and accuracy in plain words, and why the two reports seem to disagree.
- How sure you can be about a gap of 4 claims out of 40, with a range you derive.
- What the gap could cost in dollars, at the low and high ends.
- What you do this week, this month and after, given that rollback is ruled out.
- The opening line, the one slide, and your answers to "is the AI broken?" and "why can't we just roll back?"
