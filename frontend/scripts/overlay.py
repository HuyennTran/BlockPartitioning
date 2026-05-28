import cv2

# depth colors
DEPTH_COLORS = {
    0:(255,255,255),  # white
    1:(255,255,0),    # cyan
    2:(0,255,0),      # green
    3:(0,165,255),    # orange
    4:(0,0,255)       # red
}

# line thickness by depth
DEPTH_THICKNESS = {
    0:3,
    1:2,
    2:1,
    3:1,
    4:1
}

# minimum visible block
MIN_BLOCK_SIZE = 4

# overlay transparency
ALPHA = 0.15

# draw partition blocks
def draw_blocks(frame,blocks,selected_depths=None):

    # check frame
    if frame is None:
        return frame

    # check blocks
    if blocks is None or blocks.empty:
        return frame

    # default depth filter
    if selected_depths is None:
        selected_depths = [0,1,2,3,4]

    # frame size
    frame_h,frame_w = frame.shape[:2]

    # overlay layer
    overlay = frame.copy()

    # csv max boundary
    max_x = (
        blocks["x"] +
        blocks["width"]
    ).max()

    max_y = (
        blocks["y"] +
        blocks["height"]
    ).max()

    # avoid invalid scale
    if max_x <= 0 or max_y <= 0:
        return frame

    # scale factor
    scale_x = frame_w / max_x
    scale_y = frame_h / max_y

    # sort by depth
    # large blocks first
    blocks = blocks.sort_values(
        by="qtDepth"
    )

    # draw each block
    for _,block in blocks.iterrows():

        # block depth
        depth = int(
            block["qtDepth"]
        )

        # skip hidden depth
        if depth not in selected_depths:
            continue

        # original block
        x = block["x"]
        y = block["y"]

        w = block["width"]
        h = block["height"]

        # skip invalid block
        if w <= 0 or h <= 0:
            continue

        # scale block
        x = int(x * scale_x)
        y = int(y * scale_y)

        w = int(w * scale_x)
        h = int(h * scale_y)

        # skip tiny block
        if (
            w < MIN_BLOCK_SIZE or
            h < MIN_BLOCK_SIZE
        ):
            continue

        # frame clamp
        x1 = max(0,x)
        y1 = max(0,y)

        x2 = min(
            frame_w - 1,
            x + w
        )

        y2 = min(
            frame_h - 1,
            y + h
        )

        # block color
        color = DEPTH_COLORS.get(
            depth,
            (180,180,180)
        )

        # line thickness
        thickness = DEPTH_THICKNESS.get(
            depth,
            1
        )

        # fill only largest block
        if depth == 0:

            cv2.rectangle(
                overlay,
                (x1,y1),
                (x2,y2),
                color,
                -1
            )

        # draw block border
        cv2.rectangle(
            overlay,
            (x1,y1),
            (x2,y2),
            color,
            thickness
        )

    # final blend
    output = cv2.addWeighted(
        overlay,
        ALPHA,
        frame,
        1 - ALPHA,
        0
    )

    return output

