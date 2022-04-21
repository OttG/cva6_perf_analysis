#Simple Makefile for benchmarking
mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
root-dir := $(dir $(mkfile_path))

EMBENCH_FOLDER ?= $(root-dir)../embench
EMBENCH_TEST_LIST ?= $(root-dir)/embench-test-list-full
EMBENCH_TESTS 	  := $(shell xargs printf '\n%s' < $(EMBENCH_TEST_LIST))

SPIKE_ROOT     ?= $(RISCV)

# questa library
library        ?= work
# library for DPI
dpi-library    ?= work-dpi
# Top level module to compile
top_level      ?= ariane_tb
#Compile and sim flags
questa-flags   := -t 1ns -64 -coverage -classdebug $(gui-sim) $(QUESTASIM_FLAGS)

ANALYSIS_DIR ?= $(root-dir)/trace_analysis

LOG_DIR   ?= logs
LOG_FILE  ?= transcript
LOG_PATH  ?= $(ANALYSIS_DIR)/$(LOG_DIR)

TRACE_DIR  ?= traces
TRACE_FILE ?= trace_hart_0.log
TRACE_PATH ?= $(ANALYSIS_DIR)/$(TRACE_DIR)

ifdef batch-mode
	questa-flags += -c
	questa-cmd   := -do " log -r /*; run -all; quit"
else
	questa-cmd   := -do " log -r /*; run -all;"
endif

ifdef preload
	questa-cmd += +PRELOAD=$(preload)
	elf-bin = none
endif

create-dir:
	mkdir -p $(LOG_PATH)
	mkdir -p $(TRACE_PATH)

test-all: | create-dir $(EMBENCH_TESTS)
	cd $(ANALYSIS_DIR); python3 ./trace_analyzer.py

sim:
	vsim${questa_version} +permissive $(questa-flags) $(questa-cmd) -lib $(root-dir)/$(library) \
	-gblso $(SPIKE_ROOT)/lib/libfesvr.so -sv_lib $(root-dir)/$(dpi-library)/ariane_dpi          \
	${top_level}_optimized +permissive-off ++$(elf-bin) ++$(target-options) | tee sim.log

$(EMBENCH_TESTS): 
	$(eval TMP := $(shell mktemp -d -p ${root-dir}))
	cd $(TMP) && make -f ${root-dir}/Makefile sim preload=${EMBENCH_FOLDER}/$@/$@ batch-mode=1
	cp $(TMP)/$(LOG_FILE) $(LOG_PATH)/$@-run.log
#	cp $(TMP)/$(TRACE_FILE) $(TRACE_PATH)/$@-trace.log
	rm -r $(TMP)
