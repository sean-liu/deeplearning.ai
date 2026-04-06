import os
import zipfile

output_zip = "current_level_contents.zip"

with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
    for item in os.listdir("."):
        if item == output_zip:
            continue  # avoid zipping the zip itself

        if os.path.isfile(item):
            zipf.write(item, arcname=item)

        elif os.path.isdir(item):
            for root, dirs, files in os.walk(item):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, start=".")
                    zipf.write(file_path, arcname)

print(f"Created zip file: {output_zip}")