"""
GitHub API client for repository and release operations.

Handles GitHub API interactions including repository info fetching,
release downloads, and rate limit management.

REFACTORED: Thread-safe cache and rate limit tracking with proper locking.
"""

import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import git
import requests

from src.config.constants import GITHUB_API_BASE
from src.models.github_info import GitHubRepo, GitHubRelease, GitHubAsset, GitHubContentItem
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GitHubClient:
    """
    GitHub API client with caching and rate limit handling.

    Provides methods for:
    - Fetching repository information
    - Getting releases and assets
    - Downloading release assets
    - Cloning repositories
    - Searching for IDA plugins

    Thread-safe: All shared state is protected by locks.
    """

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub client.

        Args:
            token: Optional GitHub personal access token for higher rate limits
        """
        self.token = token
        self.session = requests.Session()
        self.cache: dict = {}

        # Thread safety locks
        self._cache_lock = threading.RLock()  # Reentrant for nested calls
        self._rate_limit_lock = threading.Lock()

        # Set up headers
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        self.session.headers.update(headers)

        # Rate limit tracking (protected by _rate_limit_lock)
        self.rate_limit_remaining = 60
        self.rate_limit_reset = 0

    def _check_rate_limit(self) -> bool:
        """
        Check if we're within rate limits.

        Thread-safe: Uses _rate_limit_lock.

        Returns:
            True if we can make requests, False if rate limited
        """
        with self._rate_limit_lock:
            if self.rate_limit_remaining <= 1:
                now = int(time.time())
                if now < self.rate_limit_reset:
                    wait_time = self.rate_limit_reset - now
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds")
                    time.sleep(min(wait_time, 60))
        return True

    def _update_rate_limit(self, response: requests.Response) -> None:
        """
        Update rate limit info from response headers.

        Thread-safe: Uses _rate_limit_lock.

        Args:
            response: HTTP response object
        """
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")

        with self._rate_limit_lock:
            if remaining:
                self.rate_limit_remaining = int(remaining)
            if reset:
                self.rate_limit_reset = int(reset)

    def _get_cached(self, cache_key: str) -> Optional[any]:
        """
        Get value from cache.

        Thread-safe: Uses _cache_lock.

        Args:
            cache_key: Cache key

        Returns:
            Cached value or None
        """
        with self._cache_lock:
            if cache_key in self.cache:
                cached_time, value = self.cache[cache_key]
                # Cache expires after 1 hour
                if time.time() - cached_time < 3600:
                    return value
                else:
                    # Remove expired entry
                    del self.cache[cache_key]
        return None

    def _set_cached(self, cache_key: str, value: any) -> None:
        """
        Set value in cache.

        Thread-safe: Uses _cache_lock.

        Args:
            cache_key: Cache key
            value: Value to cache
        """
        with self._cache_lock:
            self.cache[cache_key] = (time.time(), value)

    def get_repository_info(self, owner: str, repo: str) -> Optional[GitHubRepo]:
        """
        Fetch repository information from GitHub.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            GitHubRepo object or None if failed
        """
        self._check_rate_limit()

        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        cache_key = f"repo:{owner}/{repo}"

        # Check cache first (thread-safe)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            response = self.session.get(url, timeout=30)
            self._update_rate_limit(response)
            response.raise_for_status()

            data = response.json()
            repo_info = GitHubRepo(
                id=f"{owner}/{repo}",
                repo_owner=owner,
                repo_name=repo,
                stars=data.get("stargazers_count", 0),
                topics=data.get("topics", []),
                last_fetched=datetime.utcnow(),
            )

            # Cache result (thread-safe)
            self._set_cached(cache_key, repo_info)
            return repo_info

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch repository info: {e}")
            return None

    def get_readme(self, owner: str, repo: str) -> Optional[str]:
        """
        Fetch README content from repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            README content or None if not found
        """
        self._check_rate_limit()

        # Try common README names
        for readme_name in ["README.md", "README.rst", "README.txt", "README"]:
            url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{readme_name}"

            try:
                response = self.session.get(url, timeout=30)
                self._update_rate_limit(response)

                if response.status_code == 200:
                    # README content is base64 encoded
                    import base64

                    data = response.json()
                    content = base64.b64decode(data["content"]).decode("utf-8")
                    return content

            except requests.exceptions.RequestException:
                continue

        return None

    def get_repository_contents(
        self, owner: str, repo: str, path: str = "", branch: str = "main"
    ) -> List[GitHubContentItem]:
        """
        Fetch contents of a repository directory.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Directory path (empty for root)
            branch: Branch name (default: "main")

        Returns:
            List of GitHubContentItem objects
        """
        self._check_rate_limit()

        # Try the requested branch first
        branches_to_try = [branch]

        # If default "main" branch is requested, also try "master" as fallback
        if branch == "main":
            branches_to_try.append("master")

        for try_branch in branches_to_try:
            url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}?ref={try_branch}"

            try:
                response = self.session.get(url, timeout=30)
                self._update_rate_limit(response)

                # If successful, parse and return
                if response.status_code == 200:
                    items = []
                    for data in response.json():
                        item = GitHubContentItem(
                            name=data["name"],
                            path=data["path"],
                            type=data["type"],
                            size=data.get("size"),
                            download_url=data.get("download_url"),
                        )
                        items.append(item)
                    logger.info(f"Successfully fetched contents from branch '{try_branch}'")
                    return items

                # If not 404, don't try other branches
                if response.status_code != 404:
                    response.raise_for_status()

            except requests.exceptions.HTTPError as e:
                # If not 404, don't try other branches
                if e.response.status_code != 404:
                    logger.error(f"Failed to fetch repository contents: {e}")
                    return []
                # 404: try next branch
                logger.debug(f"Branch '{try_branch}' not found (404), trying fallback...")

            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch repository contents: {e}")
                return []

        # All branches failed
        logger.error(f"Failed to fetch repository contents: no branches found (tried: {branches_to_try})")
        return []

    def get_releases(self, owner: str, repo: str) -> List[GitHubRelease]:
        """
        Fetch releases from repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of GitHubRelease objects
        """
        self._check_rate_limit()

        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/releases"
        cache_key = f"releases:{owner}/{repo}"

        # Check cache first (thread-safe)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            response = self.session.get(url, timeout=30)
            self._update_rate_limit(response)
            response.raise_for_status()

            releases = []
            for data in response.json():
                release = GitHubRelease(
                    tag_name=data.get("tag_name"),
                    name=data.get("name") or data.get("tag_name"),
                    body=data.get("body"),
                    prerelease=data.get("prerelease", False),
                    created_at=data.get("created_at"),
                    published_at=data.get("published_at"),
                    assets=[
                        GitHubAsset(
                            name=asset["name"],
                            size=asset.get("size", 0),
                            download_url=asset.get("browser_download_url"),
                        )
                        for asset in data.get("assets", [])
                    ],
                )
                releases.append(release)

            # Cache result (thread-safe)
            self._set_cached(cache_key, releases)
            return releases

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch releases: {e}")
            return []

    def download_release_asset(
        self, download_url: str, destination: Path, timeout: int = 300
    ) -> Optional[Path]:
        """
        Download a release asset.

        Args:
            download_url: URL to download from
            destination: Destination file path
            timeout: Download timeout in seconds

        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # For large files, we might need to follow redirects
            response = self.session.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            # Ensure parent directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Download with progress
            with open(destination, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"Downloaded asset to {destination}")
            return destination

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download asset: {e}")
            return None

    def clone_repository(self, repo_url: str, destination: Path, branch: str = "main") -> bool:
        """
        Clone a GitHub repository using GitPython.

        Args:
            repo_url: Repository URL
            destination: Destination directory
            branch: Branch to clone (default: "main")

        Returns:
            True if successful, False otherwise
        """
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Try the requested branch first
            branches_to_try = [branch]

            # If default "main" branch is requested, also try "master" as fallback
            if branch == "main":
                branches_to_try.append("master")

            for try_branch in branches_to_try:
                try:
                    # Clone using GitPython with shallow clone for speed
                    git.Repo.clone_from(
                        repo_url,
                        destination,
                        branch=try_branch,
                        depth=1,  # Shallow clone
                    )
                    logger.info(f"Cloned repository to {destination} from branch '{try_branch}'")
                    return True

                except git.GitCommandError as e:
                    stderr = str(e.stderr).strip() if e.stderr else ""
                    # Check if it's a branch not found error
                    if "Remote branch" in stderr or "does not exist" in stderr.lower():
                        logger.warning(f"Branch '{try_branch}' not found, trying fallback...")
                        # Clean up partial clone if any
                        if destination.exists():
                            shutil.rmtree(destination, ignore_errors=True)
                        continue  # Try next branch
                    else:
                        # Other error, don't try other branches
                        logger.error(f"Git clone failed: {stderr}")
                        return False

            # All branches failed
            logger.error(f"Git clone failed: no valid branches found (tried: {branches_to_try})")
            return False

        except git.GitCommandError as e:
            logger.error(f"Git command error: {e.stderr if e.stderr else e}")
            return False
        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")
            return False

    def get_commit_hash(self, repo_path: Path) -> Optional[str]:
        """
        Get the current commit hash of a cloned repository.

        Args:
            repo_path: Path to the cloned repository

        Returns:
            Commit hash (first 8 characters) or None if failed
        """
        try:
            repo = git.Repo(repo_path)
            commit_hash = repo.head.commit.hexsha
            return commit_hash[:8]  # Return first 8 characters for version display
        except Exception as e:
            logger.error(f"Failed to get commit hash: {e}")
            return None

    def pull_repository(self, repo_path: Path) -> bool:
        """
        Pull latest changes for a cloned repository.

        Args:
            repo_path: Path to the cloned repository

        Returns:
            True if successful, False otherwise
        """
        try:
            repo = git.Repo(repo_path)
            repo.remotes.origin.pull()
            logger.info(f"Pulled latest changes for {repo_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to pull repository: {e}")
            return False

    def search_repositories(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 100,
    ) -> List[GitHubRepo]:
        """
        Search for GitHub repositories.

        Args:
            query: Search query
            sort: Sort field (stars, forks, updated)
            order: Sort order (asc, desc)
            per_page: Results per page (max 100)

        Returns:
            List of GitHubRepo objects
        """
        self._check_rate_limit()

        url = f"{GITHUB_API_BASE}/search/repositories"
        cache_key = f"search:{query}:{sort}:{order}:{per_page}"

        # Check cache first (thread-safe)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            params = {
                "q": f"{query} topic:ida pro",
                "sort": sort,
                "order": order,
                "per_page": per_page,
            }

            response = self.session.get(url, params=params, timeout=30)
            self._update_rate_limit(response)
            response.raise_for_status()

            data = response.json()
            repos = []

            for item in data.get("items", []):
                repo = GitHubRepo(
                    id=f"{item['owner']['login']}/{item['name']}",
                    repo_owner=item["owner"]["login"],
                    repo_name=item["name"],
                    stars=item.get("stargazers_count", 0),
                    topics=item.get("topics", []),
                    last_fetched=datetime.utcnow(),
                )
                repos.append(repo)

            # Cache result (thread-safe)
            self._set_cached(cache_key, repos)
            return repos

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to search repositories: {e}")
            return []

    def close(self) -> None:
        """
        Close the HTTP session.

        Call this when shutting down the application.
        """
        try:
            self.session.close()
            logger.info("GitHub client session closed")
        except Exception as e:
            logger.error(f"Failed to close GitHub client session: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures session is properly closed."""
        self.close()
