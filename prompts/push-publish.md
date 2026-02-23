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

## SubAgent Strategy

This workflow benefits from parallel analysis in the early phases.

**Codex note:** Codex does not support `Task(...)` subagents. Use `functions.shell_command` and `multi_tool_use.parallel` to run the same commands, or run steps sequentially. For Explore/Plan tasks, use normal file searches and the plan tool. See [`../COMPATIBILITY.md`](../COMPATIBILITY.md).

### Phase 1: Parallel Discovery

Launch these SubAgents **simultaneously**:

1. **Bash SubAgent**: Get version info
   ```
   Task(subagent_type="Bash", prompt="Run these commands:
   - git describe --tags --abbrev=0 2>/dev/null || echo 'v0.0.0' (latest tag)
   - git log $(git describe --tags --abbrev=0 2>/dev/null || echo '')..HEAD --oneline (commits since tag)
   - cat package.json | jq -r .version 2>/dev/null (current package version)")
   ```

2. **Bash SubAgent**: Analyse commit types
   ```
   Task(subagent_type="Bash", prompt="Run: git log $(git describe --tags --abbrev=0 2>/dev/null)..HEAD --format='%s' and categorise commits by type (feat/fix/BREAKING CHANGE/etc)")
   ```

3. **Explore SubAgent**: Find version files
   ```
   Task(subagent_type="Explore", prompt="Find all files that contain version numbers that need updating: package.json, package-lock.json, Cargo.toml, pyproject.toml, version.ts, etc. List their paths and current versions.")
   ```

4. **Bash SubAgent**: Check NPM status (if applicable)
   ```
   Task(subagent_type="Bash", prompt="Run: npm whoami 2>/dev/null && npm view $(cat package.json | jq -r .name) versions --json 2>/dev/null to check NPM auth and existing versions")
   ```

### Phase 2: Changelog Generation

Use a **general-purpose SubAgent** to generate the changelog:
```
Task(subagent_type="general-purpose", prompt="Generate a CHANGELOG.md entry for version <NEW_VERSION>. Group changes by: Added, Changed, Fixed, Removed, Security. Use these commits: <COMMIT_LIST>")
```

### Phase 3: Parallel Updates (After Version Determined)

Launch these **in parallel** to update all version files:
```
Task(subagent_type="Bash", prompt="Update version in package.json to <NEW_VERSION> using: npm version <NEW_VERSION> --no-git-tag-version")
```

Additional file updates can be done in parallel with Edit tool calls.

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
