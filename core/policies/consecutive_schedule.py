from core.scheduler import *

class ConsecutiveScheduler(Scheduler):
    def __init__(self, delay):
        super().__init__()
        self.delay = delay


    # Create a schedule for the applications
    def createSchedule(self, applications):
        # default schedule: all applications consecutively one after the other
        t = 0
        for app in applications:
            self.schedule[app] = t*self.delay
            t += 1
        return self.schedule