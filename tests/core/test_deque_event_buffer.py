import unittest

from ardis.core.buffering.deque_based_event_buffer import DequeBasedEventBuffer


class TestDequeBasedEventBuffer(unittest.TestCase):
    
    def test_basic_insertion_core(self):
        buffer = DequeBasedEventBuffer(10)
        buffer.push_core_and_sys_events(
            app_events={
                1 : {"inst": 10, "cycles": 20}, 
                2 : {"inst": 20, "cycles": 40}
            },
            system_events={ "power_system" : 100, "power_core": 10, "power_package": 20},
            frequencies={},
            relative_sample_duration=1.0,
            core_to_application={}
        )
        # Check if basic insertion works (app events)
        self.assertEqual(buffer.get_metrics_for_core(core_id=1,n=1)[-1]["inst"], 10)
        self.assertEqual(buffer.get_metrics_for_core(core_id=1,n=1)[-1]["cycles"], 20)
        self.assertEqual(buffer.get_metrics_for_core(core_id=2,n=1)[-1]["inst"], 20)
        self.assertEqual(buffer.get_metrics_for_core(core_id=2,n=1)[-1]["cycles"], 40)
        
        # Check if basic insertion works (system events)
        self.assertEqual(buffer.get_system_metrics(n=1)[-1]["power_system"],100)
        self.assertEqual(buffer.get_system_metrics(n=1)[-1]["power_core"],10)
        
        # Check edge cases
        self.assertEqual(buffer.get_metrics_for_core(core_id=-1,n=1), []) # invalid core
        self.assertEqual(len(buffer.get_metrics_for_core(core_id=1,n=5)), 1) # requested window size > buffer content
        self.assertEqual(len(buffer.get_metrics_for_core(core_id=1,n=0)), 0) # requested window size == 0

    def test_basic_insertion_pid(self):
        buffer = DequeBasedEventBuffer(10)
        buffer.push_pid_and_sys_events(
            app_events={
                1 :  {"inst": 10, "cycles": 20}, 
                42 : {"inst": 20, "cycles": 40}
            },
            system_events={ "power_system" : 100, "power_core": 10, "power_package": 20},
            frequencies={},
            relative_sample_duration=1.0,
            pid_to_application={}
        )
        # Check basic insertion (application events)
        self.assertEqual(buffer.get_metrics_for_pid(pid=1,n=1)[-1]["inst"], 10)
        self.assertEqual(buffer.get_metrics_for_pid(pid=1,n=1)[-1]["cycles"], 20)
        self.assertEqual(buffer.get_metrics_for_pid(pid=42,n=1)[-1]["inst"], 20)
        self.assertEqual(buffer.get_metrics_for_pid(pid=42,n=1)[-1]["cycles"], 40)
        
        # Check basic insertion (system events)
        self.assertEqual(buffer.get_system_metrics(n=1)[-1]["power_system"],100)
        self.assertEqual(buffer.get_system_metrics(n=1)[-1]["power_core"],10)
        
        # Check edge cases
        self.assertEqual(buffer.get_metrics_for_pid(pid=-1,n=1), []) # invalid pid
        self.assertEqual(len(buffer.get_metrics_for_pid(pid=42,n=5)), 1) # requested window size > buffer content
        self.assertEqual(len(buffer.get_metrics_for_pid(pid=42,n=0)), 0) # requested window size == 0

    def test_multi_insertion(self):
        buffer = DequeBasedEventBuffer(10)
        buffer.push_core_and_sys_events(
            app_events={
                0: {"instructions": 0},
                2: {"instructions": 0}
            },
            system_events={},
            frequencies={},
            relative_sample_duration=1.0,
            core_to_application={}
        )
        buffer.push_core_and_sys_events(
            app_events={
                0: {"instructions": 42},
                2: {"instructions": 20}
            },
            system_events={},
            frequencies={},
            relative_sample_duration=1.0,
            core_to_application={}
        )
        core_event_trace = buffer.get_metrics_for_core(core_id=0, n=2)
        instructions = [events["instructions"] for events in core_event_trace]
        self.assertEqual(instructions, [0, 42])
        