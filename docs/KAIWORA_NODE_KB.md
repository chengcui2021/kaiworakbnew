# Kaiwora KB in the Customer Node

Kaiwora KB is the private engineering-intelligence layer for each customer node. The KB software is identical across Kaiwora reference and customer nodes; only tenant data, source credentials and learned knowledge differ.

Knowledge Sources now include GitHub repository ingestion from an immutable commit snapshot. The existing Agent -> KB `lock-from-analysis` path remains the production path for Project Run: Agent performs local requirement/repository analysis, KB automatically resolves approved + validated tenant/repository knowledge, and the resulting Context Lock is consumed internally without manual Lock ID handoff.

The legacy Project Context UI was intentionally **not** made part of the required customer flow because it duplicates this automated handoff and its reference implementation uses Jira/Bedrock-oriented analysis. Kaiwora keeps analysis local/provider-neutral and treats any KB analysis UI as an optional diagnostic/admin surface rather than a production prerequisite.

Governed learning remains conservative: first successful evidence is a candidate; repeated high-confidence successful evidence for the same tenant/repository fingerprint can auto-promote to validated and then enter future Context Locks. This protects customers from one-off or accidental behaviour becoming policy.
