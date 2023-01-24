import argparse
import os

I_MPI_PMI_LIBRARY = "/usr/lib/x86_64-linux-gnu/libpmi2.so"

short_to_long = {
    "-a": "--array",
    "-A": "--account",
    "-b": "--begin",
    "-c": "--cpus-per-task",
    "-d": "--dependency",
    "-D": "--chdir",
    "-e": "--error",
    "-H": "--hold",
    "-i": "--input",
    "-J": "--job-name",
    "-k": "--no-kill",
    "-L": "--licenses",
    "-M": "--clusters",
    "-m": "--distribution",
    "-n": "--ntasks",
    "-N": "--nodes",
    "-o": "--output",
    "-O": "--overcommit",
    "-p": "--partition",
    "-q": "--qos",
    "-Q": "--quiet",
    "-s": "--oversubscribe",
    "-S": "--core-spec",
    "-t": "--time",
    "-v": "--verbose",
    "-W": "--wait",
    "-C": "--constraint",
    "-F": "--nodefile",
    "-w": "--nodelist",
    "-x": "--exclude",
    "-G": "--gpus",
    "-h": "--help",
    "-V": "--version",
}


def strip_sbatch(file):
    try:
        with open(file, "r") as f:
            sbatch_lines = [
                line.split(maxsplit=2)[1:]
                for line in f.readlines()
                if line.startswith("#SBATCH")
            ]

            lines_spaced = [
                line[0].split("=", maxsplit=1) + line[1:] for line in sbatch_lines
            ]

            options_raw = [
                (line[0], " ".join(line[1:]).strip()) for line in lines_spaced
            ]
            options = [(short_to_long.get(k, k), v) for k, v in options_raw]

            options_dict = {k: v for k, v in options}

            return options_dict
    except FileNotFoundError:
        return {}


def format_time(time):
    c = time.count(":")
    d = time.count("-")

    if c == 0 and d == 0:
        return f"0-00:{time}:00"
    elif c == 0 and d == 1:
        return f"{time}:00:00"
    elif c == 1 and d == 0:
        return f"0-00:{time}"
    elif c == 1 and d == 1:
        return f"{time}:00"
    elif c == 2 and d == 0:
        return f"0-{time}"
    elif c == 2 and d == 1:
        return time
    else:
        # problems? I hope not.
        return time


