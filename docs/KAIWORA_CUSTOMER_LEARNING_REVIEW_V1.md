# Customer Learning Review V1

Kaiwora KB keeps the existing governed knowledge architecture. Customer Project Run observations arrive as tenant-scoped `LearningEntryDB` candidates and as normal OPEN knowledge entries. They are non-authoritative until customer review.

New review behavior:

- list tenant learning candidates;
- approve, reject, or defer;
- optionally edit the observation before approval;
- choose repository, workspace, or tenant scope;
- on approval, mark the learning row `validated` and resolve the corresponding KB entry;
- rejected/deferred candidates never enter approved knowledge;
- no customer candidate is promoted into global Kaiwora learning.

The existing Knowledge Resolver and Context Lock paths remain unchanged. Approved tenant/workspace/repository knowledge continues to participate in governed Context Assembly according to existing scope filtering and ranking.
