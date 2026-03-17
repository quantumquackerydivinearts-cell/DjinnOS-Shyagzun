import sys
import os

# DjinnOS_Shyagzun/shygazun must take precedence over the root-level shygazun/
# copy, which shadows it when '' (cwd) appears first in sys.path.
_repo_root = os.path.dirname(__file__)
_kernel_path = os.path.join(_repo_root, "DjinnOS_Shyagzun")
if _kernel_path not in sys.path:
    sys.path.insert(0, _kernel_path)
