import numpy as np

tolerance = 0.00001


def get_normalized_hw(coords):
    # sort the coordianates by y value
    coords = coords.astype(float)
    coords = coords[~np.all(np.isnan(coords), axis=1)]
    coords_sorted = coords[coords[:, 1].argsort()]

    # Add a width the sorted coordinate array
    new_vals = np.expand_dims(np.array([0.0] * coords_sorted.shape[0]), axis=1)
    coords_sorted = np.hstack((coords_sorted, new_vals))
    # print(coords_sorted)

    z_vals = np.unique(coords_sorted[:, 1])
    # print(z_vals)
    z_min = coords_sorted[0, 1]
    z_max = coords_sorted[-1, 1]

    hw_vals = []
    for i, target_z in enumerate(z_vals):
        # print(f'Point {i}')
        # Get the width at the ith point

        intersection_x_coords = []
        # Find points within the tolerance
        for j in range(coords.shape[0]):
            if abs(coords[j, 1] - target_z) < tolerance:
                # We want to throw out some points if there are points before and after due for duplicates,
                # peaks, or valleys
                if 1 < j < coords.shape[0] - 1:
                    # If point before was also within tolerance do not include if point after is within or below
                    if abs(coords[j - 1, 1] - target_z) < tolerance:
                        if coords[j + 1, 1] < target_z + tolerance:
                            continue
                    # If point after was also within tolerance do not include if point after is within or below
                    if abs(coords[j + 1, 1] - target_z) < tolerance:
                        if coords[j - 1, 1] < target_z + tolerance:
                            continue
                    # Do not include if points before and after are both below the point (remove middle peaks
                    # at z because they aren't used to calculate width)
                    if coords[j - 1, 1] < target_z - tolerance and \
                            coords[j + 1, 1] < target_z - tolerance:
                        continue
                    # Do not include if points before and after are above the point (will be a zero width segment)
                    if coords[j - 1, 1] > target_z + tolerance and \
                            coords[j + 1, 1] > target_z + tolerance:
                        continue

                intersection_x_coords.append(coords[j, 0])

        # Find segments that cross the elevation
        for j in range(coords.shape[0] - 1):
            p1x = coords[j, 0]
            p1y = coords[j, 1]
            p2x = coords[j + 1, 0]
            p2y = coords[j + 1, 1]

            # One point must be below the elevation and the other above
            if p1y < target_z - tolerance:  # first point is below
                if p2y > target_z + tolerance:  # second point is above
                    # interpolate to find x at intersection
                    x = (target_z - p1y) / (p2y - p1y) * (p2x - p1x) + p1x
                    intersection_x_coords.append(x)
            if p1y > target_z + tolerance:  # first point is below
                if p2y < target_z - tolerance:  # second point is above
                    # interpolate to find x at intersection
                    x = (p2y - target_z) / (p1y - p2y) * (p1x - p2x) + p2x
                    intersection_x_coords.append(x)

        intersection_x_coords = sorted(intersection_x_coords)
        # print(intersection_x_coords)

        if len(intersection_x_coords) == 0: # Happens at lowest point
            hw_vals.append((target_z - z_min, 0.0))
        elif len(intersection_x_coords) == 1:
            hw_vals.append((target_z - z_min, 0.0))
        elif len(intersection_x_coords) == 2 or len(intersection_x_coords) == 3:  # 1 channel with a hump or flat spot
            hw_vals.append((target_z - z_min, intersection_x_coords[-1] - intersection_x_coords[0]))
        elif len(intersection_x_coords) % 2 == 0:  # even multiple channels
            sum_width = 0.0
            for k in range(0, len(intersection_x_coords) - 1, 2):
                sum_width = sum_width + (intersection_x_coords[k + 1] - intersection_x_coords[k])
            hw_vals.append((target_z - z_min, sum_width))
        else:
            raise ValueError(f'Error converting cross-section tables to H/W. Contact Support\n'
                             f'Elev: {target_z}\n'
                             f'Intersection x-coords: {intersection_x_coords}')

    hw_vals = np.array(hw_vals)
    hw_vals = hw_vals / (z_max-z_min)

    # print(hw_vals)

    return z_min, z_max, hw_vals
