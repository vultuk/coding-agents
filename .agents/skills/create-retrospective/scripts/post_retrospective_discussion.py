#!/usr/bin/env python3
"""
Post a retrospective discussion to a GitHub Discussions category.

Examples:
  python3 post_retrospective_discussion.py \\
    --title "[Retrospective] LP failover lag (2026-03-05)" \\
    --body-file /tmp/retro.md

  python3 post_retrospective_discussion.py \\
    --repo nummus-software/afx-markets \\
    --category Retrospectives \\
    --title "[Retrospective] Pricing stream outage (2026-03-05)" \\
    --body-file /tmp/retro.md
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> str:
    try:
        result = subprocess.run(
            cmd,
            check=True,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        print("Error: required executable not found. Install GitHub CLI (gh).", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        stdout = exc.stdout.strip() if exc.stdout else ""
        detail = stderr or stdout or "unknown gh error"
        print(f"Error running command: {' '.join(cmd)}", file=sys.stderr)
        print(detail, file=sys.stderr)
        sys.exit(1)
    return result.stdout


def ensure_gh_auth() -> None:
    run(["gh", "auth", "status"])


def resolve_repo(repo: str | None) -> str:
    if repo:
        if "/" not in repo:
            print("Error: --repo must be in owner/repo format.", file=sys.stderr)
            sys.exit(1)
        return repo
    detected = run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"]).strip()
    if not detected or "/" not in detected:
        print("Error: unable to resolve repository from current directory.", file=sys.stderr)
        sys.exit(1)
    return detected


def graphql(query: str, fields: dict[str, str]) -> dict:
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in fields.items():
        cmd.extend(["-F", f"{key}={value}"])
    raw = run(cmd)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("Error: failed to parse JSON response from gh api graphql.", file=sys.stderr)
        print(raw, file=sys.stderr)
        sys.exit(1)


def resolve_category_and_repo_id(owner: str, repo: str, category_name: str) -> tuple[str, str, list[str]]:
    query = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    id
    discussionCategories(first: 100) {
      nodes {
        id
        name
      }
    }
  }
}
""".strip()
    response = graphql(query, {"owner": owner, "name": repo})
    repository = (response.get("data") or {}).get("repository")
    if not repository:
        print(f"Error: repository not found or not accessible: {owner}/{repo}", file=sys.stderr)
        sys.exit(1)

    repo_id = repository.get("id")
    categories = ((repository.get("discussionCategories") or {}).get("nodes") or [])
    category_lookup = {str(c.get("name", "")).lower(): c for c in categories}
    matched = category_lookup.get(category_name.lower())
    available = sorted(str(c.get("name", "")).strip() for c in categories if c.get("name"))

    if not matched:
        print(
            f"Error: category '{category_name}' not found in {owner}/{repo}.",
            file=sys.stderr,
        )
        if available:
            print(f"Available categories: {', '.join(available)}", file=sys.stderr)
        sys.exit(1)

    category_id = matched.get("id")
    if not repo_id or not category_id:
        print("Error: missing repository/category IDs from GraphQL response.", file=sys.stderr)
        sys.exit(1)

    return repo_id, category_id, available


def create_discussion(repo_id: str, category_id: str, title: str, body: str) -> dict:
    mutation = """
mutation($repositoryId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
  createDiscussion(input: {
    repositoryId: $repositoryId
    categoryId: $categoryId
    title: $title
    body: $body
  }) {
    discussion {
      id
      number
      url
      title
      category {
        name
      }
    }
  }
}
""".strip()
    response = graphql(
        mutation,
        {
            "repositoryId": repo_id,
            "categoryId": category_id,
            "title": title,
            "body": body,
        },
    )
    discussion = ((response.get("data") or {}).get("createDiscussion") or {}).get("discussion")
    if not discussion:
        print("Error: createDiscussion returned no discussion object.", file=sys.stderr)
        print(json.dumps(response, indent=2), file=sys.stderr)
        sys.exit(1)
    return discussion


def read_body(body: str | None, body_file: str | None) -> str:
    if body:
        return body.strip()
    if not body_file:
        print("Error: provide --body or --body-file.", file=sys.stderr)
        sys.exit(1)
    path = Path(body_file)
    if not path.exists():
        print(f"Error: body file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return path.read_text(encoding="utf-8").strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a GitHub Discussion retrospective post.")
    parser.add_argument("--title", required=True, help="Discussion title")
    parser.add_argument("--body", help="Discussion body markdown")
    parser.add_argument("--body-file", help="Path to markdown file for discussion body")
    parser.add_argument("--repo", help="Repository in owner/repo format (defaults to current repo)")
    parser.add_argument("--category", default="Retrospectives", help="Discussion category name")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve IDs and print posting summary without creating discussion",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    body = read_body(args.body, args.body_file)
    if not args.title.strip():
        print("Error: title cannot be empty.", file=sys.stderr)
        sys.exit(1)
    if not body:
        print("Error: body cannot be empty.", file=sys.stderr)
        sys.exit(1)

    ensure_gh_auth()
    name_with_owner = resolve_repo(args.repo)
    owner, repo = name_with_owner.split("/", 1)
    repo_id, category_id, available = resolve_category_and_repo_id(owner, repo, args.category)

    if args.dry_run:
        print("Dry run successful.")
        print(f"Repository: {name_with_owner}")
        print(f"Category: {args.category}")
        print(f"Title: {args.title}")
        print(f"Body length: {len(body)} characters")
        if available:
            print(f"Available categories: {', '.join(available)}")
        print(f"Resolved repository ID: {repo_id}")
        print(f"Resolved category ID: {category_id}")
        return

    discussion = create_discussion(repo_id, category_id, args.title.strip(), body)
    print("Discussion created successfully.")
    print(f"URL: {discussion.get('url')}")
    print(f"Number: {discussion.get('number')}")
    print(f"Category: {(discussion.get('category') or {}).get('name')}")


if __name__ == "__main__":
    main()
