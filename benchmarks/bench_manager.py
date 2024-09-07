import os
import subprocess
from config import *

#TODO: maybe we move this to the config file
PARSECBASE = "/home/sikmoh00/Subjects/RealHardware/parsec-3.0/"
SPECPBASE = "/home/sikmoh00/Subjects/RealHardware/cpu2006/"
CONFIGFILE = "mytest.cfg"


class BenchManager:
    def __init__(self, benchmarks = ["spec", "parsec"]):
        self.__supported_benchmarks = benchmarks

    def runApplicationOnCore(self, app_string, core):
        benchmark, app = app_string.split("-")[:2]
        #print("benchmark: ", benchmark, " app: ", app)
        #size = app_string.split("-")[2]
        if benchmark not in self.__supported_benchmarks:
            raise ValueError(f"Unsupported benchmark {benchmark}")
        else:
            #TODO maybe we can get the input size from the app_string if we wanted to enable this
            if benchmark == "spec":
                self.__run_spec_app(app, core)#, size)
            elif benchmark == "parsec":
                self.__run_parsec_app(app=app, core=core)#, size)


    def __run_parsec_app(self, app, core, input_size = "native"):
        # set parsec environment if it hasn't been done yet
        if "xxPARSECDIRxx" not in os.environ:
            os.chdir(PARSECBASE)
            env_script_path = os.path.join(PARSECBASE, "env.sh")
            command = f"source {env_script_path} && env"
            process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, executable="/bin/bash")
            output, error = process.communicate()

            # Parse output and update os.environ
            for line in output.decode().splitlines():
                key, value = line.split("=", 1)
                os.environ[key] = value

        # run parsec app on core with nice value 0 if a core is assigned; otherwise, that means we are using the default governor
        if core is not None:
            command = f"taskset -c {core} nice -n 0 parsecmgmt -a run -i {input_size} -n 1 -p {app} > {app}.log"
        else:
            command = f"parsecmgmt -a run -i {input_size} -n 1 -p {app}"
            
        #print("command: ", command)
        subprocess.run(command, shell=True, executable="/bin/bash")
        os.chdir(ROOTPATH)

    def __run_spec_app(self, app, core, input_size = "ref"):      
        # set spec environment if it hasn't been done yet
        if "SPECBIN" not in os.environ:
            # Change to SPECPBASE directory
            os.chdir(SPECPBASE)
            # Source shrc and capture environment variables
            command = f"source {SPECPBASE}/shrc && env"
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, executable="/bin/bash")
            output, error = proc.communicate()

            # Parse output and update os.environ
            for line in output.decode().splitlines():
                if "=" in line:  # Check if line contains '='
                    key, value = line.split("=", 1)
                    os.environ[key] = value

        # run app $1 on core $2
        
        if core is not None:
            command = f"taskset -c {core} nice -n 0 runspec --iterations 1 --size {input_size} --action onlyrun --config {CONFIGFILE} --noreportable {app} > {app}.log"
        else:
            command = f"runspec --iterations 1 --size {input_size} --action onlyrun --config {CONFIGFILE} --noreportable {app} > {app}.log"
        #print("command: ", command)	
        subprocess.run(command, shell=True, env=os.environ)
        os.chdir(ROOTPATH)
