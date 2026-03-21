#!/usr/bin/env python3
"""
Script to map dependencies from an SBOM JSON file to their public code repositories.
This script accepts a JSON file that contains a "dependencies" property with package information
and attempts to find the public code repository (GitHub, GitLab, etc.) for each dependency.
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# Fix for the urllib3 dependency issue
try:
    import requests
except ImportError:
    print("Error: The requests library is not properly installed.", file=sys.stderr)
    print("Try running: pip install --upgrade requests urllib3", file=sys.stderr)
    sys.exit(1)


def find_repository_for_npm_package(package_name: str) -> tuple[Optional[str], Optional[str]]:
    """Find the repository URL and license for an NPM package."""
    try:
        response = requests.get(f"https://registry.npmjs.org/{package_name}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            repo_url = None
            license_info = None

            # Extract repository URL
            if "repository" in data:
                repo = data["repository"]
                if isinstance(repo, dict) and "url" in repo:
                    repo_url = clean_repository_url(repo["url"])
                elif isinstance(repo, str):
                    repo_url = clean_repository_url(repo)

            # Check homepage as fallback for repo URL
            if repo_url is None and "homepage" in data:
                homepage = data["homepage"]
                if homepage and ("github.com" in homepage or "gitlab.com" in homepage):
                    repo_url = homepage

            # Extract license information
            if "license" in data:
                license_data = data["license"]
                if isinstance(license_data, str):
                    license_info = license_data
                elif isinstance(license_data, dict) and "type" in license_data:
                    license_info = license_data["type"]

            return repo_url, license_info

        return None, None
    except Exception as e:
        print(
            f"Error finding repository for NPM package {package_name}: {e}",
            file=sys.stderr,
        )
        return None, None


def find_repository_for_python_package(package_name: str) -> tuple[Optional[str], Optional[str]]:
    """Find the repository URL and license for a Python package."""
    try:
        # Try PyPI API first
        response = requests.get(f"https://pypi.org/pypi/{package_name}/json", timeout=10)
        if response.status_code == 200:
            data = response.json()
            info = data.get("info", {})
            repo_url = None
            license_info = None

            # Check project_urls first for repo URL
            project_urls = info.get("project_urls", {})
            if project_urls:
                for key, url in project_urls.items():
                    if any(
                        term in key.lower()
                        for term in ["source", "code", "github", "gitlab", "repository"]
                    ):
                        if "github.com" in url or "gitlab.com" in url:
                            repo_url = clean_repository_url(url)
                            break

            # Check home_page if no repo URL found
            if repo_url is None:
                home_page = info.get("home_page")
                if home_page and ("github.com" in home_page or "gitlab.com" in home_page):
                    repo_url = clean_repository_url(home_page)

            # Check project_url if still no repo URL
            if repo_url is None:
                project_url = info.get("project_url")
                if project_url and ("github.com" in project_url or "gitlab.com" in project_url):
                    repo_url = clean_repository_url(project_url)

            # Extract license information
            license_info = info.get("license")
            if not license_info or license_info.lower() in ["", "unknown"]:
                classifiers = info.get("classifiers", [])
                for classifier in classifiers:
                    if classifier.startswith("License ::"):
                        license_info = classifier.split("::")[-1].strip()
                        break

            return repo_url, license_info

        return None, None
    except Exception as e:
        print(
            f"Error finding repository for Python package {package_name}: {e}",
            file=sys.stderr,
        )
        return None, None


def clean_repository_url(url: str) -> str:
    """Clean and normalize repository URLs."""
    # Remove git+ prefix
    if url.startswith("git+"):
        url = url[4:]

    # Convert git:// to https://
    if url.startswith("git://"):
        url = "https://" + url[6:]

    # Handle git@github.com: format
    if url.startswith("git@"):
        parts = url.split(":", 1)
        if len(parts) == 2:
            domain = parts[0].replace("git@", "")
            path = parts[1]
            url = f"https://{domain}/{path}"

    # Remove .git suffix
    if url.endswith(".git"):
        url = url[:-4]

    # Parse URL to ensure it's valid
    parsed = urlparse(url)
    if not parsed.scheme:
        # Try adding https:// if no scheme
        url = "https://" + url

    return url


def extract_license_from_repo(repo_url: str) -> Optional[str]:
    """Extract license information from a repository."""
    if not repo_url:
        return None

    try:
        # Convert repository URL to GitHub API URL format
        if "github.com" in repo_url:
            # Extract owner and repo name from URL
            parts = repo_url.split("github.com/")
            if len(parts) < 2:
                return None

            owner_repo = parts[1].strip("/")
            api_url = f"https://api.github.com/repos/{owner_repo}/license"

            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                license_data = response.json()
                if "license" in license_data and "spdx_id" in license_data["license"]:
                    return license_data["license"]["spdx_id"]

        # For GitLab or other repositories, we could implement similar logic
        # but would need to use their specific APIs

        return None
    except Exception as e:
        print(f"Error extracting license from {repo_url}: {e}", file=sys.stderr)
        return None


def process_dependency(dependency: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single dependency to find its repository."""
    name = dependency.get("name", "")
    packager = dependency.get("packager", "").lower()

    repository_url = None
    license_info = None

    if packager == "npm":
        repository_url, license_info = find_repository_for_npm_package(name)
    elif packager in ["poetry", "pip", "python"]:
        repository_url, license_info = find_repository_for_python_package(name)

    # Create a result with name, repository URL and license
    result = {"name": name, "repository_url": repository_url}

    # Add license if found from package registry
    if license_info:
        result["license"] = license_info

    # Print a warning if no repository URL was found
    if repository_url is None:
        print(f"Warning: No repository URL found for {name} ({packager})", file=sys.stderr)
    else:
        # When repository is found, try to extract the LICENSE from the repo if not already found
        if not license_info:
            repo_license = extract_license_from_repo(repository_url)
            if repo_license:
                result["license"] = repo_license
                print(f"Found license {repo_license} for {name} from repository", file=sys.stderr)
            else:
                print(f"No license information found for {name}", file=sys.stderr)
        else:
            print(f"Found license {license_info} for {name} from package registry", file=sys.stderr)

    return result


