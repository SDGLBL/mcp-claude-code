CREATE_RELEASE_PROMPT = """Help me create a new release for my project. Follow these steps:

## Initial Analysis
1. Examine the project version files (typically `__init__.py`, `package.json`, `pyproject.toml`, etc.)
2. Review the current CHANGELOG.md format and previous releases
3. Check the release workflow configuration (GitHub Actions, CI/CD pipelines)
4. Review commits since the last release tag:
   ```bash
   git log <last-tag>..HEAD --pretty=format:"%h %s%n%b" --name-status
   ```

## Version Update
1. Identify all files containing version numbers
2. Update version numbers consistently across all files
3. Follow semantic versioning guidelines (MAJOR.MINOR.PATCH)

## Changelog Creation
1. Add a new section at the top of CHANGELOG.md with the new version and today's date
2. Group changes by type: Added, Changed, Fixed, Removed, etc.
3. Include commit hashes in parentheses for reference
4. Write clear, detailed descriptions for each change
5. Follow established project conventions for changelog format

## Release Commit and Tag
1. Commit the version and changelog updates:
   ```bash
   git add <changed-files>
   git commit -m "chore: bump version to X.Y.Z"
   ```
2. Create an annotated tag:
   ```bash
   git tag -a "vX.Y.Z" -m "Release vX.Y.Z"
   ```
3. Push the changes and tag:
   ```bash
   git push origin main
   git push origin vX.Y.Z
   ```"""
