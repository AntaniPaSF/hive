"""
Manifest Tracking System

Tracks changes to manifest.json over time:
- Version history for all ingestions
- Change detection and logging
- Document addition/removal tracking
- Configuration change tracking
- Integration with git versioning
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import hashlib
from deepdiff import DeepDiff

logger = logging.getLogger(__name__)


@dataclass
class ManifestVersion:
    """Represents a manifest version."""
    
    version_id: str
    timestamp: datetime
    manifest_version: str
    total_documents: int
    total_chunks: int
    commit_hash: Optional[str] = None
    changes_summary: Optional[str] = None


@dataclass
class ManifestChange:
    """Represents a change to the manifest."""
    
    change_id: str
    timestamp: datetime
    change_type: str  # 'document_added', 'document_removed', 'config_changed', 'full_update'
    description: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    affected_documents: Optional[List[str]] = None


@dataclass
class DocumentChange:
    """Represents a change to a document."""
    
    document_id: str
    filename: str
    change_type: str  # 'added', 'removed', 'modified', 'checksum_changed'
    timestamp: datetime
    old_chunk_count: Optional[int] = None
    new_chunk_count: Optional[int] = None
    old_checksum: Optional[str] = None
    new_checksum: Optional[str] = None


class ManifestTracker:
    """
    Tracks manifest changes over time.
    
    Features:
    - Load and parse manifest files
    - Detect changes between versions
    - Track document additions/removals
    - Track configuration changes
    - Generate change summaries
    - Store version history
    """
    
    def __init__(self, manifest_path: Optional[str] = None, history_path: Optional[str] = None):
        """
        Initialize manifest tracker.
        
        Args:
            manifest_path: Path to manifest.json file
            history_path: Path to store version history (JSON file)
        """
        if manifest_path is None:
            manifest_path = os.path.join(os.getcwd(), "data", "manifest.json")
        
        if history_path is None:
            history_path = os.path.join(os.getcwd(), "data", "manifest_history.json")
        
        self.manifest_path = Path(manifest_path)
        self.history_path = Path(history_path)
        
        # Ensure data directory exists
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or initialize history
        self.history: Dict[str, Any] = self._load_history()
        
        logger.info(f"Manifest tracker initialized")
        logger.debug(f"Manifest path: {self.manifest_path}")
        logger.debug(f"History path: {self.history_path}")
    
    def _load_history(self) -> Dict[str, Any]:
        """Load version history from file."""
        if not self.history_path.exists():
            return {
                "versions": [],
                "changes": [],
                "document_changes": []
            }
        
        try:
            with open(self.history_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return {
                "versions": [],
                "changes": [],
                "document_changes": []
            }
    
    def _save_history(self):
        """Save version history to file."""
        try:
            with open(self.history_path, 'w') as f:
                json.dump(self.history, f, indent=2, default=str)
            logger.debug("Saved manifest history")
        except Exception as e:
            logger.error(f"Error saving history: {e}")
    
    def load_manifest(self) -> Optional[Dict[str, Any]]:
        """
        Load current manifest file.
        
        Returns:
            Manifest data as dictionary or None
        """
        if not self.manifest_path.exists():
            logger.warning(f"Manifest file not found: {self.manifest_path}")
            return None
        
        try:
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading manifest: {e}")
            return None
    
    def get_manifest_hash(self, manifest: Dict[str, Any]) -> str:
        """
        Calculate hash of manifest content.
        
        Args:
            manifest: Manifest data
        
        Returns:
            SHA256 hash of manifest
        """
        manifest_json = json.dumps(manifest, sort_keys=True)
        return hashlib.sha256(manifest_json.encode()).hexdigest()
    
    def get_current_version(self) -> Optional[ManifestVersion]:
        """
        Get current manifest version.
        
        Returns:
            ManifestVersion object or None
        """
        manifest = self.load_manifest()
        if not manifest:
            return None
        
        version_id = self.get_manifest_hash(manifest)
        
        return ManifestVersion(
            version_id=version_id,
            timestamp=datetime.now(),
            manifest_version=manifest.get("manifest_version", "unknown"),
            total_documents=manifest.get("total_documents", 0),
            total_chunks=manifest.get("total_chunks", 0),
            commit_hash=None,
            changes_summary=None
        )
    
    def get_version_history(self, limit: Optional[int] = None) -> List[ManifestVersion]:
        """
        Get version history.
        
        Args:
            limit: Maximum number of versions to return
        
        Returns:
            List of ManifestVersion objects
        """
        versions = []
        
        for version_data in self.history.get("versions", []):
            try:
                # Parse timestamp
                timestamp = version_data.get("timestamp")
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                
                version = ManifestVersion(
                    version_id=version_data["version_id"],
                    timestamp=timestamp,
                    manifest_version=version_data["manifest_version"],
                    total_documents=version_data["total_documents"],
                    total_chunks=version_data["total_chunks"],
                    commit_hash=version_data.get("commit_hash"),
                    changes_summary=version_data.get("changes_summary")
                )
                versions.append(version)
            except Exception as e:
                logger.error(f"Error parsing version: {e}")
        
        # Sort by timestamp (newest first)
        versions.sort(key=lambda v: v.timestamp, reverse=True)
        
        if limit:
            versions = versions[:limit]
        
        return versions
    
    def detect_changes(
        self,
        old_manifest: Dict[str, Any],
        new_manifest: Dict[str, Any]
    ) -> List[ManifestChange]:
        """
        Detect changes between two manifest versions.
        
        Args:
            old_manifest: Previous manifest data
            new_manifest: New manifest data
        
        Returns:
            List of ManifestChange objects
        """
        changes = []
        timestamp = datetime.now()
        
        # Check for document changes
        old_docs = {doc["document_id"]: doc for doc in old_manifest.get("documents", [])}
        new_docs = {doc["document_id"]: doc for doc in new_manifest.get("documents", [])}
        
        # Documents added
        added_docs = set(new_docs.keys()) - set(old_docs.keys())
        if added_docs:
            for doc_id in added_docs:
                doc = new_docs[doc_id]
                change = ManifestChange(
                    change_id=hashlib.sha256(f"{doc_id}-added-{timestamp}".encode()).hexdigest()[:16],
                    timestamp=timestamp,
                    change_type="document_added",
                    description=f"Added document: {doc['filename']}",
                    old_value=None,
                    new_value=doc,
                    affected_documents=[doc_id]
                )
                changes.append(change)
        
        # Documents removed
        removed_docs = set(old_docs.keys()) - set(new_docs.keys())
        if removed_docs:
            for doc_id in removed_docs:
                doc = old_docs[doc_id]
                change = ManifestChange(
                    change_id=hashlib.sha256(f"{doc_id}-removed-{timestamp}".encode()).hexdigest()[:16],
                    timestamp=timestamp,
                    change_type="document_removed",
                    description=f"Removed document: {doc['filename']}",
                    old_value=doc,
                    new_value=None,
                    affected_documents=[doc_id]
                )
                changes.append(change)
        
        # Documents modified
        common_docs = set(old_docs.keys()) & set(new_docs.keys())
        for doc_id in common_docs:
            old_doc = old_docs[doc_id]
            new_doc = new_docs[doc_id]
            
            # Check for checksum change
            if old_doc.get("checksum") != new_doc.get("checksum"):
                change = ManifestChange(
                    change_id=hashlib.sha256(f"{doc_id}-checksum-{timestamp}".encode()).hexdigest()[:16],
                    timestamp=timestamp,
                    change_type="document_modified",
                    description=f"Document modified: {new_doc['filename']} (checksum changed)",
                    old_value=old_doc.get("checksum"),
                    new_value=new_doc.get("checksum"),
                    affected_documents=[doc_id]
                )
                changes.append(change)
            
            # Check for chunk count change
            if old_doc.get("chunk_count") != new_doc.get("chunk_count"):
                change = ManifestChange(
                    change_id=hashlib.sha256(f"{doc_id}-chunks-{timestamp}".encode()).hexdigest()[:16],
                    timestamp=timestamp,
                    change_type="document_modified",
                    description=f"Document chunks changed: {new_doc['filename']} ({old_doc.get('chunk_count')} → {new_doc.get('chunk_count')})",
                    old_value=old_doc.get("chunk_count"),
                    new_value=new_doc.get("chunk_count"),
                    affected_documents=[doc_id]
                )
                changes.append(change)
        
        # Check for configuration changes
        old_config = old_manifest.get("configuration", {})
        new_config = new_manifest.get("configuration", {})
        
        if old_config != new_config:
            diff = DeepDiff(old_config, new_config, ignore_order=True)
            
            if diff:
                change = ManifestChange(
                    change_id=hashlib.sha256(f"config-{timestamp}".encode()).hexdigest()[:16],
                    timestamp=timestamp,
                    change_type="config_changed",
                    description=f"Configuration changed: {list(diff.keys())}",
                    old_value=old_config,
                    new_value=new_config,
                    affected_documents=None
                )
                changes.append(change)
        
        return changes
    
    def track_document_changes(
        self,
        old_manifest: Dict[str, Any],
        new_manifest: Dict[str, Any]
    ) -> List[DocumentChange]:
        """
        Track document-specific changes.
        
        Args:
            old_manifest: Previous manifest data
            new_manifest: New manifest data
        
        Returns:
            List of DocumentChange objects
        """
        doc_changes = []
        timestamp = datetime.now()
        
        old_docs = {doc["document_id"]: doc for doc in old_manifest.get("documents", [])}
        new_docs = {doc["document_id"]: doc for doc in new_manifest.get("documents", [])}
        
        # Documents added
        for doc_id in set(new_docs.keys()) - set(old_docs.keys()):
            doc = new_docs[doc_id]
            doc_changes.append(DocumentChange(
                document_id=doc_id,
                filename=doc["filename"],
                change_type="added",
                timestamp=timestamp,
                new_chunk_count=doc.get("chunk_count"),
                new_checksum=doc.get("checksum")
            ))
        
        # Documents removed
        for doc_id in set(old_docs.keys()) - set(new_docs.keys()):
            doc = old_docs[doc_id]
            doc_changes.append(DocumentChange(
                document_id=doc_id,
                filename=doc["filename"],
                change_type="removed",
                timestamp=timestamp,
                old_chunk_count=doc.get("chunk_count"),
                old_checksum=doc.get("checksum")
            ))
        
        # Documents modified
        for doc_id in set(old_docs.keys()) & set(new_docs.keys()):
            old_doc = old_docs[doc_id]
            new_doc = new_docs[doc_id]
            
            # Check for modifications
            if old_doc.get("checksum") != new_doc.get("checksum"):
                doc_changes.append(DocumentChange(
                    document_id=doc_id,
                    filename=new_doc["filename"],
                    change_type="checksum_changed",
                    timestamp=timestamp,
                    old_chunk_count=old_doc.get("chunk_count"),
                    new_chunk_count=new_doc.get("chunk_count"),
                    old_checksum=old_doc.get("checksum"),
                    new_checksum=new_doc.get("checksum")
                ))
            elif old_doc.get("chunk_count") != new_doc.get("chunk_count"):
                doc_changes.append(DocumentChange(
                    document_id=doc_id,
                    filename=new_doc["filename"],
                    change_type="modified",
                    timestamp=timestamp,
                    old_chunk_count=old_doc.get("chunk_count"),
                    new_chunk_count=new_doc.get("chunk_count"),
                    old_checksum=old_doc.get("checksum"),
                    new_checksum=new_doc.get("checksum")
                ))
        
        return doc_changes
    
    def record_version(
        self,
        commit_hash: Optional[str] = None,
        changes_summary: Optional[str] = None
    ) -> Optional[ManifestVersion]:
        """
        Record current manifest as a new version.
        
        Args:
            commit_hash: Git commit hash (if applicable)
            changes_summary: Summary of changes
        
        Returns:
            ManifestVersion object or None
        """
        manifest = self.load_manifest()
        if not manifest:
            logger.error("Cannot record version: manifest not found")
            return None
        
        version_id = self.get_manifest_hash(manifest)
        
        # Check if this version already exists
        existing_versions = [v["version_id"] for v in self.history.get("versions", [])]
        if version_id in existing_versions:
            logger.info(f"Version {version_id[:8]} already recorded")
            return None
        
        # Create version object
        version = ManifestVersion(
            version_id=version_id,
            timestamp=datetime.now(),
            manifest_version=manifest.get("manifest_version", "unknown"),
            total_documents=manifest.get("total_documents", 0),
            total_chunks=manifest.get("total_chunks", 0),
            commit_hash=commit_hash,
            changes_summary=changes_summary
        )
        
        # Detect changes from previous version
        versions = self.history.get("versions", [])
        if versions:
            # Get previous manifest
            prev_version = versions[-1]
            prev_manifest = prev_version.get("manifest_data")
            
            if prev_manifest:
                # Detect changes
                changes = self.detect_changes(prev_manifest, manifest)
                doc_changes = self.track_document_changes(prev_manifest, manifest)
                
                # Store changes
                for change in changes:
                    self.history["changes"].append(asdict(change))
                
                for doc_change in doc_changes:
                    self.history["document_changes"].append(asdict(doc_change))
                
                # Generate summary if not provided
                if not changes_summary and changes:
                    summaries = [c.description for c in changes[:3]]
                    changes_summary = "; ".join(summaries)
                    if len(changes) > 3:
                        changes_summary += f" (+{len(changes) - 3} more)"
                    version.changes_summary = changes_summary
        
        # Store version
        version_dict = asdict(version)
        version_dict["manifest_data"] = manifest  # Store full manifest
        self.history["versions"].append(version_dict)
        
        # Save history
        self._save_history()
        
        logger.info(f"Recorded version: {version_id[:8]} - {version.total_documents} docs, {version.total_chunks} chunks")
        
        return version
    
    def get_changes_since(self, version_id: str) -> List[ManifestChange]:
        """
        Get all changes since a specific version.
        
        Args:
            version_id: Starting version ID
        
        Returns:
            List of ManifestChange objects
        """
        all_changes = []
        
        # Find version index
        versions = self.history.get("versions", [])
        start_index = None
        
        for i, version in enumerate(versions):
            if version["version_id"] == version_id:
                start_index = i
                break
        
        if start_index is None:
            logger.warning(f"Version not found: {version_id}")
            return []
        
        # Get changes after this version
        for change_data in self.history.get("changes", []):
            try:
                timestamp = change_data.get("timestamp")
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                
                # Check if change is after this version
                version_timestamp = versions[start_index]["timestamp"]
                if isinstance(version_timestamp, str):
                    version_timestamp = datetime.fromisoformat(version_timestamp)
                
                if timestamp > version_timestamp:
                    change = ManifestChange(
                        change_id=change_data["change_id"],
                        timestamp=timestamp,
                        change_type=change_data["change_type"],
                        description=change_data["description"],
                        old_value=change_data.get("old_value"),
                        new_value=change_data.get("new_value"),
                        affected_documents=change_data.get("affected_documents")
                    )
                    all_changes.append(change)
            except Exception as e:
                logger.error(f"Error parsing change: {e}")
        
        return all_changes
    
    def get_document_history(self, document_id: str) -> List[DocumentChange]:
        """
        Get change history for a specific document.
        
        Args:
            document_id: Document ID
        
        Returns:
            List of DocumentChange objects
        """
        doc_changes = []
        
        for change_data in self.history.get("document_changes", []):
            if change_data.get("document_id") == document_id:
                try:
                    timestamp = change_data.get("timestamp")
                    if isinstance(timestamp, str):
                        timestamp = datetime.fromisoformat(timestamp)
                    
                    doc_change = DocumentChange(
                        document_id=change_data["document_id"],
                        filename=change_data["filename"],
                        change_type=change_data["change_type"],
                        timestamp=timestamp,
                        old_chunk_count=change_data.get("old_chunk_count"),
                        new_chunk_count=change_data.get("new_chunk_count"),
                        old_checksum=change_data.get("old_checksum"),
                        new_checksum=change_data.get("new_checksum")
                    )
                    doc_changes.append(doc_change)
                except Exception as e:
                    logger.error(f"Error parsing document change: {e}")
        
        # Sort by timestamp (newest first)
        doc_changes.sort(key=lambda c: c.timestamp, reverse=True)
        
        return doc_changes
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get manifest tracking statistics.
        
        Returns:
            Dictionary with statistics
        """
        versions = self.history.get("versions", [])
        changes = self.history.get("changes", [])
        doc_changes = self.history.get("document_changes", [])
        
        # Count change types
        change_types = {}
        for change in changes:
            change_type = change.get("change_type", "unknown")
            change_types[change_type] = change_types.get(change_type, 0) + 1
        
        # Get latest version info
        current_version = self.get_current_version()
        
        return {
            "total_versions": len(versions),
            "total_changes": len(changes),
            "total_document_changes": len(doc_changes),
            "change_types": change_types,
            "current_version": {
                "total_documents": current_version.total_documents if current_version else 0,
                "total_chunks": current_version.total_chunks if current_version else 0,
                "version_id": current_version.version_id[:8] if current_version else None
            } if current_version else None
        }


if __name__ == "__main__":
    # Example usage
    tracker = ManifestTracker()
    
    # Get current version
    current = tracker.get_current_version()
    if current:
        print(f"Current version: {current.version_id[:8]}")
        print(f"Documents: {current.total_documents}")
        print(f"Chunks: {current.total_chunks}")
    
    # Record version
    version = tracker.record_version(
        changes_summary="Initial tracking setup"
    )
    if version:
        print(f"\n✓ Recorded version: {version.version_id[:8]}")
    
    # Get statistics
    stats = tracker.get_statistics()
    print(f"\nStatistics:")
    print(f"  Total versions: {stats['total_versions']}")
    print(f"  Total changes: {stats['total_changes']}")
