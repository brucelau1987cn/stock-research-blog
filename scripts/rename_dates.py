import os
import re

blog_dir = "/root/projects/stock-research-blog/src/content/blog"
date_prefix_pattern = re.compile(r'^\d{8}-(.+\.md)$')

for filename in os.listdir(blog_dir):
    match = date_prefix_pattern.match(filename)
    if match:
        new_name = match.group(1)
        old_path = os.path.join(blog_dir, filename)
        new_path = os.path.join(blog_dir, new_name)
        print(f"Renaming: {filename} -> {new_name}")
        os.rename(old_path, new_path)
