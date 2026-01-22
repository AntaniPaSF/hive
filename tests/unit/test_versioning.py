"""
Unit Tests for Versioning Module

Comprehensive tests for:
- GitVersionManager
- ManifestTracker
- AuditTrail
"""

import pytest
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from app.versioning.git_manager import GitVersionManager, GitCommit, GitDiff
from app.versioning.manifest_tracker import ManifestTracker, ManifestVersion, ManifestChange, DocumentChange
from app.versioning.audit_trail import AuditTrail, ActionType, AuditLevel, AuditEntry


class TestGitVersionManager:
    """Tests for GitVersionManager."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def manager(self, temp_repo):
        """Create GitVersionManager instance."""
        return GitVersionManager(repo_path=temp_repo)
    
    def test_init_repository(self, manager):
        """Test repository initialization."""
        assert manager.init_repository()
        assert manager.is_git_repo()
        assert (Path(manager.repo_path) / ".git").exists()
    
    def test_is_git_repo(self, manager):
        """Test git repository detection."""
        assert not manager.is_git_repo()
        manager.init_repository()
        assert manager.is_git_repo()
    
    def test_commit_changes(self, manager, temp_repo):
        """Test committing changes."""
        manager.init_repository()
        
        # Create a test file
        test_file = Path(temp_repo) / "test.txt"
        test_file.write_text("Hello World")
        
        # Commit
        commit_hash = manager.commit_changes(
            message="Add test file",
            author="Test User <test@example.com>",
            add_all=True
        )
        
        assert commit_hash is not None
        assert len(commit_hash) == 40  # SHA-1 hash
    
    def test_commit_no_changes(self, manager):
        """Test commit with no changes."""
        manager.init_repository()
        
        # Try to commit without changes
        commit_hash = manager.commit_changes(
            message="No changes",
            add_all=True
        )
        
        assert commit_hash is None
    
    def test_get_history(self, manager, temp_repo):
        """Test getting commit history."""
        manager.init_repository()
        
        # Create multiple commits
        for i in range(3):
            test_file = Path(temp_repo) / f"test{i}.txt"
            test_file.write_text(f"Content {i}")
            manager.commit_changes(
                message=f"Commit {i}",
                add_all=True
            )
        
        # Get history
        history = manager.get_history(max_count=10)
        assert len(history) >= 3
        
        # Check commit structure
        for commit in history:
            assert isinstance(commit, GitCommit)
            assert commit.hash
            assert commit.author
            assert commit.date
            assert commit.message
    
    def test_get_diff(self, manager, temp_repo):
        """Test getting diff between commits."""
        manager.init_repository()
        
        # Create first commit
        test_file = Path(temp_repo) / "test.txt"
        test_file.write_text("Version 1")
        commit1 = manager.commit_changes(message="Commit 1", add_all=True)
        
        # Create second commit
        test_file.write_text("Version 2")
        commit2 = manager.commit_changes(message="Commit 2", add_all=True)
        
        # Get diff
        diff = manager.get_diff(from_commit=commit1, to_commit=commit2)
        
        assert diff is not None
        assert isinstance(diff, GitDiff)
        assert len(diff.files_changed) > 0
    
    def test_rollback(self, manager, temp_repo):
        """Test rollback to previous commit."""
        manager.init_repository()
        
        # Create commits
        test_file = Path(temp_repo) / "test.txt"
        test_file.write_text("Version 1")
        commit1 = manager.commit_changes(message="Commit 1", add_all=True)
        
        test_file.write_text("Version 2")
        manager.commit_changes(message="Commit 2", add_all=True)
        
        # Rollback to first commit
        success = manager.rollback(commit_hash=commit1, hard=True)
        assert success
        
        # Verify rollback
        assert test_file.read_text() == "Version 1"
    
    def test_create_tag(self, manager, temp_repo):
        """Test creating tags."""
        manager.init_repository()
        
        # Create a commit
        test_file = Path(temp_repo) / "test.txt"
        test_file.write_text("Content")
        manager.commit_changes(message="Commit", add_all=True)
        
        # Create tag
        success = manager.create_tag(
            tag_name="v1.0.0",
            message="Version 1.0.0"
        )
        
        assert success
    
    def test_list_tags(self, manager, temp_repo):
        """Test listing tags."""
        manager.init_repository()
        
        # Create commit and tags
        test_file = Path(temp_repo) / "test.txt"
        test_file.write_text("Content")
        manager.commit_changes(message="Commit", add_all=True)
        
        manager.create_tag("v1.0.0")
        manager.create_tag("v1.0.1")
        
        # List tags
        tags = manager.list_tags()
        assert len(tags) >= 2
        assert "v1.0.0" in tags
        assert "v1.0.1" in tags
    
    def test_get_status(self, manager, temp_repo):
        """Test getting repository status."""
        manager.init_repository()
        
        # Create files
        staged_file = Path(temp_repo) / "staged.txt"
        staged_file.write_text("Staged")
        manager._run_git_command(["add", "staged.txt"])
        
        untracked_file = Path(temp_repo) / "untracked.txt"
        untracked_file.write_text("Untracked")
        
        # Get status
        status = manager.get_status()
        
        assert "staged" in status
        assert "modified" in status
        assert "untracked" in status
        assert len(status["staged"]) > 0


class TestManifestTracker:
    """Tests for ManifestTracker."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def manifest_path(self, temp_dir):
        """Create temporary manifest file."""
        manifest_file = Path(temp_dir) / "manifest.json"
        manifest_data = {
            "manifest_version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "total_documents": 1,
            "total_chunks": 10,
            "documents": [
                {
                    "document_id": "doc-1",
                    "filename": "test.pdf",
                    "checksum": "abc123",
                    "page_count": 5,
                    "chunk_count": 10
                }
            ],
            "configuration": {
                "chunk_size": 512,
                "chunk_overlap": 50
            }
        }
        
        with open(manifest_file, 'w') as f:
            json.dump(manifest_data, f)
        
        return str(manifest_file)
    
    @pytest.fixture
    def tracker(self, manifest_path, temp_dir):
        """Create ManifestTracker instance."""
        history_path = Path(temp_dir) / "history.json"
        return ManifestTracker(
            manifest_path=manifest_path,
            history_path=str(history_path)
        )
    
    def test_load_manifest(self, tracker):
        """Test loading manifest."""
        manifest = tracker.load_manifest()
        assert manifest is not None
        assert manifest["total_documents"] == 1
        assert len(manifest["documents"]) == 1
    
    def test_get_current_version(self, tracker):
        """Test getting current version."""
        version = tracker.get_current_version()
        assert version is not None
        assert isinstance(version, ManifestVersion)
        assert version.total_documents == 1
        assert version.total_chunks == 10
    
    def test_record_version(self, tracker):
        """Test recording a version."""
        version = tracker.record_version(
            commit_hash="abc123",
            changes_summary="Initial version"
        )
        
        assert version is not None
        assert version.commit_hash == "abc123"
        assert version.changes_summary == "Initial version"
    
    def test_get_version_history(self, tracker):
        """Test getting version history."""
        # Record multiple versions
        tracker.record_version(changes_summary="Version 1")
        
        # Get history
        history = tracker.get_version_history(limit=10)
        assert len(history) > 0
    
    def test_detect_changes(self, tracker):
        """Test change detection."""
        old_manifest = {
            "documents": [
                {"document_id": "doc-1", "filename": "old.pdf", "checksum": "old123", "chunk_count": 5}
            ],
            "configuration": {"chunk_size": 512}
        }
        
        new_manifest = {
            "documents": [
                {"document_id": "doc-1", "filename": "old.pdf", "checksum": "new123", "chunk_count": 7},
                {"document_id": "doc-2", "filename": "new.pdf", "checksum": "abc456", "chunk_count": 3}
            ],
            "configuration": {"chunk_size": 1024}
        }
        
        changes = tracker.detect_changes(old_manifest, new_manifest)
        
        assert len(changes) > 0
        
        # Check for document added
        added = [c for c in changes if c.change_type == "document_added"]
        assert len(added) > 0
        
        # Check for document modified
        modified = [c for c in changes if c.change_type == "document_modified"]
        assert len(modified) > 0
        
        # Check for config changed
        config_changed = [c for c in changes if c.change_type == "config_changed"]
        assert len(config_changed) > 0
    
    def test_track_document_changes(self, tracker):
        """Test tracking document changes."""
        old_manifest = {
            "documents": [
                {"document_id": "doc-1", "filename": "old.pdf", "checksum": "old123", "chunk_count": 5}
            ]
        }
        
        new_manifest = {
            "documents": [
                {"document_id": "doc-2", "filename": "new.pdf", "checksum": "new123", "chunk_count": 3}
            ]
        }
        
        doc_changes = tracker.track_document_changes(old_manifest, new_manifest)
        
        assert len(doc_changes) == 2  # One removed, one added
        
        removed = [c for c in doc_changes if c.change_type == "removed"]
        assert len(removed) == 1
        
        added = [c for c in doc_changes if c.change_type == "added"]
        assert len(added) == 1
    
    def test_get_statistics(self, tracker):
        """Test getting statistics."""
        stats = tracker.get_statistics()
        
        assert "total_versions" in stats
        assert "total_changes" in stats
        assert "current_version" in stats


