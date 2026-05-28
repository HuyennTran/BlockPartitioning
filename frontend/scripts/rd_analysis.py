# analyze partition statistics
def analyze_frame(blocks):

    # empty check
    if blocks is None or blocks.empty:

        return {
            "total_blocks":0,
            "avg_qt_depth":0,
            "avg_mt_depth":0,
            "estimated_bits":0,
            "estimated_bitrate":0,
            "complexity_score":0,
            "avg_block_area":0,
            "max_depth":0
        }

    # total blocks
    total_blocks = len(blocks)
    # average qt depth
    avg_qt_depth = (
        blocks["qtDepth"]
        .mean()
    )
    # average mt depth
    avg_mt_depth = (
        blocks["mtDepth"]
        .mean()
    )
    # block area
    block_area = (
        blocks["width"] *
        blocks["height"]
    )

    # average block area
    avg_block_area = (
        block_area.mean()
    )

    # max depth
    max_depth = (
        blocks["qtDepth"]
        .max()
    )

    # estimated bits
    estimated_bits = (
        total_blocks * 12
    )

    # estimated bitrate
    estimated_bitrate = (
        estimated_bits / 1000
    )

    # complexity score
    complexity_score = (
        avg_qt_depth * 0.5 +
        avg_mt_depth * 0.5
    )

    # return metrics
    return {

        "total_blocks":
        total_blocks,

        "avg_qt_depth":
        avg_qt_depth,

        "avg_mt_depth":
        avg_mt_depth,

        "estimated_bits":
        estimated_bits,

        "estimated_bitrate":
        estimated_bitrate,

        "complexity_score":
        complexity_score,

        "avg_block_area":
        avg_block_area,

        "max_depth":
        max_depth
    }