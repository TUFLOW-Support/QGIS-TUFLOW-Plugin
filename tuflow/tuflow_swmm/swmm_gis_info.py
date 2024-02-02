

# checks to see if a layer is a SWMM Channel layer (any type)
def is_swmm_network_layer(layer):
    return layer.name().find('Links--') != -1 or layer.name().find('Nodes--') != -1