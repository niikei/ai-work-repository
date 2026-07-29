# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- bounded human- and machine-readable `workrepo review-context` evidence selection for period
  reviews;
- isolated `workrepo check --ref` validation for historical Git snapshots, including deterministic
  generated-view reproduction without modifying the current worktree;
- reversible `workrepo archive` and `workrepo restore` lifecycle operations;
- year-based `80-archive` storage with stable IDs, linked Artifact movement, local-link rewriting,
  generated-view refresh, and rollback on failure;
- archive-aware list, search, and machine-readable index behavior.
- schema-backed Catalog, Playbook, Knowledge, and Resource Library taxonomy;
- structural validation that keeps `index.md` as the only Markdown file directly inside Project and
  Area Entity directories.

### Changed

- clarified that Project and Area indexes are concise current-state dashboards.
- kept Project and Area entities flat while allowing recursively organized supporting artifacts.
- replaced the ambiguous Reference category with explicit Knowledge and Resource types, and grouped
  reusable subjects and methods under Catalog and Playbooks.

## [0.5.0] - 2026-07-29

### Added

- deterministic repository navigation and cross-content search;
- scalable Project and Area organization with Area groups and typed reviews;
- managed external resources and indexed direct external Markdown links;
- daily Log workflow and empty-directory warnings;
- GitHub Copilot instructions, prompts, agent, and repository skills;
- local Git hooks, strict validation, and cross-platform CI;
- repository timezone policy and Windows timezone support;
- public project security, contribution, and dependency-update configuration.

### Changed

- normalized diagnostic paths across operating systems;
- documented direct-link-first external document workflows;
- licensed the project under the MIT License.

[Unreleased]: https://github.com/niikei/ai-work-repository/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/niikei/ai-work-repository/releases/tag/v0.5.0
