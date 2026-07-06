# Changelog

All notable changes to LodgixHub will be documented in this file.

The format follows a simple chronological structure. Versioning will be introduced once the MVP implementation stabilizes.

## Unreleased

### Added

- Added MVP technical specification to `README.md`.
- Added staged backend implementation roadmap.
- Added changelog file for future task tracking.
- Added media/content scope for listing and room photo uploads.
- Added contributing guide with protected-branch Git workflow.
- Added initial Django app structure planning with a dedicated `content` app for media-related domain data.

### Changed

- Replaced the initial short README with a detailed project description and agreed MVP scope.
- Updated database scope from PostgreSQL to MySQL for local development and AWS RDS.
- Clarified that `config` is the Django project configuration package and `core` is a separate shared application.
