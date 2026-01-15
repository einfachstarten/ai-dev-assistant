#!/bin/bash
# GitHub Sync Setup für AI Dev Assistant

cd ~/Downloads/ai-dev-assistant

echo "📦 Erstelle GitHub Repo..."
gh repo create ai-dev-assistant --public --source=. --remote=origin --push=false

echo "🔧 Git initialisieren..."
git init
git add .
git commit -m "Initial commit: AI Dev Assistant with project management"

echo "🚀 Auf GitHub pushen..."
git branch -M main
git remote add origin https://github.com/$(gh api user --jq .login)/ai-dev-assistant.git
git push -u origin main

echo "✅ Fertig! Repo: https://github.com/$(gh api user --jq .login)/ai-dev-assistant"
