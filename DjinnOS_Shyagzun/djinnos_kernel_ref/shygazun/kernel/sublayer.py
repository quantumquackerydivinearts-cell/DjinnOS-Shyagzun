# Re-exports the sublayer segment function from the main kobra package.
# Required by chromatic.py / samosmyr.py when imported from djinnos_kernel_ref.
from shygazun.kernel.kobra.sublayer import segment  # type: ignore

__all__ = ["segment"]