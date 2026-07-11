# providers

Plugin adapters for every external capability. Each subfolder implements
one fixed interface (defined in `packages/core`) so a provider can be
swapped via config, never by editing Agent code. Full evaluation of every
provider candidate (maturity/license/pros/cons) lives in
`docs/open-source-landscape.md`.
