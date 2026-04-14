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
  split30m.py
  mergeparts.py
```

## Environment

Recommended Python version: **3.12.x**. A local `.venv` is used for working in this repository, but dependencies may vary by assignment and notebook.

Each assignment directory includes its own `requirements.txt` so dependencies can stay close to the notebook they belong to.

## Getting Started

If you are visiting this repository for the first time, a typical workflow looks like this:

1. Clone the repository.
2. Reconstruct any split files if needed.
3. Create and activate a Python virtual environment.
4. Go to the assignment folder you want to run.
5. Install that assignment's dependencies from its local `requirements.txt`.
6. Open the notebook and work from there.

Example:

```bash
python -m venv .venv
source .venv/bin/activate
python ./tools/mergeparts.py .

cd deep_learning_specialization/1_neural_networks_and_deep_learning/week_2/logistic_regression_with_a_neural_network_mindset
pip install -r requirements.txt
```

After installing the requirements for an assignment, you can open its notebook with Jupyter.

```bash
jupyter notebook
```

## Tools

The `tools/` folder is mainly for repository maintenance. It is useful to you first, and secondarily to anyone cloning the repo who wants to manage or export the course files in the same way.

- `download.py`
  Creates a zip archive of the current directory contents.

- `split30m.py`
  Recursively scans a target folder and splits files larger than 30 MiB into smaller parts while preserving the folder structure.

- `mergeparts.py`
  Reconstructs files from `.parts` folders, validates the expected parts and file size, and then cleans up the temporary split artifacts.

### Usage

```bash
python ./tools/download.py
python ./tools/split30m.py /path/to/target_folder
python ./tools/mergeparts.py /path/to/target_folder
```

## Visitor Workflow

- `mergeparts.py` is for visitors who clone the repository and need to reconstruct large files that were split into `.parts` folders.
- Assignment-level `requirements.txt` files are for visitors who want to install only the packages needed for one notebook at a time.
- `split30m.py` is mainly a maintenance tool for the repository owner when preparing large files for storage or sharing.

## Notes

- This repository is organized as a learning archive rather than a single packaged Python project.
- Dependencies were mapped per assignment from notebook and source imports.
- Large datasets, images, and split model artifacts were intentionally ignored when deriving dependency files.
