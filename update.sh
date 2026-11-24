#!/bin/zsh
# Regenerates card.svg and pushes it when it changed. A launchd agent in ~/Library/LaunchAgents runs it every 6 hours.
# Syncs commit as card-sync, an address not linked to the GitHub account, so they never add to the contribution count shown on the card.
set -eu
cd "${0:A:h}"
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
[ -f local.env ] && { set -a; source ./local.env; set +a }   # machine-specific settings, never committed
git pull -q --ff-only
python3 card.py
git add card.svg tokens.json
git diff --cached --quiet && exit 0
git -c user.name=card-sync -c user.email=card-sync@schliewesystems.com commit -q -m "card: sync $(date -u +%Y-%m-%dT%H:%MZ)"
git push -q
