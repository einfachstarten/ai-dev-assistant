#!/usr/bin/env python3
"""
AI Dev Assistant - Flask Server
ENHANCED with Projects, Sidebar, and Ticket History
"""

from flask import Flask, render_template, request, jsonify, Response
import json
import subprocess
import os
import time
import threading
from datetime import datetime
from queue import Queue
from pathlib import Path

# Import our custom modules
from ollama_integration import OllamaCodeGenerator
from git_operations import GitOperations
from repo_indexer import RepositoryIndexer
from context_selector import SmartContextSelector
from code_editor import CodeEditor, Edit
from project_manager import ProjectManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-change-in-production'

# Store active ticket generation status
ticket_status_store = {}
ticket_queues = {}

# Cache for repository indexers
repo_indexers = {}

# Initialize project manager
project_manager = ProjectManager()

# ───────────────────────────────────────────────────────
# ROUTES - CORE
# ───────────────────────────────────────────────────────

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/api/check-setup', methods=['GET'])
def check_setup():
    """Check if all dependencies are installed"""
    status = {
        'git': check_command('git --version'),
        'gh': check_command('gh --version'),
        'ollama': check_ollama(),
        'model': check_ollama_model('qwen2.5-coder:7b')
    }
    
    all_ready = all(status.values())
    
    return jsonify({
        'ready': all_ready,
        'status': status
    })

@app.route('/api/repos', methods=['GET'])
def get_repos():
    """Get all GitHub repositories for authenticated user"""
    try:
        result = subprocess.run(
            ['gh', 'repo', 'list', '--json', 'name,owner,url', '--limit', '100'],
            capture_output=True,
            text=True,
            check=True
        )
        repos = json.loads(result.stdout)
        return jsonify({'success': True, 'repos': repos})
    except subprocess.CalledProcessError:
        return jsonify({'success': False, 'error': 'GitHub CLI not authenticated'}), 401
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ───────────────────────────────────────────────────────
# ROUTES - PROJECTS
# ───────────────────────────────────────────────────────

@app.route('/api/projects', methods=['GET'])
def list_projects():
    """List all projects"""
    try:
        projects = project_manager.list_projects()
        return jsonify({'success': True, 'projects': projects})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/projects', methods=['POST'])
