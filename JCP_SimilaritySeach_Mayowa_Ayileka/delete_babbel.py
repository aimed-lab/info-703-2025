import os
import pooch

babel_cache = pooch.os_cache("pooch")
for file in os.listdir(babel_cache):
    if "babel.db" in file:
        os.remove(os.path.join(babel_cache, file))
        print(f"Deleted: {file}")