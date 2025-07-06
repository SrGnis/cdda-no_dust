#!/usr/bin/env python3
"""
Git Manager for CDDA No Dust Mod Automation

This module handles git operations including staging, committing, pushing,
and tagging changes for the automation system.
"""

import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
import logging

from config import Config
from utils import run_command, check_git_repository


class GitManager:
    """Handles git operations for the automation system."""
    
    def __init__(self, config: Config):
        """Initialize the git manager with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.repo_path = Path(config.project_root).resolve()
    
    def is_git_repository(self) -> bool:
        """
        Check if the current directory is a git repository.
        
        Returns:
            bool: True if it's a git repository
        """
        return check_git_repository(self.repo_path)
    
    def get_git_status(self) -> Tuple[bool, str]:
        """
        Get the current git status.
        
        Returns:
            Tuple[bool, str]: (success, status_output)
        """
        try:
            result = run_command(["git", "status", "--porcelain"], cwd=self.repo_path)
            return result.returncode == 0, result.stdout
        except Exception as e:
            self.logger.error(f"Failed to get git status: {e}")
            return False, ""
    
    def has_uncommitted_changes(self) -> bool:
        """
        Check if there are uncommitted changes in the repository.
        
        Returns:
            bool: True if there are uncommitted changes
        """
        success, status = self.get_git_status()
        return success and bool(status.strip())
    
    def stage_changes(self, paths: Optional[List[str]] = None) -> bool:
        """
        Stage changes for commit.
        
        Args:
            paths: List of paths to stage (None to stage all changes)
            
        Returns:
            bool: True if staging was successful
        """
        try:
            if paths is None:
                # Stage all changes in src/ directory and tracking files
                paths_to_stage = [
                    self.config.output_dir,
                    self.config.last_version_file,
                    self.config.last_sha_file
                ]
            else:
                paths_to_stage = paths
            
            # Check which paths exist before staging
            existing_paths = []
            for path in paths_to_stage:
                path_obj = Path(path)
                if path_obj.exists():
                    existing_paths.append(str(path))
            
            if not existing_paths:
                self.logger.warning("No existing paths to stage")
                return True
            
            command = ["git", "add"] + existing_paths
            result = run_command(command, cwd=self.repo_path)
            
            if result.returncode == 0:
                self.logger.info(f"Staged changes: {', '.join(existing_paths)}")
                return True
            else:
                self.logger.error(f"Failed to stage changes: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error staging changes: {e}")
            return False
    
    def commit_changes(self, message: str, author: Optional[str] = None) -> bool:
        """
        Commit staged changes.
        
        Args:
            message: Commit message
            author: Optional author string (format: "Name <email>")
            
        Returns:
            bool: True if commit was successful
        """
        try:
            command = ["git", "commit", "-m", message]
            
            if author:
                command.extend(["--author", author])
            
            result = run_command(command, cwd=self.repo_path)
            
            if result.returncode == 0:
                self.logger.info(f"Committed changes: {message}")
                return True
            else:
                # Check if there were no changes to commit
                if "nothing to commit" in result.stdout:
                    self.logger.info("No changes to commit")
                    return True
                else:
                    self.logger.error(f"Failed to commit changes: {result.stderr}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error committing changes: {e}")
            return False
    
    def create_tag(self, tag_name: str, tag_message: Optional[str] = None) -> bool:
        """
        Create a git tag.
        
        Args:
            tag_name: Name of the tag
            tag_message: Optional tag message
            
        Returns:
            bool: True if tag creation was successful
        """
        try:
            # Check if tag already exists
            if self._tag_exists(tag_name):
                self.logger.warning(f"Tag already exists: {tag_name}")
                return True
            
            command = ["git", "tag"]
            
            if tag_message:
                command.extend(["-a", tag_name, "-m", tag_message])
            else:
                command.append(tag_name)
            
            result = run_command(command, cwd=self.repo_path)
            
            if result.returncode == 0:
                self.logger.info(f"Created tag: {tag_name}")
                return True
            else:
                self.logger.error(f"Failed to create tag {tag_name}: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating tag {tag_name}: {e}")
            return False
    
    def push_changes(self, remote: str = "origin", branch: str = "main") -> bool:
        """
        Push committed changes to remote repository.
        
        Args:
            remote: Remote name (default: origin)
            branch: Branch name (default: main)
            
        Returns:
            bool: True if push was successful
        """
        try:
            command = ["git", "push", remote, branch]
            result = run_command(command, cwd=self.repo_path)
            
            if result.returncode == 0:
                self.logger.info(f"Pushed changes to {remote}/{branch}")
                return True
            else:
                self.logger.error(f"Failed to push changes: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error pushing changes: {e}")
            return False
    
    def push_tags(self, remote: str = "origin") -> bool:
        """
        Push tags to remote repository.
        
        Args:
            remote: Remote name (default: origin)
            
        Returns:
            bool: True if push was successful
        """
        try:
            command = ["git", "push", remote, "--tags"]
            result = run_command(command, cwd=self.repo_path)
            
            if result.returncode == 0:
                self.logger.info(f"Pushed tags to {remote}")
                return True
            else:
                self.logger.error(f"Failed to push tags: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error pushing tags: {e}")
            return False
    
    def _tag_exists(self, tag_name: str) -> bool:
        """
        Check if a tag exists.
        
        Args:
            tag_name: Name of the tag to check
            
        Returns:
            bool: True if tag exists
        """
        try:
            result = run_command(["git", "tag", "-l", tag_name], cwd=self.repo_path)
            return result.returncode == 0 and tag_name in result.stdout
        except Exception:
            return False
    
    def get_current_branch(self) -> Optional[str]:
        """
        Get the current branch name.
        
        Returns:
            Optional[str]: Current branch name or None if failed
        """
        try:
            result = run_command(["git", "branch", "--show-current"], cwd=self.repo_path)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return None
        except Exception:
            return None
    
    def get_remote_url(self, remote: str = "origin") -> Optional[str]:
        """
        Get the URL of a remote repository.
        
        Args:
            remote: Remote name (default: origin)
            
        Returns:
            Optional[str]: Remote URL or None if failed
        """
        try:
            result = run_command(["git", "remote", "get-url", remote], cwd=self.repo_path)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return None
        except Exception:
            return None
    
    def configure_git_user(self, name: str, email: str, global_config: bool = False) -> bool:
        """
        Configure git user name and email.
        
        Args:
            name: User name
            email: User email
            global_config: Whether to set global configuration
            
        Returns:
            bool: True if configuration was successful
        """
        try:
            scope = "--global" if global_config else "--local"
            
            # Set user name
            result1 = run_command(["git", "config", scope, "user.name", name], cwd=self.repo_path)
            
            # Set user email
            result2 = run_command(["git", "config", scope, "user.email", email], cwd=self.repo_path)
            
            if result1.returncode == 0 and result2.returncode == 0:
                self.logger.info(f"Configured git user: {name} <{email}>")
                return True
            else:
                self.logger.error("Failed to configure git user")
                return False
                
        except Exception as e:
            self.logger.error(f"Error configuring git user: {e}")
            return False
    
    def get_git_info(self) -> dict:
        """
        Get comprehensive git repository information.
        
        Returns:
            dict: Dictionary containing git repository information
        """
        info = {
            "is_git_repo": self.is_git_repository(),
            "has_uncommitted_changes": False,
            "current_branch": None,
            "remote_url": None,
            "last_commit": None
        }
        
        if info["is_git_repo"]:
            info["has_uncommitted_changes"] = self.has_uncommitted_changes()
            info["current_branch"] = self.get_current_branch()
            info["remote_url"] = self.get_remote_url()
            
            # Get last commit info
            try:
                result = run_command(["git", "log", "-1", "--oneline"], cwd=self.repo_path)
                if result.returncode == 0:
                    info["last_commit"] = result.stdout.strip()
            except Exception:
                pass
        
        return info
