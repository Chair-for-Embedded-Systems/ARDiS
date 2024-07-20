import os
import subprocess

PARSECBASE = "/home/sikmoh00/Subjects/RealHardware/parsec-3.0/"
SCRIPTPTH = os.getcwd()


def run_parsec_app(app, core):
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

        os.chdir(SCRIPTPTH)

    # run parsec app on core with nice value 0
    command = f"taskset -c {core} nice -n 0 parsecmgmt -a run -i simlarge -n 1 -p {app} > {app}.log"
    subprocess.run(command, shell=True, executable="/bin/bash")

# if __name__ == "__main__":
#     app = "fluidanimate"
#     core = 12
#     run_parsec_app(app, core)