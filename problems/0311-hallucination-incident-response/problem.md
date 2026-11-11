### Context

You are the VP of AI Engineering at a benefits-administration SaaS company: $260M ARR, 1,900 employer customers, 2.6M covered employees. Its AI assistant answers employees' benefit questions inside the enrollment portal. It is day 3 of the 21-day open-enrollment window, the three weeks a year that matter most. At 7:40 this morning the HR director of a large customer escalated: the assistant has been telling employees they can add dependents "any time during the plan year", when the plan only allows it during enrollment or after a qualifying life event. An employee has posted a screenshot publicly. The CEO has asked you to run the response and brief the executive team at noon.

### What you have

- **Volume.** The assistant handles 140,000 conversations a day during enrollment; 18 percent are about eligibility and dependents.
- **What the overnight sample shows.** Of 2,000 eligibility answers since the release, 46 were wrong. Of 1,000 answers on other topics, 4 were wrong, the same rate as last month. Last month's eligibility sample was 3 wrong in 1,000.
- **The release.** On day 1 of the window the team shipped a new prompt and a newer model version. The eval suite passed at 97 percent, but it has only 40 eligibility cases. The previous version can be restored in 20 minutes.
- **Contact center.** Capacity is 12,000 contacts a day at full enrollment staffing, and it is running at 9,500. Contacts above 9,500 cost about $6 each in overtime (assumed). A BPO partner can add up to 5,000 contacts a day after 4 days' notice, at $14 a contact (assumed). When employees can't get an answer from the assistant, an assumed 30 percent contact the center; the rest ask HR or read the guide.
- **Answer cards.** The content team can publish verified answer cards for the 12 most common eligibility questions in about 8 hours. Each card is filled from the employer's own plan setup in the admin system (deadlines, dependent rules), with no model in the loop. Those 12 questions make up 70 percent of eligibility conversations.
- **Logs.** Every conversation is logged with the employer, the employee, the answer and the plan documents retrieved. Re-checking a logged answer against plan rules automatically flags about 8 percent for a human (assumed), and a benefits specialist takes about 3 minutes per flagged answer. The implementation team can lend 20 benefits specialists, who are not part of the contact center's capacity.
- **Contracts.** Customer contracts require notice of a service error that affects their employees within 5 business days of confirming it. Carriers will generally accept late dependent adds caused by administrative error if the employer requests them within 30 days after the window closes (per the account team; assumed to hold for most carriers).
- **Revenue at stake.** The escalating customer has 38,000 employees, $4.1M ARR, and renews in 4 months. 310 customers worth $52M ARR renew in Q1.

### The constraint

Turning the assistant off is the obvious safe call, and the contact center can't absorb it: it has room for 2,500 more contacts a day. Keeping it on as it is means more employees get a wrong eligibility answer every day of the 18 left in the window. Sales has asked that you notify only the customer who complained.

### What a strong answer covers

- How many employees have been affected so far, and how many more each day you wait.
- How you stop the harm without taking down the support the enrollment window depends on.
- Who you notify, when, and what you say, given the contract and sales' request.
- How affected employees are found and made whole before their deadlines pass.
- What changes so the next release can't ship the same failure, and how you'll know the fix holds.
