---
name: push-publish
description: Release and publish workflow. Determines the next semantic version, updates changelog and version metadata, tags and pushes, creates a release, merges the PR, and publishes if required.
arguments:
  - name: VERSION_OVERRIDE
    required: false
    description: Override the auto-detected version (e.g., "1.2.3" or "major/minor/patch")
---

# Push and Publish Release

Analyse all changes since the last published version. Determine the appropriate new version number using semantic versioning rules:

- **MAJOR** for incompatible API changes
- **MINOR** for backwards-compatible new features
- **PATCH** for backwards-compatible bug fixes

## Prerequisites

- Git repository with origin remote
- `gh` CLI authenticated
- Write access to the repository
- (Optional) NPM credentials if publishing to NPM

## Codex Execution Strategy

This workflow benefits from parallel discovery, but release actions must stay sequential.

- Use `multi_tool_use.parallel` for read-only discovery:
  - latest tag and commits since tag
  - version file inventory
  - publish-target/auth checks such as NPM status
- Generate the version decision and changelog only after discovery is complete.
- Keep version writes, commit/tag creation, push, release creation, merge, and publish steps sequential and verified.
- Use `functions.exec_command` for git, `gh`, package-manager, and registry commands, and `apply_patch` for manual changelog/version-file edits.

## Completion Contract

- Treat the release as incomplete until version files, changelog, tags, remote release state, and optional publish state are all confirmed or explicitly `[blocked]`.
- Do not guess the bump level when commit evidence is mixed; document the exact release rationale.
- Do not publish or merge if local validation or dry-run packaging fails.

## Action Safety

Before the first irreversible step, print a short pre-flight summary covering:
- previous version,
- proposed new version,
- release type (`major|minor|patch|override`),
- publish targets (GitHub release, package registry, other).

If the version decision or publish target is materially ambiguous, stop for confirmation.

## Verification Loop

Before finalizing:
- verify all version-bearing files were updated consistently,
- verify the changelog matches the selected version and commit set,
- verify tags, remote branch/PR state, and release URL after push,
- if publishing, verify the published version or the exact blocked failure.

## Workflow

Once ready:

1. Update the project's version number in all relevant files
2. Update the CHANGELOG.md file with the new changes
3. Create an appropriately named branch (e.g., `release/v1.2.3`)
4. Add all modified files to the commit (`git add -A`)
5. Create a commit with a clear message following conventional commit format (e.g., `chore(release): v1.2.3`)
6. Tag the commit with the new version number
7. Push both the commit and the tag to GitHub
8. Create a release from the new tag
9. Create a PR to main from this new branch
10. Use the gh command to merge the PR (with appropriate merge strategy)
11. If the project requires publishing to NPM, publish the updated project

## Error Handling

### If NPM publish fails

1. Check NPM authentication: `npm whoami`
2. Verify package.json is valid: `npm pack --dry-run`
3. Check if version already exists: `npm view <package>@<version>`
4. If 2FA is required, ensure it's configured or use automation token

### Rollback procedure

If the release needs to be reverted:

```bash
# Delete the remote tag
git push origin --delete v$VERSION

# Delete the local tag
git tag -d v$VERSION

# Revert the version bump commit
git revert HEAD

# Push the revert
git push origin main
```

For NPM packages:
```bash
# Deprecate the version (preferred over unpublish)
npm deprecate <package>@<version> "Released in error, use <previous-version>"

# Or unpublish within 72 hours (use sparingly)
npm unpublish <package>@<version>
```

## Version Detection

The prompt analyses:
- Commit messages since last tag
- Breaking change indicators (`BREAKING CHANGE:`, `!` in type)
- Feature additions (`feat:`)
- Bug fixes (`fix:`)
- If no conventional commits, falls back to PATCH

## Output

After successful completion, report:
- Previous version
- New version
- Changelog entries added
- Release URL
- NPM publish status (if applicable)
