class Scheduler:
    def __init__(self):
        # schedule is a dictionary with the application as key and the time of arrival as value
        self.schedule = {}
    
    # Create a schedule for the applications
    def createSchedule(self, applications):
        # default schedule: all applications arrive at the same time
        for app in applications:
            self.schedule[app] = 0
