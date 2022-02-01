## Repository for Testing and Analyzing performance of CVA6 on Embench-iot

Directory Structure:

* __embench-test-list-full:__ Contains the list of tests to execute
* __Makefile:__ Used to run the tests with Questasim.
* __README.md__
* __trace_analysis__
  * __trace_analyzer.py:__ Script to analyze and extract performance metrics from simulation logs and traces.
  
### Makefile

The Makefile is used to run the tests listed in the file __embench-test-list-full__. Several variables needs to be set properly in order to work.
First of all the `library` and `dpi-library` are required for the simulation. These can be linked with a _symbolic link_ directly in the folder otherwise the full path needs to be specified.
The `top_level`, `questa-flags` and `questa-cmd` for the simulation, support for other tools can be added since these are Questasim specific.

In order to run the tests the location of the binaries is required. `EMBENCH_FOLDER` should refer to the folder containing the subfolder with the binaries. Normally, compiling embench-iot creates a folder named `bd/src` which should be the target of this variable.

Once these variables are set we can launch all the tests by using the command `make test-all -jn` where n indicates the number of simulateous jobs to launch.
For each test, a temporary folder is created in order to avoid contention on files (if multiple jobs are launched). Once a simulation is over, the simulation log is compied and renamed to `trace_analysis/logs` and the trace to `trace_analysis/traces`.
The temporary folder is then removed and the next test is launched until they are all completed.

### Trace Analyzer

The `trace_analyzer.py` script is used to extract information from the run and trace logs. As of now, the trace analysis is disabled but can be renabled by uncommenting its code.
The scripts works by opening each run log from the folder `trace_analysis/logs` and read all the information displayed at the end of the simulation.
there are 3 main categories:
* __Performance counters:__ They are the information read from the performance counters (which are also present in RTL).
* __Inactivity counters:__ These read the values that are probed in the id and issue stage. These are only simulation level and not present in RTL.
* __Miss Prediction Conters:__ These are used to quickly gauge the information about misprediction. They tell Total branches (not Jumps since they are not using branch prediction) and the sources of the misprediction: BHT, BTB or RAS.

These information are stored inside a python dictionary, this is organized in the following way:
* `Test Name`
  * `PC`
    * `Perf Counters`
  * `IC`
    * `Inactivity Counters`
  * `MP`
    * `Misprediction Counters`

The first output of the Script is a .csv file which contains only test-name (alphabetically ordered), cycles, instructions and IPC. This could be used to quickly compare different implementation of the core between each other.

__ *NOTE :* __ The excel file might give out a warning and to properly open the file click yes.
The second output of the Script is .xls file. This contains an in depth analysis of each test. 
The first page contains a recap of all the tests, it lists the instructions and stalls encountered during the execution. These are normalized to the value of `instr + all_stalls` in order to have a readable graph.
As mentioned, this information can be displayed as a graph by selecting all cells between `A1` to `P1` down to the last test. This data can be displayed by selecting a stacked bars graph.

__ *NOTE :* __ The values from these counters only represent the cycles and stalls during the benchmark, no overhead is present. This is done by checking the accesses to the cycle counter register in the `csr_regfile`. The reasoning behing this choice is that we access this specific register at the beginning and at the end of the benchmarks.
The various field found in the graph have the following meaning:
* __Instr__: The percentage of cycles spent exectuing instructions. A perfect test would have the full bar composed only of this field (IPC = 1).
* __Multb2b__: Indicates the stalls due to executing instructions that utilize a `Fixed latency unit (FLU)` after a multiplication. More specificly, csr, alu, branches and ALUs operation utilize the same write-back port to the scoreboard. Given that multiplication takes 2 cycles, any other 1 cycles operation on the same writeback port would collide hence we stall.
* __RS xxx__: Source Operand is missing because the FU specified is writing back to that register file location. This could be limited as more than one source operand could be missing but only one is shown.
* __FF Empty__: The Instruction FIFO that decouples the Frontend and Backend has no instructions ready.
* __Scoreboard Full__: The Instruction could not be issued because the Scoreboard is Full.
* __WAW__: A Write After Write Hazard is stalling the Issue Stage.
* __FU xxx__: The Instruction couldn't be issued because the Functional Unit wasn't ready.

__ * TO DO:* __ This page gives an estimation about the stalls of the core but its not completed. The number of Instr + Stalls is not equal to the total amount of Instructions. This can be attributed to the fact that we are only analyzing the stalls in the issue stage when an instruction is ready to be issued but can't be issued for several reasons.
This is tricky since the Frontend and Backend are decoupled and require some thought on how to make this analysis more accurate.

The other pages are in the excel file contains the information per test and are ordered by __IPC__. 
