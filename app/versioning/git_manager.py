"""
Git-based Document Version Manager

Provides version control for ingested documents:
- Commit documents to git repository
- Track changes over time
- Diff between versions
- Rollback to previous versions
- Branch management for document versions
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class GitCommit:
    """Represents a git commit."""
    
    hash: str
    author: str
    date: datetime
    message: str
    files_changed: List[str]


@dataclass
class GitDiff:
    """Represents a diff between two versions."""
    
    from_commit: str
    to_commit: str
    files_changed: List[str]
    additions: int
    deletions: int
    diff_text: str


class GitVersionManager:
    """
    Manages document versioning using git.
    
    Features:
    - Initialize git repository for documents
    - Commit document changes with metadata
    - View version history
    - Diff between versions
    - Rollback to previous versions
    - Tag important versions
    """
    
    def __init__(self, repo_path: Optional[str] = None):
        """
        Initialize git version manager.
        
        Args:
            repo_path: Path to git repository (defaults to data directory)
        """
        if repo_path is None:
            repo_path = os.path.join(os.getcwd(), "data")
        
        self.repo_path = Path(repo_path)
        self.repo_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Git version manager initialized at: {self.repo_path}")
    
    def _run_git_command(self, command: List[str], check: bool = True) -> Tuple[int, str, str]:
        """
        Run a git command in the repository.
        
        Args:
            command: Git command as list of strings
            check: Whether to raise exception on non-zero exit
        
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            result = subprocess.run(
                ["git"] + command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=check
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {' '.join(command)}")
            logger.error(f"Error: {e.stderr}")
            if check:
                raise
            return e.returncode, e.stdout, e.stderr
    
    def is_git_repo(self) -> bool:
        """Check if directory is a git repository."""
        git_dir = self.repo_path / ".git"
        return git_dir.exists() and git_dir.is_dir()
    
    def init_repository(self) -> bool:
        """
        Initialize git repository if not already initialized.
        
        Returns:
            True if initialized or already exists, False on error
        """
        if self.is_git_repo():
            logger.info("Git repository already initialized")
            return True
        
        try:
            returncode, stdout, stderr = self._run_git_command(["init"])
            if returncode == 0:
                logger.info(f"Initialized git repository at {self.repo_path}")
                
                # Set up .gitignore
                self._create_gitignore()
                
                # Initial commit
                self.commit_changes(
                    message="Initial commit - Document versioning setup",
                    author="System",
                    add_all=True
                )
                
                return True
            else:
                logger.error(f"Failed to initialize git repository: {stderr}")
                return False
        except Exception as e:
            logger.error(f"Error initializing git repository: {e}")
            return False
    
    def _create_gitignore(self):
        """Create .gitignore file for the repository."""
        gitignore_path = self.repo_path / ".gitignore"
        
        gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Virtual environments
.venv/
venv/
ENV/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.temp
*.log

# ChromaDB (handled separately)
chroma.sqlite3
chroma.sqlite3-*
"""
        
        with open(gitignore_path, 'w') as f:
            f.write(gitignore_content)
        
        logger.debug("Created .gitignore file")
    
    def commit_changes(
        self,
        message: str,
        author: Optional[str] = None,
        files: Optional[List[str]] = None,
        add_all: bool = False
    ) -> Optional[str]:
        """
        Commit changes to the repository.
        
        Args:
            message: Commit message
            author: Author name (format: "Name <email>")
            files: Specific files to commit
            add_all: Add all changed files
        
        Returns:
            Commit hash if successful, None otherwise
        """
        if not self.is_git_repo():
            logger.error("Not a git repository. Run init_repository() first.")
            return None
        
        try:
            # Stage files
            if add_all:
                self._run_git_command(["add", "."])
            elif files:
                for file in files:
                    self._run_git_command(["add", file])
            else:
                logger.warning("No files specified to commit")
                return None
            
            # Check if there are changes to commit
            returncode, stdout, stderr = self._run_git_command(
                ["diff", "--cached", "--quiet"],
                check=False
            )
            
            if returncode == 0:
                logger.info("No changes to commit")
                return None
            
            # Build commit command
            commit_cmd = ["commit", "-m", message]
            if author:
                commit_cmd.extend(["--author", author])
            
            # Commit
            returncode, stdout, stderr = self._run_git_command(commit_cmd)
            
            if returncode == 0:
                # Get commit hash
                _, commit_hash, _ = self._run_git_command(["rev-parse", "HEAD"])
                commit_hash = commit_hash.strip()
                logger.info(f"Created commit: {commit_hash[:8]} - {message}")
                return commit_hash
            else:
                logger.error(f"Failed to commit: {stderr}")
                return None
        
        except Exception as e:
            logger.error(f"Error committing changes: {e}")
            return None
    
    def get_history(
        self,
        max_count: int = 50,
        file_path: Optional[str] = None
    ) -> List[GitCommit]:
        """
        Get commit history.
        
        Args:
            max_count: Maximum number of commits to return
            file_path: Optional file path to filter history
        
        Returns:
            List of GitCommit objects
        """
        if not self.is_git_repo():
            logger.warning("Not a git repository")
            return []
        
        try:
            # Build git log command
            cmd = [
                "log",
                f"--max-count={max_count}",
                "--pretty=format:%H|%an|%ai|%s",
                "--name-only"
            ]
            
            if file_path:
                cmd.append("--")
                cmd.append(file_path)
            
            returncode, stdout, stderr = self._run_git_command(cmd, check=False)
            
            if returncode != 0 or not stdout:
                return []
            
            # Parse output
            commits = []
            commit_blocks = stdout.strip().split('\n\n')
            
            for block in commit_blocks:
                if not block.strip():
                    continue
                
                lines = block.strip().split('\n')
                if not lines:
                    continue
                
                # Parse commit info (hash|author|date|message)
                commit_info = lines[0].split('|', 3)
                if len(commit_info) < 4:
                    continue
                
                commit_hash, author, date_str, message = commit_info
                
                # Parse files changed
                files_changed = [line.strip() for line in lines[1:] if line.strip()]
                
                # Parse date
                try:
                    commit_date = datetime.fromisoformat(date_str.replace(' ', 'T', 1).rsplit(' ', 1)[0])
                except:
                    commit_date = datetime.now()
                
                commits.append(GitCommit(
                    hash=commit_hash,
                    author=author,
                    date=commit_date,
                    message=message,
                    files_changed=files_changed
                ))
            
            return commits
        
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []
    
    def get_diff(
        self,
        from_commit: str = "HEAD~1",
        to_commit: str = "HEAD",
        file_path: Optional[str] = None
    ) -> Optional[GitDiff]:
        """
        Get diff between two commits.
        
        Args:
            from_commit: Starting commit (default: previous commit)
            to_commit: Ending commit (default: current HEAD)
            file_path: Optional file to limit diff to
        
        Returns:
            GitDiff object or None
        """
        if not self.is_git_repo():
            logger.warning("Not a git repository")
            return None
        
        try:
            # Build diff command
            cmd = ["diff", from_commit, to_commit, "--stat"]
            if file_path:
                cmd.append("--")
                cmd.append(file_path)
            
            # Get diff stats
            returncode, stats_output, stderr = self._run_git_command(cmd, check=False)
            
            if returncode != 0:
                logger.warning(f"Failed to get diff stats: {stderr}")
                return None
            
            # Parse stats
            additions = 0
            deletions = 0
            files_changed = []
            
            for line in stats_output.strip().split('\n'):
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        file_name = parts[0].strip()
                        files_changed.append(file_name)
                        
                        # Extract +/- counts
                        stats_part = parts[1].strip()
                        additions += stats_part.count('+')
                        deletions += stats_part.count('-')
            
            # Get full diff text
            cmd = ["diff", from_commit, to_commit]
            if file_path:
                cmd.append("--")
                cmd.append(file_path)
            
            returncode, diff_text, stderr = self._run_git_command(cmd, check=False)
            
            return GitDiff(
                from_commit=from_commit,
                to_commit=to_commit,
                files_changed=files_changed,
                additions=additions,
                deletions=deletions,
                diff_text=diff_text if returncode == 0 else ""
            )
        
        except Exception as e:
            logger.error(f"Error getting diff: {e}")
            return None
    
    def rollback(
        self,
        commit_hash: str,
        hard: bool = False
    ) -> bool:
        """
        Rollback to a specific commit.
        
        Args:
            commit_hash: Commit hash to rollback to
            hard: If True, discard all changes (git reset --hard)
                  If False, keep changes in working directory (git reset --soft)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_git_repo():
            logger.error("Not a git repository")
            return False
        
        try:
            reset_type = "--hard" if hard else "--soft"
            
            returncode, stdout, stderr = self._run_git_command(
                ["reset", reset_type, commit_hash]
            )
            
            if returncode == 0:
                logger.info(f"Rolled back to commit: {commit_hash[:8]}")
                return True
            else:
                logger.error(f"Failed to rollback: {stderr}")
                return False
        
        except Exception as e:
            logger.error(f"Error rolling back: {e}")
            return False
    
    def create_tag(
        self,
        tag_name: str,
        message: Optional[str] = None,
        commit_hash: Optional[str] = None
    ) -> bool:
        """
        Create a tag for a commit.
        
        Args:
            tag_name: Name of the tag
            message: Optional tag message
            commit_hash: Commit to tag (default: HEAD)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_git_repo():
            logger.error("Not a git repository")
            return False
        
        try:
            cmd = ["tag"]
            
            if message:
                cmd.extend(["-a", tag_name, "-m", message])
            else:
                cmd.append(tag_name)
            
            if commit_hash:
                cmd.append(commit_hash)
            
            returncode, stdout, stderr = self._run_git_command(cmd)
            
            if returncode == 0:
                logger.info(f"Created tag: {tag_name}")
                return True
            else:
                logger.error(f"Failed to create tag: {stderr}")
                return False
        
        except Exception as e:
            logger.error(f"Error creating tag: {e}")
            return False
    
    def list_tags(self) -> List[str]:
        """
        List all tags.
        
        Returns:
            List of tag names
        """
        if not self.is_git_repo():
            return []
        
        try:
            returncode, stdout, stderr = self._run_git_command(["tag", "-l"])
            
            if returncode == 0:
                tags = [tag.strip() for tag in stdout.strip().split('\n') if tag.strip()]
                return tags
            else:
                return []
        
        except Exception as e:
            logger.error(f"Error listing tags: {e}")
            return []
    
    def get_file_at_commit(
        self,
        file_path: str,
        commit_hash: str
    ) -> Optional[str]:
        """
        Get file content at a specific commit.
        
        Args:
            file_path: Path to file (relative to repo root)
            commit_hash: Commit hash
        
        Returns:
            File content as string or None
        """
        if not self.is_git_repo():
            return None
        
        try:
            returncode, stdout, stderr = self._run_git_command(
                ["show", f"{commit_hash}:{file_path}"],
                check=False
            )
            
            if returncode == 0:
                return stdout
            else:
                logger.warning(f"File not found at commit: {file_path} @ {commit_hash[:8]}")
                return None
        
        except Exception as e:
            logger.error(f"Error getting file at commit: {e}")
            return None
    
    def get_status(self) -> Dict[str, List[str]]:
        """
        Get current repository status.
        
        Returns:
            Dictionary with 'staged', 'modified', 'untracked' file lists
        """
        if not self.is_git_repo():
            return {"staged": [], "modified": [], "untracked": []}
        
        try:
            returncode, stdout, stderr = self._run_git_command(["status", "--porcelain"])
            
            status = {
                "staged": [],
                "modified": [],
                "untracked": []
            }
            
            for line in stdout.strip().split('\n'):
                if not line.strip():
                    continue
                
                status_code = line[:2]
                file_path = line[3:].strip()
                
                if status_code[0] in ['M', 'A', 'D', 'R', 'C']:
                    status["staged"].append(file_path)
                if status_code[1] == 'M':
                    status["modified"].append(file_path)
                if status_code == '??':
                    status["untracked"].append(file_path)
            
            return status
        
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"staged": [], "modified": [], "untracked": []}


if __name__ == "__main__":
    # Example usage
    manager = GitVersionManager()
    
    # Initialize repository
    if manager.init_repository():
        print("✓ Repository initialized")
    
    # Get status
    status = manager.get_status()
    print(f"\nStatus:")
    print(f"  Staged: {len(status['staged'])} files")
    print(f"  Modified: {len(status['modified'])} files")
    print(f"  Untracked: {len(status['untracked'])} files")
    
    # Get history
    history = manager.get_history(max_count=5)
    print(f"\nRecent commits: {len(history)}")
    for commit in history[:3]:
        print(f"  {commit.hash[:8]} - {commit.message} ({commit.author})")
