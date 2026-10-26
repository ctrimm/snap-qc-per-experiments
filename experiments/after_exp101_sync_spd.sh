#!/bin/bash
# After queue_exp101b.sh: fast-forward the local state-policy-docs to origin/main (the CDSS letters import, 7a265f0)
# and remove the letters worktree. Waits so exp101 runs on one unchanged corpus.
while pgrep -f "queue_exp101[b][.]sh" >/dev/null; do sleep 300; done
cd /Users/corytrimm/Documents/GitHub/state-policy-docs && git fetch -q origin && git merge -q --ff-only origin/main && \
  git worktree remove ../state-policy-docs-letters && git branch -q -d cdss-cited-letters && echo "$(date) synced to $(git log --oneline -1)"
