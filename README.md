# 🤖 AI Dev Assistant - FULL WORKFLOW

## ✨ Features

✅ **AI Code Generation** - Local Ollama models generate production-ready code  
✅ **Multi-Repository Support** - Connect and manage multiple GitHub repos  
✅ **Automatic Git Branching** - Creates feature branches automatically  
✅ **File Creation** - Generates HTML, CSS, and JavaScript files  
✅ **GitHub Integration** - Automatic Pull Request creation  
✅ **Real-time Progress** - Live status updates during generation  

## 🚀 Complete Workflow

```
User describes feature
         ↓
AI generates code (Ollama)
         ↓
Files created automatically
         ↓
Git branch created
         ↓
Committed & pushed
         ↓
Pull Request created
         ↓
Ready to review & merge!
```

## 📦 Installation

### Prerequisites

- **Python 3.9+**
- **Ollama** (for AI code generation)
- **GitHub CLI** (gh)
- **Git**

### Step 1: Install Dependencies

```bash
# Install Python packages
cd ~/Downloads/ai-dev-assistant
pip3 install -r requirements.txt

# Install GitHub CLI (if not already installed)
brew install gh

# Authenticate GitHub CLI
gh auth login

# Install Ollama (if not already installed)
brew install ollama

# Download AI model
ollama pull qwen2.5-coder:7b
```

### Step 2: Start Ollama

```bash
# In a separate terminal, start Ollama server
ollama serve
```

Keep this terminal running!

### Step 3: Start AI Dev Assistant

```bash
cd ~/Downloads/ai-dev-assistant
python3 app.py
```

### Step 4: Open Browser

```
http://localhost:3000
```

## 🎯 Usage

### 1. Connect Repositories

- Click "➕ Add Repository"
- Select repos from your GitHub account
- Click "Speichern"

### 2. Create a Feature

- Select target repository
- Enter Ticket ID (e.g., FEAT-001)
- Describe what you want to build
- Click "🚀 Generate Code"

### 3. Watch the Magic! ✨

The system will automatically:
1. Generate code with AI (30-60 seconds)
2. Create a new git branch
3. Write all files to the repository
4. Commit changes
5. Push to GitHub
6. Create a Pull Request

### 4. Review & Merge

- Click the PR link to review
- Check generated code
- Merge when ready!

## 📝 Example Tickets

**Simple Contact Form:**
```
FEAT-001: Create a contact form with name, email and message fields. 
Include validation and a success message.
```

**Pricing Table:**
```
FEAT-002: Build a pricing table with 3 tiers: Basic ($9/mo), 
Pro ($29/mo), Enterprise ($99/mo). Each tier should list 5 features 
and have a signup button.
```

**Navigation Menu:**
```
FEAT-003: Create a responsive navigation menu with logo, 5 menu items, 
and a hamburger icon for mobile. Include smooth animations.
```

## 🗂️ Project Structure

```
ai-dev-assistant/
├── app.py                      # Flask server & workflow orchestration
├── git_operations.py           # Git & GitHub operations
├── ollama_integration.py       # AI code generation
├── requirements.txt            # Python dependencies
├── templates/
│   └── index.html             # Web UI
├── static/
│   ├── css/
│   │   └── style.css          # Styling
│   └── js/
│       └── main.js            # Frontend logic
└── README.md                   # This file
```

## ⚙️ How It Works

### Backend (Python)

**app.py** - Main Flask server
- Routes for API endpoints
- SSE for real-time status updates
- Workflow orchestration

**git_operations.py** - Git automation
- Repository cloning
- Branch creation
- File writing
- Commit & push
- PR creation via GitHub CLI

**ollama_integration.py** - AI integration
- Ollama API calls
- Prompt engineering
- JSON parsing from AI output
- Fallback handling

### Frontend (JavaScript)

**main.js** - UI logic
- Repository management (localStorage)
- Form handling
- SSE client for progress updates
- Dynamic UI updates

## 🔧 Configuration

### Change AI Model

Edit `ollama_integration.py`:
```python
OllamaCodeGenerator(model='your-model-name')
```

### Change Port

Edit `app.py`:
```python
app.run(port=3000)  # Change 3000 to your port
```

### Repository Clone Location

Git operations clone to `~/repos/` by default.  
Edit `git_operations.py` to change.

## 🐛 Troubleshooting

### Port 5000 Already in Use

Apple's AirPlay uses port 5000. We use port 3000 instead.

### Ollama Not Running

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it:
ollama serve
```

### Model Not Found

```bash
# Download the model:
ollama pull qwen2.5-coder:7b

# Check installed models:
ollama list
```

### GitHub Authentication Failed

```bash
# Re-authenticate:
gh auth login

# Check status:
gh auth status
```

### Repository Clone Failed

Make sure you have access to the repository and GitHub CLI is authenticated.

### AI Generation Takes Too Long

- First generation may take 30-60 seconds (model loading)
- Subsequent generations are faster
- Complex requests take longer
- Check Ollama logs: `ollama serve` terminal

## 📊 Performance

- **First Request:** 30-60 seconds (model loading)
- **Subsequent Requests:** 15-30 seconds
- **File Creation:** < 1 second
- **Git Operations:** 2-5 seconds
- **PR Creation:** 1-2 seconds

**Total Time:** ~30-60 seconds from description to PR!

## 🎓 Tips for Best Results

### Good Descriptions

✅ **Specific:**  
"Create a contact form with name, email, phone fields. Add validation for email format."

✅ **Detailed:**  
"Build a pricing table with 3 columns. Each column should have a title, price, 5 feature bullets, and a CTA button."

✅ **Clear Requirements:**  
"Create a responsive navbar with logo on left, menu items in center, and login button on right."

### Avoid

❌ "Make a website"  
❌ "Add stuff to the page"  
❌ "Create something cool"  

## 🚀 Next Steps

- [ ] Add code linting
- [ ] Integrate with CI/CD
- [ ] Add testing framework
- [ ] Support for more file types
- [ ] Team collaboration features
- [ ] Custom AI model training

## 💡 Advanced Usage

### Custom Prompts

Edit `ollama_integration.py` → `_build_prompt()` to customize how AI generates code.

### Pre-commit Hooks

Add `.git/hooks/pre-commit` to your repos for validation before push.

### Multiple Branches

The system creates feature branches automatically.  
Merge to main when ready.

## 🤝 Contributing

This is a workshop project. Feel free to:
- Fork and extend
- Add features
- Improve prompts
- Share with others

## 📞 Support

- GitHub Issues
- Email Support
- Community Discord

## 🎉 Credits

Built with:
- **Flask** - Web framework
- **Ollama** - Local AI models
- **GitHub CLI** - Git automation
- **qwen2.5-coder** - AI code generation

---

**Built with ❤️ for Workshop Participants**

Enjoy your AI-powered development workflow! 🚀
