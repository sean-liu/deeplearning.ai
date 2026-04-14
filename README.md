# deeplearning.ai

Programming assignments, notes, and helper scripts for courses on deeplearning.ai.

## Contents

- [Deep Learning Specialization](./deep_learning_specialization/)
  - [1. Neural Networks and Deep Learning](./deep_learning_specialization/1_neural_networks_and_deep_learning/)
  - [2. Improving Deep Neural Networks](./deep_learning_specialization/2_improving_deep_neural_networks/)
  - [4. Convolutional Neural Networks](./deep_learning_specialization/4_convolutional_neural_networks/)

## Structure

```text
deep_learning_specialization/
  1_neural_networks_and_deep_learning/
    week_2/
    week_3/
    week_4/
  2_improving_deep_neural_networks/
    week_1/
    week_2/
    week_3/
  4_convolutional_neural_networks/
    week_1/
    week_2/
    week_3/
    week_4/

tools/
  download.py
  prepare.py
  tidy.py
  split30m.py
  mergeparts.py
```

## Environment

Recommended Python version: **3.12.x**. A local `.venv` is used for working in this repository, but dependencies may vary by assignment and notebook.

Each assignment directory includes its own `requirements.txt` so dependencies can stay close to the notebook they belong to.

## Getting Started

If you are visiting this repository for the first time, a typical workflow looks like this:

1. Clone the repository.
2. Run the prepare script.
3. Open the notebook in VS Code.
4. Select the repo `.venv` as the Jupyter kernel.

Example:

```bash
python3 ./tools/prepare.py
```

The prepare script will:

- detect whether any split `.parts` folders need to be merged
- create the repo-level `.venv` if it does not exist yet
- let you choose an assignment
- install that assignment's dependencies
- install `ipykernel` only if it is not already present in the repo `.venv`

You can also prepare a specific assignment directly:

```bash
python3 ./tools/prepare.py deep_learning_specialization/1_neural_networks_and_deep_learning/week_2/logistic_regression_with_a_neural_network_mindset
```

For VS Code with the Jupyter extension:

1. Run `python3 ./tools/prepare.py`
2. Open the notebook you want to use
3. Click `Select Kernel`
4. Choose the interpreter inside this repository's `.venv`

The script prints the exact interpreter path when it finishes.

If you prefer terminal-based Jupyter, you can still activate the environment manually:

```bash
source .venv/bin/activate
```

After preparing an assignment, you can open its notebook with Jupyter.

```bash
jupyter notebook
```

## Tools

The `tools/` folder is mainly for repository maintenance. It is useful to you first, and secondarily to anyone cloning the repo who wants to manage or export the course files in the same way.

- `download.py`
  Creates a zip archive of the current directory contents.

- `prepare.py`
  Visitor-friendly setup script. It checks whether split files need to be merged, creates the repo-level `.venv`, and installs the selected assignment's requirements.

- `tidy.py`
  Maintenance script for the repository owner. It scans for files larger than 30 MiB, skips ignored folders such as `.git`, `.venv`, and existing `.parts` folders, and offers to split the remaining large files.

- `split30m.py`
  Recursively scans a target folder and splits files larger than 30 MiB into smaller parts while preserving the folder structure.

- `mergeparts.py`
  Reconstructs files from `.parts` folders, validates the expected parts and file size, and then cleans up the temporary split artifacts.

### Usage

```bash
python3 ./tools/download.py
python3 ./tools/prepare.py
python3 ./tools/tidy.py
python3 ./tools/split30m.py /path/to/target_folder
python3 ./tools/mergeparts.py /path/to/target_folder
```

## Visitor Workflow

- `prepare.py` is the main visitor entry point for local setup.
- `mergeparts.py` is used by `prepare.py`, or directly by visitors who only want to reconstruct split files.
- Assignment-level `requirements.txt` files are for visitors who want to install only the packages needed for one notebook at a time.
- `tidy.py` is the main maintenance entry point before sharing or committing large repo content.
- `split30m.py` is the lower-level file splitting utility used when you want to split a chosen folder directly.

## Notes

- This repository is organized as a learning archive rather than a single packaged Python project.
- Dependencies were mapped per assignment from notebook and source imports.
- Large datasets, images, and split model artifacts were intentionally ignored when deriving dependency files.
