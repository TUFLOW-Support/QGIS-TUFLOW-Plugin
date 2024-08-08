import numpy as np

standard_sizes_in = [
    (19, 30),
    (22, 34),
    (24, 38),
    (27, 42),
    (29, 45),
    (32, 49),
    (34, 53),
    (38, 60),
    (43, 68),
    (48, 76),
    (53, 83),
    (58, 91),
    (63, 98),
    (68, 106),
    (72, 113),
    (72, 121),
    (82, 128),
    (87, 136),
    (92, 143),
    (97, 151),
    (106, 166),
    (116, 180),
]

out_sizes_met = [(float(x) * 25.4 / 1000.0, float(y) * 25.4 / 1000.0) for x, y in standard_sizes_in]
out_sizes_eng = [(float(x) / 12.0, float(y) / 12.0) for x, y in standard_sizes_in]

arr_met = np.asarray([x[0] for x in out_sizes_met])
arr_eng = np.asarray([x[0] for x in out_sizes_eng])

arr_met_width = np.asarray([x[1] for x in out_sizes_met])
arr_eng_width = np.asarray([x[1] for x in out_sizes_eng])

arch_sizes_in = [
    (11, 18),
    (13, 17),
    (13.5, 22),
    (15, 21),
    (15.5, 26),
    (18, 24),
    (18.25, 28.5),
    (20, 28),
    (22.5, 36.25),
    (24, 35),
    (26.625, 43.75),
    (29, 42),
    (31, 40),
    (31.25, 46),
    (31.3125, 51.125),
    (33, 49),
    (36, 58.5),
    (38, 57),
    (40, 65),
    (41, 53),
    (43, 64),
    (45, 73),
    (46, 60),
    (47, 71),
    (51, 66),
    (52, 77),
    (54, 88),
    (55, 73),
    (55.25, 73),
    (57, 76),
    (57.25, 83),
    (59, 81),
    (59.25, 81),
    (61, 84),
    (62, 102),
    (63, 87),
    (63.25, 87),
    (65, 92),
    (67, 95),
    (69, 98),
    (71, 103),
    (71.5, 103),
    (72, 115),
    (73, 106),
    (75, 112),
    (75.5, 122),
    (77, 114),
    (77.5, 112),
    (79, 117),
    (79.5, 117),
    (81, 123),
    (83, 128),
    (83.5, 128),
    (85, 131),
    (87, 137),
    (87.125, 138),
    (87.5, 137),
    (89, 139),
    (91, 142),
    (91.5, 142),
    (93, 148),
    (95, 150),
    (96.875, 154),
    (97, 152),
    (100, 154),
    (101, 161),
    (103, 167),
    (105, 169),
    (106.5, 168.75),
    (107, 171),
    (109, 178),
    (111, 184),
    (112, 159),
    (113, 186),
    (114, 162),
    (115, 188),
    (116, 168),
    (118, 170),
    (118.25, 190),
    (119, 197),
    (120, 173),
    (121, 199),
    (122, 179),
    (124, 184),
    (126, 187),
    (128, 190),
    (130, 195),
    (132, 198),
    (134, 204),
    (136, 206),
    (138, 209),
    (140, 215),
    (142, 217),
    (144, 223),
    (146, 225),
    (148, 231),
    (150, 234),
    (152, 236),
    (154, 239),
    (156, 245),
    (158, 247),
]

arch_sizes_met = [(float(x) * 25.4 / 1000.0, float(y) * 25.4 / 1000.0) for x, y in arch_sizes_in]
arch_sizes_eng = [(float(x) / 12.0, float(y) / 12.0) for x, y in arch_sizes_in]

arch_arr_met = np.asarray([x[0] for x in arch_sizes_met])
arch_arr_eng = np.asarray([x[0] for x in arch_sizes_eng])

def get_nearest_height_for_horzellipse(metric_units, width):
    if metric_units:
        index = (np.abs(arr_met_width - width)).argmin()
        return out_sizes_met[index][0]
    else:
        index = (np.abs(arr_eng_width - width)).argmin()
        return out_sizes_eng[index][0]
def get_nearest_width_for_horzellipse(metric_units, height):
    if metric_units:
        index = (np.abs(arr_met - height)).argmin()
        return out_sizes_met[index][1]
    else:
        index = (np.abs(arr_eng - height)).argmin()
        return out_sizes_eng[index][1]


def get_arch_width(metric_units, height):
    if metric_units:
        index = (np.abs(arch_arr_met - height)).argmin()
        return arch_sizes_met[index][1]
    else:
        index = (np.abs(arch_arr_eng - height)).argmin()
        return arch_sizes_eng[index][1]


if __name__ == '__main__':
    print(out_sizes_eng)
    print(out_sizes_met)

    print(get_nearest_width_for_horzellipse(False, 2.25))
    print(get_nearest_width_for_horzellipse(True, 1.60))

    print(arch_sizes_met)
    print(get_arch_width(True, 1.143))
    print(get_arch_width(False, 3.75))