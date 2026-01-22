"""
Versioning API Endpoints

REST API for version control operations:
- List versions
- Get diffs between versions
- Rollback to previous versions
- View change history
- Manage tags
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from app.versioning.git_manager import GitVersionManager, GitCommit, GitDiff
from app.versioning.manifest_tracker import ManifestTracker, ManifestVersion, ManifestChange, DocumentChange
from app.versioning.audit_trail import AuditTrail, ActionType, AuditLevel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/versions", tags=["versioning"])


# Initialize managers
git_manager = GitVersionManager()
manifest_tracker = ManifestTracker()
audit_trail = AuditTrail()


# Pydantic models
class CommitInfo(BaseModel):
    """Git commit information."""
    hash: str
    author: str
    date: str
    message: str
    files_changed: List[str]


class DiffInfo(BaseModel):
    """Diff information."""
    from_commit: str
    to_commit: str
    files_changed: List[str]
    additions: int
    deletions: int
    diff_text: str


class ManifestVersionInfo(BaseModel):
    """Manifest version information."""
    version_id: str
    timestamp: str
    manifest_version: str
    total_documents: int
    total_chunks: int
    commit_hash: Optional[str] = None
    changes_summary: Optional[str] = None


class ChangeInfo(BaseModel):
    """Change information."""
    change_id: str
    timestamp: str
    change_type: str
    description: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    affected_documents: Optional[List[str]] = None


class DocumentChangeInfo(BaseModel):
    """Document change information."""
    document_id: str
    filename: str
    change_type: str
    timestamp: str
    old_chunk_count: Optional[int] = None
    new_chunk_count: Optional[int] = None
    old_checksum: Optional[str] = None
    new_checksum: Optional[str] = None


class CommitRequest(BaseModel):
    """Request to commit changes."""
    message: str = Field(..., description="Commit message")
    author: Optional[str] = Field("System", description="Author name")
    files: Optional[List[str]] = Field(None, description="Specific files to commit")
    add_all: bool = Field(True, description="Add all changed files")
    track_manifest: bool = Field(True, description="Track manifest version")


class RollbackRequest(BaseModel):
    """Request to rollback to a version."""
    commit_hash: str = Field(..., description="Commit hash to rollback to")
    hard: bool = Field(False, description="Discard all changes (hard reset)")


class TagRequest(BaseModel):
    """Request to create a tag."""
    tag_name: str = Field(..., description="Tag name")
    message: Optional[str] = Field(None, description="Tag message")
    commit_hash: Optional[str] = Field(None, description="Commit to tag (default: HEAD)")


class StatusResponse(BaseModel):
    """Repository status."""
    staged: List[str]
    modified: List[str]
    untracked: List[str]
    total_files: int


# Endpoints

@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Get current repository status."""
    try:
        status = git_manager.get_status()
        
        return StatusResponse(
            staged=status["staged"],
            modified=status["modified"],
            untracked=status["untracked"],
            total_files=len(status["staged"]) + len(status["modified"]) + len(status["untracked"])
        )
    
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/commit")
async def commit_changes(request: CommitRequest):
    """Commit changes to repository."""
    try:
        # Initialize repository if needed
        if not git_manager.is_git_repo():
            git_manager.init_repository()
        
        # Commit changes
        commit_hash = git_manager.commit_changes(
            message=request.message,
            author=request.author,
            files=request.files,
            add_all=request.add_all
        )
        
        if not commit_hash:
            raise HTTPException(status_code=400, detail="No changes to commit")
        
        # Track manifest version if requested
        manifest_version = None
        if request.track_manifest:
            manifest_version = manifest_tracker.record_version(
                commit_hash=commit_hash,
                changes_summary=request.message
            )
        
        # Log to audit trail
        audit_trail.log_action(
            action_type=ActionType.VERSION_COMMIT,
            user=request.author or "System",
            description=f"Committed changes: {request.message}",
            level=AuditLevel.INFO,
            details={
                "commit_hash": commit_hash,
                "message": request.message,
                "files": request.files or "all"
            }
        )
        
        return {
            "success": True,
            "commit_hash": commit_hash,
            "message": request.message,
            "manifest_version": manifest_version.version_id[:8] if manifest_version else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error committing changes: {e}")
        audit_trail.log_action(
            action_type=ActionType.VERSION_COMMIT,
            user=request.author or "System",
            description=f"Failed to commit changes: {request.message}",
            level=AuditLevel.ERROR,
            success=False,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[CommitInfo])
async def get_history(
    max_count: int = Query(50, description="Maximum number of commits"),
    file_path: Optional[str] = Query(None, description="Filter by file path")
):
    """Get commit history."""
    try:
        if not git_manager.is_git_repo():
            return []
        
        commits = git_manager.get_history(max_count=max_count, file_path=file_path)
        
        return [
            CommitInfo(
                hash=commit.hash,
                author=commit.author,
                date=commit.date.isoformat(),
                message=commit.message,
                files_changed=commit.files_changed
            )
            for commit in commits
        ]
    
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diff", response_model=DiffInfo)
async def get_diff(
    from_commit: str = Query("HEAD~1", description="Starting commit"),
    to_commit: str = Query("HEAD", description="Ending commit"),
    file_path: Optional[str] = Query(None, description="Limit diff to file")
):
    """Get diff between commits."""
    try:
        if not git_manager.is_git_repo():
            raise HTTPException(status_code=400, detail="Not a git repository")
        
        diff = git_manager.get_diff(
            from_commit=from_commit,
            to_commit=to_commit,
            file_path=file_path
        )
        
        if not diff:
            raise HTTPException(status_code=404, detail="Diff not found")
        
        return DiffInfo(
            from_commit=diff.from_commit,
            to_commit=diff.to_commit,
            files_changed=diff.files_changed,
            additions=diff.additions,
            deletions=diff.deletions,
            diff_text=diff.diff_text
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting diff: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollback")
async def rollback(request: RollbackRequest):
    """Rollback to a specific commit."""
    try:
        if not git_manager.is_git_repo():
            raise HTTPException(status_code=400, detail="Not a git repository")
        
        success = git_manager.rollback(
            commit_hash=request.commit_hash,
            hard=request.hard
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Rollback failed")
        
        # Log to audit trail
        audit_trail.log_action(
            action_type=ActionType.VERSION_ROLLBACK,
            user="System",
            description=f"Rolled back to commit: {request.commit_hash[:8]}",
            level=AuditLevel.WARNING,
            details={
                "commit_hash": request.commit_hash,
                "hard": request.hard
            }
        )
        
        return {
            "success": True,
            "commit_hash": request.commit_hash,
            "hard": request.hard
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rolling back: {e}")
        audit_trail.log_action(
            action_type=ActionType.VERSION_ROLLBACK,
            user="System",
            description=f"Failed to rollback to: {request.commit_hash[:8]}",
            level=AuditLevel.ERROR,
            success=False,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tags")
async def create_tag(request: TagRequest):
    """Create a tag."""
    try:
        if not git_manager.is_git_repo():
            raise HTTPException(status_code=400, detail="Not a git repository")
        
        success = git_manager.create_tag(
            tag_name=request.tag_name,
            message=request.message,
            commit_hash=request.commit_hash
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to create tag")
        
        # Log to audit trail
        audit_trail.log_action(
            action_type=ActionType.VERSION_TAG,
            user="System",
            description=f"Created tag: {request.tag_name}",
            level=AuditLevel.INFO,
            details={
                "tag_name": request.tag_name,
                "message": request.message,
                "commit_hash": request.commit_hash
            }
        )
        
        return {
            "success": True,
            "tag_name": request.tag_name
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags", response_model=List[str])
async def list_tags():
    """List all tags."""
    try:
        if not git_manager.is_git_repo():
            return []
        
        return git_manager.list_tags()
    
    except Exception as e:
        logger.error(f"Error listing tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manifest/history", response_model=List[ManifestVersionInfo])
async def get_manifest_history(
    limit: Optional[int] = Query(50, description="Maximum versions to return")
):
    """Get manifest version history."""
    try:
        versions = manifest_tracker.get_version_history(limit=limit)
        
        return [
            ManifestVersionInfo(
                version_id=v.version_id,
                timestamp=v.timestamp.isoformat(),
                manifest_version=v.manifest_version,
                total_documents=v.total_documents,
                total_chunks=v.total_chunks,
                commit_hash=v.commit_hash,
                changes_summary=v.changes_summary
            )
            for v in versions
        ]
    
    except Exception as e:
        logger.error(f"Error getting manifest history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manifest/changes", response_model=List[ChangeInfo])
async def get_manifest_changes(
    version_id: Optional[str] = Query(None, description="Get changes since this version")
):
    """Get manifest changes."""
    try:
        if version_id:
            # Get changes since specific version
            changes = manifest_tracker.get_changes_since(version_id)
        else:
            # Get all recent changes
            all_changes = manifest_tracker.history.get("changes", [])[-50:]
            changes = []
            for change_data in all_changes:
                timestamp = change_data.get("timestamp")
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                changes.append(ManifestChange(
                    change_id=change_data["change_id"],
                    timestamp=timestamp,
                    change_type=change_data["change_type"],
                    description=change_data["description"],
                    old_value=change_data.get("old_value"),
                    new_value=change_data.get("new_value"),
                    affected_documents=change_data.get("affected_documents")
                ))
        
        return [
            ChangeInfo(
                change_id=c.change_id,
                timestamp=c.timestamp.isoformat(),
                change_type=c.change_type,
                description=c.description,
                old_value=c.old_value,
                new_value=c.new_value,
                affected_documents=c.affected_documents
            )
            for c in changes
        ]
    
    except Exception as e:
        logger.error(f"Error getting manifest changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/manifest/document/{document_id}", response_model=List[DocumentChangeInfo])
async def get_document_history(document_id: str):
    """Get change history for a specific document."""
    try:
        doc_changes = manifest_tracker.get_document_history(document_id)
        
        return [
            DocumentChangeInfo(
                document_id=dc.document_id,
                filename=dc.filename,
                change_type=dc.change_type,
                timestamp=dc.timestamp.isoformat(),
                old_chunk_count=dc.old_chunk_count,
                new_chunk_count=dc.new_chunk_count,
                old_checksum=dc.old_checksum,
                new_checksum=dc.new_checksum
            )
            for dc in doc_changes
        ]
    
    except Exception as e:
        logger.error(f"Error getting document history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """Get version control statistics."""
    try:
        git_status = git_manager.get_status()
        manifest_stats = manifest_tracker.get_statistics()
        audit_stats = audit_trail.get_statistics()
        
        return {
            "git": {
                "is_repo": git_manager.is_git_repo(),
                "staged_files": len(git_status["staged"]),
                "modified_files": len(git_status["modified"]),
                "untracked_files": len(git_status["untracked"]),
                "total_tags": len(git_manager.list_tags()) if git_manager.is_git_repo() else 0
            },
            "manifest": manifest_stats,
            "audit": audit_stats
        }
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
