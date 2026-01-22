"""
Version Control CLI

Command-line interface for version management:
- commit: Commit changes
- history: View commit history
- diff: Show differences between versions
- rollback: Rollback to previous version
- tags: Manage tags
- status: Show repository status
- manifest: View manifest history
- audit: View audit trail
"""

import click
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from app.versioning.git_manager import GitVersionManager
from app.versioning.manifest_tracker import ManifestTracker
from app.versioning.audit_trail import AuditTrail, ActionType, AuditLevel


@click.group()
@click.option('--repo-path', type=click.Path(), default=None, help='Repository path')
@click.pass_context
def cli(ctx, repo_path):
    """Version control CLI for document management."""
    ctx.ensure_object(dict)
    
    # Initialize managers
    ctx.obj['git'] = GitVersionManager(repo_path=repo_path)
    ctx.obj['manifest'] = ManifestTracker()
    ctx.obj['audit'] = AuditTrail()


@cli.command()
@click.option('--message', '-m', required=True, help='Commit message')
@click.option('--author', '-a', default='System', help='Author name')
@click.option('--files', '-f', multiple=True, help='Specific files to commit')
@click.option('--all', 'add_all', is_flag=True, default=True, help='Add all changed files')
@click.option('--track-manifest', is_flag=True, default=True, help='Track manifest version')
@click.pass_context
def commit(ctx, message, author, files, add_all, track_manifest):
    """Commit changes to repository."""
    git_manager = ctx.obj['git']
    manifest_tracker = ctx.obj['manifest']
    audit_trail = ctx.obj['audit']
    
    try:
        # Initialize repository if needed
        if not git_manager.is_git_repo():
            click.echo("Initializing git repository...")
            git_manager.init_repository()
        
        # Commit changes
        click.echo(f"Committing changes: {message}")
        commit_hash = git_manager.commit_changes(
            message=message,
            author=author,
            files=list(files) if files else None,
            add_all=add_all
        )
        
        if not commit_hash:
            click.echo("No changes to commit.", fg='yellow')
            return
        
        click.echo(f"✓ Committed: {commit_hash[:8]}", fg='green')
        
        # Track manifest version
        if track_manifest:
            version = manifest_tracker.record_version(
                commit_hash=commit_hash,
                changes_summary=message
            )
            if version:
                click.echo(f"✓ Tracked manifest version: {version.version_id[:8]}", fg='green')
        
        # Log to audit trail
        audit_trail.log_action(
            action_type=ActionType.VERSION_COMMIT,
            user=author,
            description=f"Committed: {message}",
            level=AuditLevel.INFO,
            details={"commit_hash": commit_hash}
        )
        
    except Exception as e:
        click.echo(f"Error: {e}", fg='red')
        sys.exit(1)


@cli.command()
@click.option('--max-count', '-n', default=10, help='Maximum commits to show')
@click.option('--file', '-f', help='Filter by file path')
@click.option('--oneline', is_flag=True, help='Compact output')
@click.pass_context
def history(ctx, max_count, file, oneline):
    """View commit history."""
    git_manager = ctx.obj['git']
    
    try:
        if not git_manager.is_git_repo():
            click.echo("Not a git repository.", fg='yellow')
            return
        
        commits = git_manager.get_history(max_count=max_count, file_path=file)
        
        if not commits:
            click.echo("No commits found.", fg='yellow')
            return
        
        click.echo(f"\nCommit History ({len(commits)} commits):\n")
        
        for commit in commits:
            if oneline:
                click.echo(f"{commit.hash[:8]} {commit.message}")
            else:
                click.echo(f"Commit:  {commit.hash[:8]}")
                click.echo(f"Author:  {commit.author}")
                click.echo(f"Date:    {commit.date.strftime('%Y-%m-%d %H:%M:%S')}")
                click.echo(f"Message: {commit.message}")
                if commit.files_changed:
                    click.echo(f"Files:   {', '.join(commit.files_changed[:3])}")
                    if len(commit.files_changed) > 3:
                        click.echo(f"         (+{len(commit.files_changed) - 3} more)")
                click.echo()
    
    except Exception as e:
        click.echo(f"Error: {e}", fg='red')
        sys.exit(1)


