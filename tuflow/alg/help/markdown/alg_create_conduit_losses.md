This tool creates loss geometry and attributes for a SWMM conduit layer. Losses are dependent upon whether a conduit is the furthest upstream, furthest downstream, and which nodes are connected to inlets.

__Note: This tool relies on the "From Node" and "To Node" fields to determine position in the network so make sure they are up-to-date.__

## Usage
Upstream entrance losses are assigned to the furthest upstream channels where the upstream node is not connected to an inlet and other entrance losses assigned to all other conduits (may be 0.0). Downstream exit losses are assigned to the furthest downstream channels and other exit losses are assigned to the rest of the channels (may be 0.0).

## Limitations
This tool creates entrance and exit losses specified by the user throughout the domain. Channels that experience atypical size changes may need higher or lower loss coefficients.