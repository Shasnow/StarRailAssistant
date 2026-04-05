def compress_image_bytes(
        image_bytes: bytes,
        target_size: int,
        min_quality: int = 30,
        max_quality: int = 90) -> tuple[bytes | None, str | None, int]:
    """
    将图片压缩为渐进式 JPG，使用二分搜索质量，尽量贴近目标大小。

    返回：(压缩后的字节, 格式, 质量)
    """
    if not image_bytes:
        return None, None, -1

    import cv2
    import numpy as np

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
    if img is None:
        return None, None, -1

    # JPEG 仅支持 1/3 通道，若为 4 通道则转为 BGR
    if len(img.shape) == 2:
        bgr = img
    else:
        if img.shape[2] == 4:
            bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        elif img.shape[2] == 3:
            bgr = img
        else:
            bgr = img[:, :, :3]

    best: bytes | None = None
    best_q: int = -1
    lo, hi = min_quality, max_quality

    while lo <= hi:
        q = (lo + hi) // 2
        params = [
            int(cv2.IMWRITE_JPEG_QUALITY), int(q),
            int(cv2.IMWRITE_JPEG_OPTIMIZE), 1,
            int(cv2.IMWRITE_JPEG_PROGRESSIVE), 1,
        ]
        ok, enc = cv2.imencode('.jpg', bgr, params)
        if not ok:
            break

        size = enc.nbytes
        if size <= target_size:
            best = enc.tobytes()
            best_q = q
            lo = q + 1
        else:
            hi = q - 1

    if best:
        return best, 'jpeg', best_q
    else:
        return None, None, -1
