#!/usr/bin/env python3
"""
Advanced Code Editor
Handles editing existing files with diffs, patches, and safe updates
"""

import os
import shutil
import difflib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re


@dataclass
class Edit:
    """Represents a code edit operation"""
    file_path: str
    operation: str  # 'replace', 'insert', 'delete', 'full_replace'
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    success: bool = False
    error: Optional[str] = None


@dataclass
class EditResult:
    """Result of applying edits"""
    success: bool
    edits_applied: List[Edit]
    edits_failed: List[Edit]
    backup_path: Optional[str] = None
    diff: Optional[str] = None


class CodeEditor:
    """
    Advanced code editor with multiple edit strategies
    
    Features:
    - Multiple edit strategies (line-based, search-replace, full file)
    - Diff generation and visualization
    - Safe editing with automatic backups
    - Validation before applying changes
    - Rollback capability
    """
    
    def __init__(self, repo_path: str, create_backups: bool = True):
        """
        Initialize code editor
        
        Args:
            repo_path: Path to repository root
            create_backups: Whether to create backup files
        """
        self.repo_path = Path(repo_path)
        self.create_backups = create_backups
        self.backup_dir = self.repo_path / '.ai-dev-assistant-backups'
        
        if create_backups:
            self.backup_dir.mkdir(exist_ok=True)
    
    def apply_edits(self, edits: List[Edit]) -> EditResult:
        """
        Apply a list of edits
        
        Args:
            edits: List of Edit objects to apply
            
        Returns:
            EditResult with success status and details
        """
        applied = []
        failed = []
        backup_path = None
        
        # Group edits by file
        edits_by_file = {}
        for edit in edits:
            if edit.file_path not in edits_by_file:
                edits_by_file[edit.file_path] = []
            edits_by_file[edit.file_path].append(edit)
        
        # Apply edits file by file
        for file_path, file_edits in edits_by_file.items():
            full_path = self.repo_path / file_path
            
            # Create backup
            if self.create_backups and full_path.exists():
                backup_path = self._create_backup(full_path)
            
            try:
                # Read current content
                if full_path.exists():
                    with open(full_path, 'r', encoding='utf-8') as f:
                        current_content = f.read()
                else:
                    current_content = ""
                
                # Apply edits sequentially
                modified_content = current_content
                
                for edit in file_edits:
                    if edit.operation == 'full_replace':
                        modified_content = edit.new_content
                        edit.success = True
                    
                    elif edit.operation == 'replace':
                        if edit.old_content in modified_content:
                            modified_content = modified_content.replace(
                                edit.old_content,
                                edit.new_content,
                                1  # Only first occurrence
                            )
                            edit.success = True
                        else:
                            edit.error = "Old content not found in file"
                            edit.success = False
                    
                    elif edit.operation == 'insert':
                        lines = modified_content.split('\n')
                        if 0 <= edit.line_start <= len(lines):
                            lines.insert(edit.line_start, edit.new_content)
                            modified_content = '\n'.join(lines)
                            edit.success = True
                        else:
                            edit.error = f"Invalid line number: {edit.line_start}"
                            edit.success = False
                    
                    elif edit.operation == 'delete':
                        lines = modified_content.split('\n')
                        if 0 <= edit.line_start < len(lines) and edit.line_end <= len(lines):
                            del lines[edit.line_start:edit.line_end]
                            modified_content = '\n'.join(lines)
                            edit.success = True
                        else:
                            edit.error = f"Invalid line range: {edit.line_start}-{edit.line_end}"
                            edit.success = False
                    
                    if edit.success:
                        applied.append(edit)
                    else:
                        failed.append(edit)
                
                # Write modified content
                if any(e.success for e in file_edits):
                    # Create parent directories if needed
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(modified_content)
                    
                    print(f"✓ Updated: {file_path}")
                
            except Exception as e:
                for edit in file_edits:
                    edit.error = str(e)
                    edit.success = False
                    failed.append(edit)
        
        # Generate diff
        diff = None
        if applied:
            diff = self.generate_diff_summary(applied)
        
        return EditResult(
            success=len(failed) == 0,
            edits_applied=applied,
            edits_failed=failed,
            backup_path=str(backup_path) if backup_path else None,
            diff=diff
        )
    
    def create_edit_from_ai_output(self,
                                   file_path: str,
                                   ai_new_content: str,
                                   operation: str = 'auto') -> Edit:
        """
        Create an Edit from AI-generated content
        
        Args:
            file_path: Relative path to file
            ai_new_content: New content generated by AI
            operation: 'auto', 'full_replace', or 'smart_replace'
            
        Returns:
            Edit object
        """
        full_path = self.repo_path / file_path
        
        # Read current content if file exists
        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                old_content = f.read()
        else:
            old_content = ""
        
        # Determine operation
        if operation == 'auto':
            if not old_content:
                operation = 'full_replace'
            else:
                # Try to find what changed
                operation = 'full_replace'  # Simplified for now
        
        return Edit(
            file_path=file_path,
            operation=operation,
            old_content=old_content if old_content else None,
            new_content=ai_new_content
        )
    
    def generate_diff(self, old_content: str, new_content: str, filename: str = '') -> str:
        """
        Generate a unified diff
        
        Args:
            old_content: Original content
            new_content: Modified content
            filename: Optional filename for diff header
            
        Returns:
            Unified diff string
        """
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{filename}" if filename else "a/file",
            tofile=f"b/{filename}" if filename else "b/file",
            lineterm=''
        )
        
        return ''.join(diff)
    
    def generate_diff_summary(self, edits: List[Edit]) -> str:
        """
        Generate a human-readable diff summary
        
        Args:
            edits: List of applied edits
            
        Returns:
            Formatted diff summary
        """
        summary_parts = []
        
        summary_parts.append("=" * 60)
        summary_parts.append("CHANGES SUMMARY")
        summary_parts.append("=" * 60)
        
        for edit in edits:
            summary_parts.append(f"\nFile: {edit.file_path}")
            summary_parts.append(f"Operation: {edit.operation}")
            
            if edit.operation == 'full_replace' and edit.old_content:
                # Show unified diff
                diff = self.generate_diff(
                    edit.old_content or "",
                    edit.new_content or "",
                    edit.file_path
                )
                summary_parts.append(diff)
            elif edit.operation == 'replace':
                summary_parts.append(f"\n- {edit.old_content[:100]}...")
                summary_parts.append(f"+ {edit.new_content[:100]}...")
            
            summary_parts.append("-" * 60)
        
        return '\n'.join(summary_parts)
    
    def validate_edit(self, edit: Edit) -> Tuple[bool, Optional[str]]:
        """
        Validate an edit before applying
        
        Args:
            edit: Edit to validate
            
        Returns:
            (is_valid, error_message)
        """
        # Check file path is relative and safe
        try:
            file_path = Path(edit.file_path)
            if file_path.is_absolute():
                return False, "File path must be relative"
            
            # Check for path traversal
            full_path = (self.repo_path / file_path).resolve()
            if not str(full_path).startswith(str(self.repo_path)):
                return False, "File path outside repository"
        except:
            return False, "Invalid file path"
        
        # Check operation is valid
        valid_ops = ['replace', 'insert', 'delete', 'full_replace']
        if edit.operation not in valid_ops:
            return False, f"Invalid operation: {edit.operation}"
        
        # Check required fields based on operation
        if edit.operation == 'replace':
            if not edit.old_content or not edit.new_content:
                return False, "Replace operation requires old_content and new_content"
        
        elif edit.operation == 'insert':
            if edit.new_content is None or edit.line_start is None:
                return False, "Insert operation requires new_content and line_start"
        
        elif edit.operation == 'delete':
            if edit.line_start is None or edit.line_end is None:
                return False, "Delete operation requires line_start and line_end"
        
        elif edit.operation == 'full_replace':
            if edit.new_content is None:
                return False, "Full replace requires new_content"
        
        return True, None
    
    def rollback(self, backup_path: str) -> bool:
        """
        Rollback changes by restoring from backup
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if successful
        """
        try:
            backup = Path(backup_path)
            if not backup.exists():
                print(f"❌ Backup not found: {backup_path}")
                return False
            
            # Extract original path from backup filename
            # Format: filename.ext.backup.TIMESTAMP
            original_name = backup.name.split('.backup.')[0]
            original_path = backup.parent / original_name
            
            # Restore from backup
            shutil.copy2(backup, original_path)
            print(f"✓ Restored: {original_path}")
            
            return True
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return False
    
    def cleanup_backups(self, keep_latest: int = 5):
        """
        Clean up old backup files
        
        Args:
            keep_latest: Number of latest backups to keep per file
        """
        if not self.backup_dir.exists():
            return
        
        # Group backups by original filename
        backups_by_file = {}
        for backup in self.backup_dir.glob('*.backup.*'):
            original = backup.name.split('.backup.')[0]
            if original not in backups_by_file:
                backups_by_file[original] = []
            backups_by_file[original].append(backup)
        
        # Keep only latest N backups per file
        for original, backups in backups_by_file.items():
            # Sort by modification time (newest first)
            backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            # Remove old backups
            for backup in backups[keep_latest:]:
                backup.unlink()
                print(f"🗑️  Removed old backup: {backup.name}")
    
    # ─────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────
    
    def _create_backup(self, file_path: Path) -> Path:
        """Create a backup of a file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{file_path.name}.backup.{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(file_path, backup_path)
        return backup_path


def test_code_editor():
    """Test the code editor"""
    import tempfile
    
    # Create a temp directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        editor = CodeEditor(tmpdir)
        
        # Test 1: Create new file
        print("\n🧪 Test 1: Create new file")
        edit1 = Edit(
            file_path='test.txt',
            operation='full_replace',
            new_content='Hello World\nLine 2\nLine 3'
        )
        result = editor.apply_edits([edit1])
        print(f"Success: {result.success}")
        
        # Test 2: Replace content
        print("\n🧪 Test 2: Replace content")
        edit2 = Edit(
            file_path='test.txt',
            operation='replace',
            old_content='World',
            new_content='Universe'
        )
        result = editor.apply_edits([edit2])
        print(f"Success: {result.success}")
        if result.diff:
            print(result.diff)
        
        # Test 3: Show final content
        print("\n📄 Final content:")
        with open(Path(tmpdir) / 'test.txt', 'r') as f:
            print(f.read())


if __name__ == '__main__':
    test_code_editor()
