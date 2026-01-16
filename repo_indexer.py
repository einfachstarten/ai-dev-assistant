#!/usr/bin/env python3
"""
Repository Indexer
Scans and indexes repository files for context-aware code generation
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, asdict
import mimetypes
import hashlib


@dataclass
class FileInfo:
    """Information about a file in the repository"""
    path: str
    relative_path: str
    size: int
    extension: str
    is_code: bool
    content: Optional[str] = None
    content_hash: Optional[str] = None
    lines: int = 0
    
    def to_dict(self):
        return asdict(self)


class RepositoryIndexer:
    """
    Indexes a repository to provide context for AI code generation
    
    Features:
    - File discovery and filtering
    - Content caching
    - Project structure detection
    - Dependency analysis
    - Smart ignore patterns
    """
    
    # Files/directories to always ignore
    IGNORE_DIRS = {
        '.git', '.svn', '.hg',
        'node_modules', '__pycache__', '.pytest_cache',
        'venv', 'env', '.venv', '.env',
        'dist', 'build', '.next', '.nuxt',
        'coverage', '.coverage', 'htmlcov',
        '.idea', '.vscode', '.DS_Store',
        'tmp', 'temp', 'cache'
    }
    
    IGNORE_FILES = {
        '.DS_Store',
        'package-lock.json', 'yarn.lock', 'poetry.lock',
        '.env', '.env.local', '.env.production'
    }
    
    # Code file extensions we care about
    CODE_EXTENSIONS = {
        '.js', '.jsx', '.ts', '.tsx',
        '.py', '.rb', '.php', '.java',
        '.html', '.css', '.scss', '.sass', '.less',
        '.json', '.xml', '.yaml', '.yml',
        '.md', '.txt',
        '.vue', '.svelte',
        '.go', '.rs', '.c', '.cpp', '.h',
        '.sh', '.bash'
    }
    
    # Binary extensions to skip
    BINARY_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.ico', '.svg',
        '.pdf', '.zip', '.tar', '.gz', '.rar',
        '.exe', '.dll', '.so', '.dylib',
        '.mp3', '.mp4', '.avi', '.mov',
        '.woff', '.woff2', '.ttf', '.eot'
    }
    
    def __init__(self, repo_path: str):
        """
        Initialize repository indexer
        
        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = Path(repo_path).resolve()
        self.files: Dict[str, FileInfo] = {}
        self.project_type = None
        self.dependencies = {}
        self._cache_file = self.repo_path / '.ai-dev-assistant-cache.json'
        
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")
    
    def index(self, force_refresh: bool = False) -> Dict[str, FileInfo]:
        """
        Index the repository
        
        Args:
            force_refresh: If True, ignore cache and re-scan
            
        Returns:
            Dictionary of relative_path -> FileInfo
        """
        print(f"📁 Indexing repository: {self.repo_path}")
        
        # Try to load from cache
        if not force_refresh and self._load_cache():
            print(f"✅ Loaded {len(self.files)} files from cache")
            return self.files
        
        # Scan repository
        self.files = {}
        file_count = 0
        
        for root, dirs, files in os.walk(self.repo_path):
            # Filter directories
            dirs[:] = [d for d in dirs if not self._should_ignore_dir(d)]
            
            for filename in files:
                if self._should_ignore_file(filename):
                    continue
                
                filepath = Path(root) / filename
                relative_path = str(filepath.relative_to(self.repo_path))
                
                file_info = self._create_file_info(filepath, relative_path)
                if file_info:
                    self.files[relative_path] = file_info
                    file_count += 1
        
        print(f"✅ Indexed {file_count} files")
        
        # Detect project type
        self._detect_project_type()
        
        # Parse dependencies
        self._parse_dependencies()
        
        # Save cache
        self._save_cache()
        
        return self.files
    
    def get_file_content(self, relative_path: str) -> Optional[str]:
        """Get content of a specific file"""
        file_info = self.files.get(relative_path)
        if not file_info:
            return None
        
        if file_info.content is not None:
            return file_info.content
        
        # Load content if not cached
        filepath = self.repo_path / relative_path
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                file_info.content = content
                return content
        except Exception as e:
            print(f"⚠️  Could not read {relative_path}: {e}")
            return None
    
    def get_code_files(self, max_size: int = 100_000) -> Dict[str, FileInfo]:
        """
        Get all code files under a certain size
        
        Args:
            max_size: Maximum file size in bytes
            
        Returns:
            Filtered dictionary of code files
        """
        return {
            path: info
            for path, info in self.files.items()
            if info.is_code and info.size <= max_size
        }
    
    def get_file_tree(self) -> Dict:
        """
        Get repository structure as a tree
        
        Returns:
            Nested dictionary representing directory structure
        """
        tree = {}
        
        for relative_path in sorted(self.files.keys()):
            parts = relative_path.split(os.sep)
            current = tree
            
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    # File
                    current[part] = self.files[relative_path].to_dict()
                else:
                    # Directory
                    if part not in current:
                        current[part] = {}
                    current = current[part]
        
        return tree
    
    def search_files(self, pattern: str) -> List[FileInfo]:
        """
        Search for files matching a pattern
        
        Args:
            pattern: Search pattern (supports wildcards)
            
        Returns:
            List of matching FileInfo objects
        """
        import fnmatch
        
        matches = []
        for path, info in self.files.items():
            if fnmatch.fnmatch(path.lower(), f"*{pattern.lower()}*"):
                matches.append(info)
        
        return matches
    
    def get_summary(self) -> Dict:
        """Get a summary of the repository"""
        code_files = [f for f in self.files.values() if f.is_code]
        
        total_lines = sum(f.lines for f in code_files)
        total_size = sum(f.size for f in self.files.values())
        
        # Count by extension
        by_extension = {}
        for file_info in code_files:
            ext = file_info.extension
            if ext not in by_extension:
                by_extension[ext] = {'count': 0, 'lines': 0}
            by_extension[ext]['count'] += 1
            by_extension[ext]['lines'] += file_info.lines
        
        return {
            'total_files': len(self.files),
            'code_files': len(code_files),
            'total_lines': total_lines,
            'total_size_mb': round(total_size / 1_000_000, 2),
            'project_type': self.project_type,
            'by_extension': by_extension,
            'dependencies': self.dependencies
        }
    
    # ─────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────
    
    def _should_ignore_dir(self, dirname: str) -> bool:
        """Check if directory should be ignored"""
        return dirname in self.IGNORE_DIRS or dirname.startswith('.')
    
    def _should_ignore_file(self, filename: str) -> bool:
        """Check if file should be ignored"""
        if filename in self.IGNORE_FILES:
            return True

        # Ignore hidden files starting with . (except known code files like .gitignore)
        if filename.startswith('.') and filename not in {'.gitignore', '.dockerignore'}:
            return True

        ext = Path(filename).suffix.lower()
        return ext in self.BINARY_EXTENSIONS
    
    def _create_file_info(self, filepath: Path, relative_path: str) -> Optional[FileInfo]:
        """Create FileInfo object for a file"""
        try:
            stat = filepath.stat()
            ext = filepath.suffix.lower()
            is_code = ext in self.CODE_EXTENSIONS
            
            # Read content for code files
            content = None
            lines = 0
            content_hash = None
            
            if is_code and stat.st_size < 500_000:  # Max 500KB for auto-loading
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.count('\n') + 1
                        content_hash = hashlib.md5(content.encode()).hexdigest()
                except:
                    pass
            
            return FileInfo(
                path=str(filepath),
                relative_path=relative_path,
                size=stat.st_size,
                extension=ext,
                is_code=is_code,
                content=content,
                content_hash=content_hash,
                lines=lines
            )
        except Exception as e:
            print(f"⚠️  Error processing {relative_path}: {e}")
            return None
    
    def _detect_project_type(self):
        """Detect project type from files"""
        if 'package.json' in self.files:
            package_json = self.get_file_content('package.json')
            if package_json:
                try:
                    data = json.loads(package_json)
                    deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                    
                    if 'react' in deps:
                        self.project_type = 'React'
                    elif 'vue' in deps:
                        self.project_type = 'Vue'
                    elif 'next' in deps:
                        self.project_type = 'Next.js'
                    elif 'express' in deps:
                        self.project_type = 'Node.js/Express'
                    else:
                        self.project_type = 'JavaScript'
                except:
                    self.project_type = 'JavaScript'
        
        elif 'requirements.txt' in self.files or 'pyproject.toml' in self.files:
            self.project_type = 'Python'
        
        elif 'Gemfile' in self.files:
            self.project_type = 'Ruby'
        
        elif 'composer.json' in self.files:
            self.project_type = 'PHP'
        
        elif 'go.mod' in self.files:
            self.project_type = 'Go'
        
        elif 'Cargo.toml' in self.files:
            self.project_type = 'Rust'
        
        else:
            # Check for plain HTML
            html_files = [f for f in self.files.values() if f.extension == '.html']
            if html_files:
                self.project_type = 'HTML/CSS/JS'
            else:
                self.project_type = 'Unknown'
    
    def _parse_dependencies(self):
        """Parse project dependencies"""
        # Node.js
        if 'package.json' in self.files:
            content = self.get_file_content('package.json')
            if content:
                try:
                    data = json.loads(content)
                    self.dependencies['npm'] = {
                        **data.get('dependencies', {}),
                        **data.get('devDependencies', {})
                    }
                except:
                    pass
        
        # Python
        if 'requirements.txt' in self.files:
            content = self.get_file_content('requirements.txt')
            if content:
                self.dependencies['pip'] = [
                    line.strip() for line in content.split('\n')
                    if line.strip() and not line.startswith('#')
                ]
    
    def _load_cache(self) -> bool:
        """Load index from cache if available"""
        if not self._cache_file.exists():
            return False
        
        try:
            with open(self._cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Validate cache version
            if cache_data.get('version') != '1.0':
                return False
            
            # Restore files
            for path, data in cache_data.get('files', {}).items():
                self.files[path] = FileInfo(**data)
            
            self.project_type = cache_data.get('project_type')
            self.dependencies = cache_data.get('dependencies', {})
            
            return True
        except Exception as e:
            print(f"⚠️  Failed to load cache: {e}")
            return False
    
    def _save_cache(self):
        """Save index to cache"""
        try:
            cache_data = {
                'version': '1.0',
                'project_type': self.project_type,
                'dependencies': self.dependencies,
                'files': {
                    path: info.to_dict()
                    for path, info in self.files.items()
                }
            }
            
            with open(self._cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Failed to save cache: {e}")


def test_indexer():
    """Test the repository indexer"""
    import sys
    
    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
    else:
        repo_path = '.'
    
    indexer = RepositoryIndexer(repo_path)
    indexer.index()
    
    summary = indexer.get_summary()
    print("\n📊 Repository Summary:")
    print(json.dumps(summary, indent=2))
    
    print("\n📁 File Tree:")
    tree = indexer.get_file_tree()
    print(json.dumps(tree, indent=2)[:500] + "...")


if __name__ == '__main__':
    test_indexer()
