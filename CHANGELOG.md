# Changelog


## Unreleased

### Changed 
- Scheduler and MappingPolicy now follow a similar pattern like the
- Mapping Policies can throw an exception which indicates that the system is full and an just arrived application cannot be mapped to a free core.
- Engine delays the execution of an application untill enough cores are available 

### Added
- New Mapping Policies (`NextAvailableCoreMapping`)
    - Dynamically maps applications to the next available core based on the current system state.
- New Scheduler (`GreedyScheduler`)
    - Schedules applications as soon as possible, depending on the availability of cores.
    - Supports task constarints, like "requires task A to be finished before task B can start".
- New Scheduler (`FixedTimeScheduler`)
    - Schedules applications at fixed times, regardless of core availability.

- Added new example which showcases the usage of the new scheduling policies

### Fixed
- Exceptions within policies no longer cause the experiment to crash
- Lazy load policies in the `core.policies` package

## 1.0.0 - 2026-01-26
Initial release of ARDiS