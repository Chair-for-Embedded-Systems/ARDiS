# Changelog
All notable changes to this project will be documented in this file.

## Our Versioning Scheme
This project uses a custom versioning scheme `(Epoch.Minor.Patch)` designed to avoid major version bloat.
Breaking changes can occur in Minor releases.

| Component | Type of Change | Compatibility | Example |
| :--- | :--- | :---: | :--- |
| **Epoch** (Major) | Generational shift / complete architectural rewrite | Breaking | `1.4.11` -> `2.0.0` |
| **Minor** | New features or breaking API changes | May Break | `1.0.5` -> `1.1.0` |
| **Patch** | Backwards-compatible bug fixes & optimizations | Safe | `1.0.1` -> `1.0.2` |

## Unreleased

### Breaking Changes
- `Scheduler` and `MappingPolicy` changed their method signatures

### Added
- New Mapping Policy (`NextAvailableCoreMapping`)
    - Dynamically maps applications to the next available core based on the current system state.
- New Scheduler (`GreedyScheduler`)
    - Schedules applications as soon as possible, depending on the availability of cores.
    - Supports task constarints, like "requires Task A to be finished before Task B can start".
- New Scheduler (`FixedTimeScheduler`)
    - Schedules applications at fixed times, regardless of core availability.
- Added new example (`schedulers.py`) which showcases the usage of the new scheduling policies
- `Application` has new properties (`get_preferred_core_count`, `is_completed`)

### Changed 
- `Scheduler` exposes a new method `is_time_to_launch(application, system_state)`, which allows to make scheduling decisions based on the current system state.
- `MappingPolicy` exposes a new method `get_mapping(application, system_state)`, which allows to make mapping decisions based on the current system state.
- `MappingPoliciy` can throw an `MappingException` which indicates that the system is full and an just arrived application cannot be mapped to a free core.
- Engine will delay the execution of an application until enough cores are available
- `Experiment` now uses `GreedyScheduler` as the default scheduler and `NextAvailableCoreMapping` as the default mapping policy


### Fixed
- Exceptions within `DVFSPolicy` and `MigrationPolicy` no longer cause the experiment to get stuck
- Lazy load policies in the `core.policies` package to prevent unnecessary imports
- Race condition which could stop the engine prematurely


## 1.0.0 - 2026-01-26
Initial release of ARDiS