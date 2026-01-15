#!/bin/bash
# GitHub Repo erstellen und pushen

cd ~/Downloads/ai-dev-assistant

echo "📦 Erstelle GitHub Repo..."
gh repo create ai-dev-assistant --public --description "AI-powered code generation assistant with project management"

echo "🚀 Push zu GitHub..."
git remote set-url origin https://github.com/einfachstarten/ai-dev-assistant.git
git branch -M main
git push -u origin main

echo "✅ Fertig! https://github.com/einfachstarten/ai-dev-assistant"
