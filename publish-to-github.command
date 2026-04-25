#!/bin/bash
# One-click: initialize git, create the GitHub repo, and push.
# Double-click to run (right-click -> Open the first time).
set -eu
cd "$(dirname "$0")"

DEFAULT_REPO_NAME="air-resource-utility"

# ---------------------------------------------------------------------------
# 1) Ensure a clean local git repo with at least one commit.
# ---------------------------------------------------------------------------
if [ -d .git ] && ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "Removing partial .git directory..."
  rm -rf .git
fi

if [ ! -d .git ]; then
  echo "Initializing local git repo on 'main'..."
  git init -b main
  git config user.email "gilbert.liborio@gmail.com"
  git config user.name  "Gilbert Liborio"
fi

if ! git rev-parse HEAD >/dev/null 2>&1; then
  echo "Staging files and making initial commit..."
  git add .
  git commit -m "Initial commit: MacBook Air resource monitor (menu bar + web dashboard)"
fi

# ---------------------------------------------------------------------------
# 2) Make sure gh CLI is installed.
# ---------------------------------------------------------------------------
if ! command -v gh >/dev/null 2>&1; then
  echo
  echo "GitHub CLI ('gh') isn't installed. It's the easiest way to create the repo."
  echo
  if command -v brew >/dev/null 2>&1; then
    read -r -p "Install gh via Homebrew now? [Y/n] " ans
    ans="${ans:-Y}"
    if [[ "$ans" =~ ^[Yy] ]]; then
      brew install gh
    else
      echo "Aborted. Install with: brew install gh"
      exit 1
    fi
  else
    echo "Homebrew isn't installed either. Install Homebrew first by running:"
    echo
    echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    echo
    echo "Then re-run this script."
    exit 1
  fi
fi

# ---------------------------------------------------------------------------
# 3) Make sure gh is authenticated.
# ---------------------------------------------------------------------------
if ! gh auth status >/dev/null 2>&1; then
  echo
  echo "Authenticating with GitHub. Pick HTTPS when asked — it's the simplest."
  gh auth login
fi

# ---------------------------------------------------------------------------
# 4) Create the GitHub repo and push (or just push if remote exists).
# ---------------------------------------------------------------------------
if git remote get-url origin >/dev/null 2>&1; then
  echo "Remote 'origin' already configured. Pushing main..."
  git push -u origin main
else
  read -r -p "Repo name [$DEFAULT_REPO_NAME]: " REPO_NAME
  REPO_NAME="${REPO_NAME:-$DEFAULT_REPO_NAME}"

  read -r -p "Visibility — public or private? [public/private] (default public): " VIS
  VIS="${VIS:-public}"
  if [[ "$VIS" != "public" && "$VIS" != "private" ]]; then
    VIS="public"
  fi

  echo
  echo "Creating https://github.com/<you>/$REPO_NAME ($VIS) and pushing..."
  gh repo create "$REPO_NAME" "--$VIS" --source=. --remote=origin --push
fi

echo
echo "----------------------------------------"
echo "Repo URL:"
gh repo view --json url -q .url || true
echo "----------------------------------------"
