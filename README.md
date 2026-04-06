# deeplearning.ai

Programming assignments and notes for courses on deeplearning.ai.

## Contents

- **Deep Learning Specialization**
  - [Neural Networks and Deep Learning](./deep-learning-specialization/neural-networks-and-deep-learning/)

## Structure

```text
deep-learning-specialization/
  neural-networks-and-deep-learning/
    week-01/
    week-02/
    ...
```

## Environment

Recommended Python version: **3.12.x** (used to create the local `.venv`).

## tools

- `split30m.py`  
  Recursively scans a target folder and splits any file larger than 30 MiB into smaller parts, preserving the original folder structure. Each split file is stored in its own `.parts` folder with a manifest for safe reconstruction.

- `mergeparts.py`  
  Recursively scans a target folder for `.parts` folders and merges the split files back into their original form. It validates the expected parts and final file size before cleaning up the parts folder.

### Usage

```bash
python ./tools/split30m.py /path/to/target_folder
python ./tools/mergeparts.py /path/to/target_folder