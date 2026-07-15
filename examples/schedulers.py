from ardis.benchmarks import Application, ParsecApplication
from ardis.core.postprocessing import SimpleClipPostProcessor
from ardis.core.postprocessing.simple_clip_postprocessor import Clips
from ardis.experiments import Experiment, MonitoringMode



def run_example_with_static_scheduler():
    from ardis.core.policies import ExplicitMapping, FixedTimeScheduler
    
    # Create a static scheduler with predefined launch times for applications
    app_to_launch_time_sec : dict[Application, float] = {
        ParsecApplication("parsec.blackscholes") : 0.0,
        ParsecApplication("parsec.blackscholes") : 5.0,
        ParsecApplication("parsec.blackscholes") : 10.0,
        ParsecApplication("parsec.blackscholes") : 15.0,
    }

    experiment = Experiment(
        name="Static Scheduler Example",
        applications=list(app_to_launch_time_sec.keys()),
        mapping_policy=ExplicitMapping([{2}, {4}, {6}, {8}]),
        scheduler=FixedTimeScheduler(app_to_launch_time_sec),
        monitoring_mode=MonitoringMode.PERIODIC_ON_TID,
    )
    
    experiment.executeExperiment()

def run_example_with_list_scheduler():

    """
    This example demonstrates the use of a greedy scheduler that launches the applications as soon as possible (based on available cores).
    """

    from ardis.core.policies import NextAvailableCoreMapping, GreedyScheduler, StaticDVFS

    # Limit the system resource to two cores (4 and 8).
    available_cores = {4, 8}

    experiment = Experiment(
        name="List Scheduler Example",
        applications=[
            ParsecApplication("parsec.dedup"),
            ParsecApplication("parsec.dedup"),
            ParsecApplication("parsec.dedup"),
            ParsecApplication("parsec.dedup"),
            ParsecApplication("parsec.dedup"),
        ],
        scheduler=GreedyScheduler(available_cores=available_cores),
        mapping_policy=NextAvailableCoreMapping(prefered_cores=list(available_cores)),
        dvfs_policy=StaticDVFS({4: 1800, 8: 4000},),
        monitoring_mode=MonitoringMode.PERIODIC_ON_PID,
    )
    experiment.setPostProcessor(
        SimpleClipPostProcessor(
            clips=[Clips.APP_EXECUTION_OVERVIEW, Clips.APP_MAPPING, Clips.SYSTEM_CORE_FREQUENCY],
            verbose=True,
        )
    )
    experiment.executeExperiment()

def run_example_with_constraint_list_scheduler():
    """
    This example demonstrates the use of a greedy scheduler with task ordering constraints.
    """

    from ardis.core.policies import GreedyScheduler, NextAvailableCoreMapping, StaticDVFS

    

    # [Task Order] :
    # 
    #   Task A --+
    #            |--> Task C ---+
    #   Task B --+              |--> Task E
    #                           |
    #   Task D -----------------+

    task_a = ParsecApplication("parsec.dedup", display_name="Task A")
    task_b = ParsecApplication("parsec.dedup", display_name="Task B")
    task_c = ParsecApplication("parsec.dedup", display_name="Task C")
    task_d = ParsecApplication("parsec.dedup", display_name="Task D")
    task_e = ParsecApplication("parsec.dedup", display_name="Task E")

    # Limit the system resource to three cores (4, 6, and 8).
    available_cores = {4, 6, 8}
    
    experiment = Experiment(
        name="Constraint List Scheduler Example",
        applications=[task_a, task_b, task_c, task_d, task_e],
        scheduler=GreedyScheduler(
            available_cores=available_cores,
            # Task ordering constraints
            task_order={
                task_c: {task_a, task_b}, # Task C must be completed before Task A and Task B
                task_e: {task_c, task_d},
            }
        ),
        mapping_policy=NextAvailableCoreMapping(
            prefered_cores=list(available_cores)
        ),
        dvfs_policy=StaticDVFS({4: 1800, 6: 2000, 8: 4000},),
        monitoring_mode=MonitoringMode.PERIODIC_ON_CORE,
    )

    experiment.setPostProcessor(
        SimpleClipPostProcessor(
            clips=[Clips.APP_EXECUTION_OVERVIEW, Clips.APP_MAPPING, Clips.SYSTEM_CORE_FREQUENCY],
            verbose=True,
        )
    )

    experiment.executeExperiment()


# Run command : python3 examples/schedulers.py
if __name__ == "__main__":
    #run_example_with_static_scheduler()
    #run_example_with_list_scheduler()
    run_example_with_constraint_list_scheduler()