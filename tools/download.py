import os
import zipfile

DOWNLOAD_ALL_LABS = True

source_dir = os.path.abspath(".." if DOWNLOAD_ALL_LABS else ".")
output_zip = os.path.abspath("course_labs.zip" if DOWNLOAD_ALL_LABS else "lab.zip")


def is_hidden_name(name: str) -> bool:
    return name.startswith(".")


with zipfile.ZipFile(
    output_zip,
    "w",
    compression=zipfile.ZIP_DEFLATED,
) as zipf:

    for root, dirs, files in os.walk(source_dir):
        # Prevent walking into hidden directories.
        dirs[:] = [
            directory
            for directory in dirs
            if not is_hidden_name(directory)
        ]

        for file in files:
            if is_hidden_name(file):
                continue

            file_path = os.path.abspath(os.path.join(root, file))

            # Do not add the ZIP currently being created.
            if file_path == output_zip:
                continue

            arcname = os.path.relpath(file_path, start=source_dir)
            zipf.write(file_path, arcname)

print(f"Created ZIP file: {output_zip}")