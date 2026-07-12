# deeplearning.ai

Programming assignments, notes, and helper scripts for courses on deeplearning.ai.

## Contents

- [Deep Learning Specialization](./deep_learning_specialization/)
  - [1. Neural Networks and Deep Learning](./deep_learning_specialization/1_neural_networks_and_deep_learning/)
  - [2. Improving Deep Neural Networks](./deep_learning_specialization/2_improving_deep_neural_networks/)
  - [4. Convolutional Neural Networks](./deep_learning_specialization/4_convolutional_neural_networks/)
  - [5. Sequence Models](./deep_learning_specialization/5_sequence_models/)

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
  5_sequence_models/
    week_1/
    week_2/
    week_3/
    week_4/

tools/
  download.py
  generate_requirements.py
  prepare.py
  tidy.py
  split_parts.py
  merge_parts.py
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

- merge any split tidy archive before restoring it, then restore only archives marked by `tidy.py`
- create the repo-level `.venv` if it does not exist yet
- let you choose an assignment
- install that assignment's dependencies
- install `ipykernel` only if it is not already present in the repo `.venv`

You can also prepare a specific assignment directly:

```bash
python3 ./tools/prepare.py deep_learning_specialization/1_neural_networks_and_deep_learning/week_2/logistic_regression_with_a_neural_network_mindset
```

Legacy `.parts` folders without a migration marker remain untouched during
normal assignment preparation. To restore unmarked legacy parts immediately,
explicitly choose an existing folder inside this repository:

```bash
python3 ./tools/prepare.py --restore-legacy-parts path/to/folder
```

`--restore-legacy-parts` only scans that folder recursively for unmarked `.parts` folders. It
validates each manifest and exact part set before merging, safely restores ZIP
archives with the same integrity, path, symbolic-link, and no-overwrite checks
used for tidy archives, and does not create a virtual environment, install
dependencies, or show the assignment picker. Ordinary unmarked `.zip` files are
not restored. Failures are reported per item while recoverable source artifacts
are retained.

To approve valid legacy parts for restoration during a future normal
`prepare.py <assignment>` run—without merging, extracting, or deleting anything—use:

```bash
python3 ./tools/prepare.py --mark-legacy-parts path/to/folder
```

`--mark-legacy-parts` writes a migration marker only after validating each
parts manifest, exact part set, and safe paths. Ordinary `foo.parts` receives
`foo.parts.prepare.json`; ZIP `foo.zip.parts` receives the compatible
`foo.zip.archive.json`. Existing valid markers are left unchanged. During later
normal preparation, unmarked parts (including unmarked ZIP parts) remain
untouched; only approved ordinary parts are merged, and approved ZIP parts are
merged and restored.

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
  Visitor-friendly setup script. Its default assignment workflow first restores approved legacy parts and tidy archives, then creates the repo-level `.venv` and installs that assignment's requirements. User-created `.zip` and unmarked `.parts` files are left untouched unless `--restore-legacy-parts` is explicitly requested for immediate restoration or `--mark-legacy-parts` is used to approve later default restoration.

- `generate_requirements.py`
  Scans a target assignment folder for `.py` and `.ipynb` imports and creates a `requirements.txt` file when one does not already exist.

- `tidy.py`
  Maintenance script for the repository owner. It removes `__pycache__` directories inside the target folder, respects `.gitignore` plus hardcoded skips such as `.git`, `.venv`, and existing `.parts` folders, and offers to split remaining files over 30 MiB. A directory with more than 200 direct regular files can instead be archived as a sibling `.zip`; archives larger than 30 MiB are split into the existing `.parts` format. Tidy writes a matching `.zip.archive.json` marker, and only archives with that marker are restored automatically by `prepare.py`.

- `split_parts.py`
  Recursively scans a target folder and splits files larger than 30 MiB into smaller parts while preserving the folder structure.

- `merge_parts.py`
  Reconstructs files from `.parts` folders, validates the expected parts and file size, and then cleans up the temporary split artifacts.

### Usage

```bash
python3 ./tools/download.py
python3 ./tools/generate_requirements.py /path/to/assignment_folder
python3 ./tools/prepare.py
python3 ./tools/prepare.py --restore-legacy-parts path/to/folder
python3 ./tools/prepare.py --mark-legacy-parts path/to/folder
python3 ./tools/tidy.py
python3 ./tools/tidy.py /path/to/target_folder
python3 ./tools/split_parts.py /path/to/target_folder
python3 ./tools/merge_parts.py /path/to/target_folder
```

## Visitor Workflow

- `prepare.py` is the main visitor entry point for local setup. By default it restores only tidy archives and legacy parts explicitly marked for restoration; arbitrary user-created `.zip`, unmarked `.parts`, and unmarked ZIP parts remain untouched. `--restore-legacy-parts` is an immediate restore-only migration path scoped to one existing repository folder, while `--mark-legacy-parts` only approves valid parts for a later default prepare run.
- `generate_requirements.py` is the maintenance helper for creating a missing assignment-level `requirements.txt`.
- `merge_parts.py` is used by `prepare.py`, or directly by visitors who only want to reconstruct split files.
- Assignment-level `requirements.txt` files are for visitors who want to install only the packages needed for one notebook at a time.
- `tidy.py` is the main maintenance entry point before sharing or committing large repo content, either repo-wide or for a chosen subfolder.
- `split_parts.py` is the lower-level file splitting utility used when you want to split a chosen folder directly.

## Notes

- This repository is organized as a learning archive rather than a single packaged Python project.
- It currently includes assignments from courses 1, 2, 4, and 5 of the Deep Learning Specialization.
- Dependencies were mapped per assignment from notebook and source imports.
- Large datasets, images, and split model artifacts were intentionally ignored when deriving dependency files.