@cli.command()
@click.option('--from', 'from_commit', default='HEAD~1', help='Starting commit')
@click.option('--to', 'to_commit', default='HEAD', help='Ending commit')
@click.option('--file', '-f', help='Limit diff to file')
@click.option('--stat', is_flag=True, help='Show only statistics')
@click.pass_context
def diff(ctx, from_commit, to_commit, file, stat):
    """Show differences between versions."""
    git_manager = ctx.obj['git']
    
    try:
        if not git_manager.is_git_repo():
            click.echo("Not a git repository.", fg='yellow')
            return
        
        diff_result = git_manager.get_diff(
            from_commit=from_commit,
            to_commit=to_commit,
            file_path=file
        )
        
        if not diff_result:
            click.echo("No differences found.", fg='yellow')
            return
        
        click.echo(f"\nDiff: {from_commit} → {to_commit}\n")
        click.echo(f"Files changed: {len(diff_result.files_changed)}")
        click.echo(f"Additions:     {diff_result.additions} lines")
        click.echo(f"Deletions:     {diff_result.deletions} lines")
        
        if diff_result.files_changed:
            click.echo(f"\nModified files:")
            for file_name in diff_result.files_changed:
                click.echo(f"  • {file_name}")
        
        if not stat and diff_result.diff_text:
            click.echo(f"\n{diff_result.diff_text}")
    
    except Exception as e:
        click.echo(f"Error: {e}", fg='red')
        sys.exit(1)


@cli.command()
@click.argument('commit_hash')
@click.option('--hard', is_flag=True, help='Discard all changes (hard reset)')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
@click.pass_context
def rollback(ctx, commit_hash, hard, yes):
    """Rollback to a specific commit."""
    git_manager = ctx.obj['git']
    audit_trail = ctx.obj['audit']
    
    try:
        if not git_manager.is_git_repo():
            click.echo("Not a git repository.", fg='yellow')
            return
        
        # Confirmation
        if not yes:
            reset_type = "hard" if hard else "soft"
            click.confirm(
                f"Rollback to {commit_hash[:8]} ({reset_type} reset)? This may discard changes.",
                abort=True
            )
        
        # Rollback
        click.echo(f"Rolling back to {commit_hash[:8]}...")
        success = git_manager.rollback(commit_hash=commit_hash, hard=hard)
        
        if success:
            click.echo(f"✓ Rolled back to {commit_hash[:8]}", fg='green')
            
            # Log to audit trail
            audit_trail.log_action(
                action_type=ActionType.VERSION_ROLLBACK,
                user="CLI",
                description=f"Rolled back to {commit_hash[:8]}",
                level=AuditLevel.WARNING,
                details={"commit_hash": commit_hash, "hard": hard}
            )
        else:
            click.echo("Rollback failed.", fg='red')
            sys.exit(1)
    
    except Exception as e:
        click.echo(f"Error: {e}", fg='red')
        sys.exit(1)


@cli.group()
def tag():
    """Manage tags."""
    pass


@tag.command('create')
@click.argument('tag_name')
@click.option('--message', '-m', help='Tag message')
@click.option('--commit', '-c', help='Commit hash to tag')
@click.pass_context
def tag_create(ctx, tag_name, message, commit):
    """Create a tag."""
    git_manager = ctx.obj['git']
    
    try:
        if not git_manager.is_git_repo():
            click.echo("Not a git repository.", fg='yellow')
            return
        
        success = git_manager.create_tag(
            tag_name=tag_name,
            message=message,
            commit_hash=commit
        )
        
        if success:
            click.echo(f"✓ Created tag: {tag_name}", fg='green')
        else:
            click.echo("Failed to create tag.", fg='red')
            sys.exit(1)
    
    except Exception as e:
        click.echo(f"Error: {e}", fg='red')
        sys.exit(1)


