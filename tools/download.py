import os
import zipfile

output_zip = "lab.zip"

def is_hidden_path(path: str) -> bool:
    return any(part.startswith(".") for part in path.split(os.sep) if part)

with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
    for item in os.listdir("."):
        if item == output_zip:
            continue  # avoid zipping the zip itself
        if is_hidden_path(item):
            continue

        if os.path.isfile(item):
            zipf.write(item, arcname=item)

        elif os.path.isdir(item):
            for root, dirs, files in os.walk(item):
                dirs[:] = [directory for directory in dirs if not is_hidden_path(directory)]
                for file in files:
                    if is_hidden_path(file):
                        continue
                    file_path = os.path.join(root, file)
                    if is_hidden_path(file_path):
                        continue
                    arcname = os.path.relpath(file_path, start=".")
                    zipf.write(file_path, arcname)

print(f"Created zip file: {output_zip}")