def process_dependencies(
    dependencies: List[Dict[str, Any]], max_workers: int = 10
) -> List[Dict[str, Any]]:
    """Process all dependencies in parallel to find their repositories."""
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i, result in enumerate(executor.map(process_dependency, dependencies)):
            results.append(result)
            # Print progress
            if (i + 1) % 10 == 0 or i + 1 == len(dependencies):
                print(
                    f"Processed {i + 1}/{len(dependencies)} dependencies",
                    file=sys.stderr,
                )

    return results


def main() -> None:
    """Main function to parse arguments and process the SBOM file."""
    parser = argparse.ArgumentParser(
        description="Map SBOM dependencies to their public code repositories"
    )
    parser.add_argument("input_file", help="Path to the input JSON file containing dependencies")
    parser.add_argument(
        "output_file", nargs="?", help="Path to the output JSON file (default: stdout)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum number of worker threads (default: 10)",
    )

    args = parser.parse_args()

    try:
        with open(args.input_file, "r") as f:
            data = json.load(f)

        if "dependencies" not in data:
            print(
                "Error: The input file does not contain a 'dependencies' property",
                file=sys.stderr,
            )
            sys.exit(1)

        dependencies = data["dependencies"]
        print(f"Processing {len(dependencies)} dependencies...", file=sys.stderr)

        start_time = time.time()
        processed_dependencies = process_dependencies(dependencies, args.max_workers)
        elapsed_time = time.time() - start_time

        # Update the original data with processed dependencies
        data["dependencies"] = processed_dependencies

        # Add metadata about the processing
        data["metadata"] = {
            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "processing_time_seconds": round(elapsed_time, 2),
            "total_dependencies": len(dependencies),
            "dependencies_with_repositories": sum(
                1 for d in processed_dependencies if d.get("repository_url")
            ),
        }

        # Output the results
        if args.output_file:
            with open(args.output_file, "w") as f:
                json.dump(data, f, indent=2)
            print(f"Results written to {args.output_file}", file=sys.stderr)
            print(
                f"Found repositories for {data['metadata']['dependencies_with_repositories']} out of {len(dependencies)} dependencies",
                file=sys.stderr,
            )
        else:
            print(json.dumps(data, indent=2))

    except FileNotFoundError:
        print(f"Error: The file {args.input_file} was not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: The file {args.input_file} is not valid JSON", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
