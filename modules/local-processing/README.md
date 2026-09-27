# Local processing adapters

The guarded overlay contains the existing local installation's source-ingestion,
provider provisioning and podcast model compatibility changes. These files are
applied to an isolated build tree, never copied over a new upstream version without
checking its baseline hash.

`cpu-constraints.txt` preserves the local container's torch/torchvision pins. A CPU
image must explicitly install the CPU wheels from `https://download.pytorch.org/whl/cpu`
and set `UV_CONSTRAINT` to this file for subsequent package installation. Selecting
this module applies the three source overlays; it does not automatically replace
the upstream dependency lock or fetch model weights. The existing local deployment
continues using its already configured CPU base image.
