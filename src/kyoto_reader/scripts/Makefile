IN_DIR := {/somewhere/orig/corpus/dir}
OUT_DIR := {/path/to}
JUMAN_DIC_DIR := $(HOME)/download/juman/dic
SCRIPTS_BASE_DIR := {here}

ADD_SEMS_ARGS= --use-wikipediadic --dir $(JUMAN_DIC_DIR)

#ifdef KYOTO_CORPUS
#	KNP_PAT = *
#else
#	KNP_PAT = */*
#	ADD_SEMS_ARGS += -input_dir_pattern "*/*"
#endif

ORIG_KNP_DONE := $(OUT_DIR)/orig_knp.done
ORIG_KNP_DIR := $(OUT_DIR)/orig
ADD_SEMS_DIR := $(OUT_DIR)/sems
OUT_KNP_DIR := $(OUT_DIR)/knp

CORPUS_KNPS := $(shell find $(IN_DIR) -type f -name "*.knp")
ORIG_KNPS := $(shell ls $(ORIG_KNP_DIR))
ADD_SEMS_KNPS := $(patsubst $(ORIG_KNP_DIR)/%.knp,$(ADD_SEMS_KNP_DIR)/%.knp,$(ORIG_KNPS))
OUT_KNPS := $(patsubst $(ADD_SEMS_KNP_DIR)/%.knp,$(OUT_KNP_DIR)/%.knp,$(ADD_SEMS_KNPS))

NICE_VALUE := 19
KNP := nice -n $(NICE_VALUE) knp
PYTHON := nice -n $(NICE_VALUE) python3

all: $(ORIG_KNP_DONE)
	$(MAKE) add

# split files into documents
$(ORIG_KNP_DONE): %: $(CORPUS_KNPS)
	mkdir -p $(ORIG_KNP_DIR)
	cat $< | $(PYTHON) $(SCRIPTS_BASE_DIR)/split_corpus.py --output-dir $(ORIG_KNP_DIR) && touch $(ORIG_KNP_DONE)

add: $(OUT_KNPS)

# knp -read-feature
$(OUT_KNPS): $(OUT_KNP_DIR)/%.knp: $(ADD_SEMS_DIR)/%.knp
	mkdir -p $(dir $@)
	cat $< | $(KNP) -tab -read-feature > $@ || rm -f $@

# add_sems.py
$(ADD_SEMS_KNPS): $(ADD_SEMS_DIR)/%.knp: $(ORIG_KNP_DIR)/%.knp
	mkdir -p $(dir $@)
	cat $< | $(PYTHON) $(SCRIPTS_BASE_DIR)/add_sems.py $(ADD_SEMS_ARGS) > $@ || rm -f $@
