"""
The environment of the ePuck robot consists of several walls and
obstacles. The difference between those two is that walls are isolated
lines while obstacles are polygons, hence closed shapes. Some obstacles
and arena arrangements have been prepared in this file.

"""
# open rectangle
left, right = -1.0, 5.0
bottom, top = -4.0, 20.0
obstacles_open=[
    (left, bottom, right, bottom), # bottom line
    (left, bottom, left, top),     # left line
    (right, bottom, right, top)    # right line
]

# rhomboid
rad_x, rad_y = 10.0, 10.0
obstacles_rhomb=[
    (0.0, rad_y, rad_x, 0.0),  # top to right
    (0.0, -rad_y, rad_x, 0.0), # bottom to right
    (-rad_x, 0.0, 0.0, rad_y), # left to top
    (-rad_x, 0.0, 0.0, -rad_y) # left to bottom
]

# box
rad_x, rad_y = 10.0, 10.0
obstacles_box=[
    ( rad_x, -rad_y,  rad_x,  rad_y), # right
    (-rad_x, -rad_y, -rad_x,  rad_y), # left
    (-rad_x,  rad_y,  rad_x,  rad_y), # top
    (-rad_x, -rad_y,  rad_x, -rad_y)  # bottom
]

# wall
dist=5.0
obstacles_wall=[
    ( dist, -10, dist, 10 ) # wall at dist
]

# lower box
train_lower = [
    (6.0, -6.0),
    (10.0, -6.0),
    (10.0, -10.0),
    (6.0, -10.0)
]

# middle lower box
train_middle = [
    (0.0, -3.0),
    (2.0, -5.0),
    (0.0, -7.0),
    (-2.0, -5.0)
]

# left rectangle
train_left = [
    (-6.0, 4.0),
    (-4.0, 4.0),
    (-4.0, -2.0),
    (-6.0, -2.0)
]

# upper right box
train_upper = [
    (5.0, 6.0),
    (6.0, 2.0),
    (5.0, -1.0),
    (0.0, 4.0)
]

# right triangle
test_right=[
    (2.0, -7.0),
    (4.0, 1.0),
    (6.0, -2.0)
]

# upper rectangle
test_upper=[
    (-6.0, 4.0),
    (-6.0, 6.0),
    (6.0, 6.0),
    (6.0, 4.0)
]

# left lower rectangle
test_left=[
    (-4.0, 0.0),
    (-1.0, -4.0),
    (-4.0, -7.0),
    (-7.0, -4.0)
]

def box_gen_lines((cx,cy), (sx, sy)):
    """Create a rectangle using a center ``(cx,cy)`` and side length
    ``(sx, sy)``."""
    return [
        (cx - sx, cy - sy, cx - sx, cy + sy),
        (cx + sx, cy - sy, cx + sx, cy + sy),
        (cx - sx, cy + sy, cx + sx, cy + sy),
        (cx - sx, cy - sy, cx + sx, cy - sy)
    ]

def box_gen_corners((cx,cy), (sx, sy)):
    """Create a rectangle using two corners ``(cx,cy)`` and ``(sx,sy)``."""
    return [
        (cx - sx, cy - sy),
        (cx + sx, cy - sy),
        (cx + sx, cy + sy),
        (cx - sx, cy + sy)
    ]

obstacles_boxes=box_gen_lines((5.0, 5.0), (1.0, 1.0)) \
    + box_gen_lines((0.0, 3.0), (1.0, 1.0)) \
    + box_gen_lines((-2.0, -3.0), (1.0, 1.0)) \
    + box_gen_lines((4.0, -2.0), (1.0, 1.0)) \
    + box_gen_lines((-6.0, 5.0), (1.0, 1.0))

obstacles_maze=box_gen_lines((3.0, 3.0), (2.5, 1.5)) + box_gen_lines((3.0, 3.0), (5.0, 4.5))

obstacles_pipe=[
    (-1.0, 1.5, -1.0, -1.5), # behind
    (-1.0, 1.5, 5.0, 1.5), # top
    (-1.0, -1.5, 8.0, -1.5), # bottom
    (5.0, 1.5, 5.0, 8.0), # ascent, left
    (8.0, -1.5, 8.0, 5.0), # ascent, right
    (5.0, 8.0, 15.0, 8.0), # opening, left
    (8.0, 5.0, 15.0, 5.0)  # opening, right
]
    

# Inverse crown
obstacle_crown = [
    (0.0, 0.0),
    (1.0, 1.0),
    (2.0, -1.0),
    (3.0, 1.0),
    (4.0, 0.0),
    (4.0, 2.0),
    (0.0, 2.0)
]
