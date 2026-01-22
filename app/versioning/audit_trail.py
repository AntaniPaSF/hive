"""
Audit Trail System

Comprehensive audit logging with user attribution:
- Action tracking (ingest, query, rollback, etc.)
- User attribution and timestamps
- Request/response logging
- Change history
- Security auditing
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of auditable actions."""
    
    # Document operations
    DOCUMENT_INGEST = "document_ingest"
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_UPDATE = "document_update"
    
    # Query operations
    QUERY_EXECUTE = "query_execute"
    SEARCH_EXECUTE = "search_execute"
    
    # Version control operations
    VERSION_COMMIT = "version_commit"
    VERSION_ROLLBACK = "version_rollback"
    VERSION_TAG = "version_tag"
    
    # Configuration operations
    CONFIG_UPDATE = "config_update"
    
    # System operations
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    
    # API operations
    API_REQUEST = "api_request"
    API_ERROR = "api_error"


class AuditLevel(Enum):
    """Audit log levels."""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEntry:
    """Represents an audit log entry."""
    
    entry_id: str
    timestamp: datetime
    action_type: str
    user: str
    level: str
    description: str
    details: Optional[Dict[str, Any]] = None
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    ip_address: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class UserSession:
    """Represents a user session."""
    
    session_id: str
    user: str
    start_time: datetime
    end_time: Optional[datetime] = None
    ip_address: Optional[str] = None
    actions_count: int = 0
    last_action: Optional[datetime] = None


