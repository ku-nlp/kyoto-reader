IN_DIR := {in_dir}
OUT_DIR := {out_dir}
JUMAN_DIC_DIR := {juman_dic_dir}
SCRIPTS_BASE_DIR := {scripts_base_dir}

ORIG_KNP_DONE := $(OUT_DIR)/orig_knp.done
ORIG_KNP_DIR := $(OUT_DIR)/orig
ADD_SEMS_KNP_DIR := $(OUT_DIR)/sems
OUT_KNP_DIR := $(OUT_DIR)/knp

CORPUS_KNPS := $(shell find $(IN_DIR) -type f -name "*.knp")
ORIG_KNPS := $(shell find $(ORIG_KNP_DIR) -type f -name "*.knp" 2> /dev/null)
ADD_SEMS_KNPS := $(patsubst $(ORIG_KNP_DIR)/%.knp,$(ADD_SEMS_KNP_DIR)/%.knp,$(ORIG_KNPS))
OUT_KNPS := $(patsubst $(ADD_SEMS_KNP_DIR)/%.knp,$(OUT_KNP_DIR)/%.knp,$(ADD_SEMS_KNPS))

ADD_SEMS_ARGS := --use-wikipediadic --dic-dir $(JUMAN_DIC_DIR)
LAST_MAKEFILE := $(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST))
NICE_VALUE := 19
KNP := nice -n $(NICE_VALUE) {knp}
PYTHON := nice -n $(NICE_VALUE) {python}

all:
	$(MAKE) -f $(LAST_MAKEFILE) $(ORIG_KNP_DONE)
	$(MAKE) -f $(LAST_MAKEFILE) add-feats

# split files into documents
$(ORIG_KNP_DONE): $(CORPUS_KNPS)
	mkdir -p $(ORIG_KNP_DIR)
	$(PYTHON) $(SCRIPTS_BASE_DIR)/docsplit.py --input-dir $(IN_DIR) --output-dir $(ORIG_KNP_DIR) && touch $@

.PHONY: add-feats
add-feats: $(OUT_KNPS)

# knp -dpnd -read-feature
# -dpnd-fast: 格解析を行わない
# -read-feature: <rel>タグを消さない
$(OUT_KNPS): $(OUT_KNP_DIR)/%.knp: $(ADD_SEMS_KNP_DIR)/%.knp
	mkdir -p $(dir $@) && cat $< | $(KNP) -tab -dpnd-fast -read-feature > $@ || rm -f $@

# add_sems.py
$(ADD_SEMS_KNPS): $(ADD_SEMS_KNP_DIR)/%.knp: $(ORIG_KNP_DIR)/%.knp
	mkdir -p $(dir $@) && cat $< | $(PYTHON) $(SCRIPTS_BASE_DIR)/add_sems.py $(ADD_SEMS_ARGS) > $@ || rm -f $@
