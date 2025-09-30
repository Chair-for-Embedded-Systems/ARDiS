import os

class PostProcessor:
    def __init__(self, workdir):
        self.workdir = workdir
        self.periodic_log = os.path.join(workdir, 'periodic_counters.log')
        self.energy_pkg = 0
        self.energy_cores = 0
        self.energy_psys = 0
        self.total_instructions = 0
        self.parse_log()

    def parse_log(self):
        if not os.path.exists(self.periodic_log):
            raise FileNotFoundError(f"Log file {self.periodic_log} does not exist.")
        
        with open(self.periodic_log, 'r') as f:
            for line in f:
                self.__parse_line(line)

    def __parse_line(self, line):
        parts = line.split('|')
        for part in parts:
            part = part.strip()
            if part.startswith("instructions"):
                self.total_instructions += int(part.split('=')[1].strip().replace(',', ''))
            elif part.startswith("power/energy-pkg/"):
                self.energy_pkg += int(part.split('=')[1].strip().replace(',', ''))
            elif part.startswith("power/energy-cores/"):
                self.energy_cores += int(part.split('=')[1].strip().replace(',', ''))
            elif part.startswith("power/energy-psys/"):
                self.energy_psys += int(part.split('=')[1].strip().replace(',', ''))

    def compute_total_energy(self):
        # Returns total energy in each component in Joules
        total_energy_pkg_joules = self.energy_pkg
        total_energy_cores_joules = self.energy_cores
        total_energy_psys_joules = self.energy_psys
        
        return {
            'total_energy_pkg': total_energy_pkg_joules,
            'total_energy_cores': total_energy_cores_joules,
            'total_energy_psys': total_energy_psys_joules
        }
    
    def compute_energy_efficiency(self):
        # Efficiency is typically measured as instructions per Joule
        total_energy = self.energy_pkg + self.energy_cores + self.energy_psys
        if total_energy == 0:
            return 0
        return self.total_instructions / total_energy