#!/usr/bin/env python3
"""
Smart Context Selector
Intelligently selects relevant files for AI code generation based on the task
"""

import re
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from pathlib import Path
from repo_indexer import FileInfo, RepositoryIndexer


@dataclass
class RelevantFile:
    """A file with relevance score and reasoning"""
    file_info: FileInfo
    score: float
    reasons: List[str]
    
    def __lt__(self, other):
        return self.score < other.score


class SmartContextSelector:
    """
    Intelligently selects relevant files for a given task
    
    Scoring factors:
    - Keyword matching (filename, content)
    - File type relevance
    - Dependency relationships
    - Recent modifications (if available)
    - File size (prefer smaller files)
    - Path similarity
    """
    
    # Weights for different scoring factors
    WEIGHTS = {
        'filename_exact': 10.0,
        'filename_partial': 5.0,
        'content_high': 8.0,
        'content_medium': 4.0,
        'content_low': 1.0,
        'extension_match': 3.0,
        'path_similarity': 2.0,
        'dependency': 6.0,
        'small_file_bonus': 1.0
    }
    
    # Maximum number of files to include in context
    MAX_FILES = 10
    
    # Maximum total tokens (approximate: 1 token ≈ 4 chars)
    MAX_TOKENS = 8000
    
    def __init__(self, indexer: RepositoryIndexer):
        """
        Initialize context selector
        
        Args:
            indexer: Repository indexer with indexed files
        """
        self.indexer = indexer
        self.files = indexer.files
    
    def select_context(self, 
                      task_description: str,
                      target_files: List[str] = None,
                      max_files: int = None,
                      max_tokens: int = None) -> List[RelevantFile]:
        """
        Select relevant files for a task
        
        Args:
            task_description: Natural language description of the task
            target_files: Specific files mentioned in task (e.g., "edit contact.js")
            max_files: Maximum number of files to return
            max_tokens: Maximum total tokens
            
        Returns:
            List of RelevantFile objects, sorted by relevance
        """
        max_files = max_files or self.MAX_FILES
        max_tokens = max_tokens or self.MAX_TOKENS
        
        print(f"🔍 Selecting context for task...")
        
        # Extract keywords from task
        keywords = self._extract_keywords(task_description)
        print(f"📝 Keywords: {', '.join(keywords)}")
        
        # Detect task type
        task_type = self._detect_task_type(task_description)
        print(f"🎯 Task type: {task_type}")
        
        # Score all files
        scored_files = []
        for relative_path, file_info in self.files.items():
            # Skip non-code files
            if not file_info.is_code:
                continue
            
            score, reasons = self._score_file(
                file_info, 
                keywords, 
                task_type,
                target_files or []
            )
            
            if score > 0:
                scored_files.append(RelevantFile(file_info, score, reasons))
        
        # Sort by score
        scored_files.sort(reverse=True)
        
        # Select top files within token budget
        selected = self._select_within_budget(scored_files, max_files, max_tokens)
        
        print(f"✅ Selected {len(selected)} relevant files:")
        for i, rf in enumerate(selected[:5], 1):
            print(f"  {i}. {rf.file_info.relative_path} (score: {rf.score:.1f})")
        
        return selected
    
    def get_context_summary(self, relevant_files: List[RelevantFile]) -> str:
        """
        Generate a summary of the selected context
        
        Returns:
            Formatted string describing the context
        """
        summary_parts = []
        
        summary_parts.append(f"📁 Repository Context ({len(relevant_files)} files):\n")
        
        for i, rf in enumerate(relevant_files, 1):
            file_info = rf.file_info
            summary_parts.append(
                f"{i}. {file_info.relative_path} "
                f"({file_info.lines} lines, {file_info.extension})"
            )
            if rf.reasons:
                summary_parts.append(f"   Reasons: {', '.join(rf.reasons[:2])}")
        
        return '\n'.join(summary_parts)
    
    def format_context_for_ai(self, relevant_files: List[RelevantFile]) -> str:
        """
        Format selected files for AI prompt with repository overview and dependencies

        Returns:
            Formatted string with file contents
        """
        context_parts = []

        # Repository Overview
        context_parts.append("=== REPOSITORY OVERVIEW ===\n")
        context_parts.append(f"Project Type: {self.indexer.project_type}")

        summary = self.indexer.get_summary()
        context_parts.append(f"Total Files: {summary['total_files']} ({summary['code_files']} code files)")
        context_parts.append(f"Total Lines: {summary['total_lines']:,}")

        # File structure overview
        context_parts.append(f"\n📁 Repository Structure:")
        file_tree = self._build_file_tree_overview()
        context_parts.append(file_tree)

        # Dependencies
        if self.indexer.dependencies:
            context_parts.append(f"\n📦 Dependencies:")
            for dep_type, deps in self.indexer.dependencies.items():
                if isinstance(deps, dict):
                    context_parts.append(f"  {dep_type}: {', '.join(list(deps.keys())[:10])}")
                elif isinstance(deps, list):
                    context_parts.append(f"  {dep_type}: {', '.join(deps[:10])}")

        # File extensions breakdown
        if summary.get('by_extension'):
            context_parts.append(f"\n📊 Code Distribution:")
            for ext, stats in sorted(summary['by_extension'].items(), key=lambda x: x[1]['lines'], reverse=True)[:5]:
                context_parts.append(f"  {ext}: {stats['count']} files, {stats['lines']} lines")

        context_parts.append(f"\n{'='*60}")
        context_parts.append(f"=== RELEVANT FILES FOR THIS TASK ({len(relevant_files)}) ===\n")

        for rf in relevant_files:
            file_info = rf.file_info
            content = self.indexer.get_file_content(file_info.relative_path)

            if content:
                context_parts.append(f"\n--- FILE: {file_info.relative_path} ---")
                context_parts.append(f"Lines: {file_info.lines} | Extension: {file_info.extension}")
                context_parts.append(f"Relevance: {', '.join(rf.reasons[:2])}")

                # Add detected dependencies for this file
                file_deps = self._detect_file_dependencies(content, file_info.extension)
                if file_deps:
                    context_parts.append(f"Dependencies: {', '.join(file_deps[:5])}")

                context_parts.append("")
                context_parts.append(content)
                context_parts.append(f"\n--- END FILE: {file_info.relative_path} ---\n")

        return '\n'.join(context_parts)
    
    # ─────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'should', 'could', 'can', 'may', 'might', 'must', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'create', 'add', 'update', 'delete', 'make', 'build', 'implement'
        }
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z_][\w-]*\b', text.lower())
        
        # Filter and deduplicate
        keywords = []
        seen = set()
        for word in words:
            if len(word) > 2 and word not in stop_words and word not in seen:
                keywords.append(word)
                seen.add(word)
        
        return keywords
    
    def _detect_task_type(self, description: str) -> str:
        """Detect what type of task this is"""
        desc_lower = description.lower()
        
        # Edit existing file
        edit_keywords = ['edit', 'modify', 'update', 'change', 'fix', 'refactor']
        if any(kw in desc_lower for kw in edit_keywords):
            return 'edit'
        
        # Create new feature
        create_keywords = ['create', 'add', 'build', 'implement', 'new']
        if any(kw in desc_lower for kw in create_keywords):
            return 'create'
        
        # Bug fix
        if 'bug' in desc_lower or 'error' in desc_lower or 'fix' in desc_lower:
            return 'bugfix'
        
        # Style/UI changes
        if any(kw in desc_lower for kw in ['style', 'css', 'design', 'ui', 'layout']):
            return 'style'
        
        return 'general'
    
    def _score_file(self, 
                   file_info: FileInfo,
                   keywords: List[str],
                   task_type: str,
                   target_files: List[str]) -> Tuple[float, List[str]]:
        """
        Score a file's relevance to the task
        
        Returns:
            (score, reasons)
        """
        score = 0.0
        reasons = []
        
        filename = file_info.relative_path.lower()
        content = file_info.content or ''
        content_lower = content.lower()
        
        # 1. Explicit file mention
        for target in target_files:
            if target.lower() in filename:
                score += self.WEIGHTS['filename_exact']
                reasons.append(f"mentioned in task")
                break
        
        # 2. Filename keyword matching
        for keyword in keywords:
            if keyword in filename:
                score += self.WEIGHTS['filename_partial']
                reasons.append(f"filename contains '{keyword}'")
                break
        
        # 3. Content keyword matching (if content available)
        if content:
            keyword_density = 0
            matched_keywords = []
            
            for keyword in keywords:
                count = content_lower.count(keyword)
                if count > 0:
                    keyword_density += count
                    matched_keywords.append(keyword)
            
            if keyword_density > 10:
                score += self.WEIGHTS['content_high']
                reasons.append(f"high keyword density")
            elif keyword_density > 3:
                score += self.WEIGHTS['content_medium']
                reasons.append(f"contains keywords")
            elif keyword_density > 0:
                score += self.WEIGHTS['content_low']
        
        # 4. Extension matching based on task type
        relevant_extensions = self._get_relevant_extensions(task_type, keywords)
        if file_info.extension in relevant_extensions:
            score += self.WEIGHTS['extension_match']
            reasons.append(f"relevant file type")
        
        # 5. Path similarity (if editing similar files)
        if task_type == 'edit' and target_files:
            for target in target_files:
                target_dir = str(Path(target).parent)
                file_dir = str(Path(filename).parent)
                if target_dir == file_dir:
                    score += self.WEIGHTS['path_similarity']
                    reasons.append(f"same directory")
                    break
        
        # 6. Small file bonus (easier to include)
        if file_info.size < 10_000:  # < 10KB
            score += self.WEIGHTS['small_file_bonus']
        
        # 7. Config/utility file bonus
        if self._is_important_file(filename):
            score += 2.0
            reasons.append(f"important config/utility")
        
        return score, reasons
    
    def _get_relevant_extensions(self, task_type: str, keywords: List[str]) -> Set[str]:
        """Get relevant file extensions based on task"""
        extensions = set()
        
        # Always include related extensions
        if any(kw in keywords for kw in ['html', 'page', 'template']):
            extensions.update(['.html', '.css', '.js'])
        
        if any(kw in keywords for kw in ['style', 'css', 'design']):
            extensions.update(['.css', '.scss', '.sass', '.less'])
        
        if any(kw in keywords for kw in ['script', 'javascript', 'function']):
            extensions.update(['.js', '.jsx', '.ts', '.tsx'])
        
        if any(kw in keywords for kw in ['component', 'react', 'vue']):
            extensions.update(['.jsx', '.tsx', '.vue'])
        
        # Task type defaults
        if task_type == 'style':
            extensions.update(['.css', '.scss', '.sass', '.html'])
        elif task_type == 'create':
            # Include all common types
            extensions.update(['.html', '.css', '.js', '.jsx', '.ts', '.tsx'])
        
        return extensions or {'.html', '.css', '.js'}  # Default
    
    def _is_important_file(self, filename: str) -> bool:
        """Check if file is an important config/utility"""
        important_patterns = [
            'config', 'package.json', 'tsconfig', 'webpack',
            'vite', 'next.config', 'tailwind.config',
            'utils', 'helpers', 'constants', 'types'
        ]
        
        return any(pattern in filename.lower() for pattern in important_patterns)
    
    def _select_within_budget(self,
                             scored_files: List[RelevantFile],
                             max_files: int,
                             max_tokens: int) -> List[RelevantFile]:
        """Select files within token budget"""
        selected = []
        total_tokens = 0

        for rf in scored_files:
            if len(selected) >= max_files:
                break

            # Estimate tokens (rough: 1 token ≈ 4 chars)
            file_tokens = (rf.file_info.size // 4) if rf.file_info.size else 0

            if total_tokens + file_tokens > max_tokens:
                # Try to include at least one file even if over budget
                if len(selected) == 0:
                    selected.append(rf)
                break

            selected.append(rf)
            total_tokens += file_tokens

        return selected

    def _build_file_tree_overview(self) -> str:
        """Build a compact tree overview of repository structure"""
        tree_lines = []

        # Group files by directory
        dirs: Dict[str, List[str]] = {}
        for rel_path in sorted(self.files.keys()):
            path_obj = Path(rel_path)
            dir_name = str(path_obj.parent) if path_obj.parent != Path('.') else '/'

            if dir_name not in dirs:
                dirs[dir_name] = []
            dirs[dir_name].append(path_obj.name)

        # Format tree (limit to avoid overwhelming context)
        max_dirs = 10
        max_files_per_dir = 5

        for i, (dir_name, files) in enumerate(sorted(dirs.items())[:max_dirs]):
            tree_lines.append(f"  📁 {dir_name}/")
            for file in files[:max_files_per_dir]:
                tree_lines.append(f"     • {file}")
            if len(files) > max_files_per_dir:
                tree_lines.append(f"     ... and {len(files) - max_files_per_dir} more files")

        if len(dirs) > max_dirs:
            tree_lines.append(f"  ... and {len(dirs) - max_dirs} more directories")

        return '\n'.join(tree_lines)

    def _detect_file_dependencies(self, content: str, extension: str) -> List[str]:
        """Detect imports/requires in file content"""
        dependencies = []

        # JavaScript/TypeScript imports
        if extension in {'.js', '.jsx', '.ts', '.tsx'}:
            # ES6 imports: import X from 'module'
            import_pattern = r"import\s+(?:.*?from\s+)?['\"]([^'\"]+)['\"]"
            dependencies.extend(re.findall(import_pattern, content))

            # require(): const X = require('module')
            require_pattern = r"require\(['\"]([^'\"]+)['\"]\)"
            dependencies.extend(re.findall(require_pattern, content))

        # Python imports
        elif extension == '.py':
            # import module / from module import X
            import_pattern = r"(?:from\s+(\S+)|import\s+(\S+))"
            matches = re.findall(import_pattern, content)
            for match in matches:
                dep = match[0] or match[1]
                if dep:
                    # Get first part of dotted import
                    dependencies.append(dep.split('.')[0])

        # CSS imports
        elif extension in {'.css', '.scss', '.sass'}:
            # @import 'file'
            import_pattern = r"@import\s+['\"]([^'\"]+)['\"]"
            dependencies.extend(re.findall(import_pattern, content))

        # HTML script/link tags
        elif extension == '.html':
            # <script src="file.js">
            script_pattern = r"<script[^>]+src=['\"]([^'\"]+)['\"]"
            dependencies.extend(re.findall(script_pattern, content))

            # <link href="file.css">
            link_pattern = r"<link[^>]+href=['\"]([^'\"]+)['\"]"
            dependencies.extend(re.findall(link_pattern, content))

        # Remove duplicates and filter out external URLs
        unique_deps = []
        seen = set()
        for dep in dependencies:
            # Skip external URLs and node_modules
            if dep.startswith(('http://', 'https://', '//', 'node_modules')):
                continue
            # Skip relative paths that are too generic
            if dep in {'.', '..', './', '../'}:
                continue
            # Get just the module/file name
            dep_name = dep.split('/')[-1].replace('.js', '').replace('.css', '')
            if dep_name and dep_name not in seen:
                unique_deps.append(dep_name)
                seen.add(dep_name)

        return unique_deps[:10]  # Limit to 10 most important


def test_context_selector():
    """Test the context selector"""
    import sys
    
    repo_path = sys.argv[1] if len(sys.argv) > 1 else '.'
    task = sys.argv[2] if len(sys.argv) > 2 else "Create a contact form with validation"
    
    # Index repository
    indexer = RepositoryIndexer(repo_path)
    indexer.index()
    
    # Select context
    selector = SmartContextSelector(indexer)
    relevant = selector.select_context(task)
    
    # Print results
    print("\n" + "="*50)
    print(selector.get_context_summary(relevant))
    print("="*50)


if __name__ == '__main__':
    test_context_selector()
