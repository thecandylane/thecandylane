#!/bin/zsh
# Regenerates card.svg and pushes it when it changed. launchd runs this every 6 hours (dev.thecandylane.card.plist).
# Syncs commit as card-sync, an address not linked to the GitHub account, so they never add to the contribution count shown on the card.
set -eu
cd "${0:A:h}"
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
git pull -q --ff-only
python3 card.py
git add card.svg tokens.json
git diff --cached --quiet && exit 0
git -c user.name=card-sync -c user.email=card-sync@schliewesystems.com commit -q -m "card: sync $(date -u +%Y-%m-%dT%H:%MZ)"
git push -q