@tag.command('list')
@click.pass_context
def tag_list(ctx):
    """List all tags."""
    git_manager = ctx.obj['git']
    
    try:
        if not git_manager.is_git_repo():
            click.echo("Not a git repository.", fg='yellow')
            return
        
        tags = git_manager.list_tags()
        
        if not tags:
            click.echo("No tags found.", fg='yellow')
            return
        
        click.echo(f"\nTags ({len(tags)}):\n")
        for tag in tags:
            click.echo(f"  • {tag}")
    
    except Exception as e:
        click.echo(f"Error: {e}", fg='red')
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show repository status."""
    git_manager = ctx.obj['git']
    
    try:
        if not git_manager.is_git_repo():
            click.echo("Not a git repository. Run 'commit' to initialize.", fg='yellow')
            return
        
        status_data = git_manager.get_status()
        
        click.echo("\nRepository Status:\n")
        
        if status_data["staged"]:
            click.echo(f"Staged files ({len(status_data['staged'])}):", fg='green')
            for file in status_data["staged"]:
                click.echo(f"  • {file}")
        
        if status_data["modified"]:
            click.echo(f"\nModified files ({len(status_data['modified'])}):", fg='yellow')
            for file in status_data["modified"]:
                click.echo(f"  • {file}")
        
        if status_data["untracked"]:
            click.echo(f"\nUntracked files ({len(status_data['untracked'])}):", fg='red')
            for file in status_data["untracked"]:
                click.echo(f"  • {file}")
        
        if not any(status_data.values()):
            click.echo("Working directory clean.", fg='green')
    
    except Exception as e:
        click.echo(f"Error: {e}", fg='red')
        sys.exit(1)


@cli.group()
def manifest():
    """Manage manifest versions."""
    pass


@manifest.command('history')
@click.option('--limit', '-n', default=10, help='Maximum versions to show')
@click.pass_context
def manifest_history(ctx, limit):
    """View manifest version history."""
    manifest_tracker = ctx.obj['manifest']
    
    try:
        versions = manifest_tracker.get_version_history(limit=limit)
        
        if not versions:
            click.echo("No manifest versions found.", fg='yellow')
            return
        
        click.echo(f"\nManifest Version History ({len(versions)} versions):\n")
        
        for version in versions:
            click.echo(f"Version: {version.version_id[:8]}")
            click.echo(f"Date:    {version.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            click.echo(f"Docs:    {version.total_documents} documents, {version.total_chunks} chunks")
            if version.commit_hash:
                click.echo(f"Commit:  {version.commit_hash[:8]}")
            if version.changes_summary:
                click.echo(f"Changes: {version.changes_summary}")
            click.echo()
    
    except Exception as e:
        click.echo(f"Error: {e}", fg='red')
        sys.exit(1)


@manifest.command('stats')
@click.pass_context
def manifest_stats(ctx):
    """Show manifest statistics."""
    manifest_tracker = ctx.obj['manifest']
    
    try:
        stats = manifest_tracker.get_statistics()
        
        click.echo("\nManifest Statistics:\n")
        click.echo(f"Total versions:   {stats['total_versions']}")
        click.echo(f"Total changes:    {stats['total_changes']}")
        click.echo(f"Document changes: {stats['total_document_changes']}")
        
        if stats.get('current_version'):
            cv = stats['current_version']
            click.echo(f"\nCurrent version:")
            click.echo(f"  Documents: {cv['total_documents']}")
            click.echo(f"  Chunks:    {cv['total_chunks']}")
            click.echo(f"  ID:        {cv['version_id']}")
        
        if stats.get('change_types'):
            click.echo(f"\nChange breakdown:")
            for change_type, count in stats['change_types'].items():
                click.echo(f"  {change_type}: {count}")
    
    except Exception as e:
        click.echo(f"Error: {e}", fg='red')
        sys.exit(1)


@cli.group()
def audit():
    """View audit trail."""
    pass


@audit.command('recent')
@click.option('--limit', '-n', default=20, help='Number of entries to show')
@click.option('--user', '-u', help='Filter by user')
@click.pass_context
def audit_recent(ctx, limit, user):
    """View recent audit entries."""
    audit_trail = ctx.obj['audit']
    
    try:
        entries = audit_trail.get_entries(user=user, limit=limit)
        
        if not entries:
            click.echo("No audit entries found.", fg='yellow')
            return
        
        click.echo(f"\nRecent Audit Entries ({len(entries)}):\n")
        
        for entry in entries:
            status = "✓" if entry.success else "✗"
            time_str = entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            click.echo(f"{status} [{time_str}] {entry.user}")
            click.echo(f"   {entry.action_type}: {entry.description}")
            if entry.error_message:
                click.echo(f"   Error: {entry.error_message}", fg='red')
            click.echo()
    
    except Exception as e:
        click.echo(f"Error: {e}", fg='red')
        sys.exit(1)


@audit.command('stats')
@click.pass_context
def audit_stats(ctx):
    """Show audit statistics."""
    audit_trail = ctx.obj['audit']
    
    try:
        stats = audit_trail.get_statistics()
        
        click.echo("\nAudit Trail Statistics:\n")
        click.echo(f"Total entries:      {stats['total_entries']}")
        click.echo(f"Total sessions:     {stats['total_sessions']}")
        click.echo(f"Active sessions:    {stats['active_sessions']}")
        click.echo(f"Unique users:       {stats['unique_users']}")
        click.echo(f"Successful actions: {stats['successful_actions']}")
        click.echo(f"Failed actions:     {stats['failed_actions']}")
        
        if stats.get('action_breakdown'):
            click.echo(f"\nAction breakdown:")
            for action_type, count in sorted(stats['action_breakdown'].items(), key=lambda x: x[1], reverse=True):
                click.echo(f"  {action_type}: {count}")
    
    except Exception as e:
        click.echo(f"Error: {e}", fg='red')
        sys.exit(1)


if __name__ == '__main__':
    cli()
