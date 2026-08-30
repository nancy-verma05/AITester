Use only the folder @file:chapter_07_AI_Agents

Let's use the BLAST.md file, and let's go with protocol 0, which is the first step. Our main objective is to create a test plan creator from a Jira ID.

What we need to do is create the following files:

task_plan findings.md
progress.md
LLM.md
In these files, you need to mention all the details:

How your thinking is
What you have thought about it
How exactly we can create this project in this case
I want you to create these files and add the following:

In findings.md, mention the findings that you have found and how we can fetch them from Jira, and include any curl or request that you will be using.
In progress.md, add everything you are making every hour, every 30 minutes, or every 10 minutes: what was done, what the error was, what the results were, and everything.
In task_plan, mention all the checklists and the goals that we have for it.
In LLM.md, mention what you think about the schemas, rules, and architecture while creating this project.


---

It asked 9 questions answered as below:

1. Jira deployment:
Jira Cloud (*.atlassian.net).

2. Auth we may use:
Use a dedicated Jira service account with a Jira Cloud API token using Basic authentication.
Grant read-only access required to retrieve issues, descriptions, acceptance criteria, and related metadata.
Do not grant write permissions because the first version only generates a local test plan.

3. Acceptance Criteria location:
Acceptance criteria are primarily stored in the Jira issue description.
The agent should also inspect the configured Acceptance Criteria custom field if one exists.
If acceptance criteria cannot be found, the agent must flag this as a discovery/gap rather than inventing them.

4. Issue types in scope:
Story initially.
The architecture should allow Bug, Task, Sub-task, and Spike to be added later, but Protocol 1 should focus on Story.

5. Test plan template:
Reuse the repository template as-is.
The agent should populate the existing template rather than create its own format.

6. Output destination:
Local Markdown file only.
No Jira write operations, attachments, comments, or other external writes in the initial version.

7. LLM provider + budget:
Use Claude as specified in LLM.md.
For the initial implementation, do not impose a hard per-run cost ceiling unless LLM.md already specifies one.
The agent should minimize unnecessary model calls and avoid sending the same context repeatedly.

8. Runtime:
Use Antigravity as specified by BLAST.
The A.N.T. architecture should separate:
- retrieval/context gathering,
- reasoning/planning,
- generation/output.

The exact A.N.T. layer contract should be defined explicitly in BLAST.md and LLM.md before Protocol 1 is locked.
Each layer must have a clear input/output contract and must not bypass the defined boundaries.

9. Data sensitivity:
Jira ticket content may contain sensitive/customer information.
Do not assume unrestricted transmission is acceptable.
For the initial version, send only the minimum required Jira content to the model.
Do not send secrets, credentials, tokens, or unnecessary customer/PII data.
If the project requires zero-retention processing or redaction, that requirement must be explicitly configured before production use.