def pargs():
    parser = argparse.ArgumentParser(
        prog="ssub",
        description="castep submitter",
        epilog="""Options will be chosen with the following precedence, latter overriding former:

- Slurm defaults
- Program defaults
- Options from file scasteprc in parent directories from 3>2>1
- Options from file pointed at by $SCASTEP_OPTIONS
- Options from --default-file or --parent
- Other command line options to this program.

example usage:

ssub seed
ssub seed -n 2 -m 4G -t '2-00'
ssub seed -J '$seed:run01'

In the last example, `$seed` will be replaced with the seed..""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("seed")
    parser.add_argument("-d", "--dryrun", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-m", "--mem-per-cpu")
    parser.add_argument(
        "-f",
        "--default-file",
        help="Use this file for default options to use. Should be in the #SBATCH for just like a normal sbatch job script.",
    )
    parser.add_argument(
        "-u",
        "--parent",
        help="What parent directory level to look at for an options file. Overrides --default-file.",
    )
    parser.add_argument(
        "-c",
        "--castep",
        help="The version of castep to use.",
        default="19.11",
        choices=["19.11", "21.11", "22.11"],
    )
    parser.add_argument("-t", "--time", help="Wall time to run for.")
    parser.add_argument("-n", "--tasks", help="Number of cores or tasks to assign.")
    parser.add_argument(
        "-J", "--job-name", help="Name of the job. Defaults to seed name."
    )
    parser.add_argument(
        "-o", "--output", help="Where to send stdout. Defaults to seed.out."
    )
    parser.add_argument(
        "-e", "--error", help="Where to send stderr. Default to seed.err."
    )
    parser.add_argument(
        "-p",
        "--partition",
        help="Which partition to use. Guesses based on time if not given.",
    )
    parser.add_argument(
        "-C",
        "--constraint",
        help="Slurm constraints. Chooses based on castep requirements of not given.",
    )
    parser.add_argument(
        "--pmi-library",
        help=f"The PMI library to use. Sets $I_MPI_PMI_LIBRARY to {I_MPI_PMI_LIBRARY} by default.",
    )
    parser.add_argument(
        "-D",
        "--diagnose",
        help="Prints diagnostics to stdout after job ends.",
        action="store_true",
    )
    parser.add_argument(
        "-s",
        "--save",
        help="Whether to save the job script to a file. Will save to seed.sh.",
        action="store_true",
    )
    parser.add_argument(
        "--ib",
        help="Whether to use Infiniband. This will change the launch command from 'srun' to 'mpirun', apply the option '-iface ibs2' to mpirun, and apply the constraint 'ib' to sbatch.",
    )

    return parser.parse_args()


def main():

    ns = pargs()

    options = {
        "--constraint": '"intel&avx512"',
        "--mem-per-cpu": "6G",
        "--partition": "cpu",
        "--time": "1-00:00:00",
        "--error": "$seed.err",
        "--output": "$seed.out",
        "--job-name": "$seed",
        "--ntasks": "1",
    }

    if ns.ib:
        options["--constraint"] = "ib"

    for i in range(1, 4):
        file = "../" * i + "scasteprc"
        options.update(strip_sbatch(file))

    if "SCASTEP_OPTIONS" in os.environ:
        options.update(strip_sbatch(os.environ.get("SCASTEP_OPTIONS")))

    if ns.parent:
        options.update(strip_sbatch(ns.parent))
    elif ns.default_file:
        options.update(strip_sbatch(ns.default_file))

    if ns.mem_per_cpu:
        options["--mem-per-cpu"] = ns.mem_per_cpu
    if ns.job_name:
        options["--job-name"] = ns.job_name
    if ns.error:
        options["--error"] = ns.error
    if ns.output:
        options["--output"] = ns.output
    if ns.partition:
        options["--partition"] = ns.partition
    if ns.constraint:
        options["--constraint"] = ns.constraint
    if ns.tasks:
        options["--ntasks"] = ns.tasks
    if ns.time:
        options["--time"] = ns.time

    options["--time"] = format_time(options["--time"])

    if options["--time"] > "1-00:00:00" and not ns.partition:
        options["--partition"] = "cpu-long"

    options_str = "\n".join(
        [f"#SBATCH {k}" + (f"={v}" if v else "") for k, v in options.items()]
    )
    module_str = f"module purge 2>&1\nmodule load castep/skylake/{ns.castep} 2>&1"
    mpi_lib_str = f"export I_MPI_PMI_LIBRARY={ns.pmi_library or I_MPI_PMI_LIBRARY}"
    srun_str = "srun --kill-on-bad-exit=1 --ntasks=$np castep.mpi $seed" + (
        " -dryrun" if ns.dryrun else ""
    )
    mpirun_str = "mpirun -iface ibs2 -np $np castep.mpi $seed" + (
        " -dryrun" if ns.dryrun else ""
    )
    diagnostic_str = (
        """## run job diagnostics
echo Timings:
sacct -o JobID,Submit,Start,End,CPUTime,State -j $SLURM_JOBID
echo Resources:
sacct -o JobID,JobName,Partition,ReqMem,MaxRSS,MaxVMSize -j $SLURM_JOBID"""
        if ns.diagnose
        else ""
    )

    job_str = "\n".join(
        ["#!/bin/bash", options_str, module_str, mpi_lib_str, mpirun_str if ns.ib else srun_str, diagnostic_str]
    )

    job_str = job_str.replace("$seed", ns.seed).replace("$np", options["--ntasks"])

    if ns.save:
        with open(f"{ns.seed}.sh", "w") as f:
            f.write(job_str)

    print(job_str)
