

def find_nodes_for_conduits(lay_conduit, layers_nodes, tolerance):
    # Create a spatial index for the node layer
    node_indices = [QgsSpatialIndex(x.getFeatures()) for x in layers_nodes]
    lay_conduit.startEditing()

    # Do upstream nodes
    # Loop through each polyline in the polyline layer
    for feature in lay_conduit.getFeatures():
        # Get the upstream node of the polyline
        upstream_node = feature.geometry().asPolyline()[0]
        field_index = lay_conduit.fields().indexOf('From Node')

        # Look for a node and stop at the first one
        for layer_nodes, node_index in zip(layers_nodes, node_indices):
            # Use the spatial index to find nodes within the tolerance distance of the upstream node
            nearby_nodes = node_index.nearestNeighbor(QgsPointXY(upstream_node), 1, tolerance)

            # Replace the placeholder with your own logic for handling the nearby nodes
            # For example:
            if nearby_nodes:
                node_feature = layer_nodes.getFeature(nearby_nodes[0])
                # Do something with the node feature...
                if feature['From Node'] != node_feature['Name']:
                    print(feature['From Node'])
                    print(node_feature['Name'])
                    lay_conduit.changeAttributeValue(feature.id(), field_index, node_feature['Name'])
                    break

    # Do downstream nodes
    # Loop through each polyline in the polyline layer
    for feature in lay_conduit.getFeatures():
        # Get the upstream node of the polyline
        downstream_node = feature.geometry().asPolyline()[-1]
        field_index = lay_conduit.fields().indexOf('To Node')

        # Look for a node and stop at the first one
        for layer_nodes, node_index in zip(layers_nodes, node_indices):
            # Use the spatial index to find nodes within the tolerance distance of the upstream node
            nearby_nodes = node_index.nearestNeighbor(QgsPointXY(downstream_node), 1, tolerance)

            # Replace the placeholder with your own logic for handling the nearby nodes
            # For example:
            if nearby_nodes:
                node_feature = layer_nodes.getFeature(nearby_nodes[0])
                # Do something with the node feature...
                if feature['To Node'] != node_feature['Name']:
                    print(f"Changing to node from: {feature['To Node']} to: {node_feature['Name']}")
                    lay_conduit.changeAttributeValue(feature.id(), field_index, node_feature['Name'])
                    break

    lay_conduit.commitChanges()


def get_layer_from_geopackage(filename, layername):
    filename = filename.replace("\\", "/")
    # Get a list of all layers in the current project
    layers = QgsProject.instance().mapLayers().values()

    # Loop through each layer and check if it matches the filename and layername
    for layer in layers:
        # if layer.name() == "Links--Conduits":
        #    print(layer.type())
        #    print(layer.source())
        #    print(type(layer.source()))
        #    match_text = f"{filename}|layername={layername}"
        #    print(match_text == layer.source())
        if layer.type() == QgsMapLayerType.VectorLayer and layer.source() == f"{filename}|layername={layername}":
            # A matching layer was found, so return it
            return layer

    # No matching layer was found
    return None


if __name__ == "__main__":
    gpkg = r"D:\models\TUFLOW\test_models\SWMM\internal\Ventura\TUFLOW_models\2023\TUFLOW\SWMM\sb_w_pipes_wide_mod02.gpkg"
    conduit_layer = get_layer_from_geopackage(gpkg, "Links--Conduits")
    print(conduit_layer.name())
    node_layers = []
    junctions_layer = get_layer_from_geopackage(gpkg, "Nodes--Junctions")
    print(junctions_layer.name())
    node_layers.append(junctions_layer)
    node_layers.append(get_layer_from_geopackage(gpkg, "Nodes--Outfalls"))
    find_nodes_for_conduits(conduit_layer, node_layers, 0.001)

    print('Done')
