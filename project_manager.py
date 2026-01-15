#!/usr/bin/env python3
"""
Project Manager
Handles project creation, GitHub repo initialization, and ticket tracking with PR status
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import uuid


class ProjectManager:
    """
    Manages projects, GitHub repositories, and ticket history
    """
    
    def __init__(self, data_dir: str = './data'):
        """
        Initialize project manager
        
        Args:
            data_dir: Directory to store project data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.projects_file = self.data_dir / 'projects.json'
        
        # Initialize projects file if it doesn't exist
        if not self.projects_file.exists():
            self._save_projects({})
    
    # ─────────────────────────────────────────────────────
    # PROJECT CRUD
    # ─────────────────────────────────────────────────────
    
    def create_project(self, 
                      name: str, 
                      description: str,
                      create_github_repo: bool = False) -> Dict:
        """
        Create a new project
        
        Args:
            name: Project name
            description: Project description
            create_github_repo: Whether to create GitHub repo
            
        Returns:
            Created project dict
        """
        projects = self._load_projects()
        
        project_id = str(uuid.uuid4())[:8]
        
        project = {
            'id': project_id,
            'name': name,
            'description': description,
            'repo_name': None,
            'repo_url': None,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'tickets': []
        }
        
        # Create GitHub repo if requested
        if create_github_repo:
            repo_info = self._create_github_repo(name, description)
            if repo_info:
                project['repo_name'] = repo_info['name']
                project['repo_url'] = repo_info['url']
        
        projects[project_id] = project
        self._save_projects(projects)
        
        return project
    
    def get_project(self, project_id: str) -> Optional[Dict]:
        """Get project by ID"""
        projects = self._load_projects()
        return projects.get(project_id)
    
    def list_projects(self) -> List[Dict]:
        """List all projects"""
        projects = self._load_projects()
        return list(projects.values())
    
    def update_project(self, project_id: str, updates: Dict) -> Optional[Dict]:
        """Update project"""
        projects = self._load_projects()
        
        if project_id not in projects:
            return None
        
        projects[project_id].update(updates)
        projects[project_id]['updated_at'] = datetime.now().isoformat()
        
        self._save_projects(projects)
        return projects[project_id]
    
    def delete_project(self, project_id: str) -> bool:
        """Delete project"""
        projects = self._load_projects()
        
        if project_id in projects:
            del projects[project_id]
            self._save_projects(projects)
            return True
        
        return False
    
    def connect_repo(self, project_id: str, repo_name: str) -> Optional[Dict]:
        """
        Connect existing GitHub repo to project
        
        Args:
            project_id: Project ID
            repo_name: Repository name (format: owner/repo)
            
        Returns:
            Updated project dict
        """
        projects = self._load_projects()
        
        if project_id not in projects:
            return None
        
        # Get repo info from GitHub
        try:
            result = subprocess.run(
                ['gh', 'repo', 'view', repo_name, '--json', 'name,url,owner'],
                capture_output=True,
                text=True,
                check=True
            )
            
            repo_info = json.loads(result.stdout)
            
            projects[project_id]['repo_name'] = f"{repo_info['owner']['login']}/{repo_info['name']}"
            projects[project_id]['repo_url'] = repo_info['url']
            projects[project_id]['updated_at'] = datetime.now().isoformat()
            
            self._save_projects(projects)
            return projects[project_id]
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to get repo info: {e}")
            return None
    
    # ─────────────────────────────────────────────────────
    # TICKET MANAGEMENT
    # ─────────────────────────────────────────────────────
    
    def add_ticket(self, 
                   project_id: str,
                   ticket_id: str,
                   description: str,
                   pr_url: Optional[str] = None) -> Optional[Dict]:
        """
        Add ticket to project
        
        Args:
            project_id: Project ID
            ticket_id: Ticket ID (e.g., FEAT-001)
            description: Ticket description
            pr_url: Pull request URL (optional)
            
        Returns:
            Updated project dict
        """
        projects = self._load_projects()
        
        if project_id not in projects:
            return None
        
        ticket = {
            'ticket_id': ticket_id,
            'description': description,
            'pr_url': pr_url,
            'created_at': datetime.now().isoformat(),
            'status': 'completed' if pr_url else 'in_progress'
        }
        
        # Get PR status if URL provided
        if pr_url:
            pr_status = self.get_pr_status(pr_url)
            if pr_status:
                ticket['pr_status'] = pr_status
        
        projects[project_id]['tickets'].append(ticket)
        projects[project_id]['updated_at'] = datetime.now().isoformat()
        
        self._save_projects(projects)
        return projects[project_id]
    
    def get_project_tickets(self, project_id: str) -> List[Dict]:
        """Get all tickets for a project with refreshed PR statuses"""
        project = self.get_project(project_id)
        if not project:
            return []
        
        # Refresh PR statuses
        tickets = project['tickets']
        for ticket in tickets:
            if ticket.get('pr_url'):
                pr_status = self.get_pr_status(ticket['pr_url'])
                if pr_status:
                    ticket['pr_status'] = pr_status
        
        return tickets
    
    def update_ticket(self, 
                     project_id: str,
                     ticket_id: str,
                     updates: Dict) -> Optional[Dict]:
        """Update a ticket"""
        projects = self._load_projects()
        
        if project_id not in projects:
            return None
        
        for ticket in projects[project_id]['tickets']:
            if ticket['ticket_id'] == ticket_id:
                ticket.update(updates)
                projects[project_id]['updated_at'] = datetime.now().isoformat()
                self._save_projects(projects)
                return ticket
        
        return None
    
    # ─────────────────────────────────────────────────────
    # PR STATUS TRACKING
    # ─────────────────────────────────────────────────────
    
    def get_pr_status(self, pr_url: str) -> Optional[Dict]:
        """
        Get PR status from GitHub
        
        Args:
            pr_url: Pull request URL (e.g., https://github.com/owner/repo/pull/123)
            
        Returns:
            Dict with PR status info or None
        """
        if not pr_url:
            return None
        
        try:
            # Extract owner, repo, and PR number from URL
            # Format: https://github.com/owner/repo/pull/123
            parts = pr_url.rstrip('/').split('/')
            if len(parts) < 7 or parts[5] != 'pull':
                return None
            
            owner = parts[3]
            repo = parts[4]
            pr_number = parts[6]
            
            # Use gh CLI to get PR status
            result = subprocess.run(
                [
                    'gh', 'pr', 'view', pr_number,
                    '--repo', f"{owner}/{repo}",
                    '--json', 'state,isDraft,merged,mergedAt,closedAt,url'
                ],
                capture_output=True,
                text=True,
                check=True
            )
            
            data = json.loads(result.stdout)
            
            # Determine user-friendly status
            if data.get('merged'):
                status = 'merged'
                status_label = 'Merged'
            elif data.get('state') == 'CLOSED':
                status = 'closed'
                status_label = 'Closed'
            elif data.get('isDraft'):
                status = 'draft'
                status_label = 'Draft'
            elif data.get('state') == 'OPEN':
                status = 'open'
                status_label = 'Open'
            else:
                status = 'unknown'
                status_label = 'Unknown'
            
            return {
                'status': status,
                'status_label': status_label,
                'merged': data.get('merged', False),
                'merged_at': data.get('mergedAt'),
                'closed_at': data.get('closedAt'),
                'url': data.get('url')
            }
            
        except Exception as e:
            print(f"Failed to get PR status: {e}")
            return None
    
    # ─────────────────────────────────────────────────────
    # GITHUB OPERATIONS
    # ─────────────────────────────────────────────────────
    
    def _create_github_repo(self, name: str, description: str) -> Optional[Dict]:
        """
        Create a new GitHub repository
        
        Args:
            name: Repository name
            description: Repository description
            
        Returns:
            Repository info dict or None
        """
        try:
            # Sanitize repo name (lowercase, replace spaces with dashes)
            repo_name = name.lower().replace(' ', '-').replace('_', '-')
            
            # Create repo using gh CLI
            result = subprocess.run(
                [
                    'gh', 'repo', 'create', repo_name,
                    '--public',
                    '--description', description,
                    '--clone=false'
                ],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Get repo info
            result = subprocess.run(
                ['gh', 'repo', 'view', repo_name, '--json', 'name,url,owner'],
                capture_output=True,
                text=True,
                check=True
            )
            
            repo_info = json.loads(result.stdout)
            
            return {
                'name': f"{repo_info['owner']['login']}/{repo_info['name']}",
                'url': repo_info['url']
            }
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to create GitHub repo: {e}")
            print(f"STDERR: {e.stderr}")
            return None
    
    def initialize_repo(self, project_id: str) -> bool:
        """
        Initialize GitHub repository with README
        
        Args:
            project_id: Project ID
            
        Returns:
            True if successful
        """
        project = self.get_project(project_id)
        if not project or not project.get('repo_name'):
            return False
        
        try:
            # Clone repo
            repo_name = project['repo_name']
            clone_path = Path.home() / 'repos' / repo_name.split('/')[-1]
            
            if not clone_path.exists():
                subprocess.run(
                    ['gh', 'repo', 'clone', repo_name, str(clone_path)],
                    check=True
                )
            
            # Create README
            readme_path = clone_path / 'README.md'
            readme_content = f"""# {project['name']}

{project['description']}

## Project Information

- Created: {project['created_at']}
- Managed by: AI Dev Assistant

## Getting Started

This project is managed using AI Dev Assistant for automated code generation and PR workflows.
"""
            
            readme_path.write_text(readme_content)
            
            # Commit and push
            subprocess.run(['git', 'add', 'README.md'], cwd=clone_path, check=True)
            subprocess.run(
                ['git', 'commit', '-m', 'Initial commit: Add README'],
                cwd=clone_path,
                check=True
            )
            subprocess.run(['git', 'push', 'origin', 'main'], cwd=clone_path, check=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to initialize repo: {e}")
            return False
    
    # ─────────────────────────────────────────────────────
    # PERSISTENCE
    # ─────────────────────────────────────────────────────
    
    def _load_projects(self) -> Dict:
        """Load projects from JSON file"""
        if not self.projects_file.exists():
            return {}
        
        with open(self.projects_file, 'r') as f:
            return json.load(f)
    
    def _save_projects(self, projects: Dict):
        """Save projects to JSON file"""
        with open(self.projects_file, 'w') as f:
            json.dump(projects, f, indent=2)


# ─────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────

def test_project_manager():
    """Test project manager"""
    manager = ProjectManager('./test_data')
    
    # Create project
    project = manager.create_project(
        name='Test Project',
        description='A test project for AI Dev Assistant',
        create_github_repo=False
    )
    
    print(f"✓ Created project: {project['id']}")
    
    # Add ticket
    manager.add_ticket(
        project['id'],
        'FEAT-001',
        'Create landing page',
        pr_url='https://github.com/user/repo/pull/1'
    )
    
    print(f"✓ Added ticket: FEAT-001")
    
    # List projects
    projects = manager.list_projects()
    print(f"✓ Total projects: {len(projects)}")
    
    # Get tickets
    tickets = manager.get_project_tickets(project['id'])
    print(f"✓ Total tickets: {len(tickets)}")


if __name__ == '__main__':
    test_project_manager()
