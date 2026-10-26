#!/bin/bash
# After queue_exp100.sh: fast-forward the local state-policy-docs main to the pushed merge (34f2813) and remove
# the merge worktree. Waits so that exp99/exp100 run on one unchanged corpus.
while pgrep -f "queue_exp(9[9]|10[0])[.]sh" >/dev/null; do sleep 300; done
cd /Users/corytrimm/Documents/GitHub/state-policy-docs && git fetch -q origin && git merge -q --ff-only origin/main && \
  git worktree remove ../state-policy-docs-merge && git branch -q -d merge-hf-2026-10-18 && echo "$(date) synced to $(git log --oneline -1)"
