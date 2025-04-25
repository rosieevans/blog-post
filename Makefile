# Define paths
PYTHON_SCRIPT := src/athletics.py
MARKDOWN_FILE := index.md
PDF_FILE      := index.pdf

DATA_DIR      := data
RESULTS_DIR   := results
TABLES_DIR    := $(RESULTS_DIR)/tables
FIGURES_DIR   := $(RESULTS_DIR)/figures

# List all files that could be generated and used in the report
RESULT_FILES := $(wildcard $(TABLES_DIR)/*) $(wildcard $(FIGURES_DIR)/*)

# Default target
all: $(PDF_FILE)

# Run Python script if data changes
$(RESULT_FILES): $(PYTHON_SCRIPT) $(wildcard $(DATA_DIR)/*)
	python3 $(PYTHON_SCRIPT)

# Generate PDF using Pandoc after results are ready
$(PDF_FILE): $(MARKDOWN_FILE) $(RESULT_FILES)
	pandoc $(MARKDOWN_FILE) -o $(PDF_FILE)

# Manually run the script
run_python: $(PYTHON_SCRIPT)
	python3 $(PYTHON_SCRIPT)

# Clean generated files
clean:
	rm -f $(PDF_FILE)

# Phony targets
.PHONY: all clean run_python