class AuditTrail:
    """
    Audit trail system for tracking all system actions.
    
    Features:
    - Log all user actions with timestamps
    - Track user sessions
    - Record success/failure of operations
    - Store detailed context for each action
    - Query audit logs
    - Generate audit reports
    """
    
    def __init__(self, audit_path: Optional[str] = None):
        """
        Initialize audit trail.
        
        Args:
            audit_path: Path to store audit logs (JSON file)
        """
        if audit_path is None:
            audit_path = os.path.join(os.getcwd(), "data", "audit_trail.json")
        
        self.audit_path = Path(audit_path)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or initialize audit data
        self.audit_data: Dict[str, Any] = self._load_audit_data()
        
        # In-memory session tracking
        self.active_sessions: Dict[str, UserSession] = {}
        
        logger.info(f"Audit trail initialized at: {self.audit_path}")
    
    def _load_audit_data(self) -> Dict[str, Any]:
        """Load audit data from file."""
        if not self.audit_path.exists():
            return {
                "entries": [],
                "sessions": [],
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0"
                }
            }
        
        try:
            with open(self.audit_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading audit data: {e}")
            return {
                "entries": [],
                "sessions": [],
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0"
                }
            }
    
    def _save_audit_data(self):
        """Save audit data to file."""
        try:
            with open(self.audit_path, 'w') as f:
                json.dump(self.audit_data, f, indent=2, default=str)
            logger.debug("Saved audit data")
        except Exception as e:
            logger.error(f"Error saving audit data: {e}")
    
    def _generate_entry_id(self) -> str:
        """Generate unique entry ID."""
        import hashlib
        timestamp = datetime.now().isoformat()
        return hashlib.sha256(timestamp.encode()).hexdigest()[:16]
    
    def log_action(
        self,
        action_type: ActionType,
        user: str,
        description: str,
        level: AuditLevel = AuditLevel.INFO,
        details: Optional[Dict[str, Any]] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> AuditEntry:
        """
        Log an action to the audit trail.
        
        Args:
            action_type: Type of action being performed
            user: Username or user identifier
            description: Human-readable description
            level: Audit log level
            details: Additional context as dictionary
            resource_id: ID of affected resource
            resource_type: Type of resource (document, query, etc.)
            ip_address: IP address of user
            success: Whether action succeeded
            error_message: Error message if action failed
        
        Returns:
            AuditEntry object
        """
        entry = AuditEntry(
            entry_id=self._generate_entry_id(),
            timestamp=datetime.now(),
            action_type=action_type.value,
            user=user,
            level=level.value,
            description=description,
            details=details,
            resource_id=resource_id,
            resource_type=resource_type,
            ip_address=ip_address,
            success=success,
            error_message=error_message
        )
        
        # Store entry
        self.audit_data["entries"].append(asdict(entry))
        self._save_audit_data()
        
        # Update session if exists
        if user in self.active_sessions:
            session = self.active_sessions[user]
            session.actions_count += 1
            session.last_action = entry.timestamp
        
        logger.debug(f"Logged audit entry: {action_type.value} by {user}")
        
        return entry
    
    def start_session(
        self,
        user: str,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> UserSession:
        """
        Start a user session.
        
        Args:
            user: Username
            session_id: Optional session ID (generated if not provided)
            ip_address: IP address
        
        Returns:
            UserSession object
        """
        if session_id is None:
            session_id = self._generate_entry_id()
        
        session = UserSession(
            session_id=session_id,
            user=user,
            start_time=datetime.now(),
            ip_address=ip_address
        )
        
        self.active_sessions[user] = session
        
        # Log session start
        self.log_action(
            action_type=ActionType.SYSTEM_START,
            user=user,
            description=f"User session started: {session_id}",
            level=AuditLevel.INFO,
            details={"session_id": session_id},
            ip_address=ip_address
        )
        
        logger.info(f"Started session for user: {user}")
        
        return session
    
    def end_session(self, user: str):
        """
        End a user session.
        
        Args:
            user: Username
        """
        if user not in self.active_sessions:
            logger.warning(f"No active session for user: {user}")
            return
        
        session = self.active_sessions[user]
        session.end_time = datetime.now()
        
        # Store session
        self.audit_data["sessions"].append(asdict(session))
        self._save_audit_data()
        
        # Log session end
        self.log_action(
            action_type=ActionType.SYSTEM_STOP,
            user=user,
            description=f"User session ended: {session.session_id}",
            level=AuditLevel.INFO,
            details={
                "session_id": session.session_id,
                "duration_seconds": (session.end_time - session.start_time).total_seconds(),
                "actions_count": session.actions_count
            }
        )
        
        # Remove from active sessions
        del self.active_sessions[user]
        
        logger.info(f"Ended session for user: {user}")
    
    def get_entries(
        self,
        user: Optional[str] = None,
        action_type: Optional[ActionType] = None,
        level: Optional[AuditLevel] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        success_only: bool = False,
        limit: Optional[int] = None
    ) -> List[AuditEntry]:
        """
        Query audit entries with filters.
        
        Args:
            user: Filter by username
            action_type: Filter by action type
            level: Filter by audit level
            start_time: Filter entries after this time
            end_time: Filter entries before this time
            success_only: Only return successful actions
            limit: Maximum number of entries to return
        
        Returns:
            List of AuditEntry objects
        """
        entries = []
        
        for entry_data in self.audit_data.get("entries", []):
            try:
                # Parse timestamp
                timestamp = entry_data.get("timestamp")
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                
                # Apply filters
                if user and entry_data.get("user") != user:
                    continue
                
                if action_type and entry_data.get("action_type") != action_type.value:
                    continue
                
                if level and entry_data.get("level") != level.value:
                    continue
                
                if start_time and timestamp < start_time:
                    continue
                
                if end_time and timestamp > end_time:
                    continue
                
                if success_only and not entry_data.get("success", True):
                    continue
                
                # Create entry object
                entry = AuditEntry(
                    entry_id=entry_data["entry_id"],
                    timestamp=timestamp,
                    action_type=entry_data["action_type"],
                    user=entry_data["user"],
                    level=entry_data["level"],
                    description=entry_data["description"],
                    details=entry_data.get("details"),
                    resource_id=entry_data.get("resource_id"),
                    resource_type=entry_data.get("resource_type"),
                    ip_address=entry_data.get("ip_address"),
                    success=entry_data.get("success", True),
                    error_message=entry_data.get("error_message")
                )
                entries.append(entry)
            
            except Exception as e:
                logger.error(f"Error parsing audit entry: {e}")
        
        # Sort by timestamp (newest first)
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        
        if limit:
            entries = entries[:limit]
        
        return entries
    
    def get_user_activity(
        self,
        user: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get activity summary for a user.
        
        Args:
            user: Username
            start_time: Start of time range
            end_time: End of time range
        
        Returns:
            Dictionary with activity statistics
        """
        entries = self.get_entries(
            user=user,
            start_time=start_time,
            end_time=end_time
        )
        
        # Count actions by type
        action_counts = {}
        for entry in entries:
            action_type = entry.action_type
            action_counts[action_type] = action_counts.get(action_type, 0) + 1
        
        # Count successes and failures
        successful = sum(1 for e in entries if e.success)
        failed = len(entries) - successful
        
        # Get sessions
        user_sessions = [
            s for s in self.audit_data.get("sessions", [])
            if s.get("user") == user
        ]
        
        return {
            "user": user,
            "total_actions": len(entries),
            "successful_actions": successful,
            "failed_actions": failed,
            "action_breakdown": action_counts,
            "total_sessions": len(user_sessions),
            "time_range": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None
            }
        }
    
    def get_resource_history(
        self,
        resource_id: str,
        resource_type: Optional[str] = None
    ) -> List[AuditEntry]:
        """
        Get audit history for a specific resource.
        
        Args:
            resource_id: Resource ID
            resource_type: Optional resource type filter
        
        Returns:
            List of AuditEntry objects
        """
        entries = []
        
        for entry_data in self.audit_data.get("entries", []):
            if entry_data.get("resource_id") == resource_id:
                if resource_type and entry_data.get("resource_type") != resource_type:
                    continue
                
                try:
                    timestamp = entry_data.get("timestamp")
                    if isinstance(timestamp, str):
                        timestamp = datetime.fromisoformat(timestamp)
                    
                    entry = AuditEntry(
                        entry_id=entry_data["entry_id"],
                        timestamp=timestamp,
                        action_type=entry_data["action_type"],
                        user=entry_data["user"],
                        level=entry_data["level"],
                        description=entry_data["description"],
                        details=entry_data.get("details"),
                        resource_id=entry_data.get("resource_id"),
                        resource_type=entry_data.get("resource_type"),
                        ip_address=entry_data.get("ip_address"),
                        success=entry_data.get("success", True),
                        error_message=entry_data.get("error_message")
                    )
                    entries.append(entry)
                
                except Exception as e:
                    logger.error(f"Error parsing audit entry: {e}")
        
        # Sort by timestamp (newest first)
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        
        return entries
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get audit trail statistics.
        
        Returns:
            Dictionary with statistics
        """
        entries = self.audit_data.get("entries", [])
        sessions = self.audit_data.get("sessions", [])
        
        # Count by action type
        action_counts = {}
        for entry in entries:
            action_type = entry.get("action_type", "unknown")
            action_counts[action_type] = action_counts.get(action_type, 0) + 1
        
        # Count by level
        level_counts = {}
        for entry in entries:
            level = entry.get("level", "unknown")
            level_counts[level] = level_counts.get(level, 0) + 1
        
        # Count successes and failures
        successful = sum(1 for e in entries if e.get("success", True))
        failed = len(entries) - successful
        
        # Get unique users
        users = set(e.get("user") for e in entries)
        
        return {
            "total_entries": len(entries),
            "total_sessions": len(sessions),
            "active_sessions": len(self.active_sessions),
            "unique_users": len(users),
            "successful_actions": successful,
            "failed_actions": failed,
            "action_breakdown": action_counts,
            "level_breakdown": level_counts
        }
    
    def generate_report(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user: Optional[str] = None
    ) -> str:
        """
        Generate human-readable audit report.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            user: Optional user filter
        
        Returns:
            Report as string
        """
        entries = self.get_entries(
            user=user,
            start_time=start_time,
            end_time=end_time
        )
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("AUDIT TRAIL REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        # Time range
        if start_time or end_time:
            report_lines.append("Time Range:")
            if start_time:
                report_lines.append(f"  From: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if end_time:
                report_lines.append(f"  To:   {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append("")
        
        # User filter
        if user:
            report_lines.append(f"User: {user}")
            report_lines.append("")
        
        # Summary
        report_lines.append(f"Total Entries: {len(entries)}")
        successful = sum(1 for e in entries if e.success)
        failed = len(entries) - successful
        report_lines.append(f"Successful: {successful}")
        report_lines.append(f"Failed: {failed}")
        report_lines.append("")
        
        # Entries
        report_lines.append("Recent Entries:")
        report_lines.append("-" * 80)
        
        for entry in entries[:50]:  # Show up to 50 entries
            status = "✓" if entry.success else "✗"
            report_lines.append(
                f"{status} [{entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"{entry.user} - {entry.action_type}"
            )
            report_lines.append(f"   {entry.description}")
            if entry.error_message:
                report_lines.append(f"   Error: {entry.error_message}")
            report_lines.append("")
        
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)


if __name__ == "__main__":
    # Example usage
    audit = AuditTrail()
    
    # Start session
    session = audit.start_session("admin", ip_address="192.168.1.100")
    print(f"Started session: {session.session_id}")
    
    # Log some actions
    audit.log_action(
        action_type=ActionType.DOCUMENT_INGEST,
        user="admin",
        description="Ingested document: example.pdf",
        level=AuditLevel.INFO,
        resource_id="doc-12345",
        resource_type="document",
        details={"filename": "example.pdf", "pages": 10}
    )
    
    audit.log_action(
        action_type=ActionType.QUERY_EXECUTE,
        user="admin",
        description="Executed query: What are the benefits?",
        level=AuditLevel.INFO,
        details={"query": "What are the benefits?", "results": 5}
    )
    
    # Get statistics
    stats = audit.get_statistics()
    print(f"\nStatistics:")
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Unique users: {stats['unique_users']}")
    
    # End session
    audit.end_session("admin")
