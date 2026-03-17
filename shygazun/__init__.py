# Root-level shygazun/ is a structural copy. Extend __path__ so that submodules
# not present here (e.g. kernel_service) are found in DjinnOS_Shyagzun/shygazun/.
import os as _os

_kernel_shygazun = _os.path.join(
    _os.path.dirname(_os.path.dirname(__file__)), "DjinnOS_Shyagzun", "shygazun"
)
if _kernel_shygazun not in __path__:
    __path__.insert(0, _kernel_shygazun)
