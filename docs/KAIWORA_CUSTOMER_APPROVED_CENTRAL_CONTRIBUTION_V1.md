# Customer-approved central contribution

Global learning creation is delayed until after tenant approval. A tenant candidate is never promoted to Kaiwora global review merely because it was created or because an opt-in exists.

The contribution endpoint accepts only a tenant-owned candidate with `status=validated` and `human_approved=true`, sanitises the observation, creates a global review candidate, and still requires Kaiwora Admin review before master knowledge is created.