class TestAuditTrail:
    """Tests for AuditTrail."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def audit(self, temp_dir):
        """Create AuditTrail instance."""
        audit_path = Path(temp_dir) / "audit.json"
        return AuditTrail(audit_path=str(audit_path))
    
    def test_log_action(self, audit):
        """Test logging an action."""
        entry = audit.log_action(
            action_type=ActionType.DOCUMENT_INGEST,
            user="test_user",
            description="Ingested test.pdf",
            level=AuditLevel.INFO,
            resource_id="doc-123"
        )
        
        assert entry is not None
        assert isinstance(entry, AuditEntry)
        assert entry.action_type == ActionType.DOCUMENT_INGEST.value
        assert entry.user == "test_user"
        assert entry.success is True
    
    def test_log_error_action(self, audit):
        """Test logging an error action."""
        entry = audit.log_action(
            action_type=ActionType.API_ERROR,
            user="test_user",
            description="API call failed",
            level=AuditLevel.ERROR,
            success=False,
            error_message="Connection timeout"
        )
        
        assert entry.success is False
        assert entry.error_message == "Connection timeout"
        assert entry.level == AuditLevel.ERROR.value
    
    def test_start_session(self, audit):
        """Test starting a session."""
        session = audit.start_session(
            user="test_user",
            ip_address="192.168.1.1"
        )
        
        assert session.user == "test_user"
        assert session.ip_address == "192.168.1.1"
        assert "test_user" in audit.active_sessions
    
    def test_end_session(self, audit):
        """Test ending a session."""
        # Start session
        audit.start_session(user="test_user")
        assert "test_user" in audit.active_sessions
        
        # End session
        audit.end_session(user="test_user")
        assert "test_user" not in audit.active_sessions
    
    def test_get_entries(self, audit):
        """Test getting entries with filters."""
        # Log multiple actions
        audit.log_action(
            action_type=ActionType.DOCUMENT_INGEST,
            user="user1",
            description="Action 1",
            level=AuditLevel.INFO
        )
        
        audit.log_action(
            action_type=ActionType.QUERY_EXECUTE,
            user="user2",
            description="Action 2",
            level=AuditLevel.INFO
        )
        
        # Get all entries
        all_entries = audit.get_entries()
        assert len(all_entries) >= 2
        
        # Filter by user
        user1_entries = audit.get_entries(user="user1")
        assert all(e.user == "user1" for e in user1_entries)
        
        # Filter by action type
        ingest_entries = audit.get_entries(action_type=ActionType.DOCUMENT_INGEST)
        assert all(e.action_type == ActionType.DOCUMENT_INGEST.value for e in ingest_entries)
    
    def test_get_user_activity(self, audit):
        """Test getting user activity."""
        # Log actions for user
        for i in range(5):
            audit.log_action(
                action_type=ActionType.QUERY_EXECUTE,
                user="test_user",
                description=f"Query {i}",
                level=AuditLevel.INFO
            )
        
        # Get activity
        activity = audit.get_user_activity(user="test_user")
        
        assert activity["user"] == "test_user"
        assert activity["total_actions"] >= 5
        assert "action_breakdown" in activity
    
    def test_get_resource_history(self, audit):
        """Test getting resource history."""
        # Log actions for resource
        audit.log_action(
            action_type=ActionType.DOCUMENT_INGEST,
            user="user1",
            description="Ingested doc",
            resource_id="doc-123",
            resource_type="document"
        )
        
        audit.log_action(
            action_type=ActionType.DOCUMENT_UPDATE,
            user="user2",
            description="Updated doc",
            resource_id="doc-123",
            resource_type="document"
        )
        
        # Get resource history
        history = audit.get_resource_history(resource_id="doc-123")
        
        assert len(history) >= 2
        assert all(e.resource_id == "doc-123" for e in history)
    
    def test_get_statistics(self, audit):
        """Test getting statistics."""
        # Log some actions
        audit.log_action(
            action_type=ActionType.DOCUMENT_INGEST,
            user="user1",
            description="Action 1"
        )
        
        audit.log_action(
            action_type=ActionType.QUERY_EXECUTE,
            user="user2",
            description="Action 2",
            success=False
        )
        
        # Get statistics
        stats = audit.get_statistics()
        
        assert "total_entries" in stats
        assert "successful_actions" in stats
        assert "failed_actions" in stats
        assert "action_breakdown" in stats
        assert stats["total_entries"] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
