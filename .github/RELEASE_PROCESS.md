# Release Process

Open Notebook uses a flow-driven release process. Work moves from `ready`
issues into pull requests, pull requests merge to `main`, and maintainers cut a
version when the branch has enough validated change to ship.

## Release Model

- Patch releases ship backwards-compatible fixes.
- Minor releases ship backwards-compatible features and improvements.
- Major releases are planned with a milestone when they include breaking
  changes or migrations that need user coordination.
- Release candidates and community soak labels are no longer part of the
  process. Use the `in-dev-build` label for changes available in development
  images and `released` for shipped work.

## Normal Flow

1. Triage issues into `ready` once the scope and design are clear.
2. Implement each change in a focused pull request linked to the approved issue.
3. Merge the pull request after review and required checks pass.
4. Let the development build publish the `v1-dev` image from `main`.
5. Cut a stable release when `main` has a coherent set of changes ready for
   users.

## Cutting A Stable Release

1. Confirm `main` is green and review the changes since the previous release.
2. Update `pyproject.toml` with the target semantic version.
3. Move the relevant `CHANGELOG.md` entries from `Unreleased` into a dated
   version section.
4. Create a GitHub release for the version tag, for example `v1.11.0`.
5. Run the `Build and Release` workflow. Push `v1-latest` tags for normal
   stable releases.
6. Verify the published images are available in GHCR and Docker Hub when
   Docker Hub credentials are configured.
7. Mark shipped issues with `released` and close any release-tracking tasks.

## Manual Verification

Before publishing a stable release, manually verify the areas touched by the
release. At minimum, cover:

- installation or upgrade path changed by the release;
- source ingestion and processing when content or worker behavior changed;
- chat, search, notes, and notebooks when user workflows changed;
- provider setup when model, credential, or API behavior changed;
- Docker image startup when packaging, environment, or dependency changes
  landed.

Automated checks should catch regressions where possible, but the release owner
chooses the manual matrix from the actual changes in the release.
