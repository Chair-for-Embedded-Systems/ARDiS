import os
import subprocess

SPECPBASE = "/home/sikmoh00/Subjects/RealHardware/cpu2006/"
CONFIGFILE = "mytest.cfg"

def run_spec_app(app, core):
    # Save the current directory
    current_dir = os.getcwd()
    
    # set spec environment if it hasn't been done yet
    if "SPECBIN" not in os.environ:
        try:
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
        finally:
            # Change back to the original directory
            os.chdir(current_dir)

    # run app $1 on core $2
    command = f"taskset -c {core} nice -n 0 runspec --iterations 1 --size train --action onlyrun --config {CONFIGFILE} --noreportable {app} > {app}.log"
    subprocess.run(command, shell=True, env=os.environ)

# if __name__ == "__main__":  
#     app = "omnetpp"
#     core = 12
#     run_spec_app(app, core)