def create_project():
    """Create a new project"""
    try:
        data = request.json
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        create_repo = data.get('create_github_repo', False)
        
        if not name:
            return jsonify({'success': False, 'error': 'Project name required'}), 400
        
        project = project_manager.create_project(
            name=name,
            description=description,
            create_github_repo=create_repo
        )
        
        # Initialize repo if it was created
        if create_repo and project.get('repo_name'):
            project_manager.initialize_repo(project['id'])
        
        return jsonify({'success': True, 'project': project})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project(project_id):
    """Get project by ID"""
    try:
        project = project_manager.get_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        return jsonify({'success': True, 'project': project})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    """Update project"""
    try:
        data = request.json
        project = project_manager.update_project(project_id, data)
        
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        return jsonify({'success': True, 'project': project})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete project"""
    try:
        success = project_manager.delete_project(project_id)
        
        if not success:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/projects/<project_id>/connect-repo', methods=['POST'])
def connect_repo(project_id):
    """Connect existing GitHub repo to project"""
    try:
        data = request.json
        repo_name = data.get('repo_name', '').strip()
        
        if not repo_name:
            return jsonify({'success': False, 'error': 'Repository name required'}), 400
        
        project = project_manager.connect_repo(project_id, repo_name)
        
        if not project:
            return jsonify({'success': False, 'error': 'Failed to connect repo'}), 500
        
        return jsonify({'success': True, 'project': project})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/projects/<project_id>/tickets', methods=['GET'])
def get_project_tickets(project_id):
    """Get all tickets for a project"""
    try:
        tickets = project_manager.get_project_tickets(project_id)
        return jsonify({'success': True, 'tickets': tickets})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/projects/<project_id>/tickets/<ticket_id>', methods=['GET'])
def get_ticket_detail(project_id, ticket_id):
    """Get detailed information about a specific ticket"""
    try:
        project = project_manager.get_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        # Find ticket
        ticket = None
        for t in project.get('tickets', []):
            if t['ticket_id'] == ticket_id:
                ticket = t
                break

        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404

        return jsonify({'success': True, 'ticket': ticket})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/projects/<project_id>/files', methods=['GET'])
def get_project_files(project_id):
    """Get repository file structure for a project"""
    try:
        project = project_manager.get_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        if not project.get('repo_name'):
            return jsonify({'success': False, 'error': 'No repository connected'}), 400
        
        # Get or create indexer (force refresh to ensure we get all files)
        repo_name = project['repo_name']
        git_ops = GitOperations(repo_name)
        indexer = RepositoryIndexer(git_ops.repo_path)
        indexer.index(force_refresh=True)
        repo_indexers[repo_name] = indexer
        
        # Get file tree and summary
        files_list = []
        for rel_path, file_info in indexer.files.items():
            files_list.append({
                'path': rel_path,
                'size': file_info.size,
                'extension': file_info.extension,
                'is_code': file_info.is_code,
                'lines': file_info.lines
            })
        
        # Sort by path
        files_list.sort(key=lambda f: f['path'])
        
        summary = indexer.get_summary()
        
        return jsonify({
            'success': True,
            'files': files_list,
            'summary': summary
        })
        
    except Exception as e:
        print(f"Error getting project files: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ───────────────────────────────────────────────────────
# ROUTES - TICKETS
# ───────────────────────────────────────────────────────

@app.route('/api/ticket', methods=['POST'])
def create_ticket():
    """Generate code for a ticket - starts async workflow"""
    data = request.json
    project_id = data.get('project_id', '').strip()
    ticket_id = data.get('ticket_id', '').strip()  # Now optional!
    description = data.get('description', '').strip()
    
    if not description:
        return jsonify({'error': 'Description required'}), 400
    
    if not project_id:
        return jsonify({'error': 'Project ID required'}), 400
    
    # Get project
    project = project_manager.get_project(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    if not project.get('repo_name'):
        return jsonify({'error': 'Project has no connected repository'}), 400
    
    # Auto-generate ticket ID if not provided
    if not ticket_id:
        generator = OllamaCodeGenerator()
        existing_tickets = project.get('tickets', [])
        ticket_id = generator.generate_ticket_id(description, existing_tickets)
        print(f"🎫 Auto-generated: {ticket_id}")
    
    # Initialize status queue
    ticket_queues[ticket_id] = Queue()
    ticket_status_store[ticket_id] = {
        'status': 'started',
        'step': 'Initializing...',
        'progress': 0,
        'complete': False,
        'error': None,
        'pr_url': None
    }
    
    # Start async workflow
    thread = threading.Thread(
        target=run_enhanced_workflow,
        args=(project_id, ticket_id, description, project['repo_name'])
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'ticket_id': ticket_id,
        'description': description,
        'project_id': project_id,
        'status': 'started',
        'auto_generated': data.get('ticket_id', '').strip() == ''  # Flag if was auto-generated
    })

@app.route('/api/status/<ticket_id>')
def ticket_status(ticket_id):
    """Stream real-time status updates for a ticket"""
    def generate():
        queue = ticket_queues.get(ticket_id)
        if not queue:
            yield f"data: {json.dumps({'error': 'Ticket not found'})}\n\n"
            return
        
        while True:
            try:
                status = queue.get(timeout=30)
                yield f"data: {json.dumps(status)}\n\n"
                
                if status.get('complete') or status.get('error'):
                    break
            except:
                yield f"data: {json.dumps({'keepalive': True})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

# ───────────────────────────────────────────────────────
# WORKFLOW EXECUTION
# ───────────────────────────────────────────────────────

def send_status_update(ticket_id, step, progress, complete=False, error=None, pr_url=None):
    """Send status update to SSE stream"""
    status = {
        'step': step,
        'progress': progress,
        'complete': complete,
        'error': error,
        'pr_url': pr_url
    }
    
    queue = ticket_queues.get(ticket_id)
    if queue:
        queue.put(status)
    
    ticket_status_store[ticket_id] = status

def run_enhanced_workflow(project_id, ticket_id, description, repo_name):
    """Enhanced workflow with project integration and transparency"""
    try:
        # Step 1: Initialize
        send_status_update(ticket_id, 'Initializing...', 5)
        time.sleep(0.5)

        git_ops = GitOperations(repo_name)
        repo_path = git_ops.repo_path

        # Step 2: Index repository
        send_status_update(ticket_id, 'Scanning repository...', 10)

        if repo_name not in repo_indexers:
            indexer = RepositoryIndexer(repo_path)
            indexer.index()
            repo_indexers[repo_name] = indexer
        else:
            indexer = repo_indexers[repo_name]

        summary = indexer.get_summary()
        print(f"Repository: {summary['code_files']} files, {summary['total_lines']} lines")

        # Step 3: Context selection
        send_status_update(ticket_id, 'Analyzing files...', 15)

        selector = SmartContextSelector(indexer)
        target_files = detect_target_files(description)

        relevant_files = selector.select_context(
            task_description=description,
            target_files=target_files,
            max_files=8,
            max_tokens=6000
        )

        context = selector.format_context_for_ai(relevant_files)

        # Step 4: Detect mode
        mode = detect_mode(description, target_files, relevant_files)

        # TRANSPARENCY: Show understanding before generation
        send_status_update(ticket_id, f'📋 Understanding: {mode} mode, {len(relevant_files)} relevant files', 18)
        time.sleep(1.0)

        understanding_summary = generate_understanding_summary(
            ticket_id, description, mode, target_files, relevant_files
        )
        send_status_update(ticket_id, f'✓ Plan: {understanding_summary}', 19)
        time.sleep(1.5)

        send_status_update(
            ticket_id,
            f'Generating code ({mode} mode)...',
            20
        )
        
        # Step 5: Generate code
        generator = OllamaCodeGenerator()
        result = generator.generate_code(
            ticket_id=ticket_id,
            description=description,
            context=context if relevant_files else None,
            mode=mode
        )
        
        files = result['files']
        send_status_update(ticket_id, f'Code generated! {len(files)} file(s)', 40)
        time.sleep(0.5)
        
        # Step 6: Create branch
        send_status_update(ticket_id, 'Creating branch...', 50)
        branch_name = f"feature/{ticket_id}"
        git_ops.create_branch(branch_name)
        
        # Step 7: Apply changes
        send_status_update(ticket_id, f'Applying changes...', 60)
        
        if mode == 'edit':
            editor = CodeEditor(repo_path, create_backups=True)
            edits = []
            
            for file_data in files:
                edit = editor.create_edit_from_ai_output(
                    file_path=file_data['path'],
                    ai_new_content=file_data['content'],
                    operation='auto'
                )
                edits.append(edit)
            
            edit_result = editor.apply_edits(edits)
            
            if not edit_result.success:
                error_msg = "Failed to apply edits"
                send_status_update(ticket_id, error_msg, 0, complete=True, error=error_msg)
                return
        else:
            git_ops.write_files(files)
        
        # Step 8: Commit and push
        send_status_update(ticket_id, 'Committing...', 70)
        git_ops.commit_and_push(ticket_id, description, branch_name)
        
        send_status_update(ticket_id, 'Pushing...', 80)
        time.sleep(0.5)
        
        # Step 9: Create PR
        send_status_update(ticket_id, 'Creating PR...', 90)
        pr_url = git_ops.create_pull_request(ticket_id, description, branch_name, files)
        
        # TRANSPARENCY: Show changes summary
        send_status_update(ticket_id, 'Generating summary...', 95)
        changes_summary = generate_changes_summary(files, mode)
        send_status_update(ticket_id, f'📝 Changes: {changes_summary}', 98)
        time.sleep(1.0)

        # Step 10: Save ticket to project with workflow data
        workflow_data = {
            'mode': mode,
            'target_files': target_files,
            'relevant_files': [
                {
                    'path': rf.file_info.relative_path,
                    'score': rf.score,
                    'reasons': rf.reasons
                } for rf in relevant_files
            ],
            'files_changed': [
                {
                    'path': f['path'],
                    'lines': f.get('content', '').count('\n') + 1 if f.get('content') else 0
                } for f in files
            ],
            'understanding_summary': understanding_summary,
            'changes_summary': changes_summary
        }

        project_manager.add_ticket(
            project_id=project_id,
            ticket_id=ticket_id,
            description=description,
            pr_url=pr_url,
            workflow_data=workflow_data
        )

        # Complete
        send_status_update(
            ticket_id,
            f'✅ Complete! {len(files)} file(s) {mode}ed',
            100,
            complete=True,
            pr_url=pr_url
        )
        
    except Exception as e:
        error_msg = str(e)
        print(f"Workflow error: {error_msg}")
        import traceback
        traceback.print_exc()
        
        send_status_update(
            ticket_id,
            f'Error: {error_msg}',
            0,
            complete=True,
            error=error_msg
        )

def generate_understanding_summary(ticket_id: str, description: str, mode: str,
                                  target_files: list, relevant_files: list) -> str:
    """Generate a summary of what the AI understood and plans to do"""
    summary_parts = []

    # What we understood
    action = "create new" if mode == "create" else "modify existing"
    summary_parts.append(f"Will {action} files")

    # Target files mentioned
    if target_files:
        summary_parts.append(f"targeting {', '.join(target_files[:3])}")

    # Context files
    if relevant_files:
        file_names = [rf.file_info.relative_path for rf in relevant_files[:3]]
        summary_parts.append(f"using context from {', '.join(file_names)}")

    result = ' | '.join(summary_parts)
    print(f"\n{'='*60}")
    print(f"🎯 TICKET UNDERSTANDING: {ticket_id}")
    print(f"{'='*60}")
    print(f"Description: {description}")
    print(f"Mode: {mode}")
    print(f"Target Files: {target_files if target_files else 'Auto-detect'}")
    print(f"Relevant Context: {len(relevant_files)} files")
    if relevant_files:
        for rf in relevant_files[:5]:
            print(f"  • {rf.file_info.relative_path} (score: {rf.score:.1f})")
    print(f"{'='*60}\n")

    return result

def generate_changes_summary(files: list, mode: str) -> str:
    """Generate a summary of all changes made"""
    summary_parts = []

    # Count by operation
    file_paths = [f['path'] for f in files]

    # Group by directory
    dirs = {}
    for path in file_paths:
        dir_name = str(Path(path).parent) if Path(path).parent != Path('.') else '/'
        if dir_name not in dirs:
            dirs[dir_name] = []
        dirs[dir_name].append(Path(path).name)

    # Build summary
    summary_parts.append(f"{len(files)} files {mode}ed")

    for dir_name, filenames in sorted(dirs.items())[:3]:
        summary_parts.append(f"{dir_name}: {', '.join(filenames[:2])}")

    result = ' | '.join(summary_parts)

    print(f"\n{'='*60}")
    print(f"📝 CHANGES SUMMARY")
    print(f"{'='*60}")
    print(f"Total Files: {len(files)}")
    print(f"Operation: {mode}")
    print(f"\nFiles Changed:")
    for f in files:
        # Count lines if content available
        lines = f.get('content', '').count('\n') + 1 if f.get('content') else '?'
        print(f"  • {f['path']} (~{lines} lines)")
    print(f"{'='*60}\n")

    return result

def detect_target_files(description: str) -> list:
    """Detect file mentions in description"""
    import re
    file_pattern = r'\b[\w-]+\.(js|jsx|ts|tsx|html|css|scss|py|rb)\b'
    files = re.findall(file_pattern, description.lower())
    name_pattern = r'\b([\w-]+)\s+(component|file|module|page)\b'
    names = re.findall(name_pattern, description.lower())
    targets = list(set(files + [n[0] for n in names]))
    return targets if targets else []

def detect_mode(description: str, target_files: list, relevant_files: list) -> str:
    """Detect create vs edit mode"""
    desc_lower = description.lower()
    edit_keywords = ['edit', 'modify', 'update', 'change', 'fix', 'refactor']
    create_keywords = ['create', 'build', 'new', 'generate', 'make']
    
    has_edit = any(kw in desc_lower for kw in edit_keywords)
    has_create = any(kw in desc_lower for kw in create_keywords)
    
    if target_files and len(relevant_files) > 0:
        return 'edit'
    if has_edit and not has_create:
        return 'edit'
    if has_edit:
        return 'edit'
    
    return 'create'

# ───────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ───────────────────────────────────────────────────────

def check_command(cmd):
    try:
        subprocess.run(cmd, shell=True, capture_output=True, check=True)
        return True
    except:
        return False

def check_ollama():
    try:
        import requests
        response = requests.get('http://localhost:11434/api/tags', timeout=2)
        return response.status_code == 200
    except:
        return False

def check_ollama_model(model_name):
    try:
        import requests
        response = requests.get('http://localhost:11434/api/tags', timeout=2)
        if response.status_code == 200:
            data = response.json()
            models = [m.get('name', '') for m in data.get('models', [])]
            return any(model_name in m for m in models)
        return False
    except:
        return False

# ───────────────────────────────────────────────────────
# MAIN
# ───────────────────────────────────────────────────────

if __name__ == '__main__':
    print("\n" + "="*60)
    print("AI Dev Assistant - PROJECT MODE")
    print("="*60)
    print()
    print("Starting server...")
    print("Open: http://localhost:3000")
    print()
    print("Features:")
    print("  • Project Management")
    print("  • GitHub Repo Creation")
    print("  • Ticket History")
    print("  • Repository Context")
    print("  • Smart Editing")
    print()
    print("="*60)
    print()
    
    app.run(
        host='127.0.0.1',
        port=3000,
        debug=True,
        use_reloader=True
    )
