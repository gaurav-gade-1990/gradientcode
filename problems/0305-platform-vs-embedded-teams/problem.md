### Context

You are the SVP of AI at a listed online marketplace group that runs five classifieds businesses (autos, property, jobs, general goods and local services) across the US and Canada: $4.2B revenue, $1.3B EBITDA. The CEO hired you six weeks ago, after an incident in the jobs business put AI risk on the board's agenda. Each business unit has built its own AI team, its own model gateway and its own vendor contracts. The CTO proposes moving all 150 AI staff into one central organization under the CTO; the business-unit presidents oppose it. The CEO wants your recommendation on the AI operating model for the board meeting in six weeks.

### What you have

- **AI staff today.** 150 people, all embedded in business units. Fully loaded cost is assumed at $280k a year.

| Business unit | AI staff | Of whom infrastructure roles | Share of model spend |
|---|---|---|---|
| Autos | 48 | 10 | 40% |
| Property | 34 | 8 | 25% |
| Jobs | 28 | 7 | 15% |
| General goods | 24 | 6 | 12% |
| Local services | 16 | 5 | 8% |

- **Infrastructure roles** run each unit's gateway, eval harness, vector store and fine-tuning pipeline.
- **Model spend.** $1.5M a month today; finance forecasts 5 percent growth a month for the next 12 months. By spend: Opus 5.5 60 percent, Sonnet 5.5 35 percent, Haiku 5.5 5 percent. For every model, uncached input is about 65 percent of spend and output 35 percent; cache reads are negligible today. The five units hold 9 contracts with 4 model vendors.
- **Prices per million tokens.** Opus 5.5 $4 input, $20 output, $0.20 cache reads; Sonnet 5.5 $2, $10 and $0.20; Haiku 5.5 $0.10 and $0.50.
- **Your 6-week audit.** 45 percent of Opus traffic passes its own use-case evals on Sonnet 5.5. Half of today's uncached input tokens are repeated prefixes that could be served as cache reads. A shared platform needs 22 people; the 36 infrastructure roles can staff it and free 14 for product work. Platform tooling (gateway, eval service, observability) costs an assumed $1.2M a year in new spend.
- **The incident.** Four months ago the jobs unit sent 210,000 résumés to a model vendor it had no contract with, and no zero-retention terms. Canada's federal privacy regulator has opened an inquiry. The board's audit committee wants one named owner for AI risk, and a control that prevents a repeat across every unit, within 90 days.
- **People data.** AI staff leave at 12 percent a year. HR's data from past reorganizations: people moved into a new organization leave at 24 percent in the following 12 months. Replacing one departure costs an assumed half a year's loaded cost, $140k.
- **The autos launch.** Autos (38 percent of group EBITDA) launches an AI pricing advisor for dealers in month 5, planned at $60M ARR. Its president: "Nobody on my AI team moves before launch."

### The constraint

The audit committee's control has to cover every unit, autos included, within 90 days. But autos carries 40 percent of model spend and can't move or divert a single AI person until after its month-5 launch. And whatever you do with people is hard to undo: a reorganization that goes wrong costs people who don't come back.

### What a strong answer covers

- The real options for the operating model, including the CTO's, and what each costs in people, money and risk.
- How you meet the 90-day deadline without touching the autos team.
- Who owns what afterwards: decision rights between a platform and the units, and who pays.
- What the savings really are, where they come from, and how much depends on moving people at all.
- How you bring the CEO, the CTO, five unit presidents and the audit committee to one decision.
