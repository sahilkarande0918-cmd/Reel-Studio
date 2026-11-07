"""AI 4K upscaler, run as a subprocess in the torch environment (VIDEO_PYTHON), like video_worker.py.

    python upscale_worker.py job.json

job: {"input", "width", "height", "fps", "models": [general, wdn], "denoise", "encode": [ffmpeg args], "cwd",
      "faces": {"gfpgan": path, "yunet": path, "strength": 0.65} (optional)}
FFmpeg decodes the input to raw RGB frames → Real-ESRGAN realesr-general-x4v3 (BSD-3, xinntao/Real-ESRGAN; the compact
SRVGG network, fp16 on the GPU, the "wdn" weights blended in for denoising like Real-ESRGAN's -dn option) → resize to
the target size on the GPU → faces restored with GFPGAN v1.4 (Apache-2.0, TencentARC; detected with YuNet on the input
frame, landmarks smoothed over time against flicker, aligned to the FFHQ template, blended back at `strength` through
a feathered mask) → raw frames into a second FFmpeg that adds the overlays and encodes. No frame files on disk. Prints "progress <done> <total>" lines; exits non-zero with the error on stderr.
"""

import json
import queue
import subprocess
import sys
import threading
import time

import torch
from torch import nn
from torch.nn import functional as F


class SRVGGNetCompact(nn.Module):
    """Real-ESRGAN's compact SR network (same layer names, so the official weights load directly)."""

    def __init__(self, num_feat: int = 64, num_conv: int = 32, upscale: int = 4):
        super().__init__()
        self.upscale = upscale
        body = [nn.Conv2d(3, num_feat, 3, 1, 1), nn.PReLU(num_parameters=num_feat)]
        for _ in range(num_conv):
            body += [nn.Conv2d(num_feat, num_feat, 3, 1, 1), nn.PReLU(num_parameters=num_feat)]
        body.append(nn.Conv2d(num_feat, 3 * upscale * upscale, 3, 1, 1))
        self.body = nn.ModuleList(body)
        self.upsampler = nn.PixelShuffle(upscale)

    def forward(self, x):
        out = x
        for layer in self.body:
            out = layer(out)
        return self.upsampler(out) + F.interpolate(x, scale_factor=self.upscale, mode="nearest")


def load(models: list[str], denoise: float) -> nn.Module:
    def params(p: str) -> dict:
        d = torch.load(p, map_location="cpu", weights_only=True)
        return d.get("params_ema") or d.get("params") or d

    sd = params(models[0])
    if len(models) > 1 and denoise < 1:  # deep network interpolation: 1 = no denoising, 0 = strongest
        wdn = params(models[1])
        sd = {k: denoise * v + (1 - denoise) * wdn[k] for k, v in sd.items()}
    net = SRVGGNetCompact()
    net.load_state_dict(sd, strict=True)
    return net.eval().half().cuda().to(memory_format=torch.channels_last)  # ~1.4x faster convs


def yuv420(y: torch.Tensor) -> torch.Tensor:
    """RGB 0..1 (N,3,H,W) → BT.709 limited-range planar YUV 4:2:0 bytes (N, H*W*3/2), on the GPU: the encoder gets
    half the bytes and FFmpeg does no 4K colour conversion on the CPU."""
    r, g, b = y[:, 0], y[:, 1], y[:, 2]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    cb = F.avg_pool2d(((b - luma) / 1.8556).unsqueeze(1), 2).squeeze(1)
    cr = F.avg_pool2d(((r - luma) / 1.5748).unsqueeze(1), 2).squeeze(1)
    n = y.shape[0]
    planes = [(16 + 219 * luma).reshape(n, -1), (128 + 224 * cb).reshape(n, -1), (128 + 224 * cr).reshape(n, -1)]
    return torch.cat(planes, 1).round().clamp(0, 255).to(torch.uint8)


FFHQ = [[192.98138, 239.94708], [318.90277, 240.1936], [256.63416, 314.01935], [201.26117, 371.41043],
        [313.08905, 371.15118]]  # 5-point template of a 512x512 aligned face (GFPGAN / facexlib)
MIN_FACE = 20  # px in the input frame: smaller faces are left alone (nothing to restore, risk of invention)


def _grid(M, out_h: int, out_w: int, src_h: int, src_w: int) -> torch.Tensor:
    """grid_sample grid for an output of out_h x out_w where output pixel (u, v) reads source pixel M @ (u, v, 1)."""
    v, u = torch.meshgrid(torch.arange(out_h, device="cuda", dtype=torch.float32),
                          torch.arange(out_w, device="cuda", dtype=torch.float32), indexing="ij")
    m = torch.tensor(M, device="cuda", dtype=torch.float32)
    sx = m[0, 0] * u + m[0, 1] * v + m[0, 2]
    sy = m[1, 0] * u + m[1, 1] * v + m[1, 2]
    return torch.stack([sx / (src_w - 1) * 2 - 1, sy / (src_h - 1) * 2 - 1], -1)[None]


class Faces:
    """GFPGAN face restoration on the upscaled frame, faces found on the (small) input frame."""

    def __init__(self, cfg: dict, w: int, h: int):
        import cv2
        import numpy as np

        from gfpgan_arch import GFPGANv1Clean

        self.cv2, self.np = cv2, np
        self.det = cv2.FaceDetectorYN.create(cfg["yunet"], "", (w, h), 0.6, 0.3, 50)
        net = GFPGANv1Clean(out_size=512, num_style_feat=512, channel_multiplier=2, decoder_load_path=None,
                            fix_decoder=False, num_mlp=8, input_is_latent=True, different_w=True, narrow=1, sft_half=True)
        sd = torch.load(cfg["gfpgan"], map_location="cpu", weights_only=True)
        net.load_state_dict(sd.get("params_ema", sd), strict=True)
        self.net = net.eval().cuda()  # fp32 weights, autocast at run time: pure fp16 turns GFPGAN faces grey and hazy
        self.strength = float(cfg.get("strength", 0.65))
        self.template = np.array(FFHQ, np.float32)
        mask = torch.zeros(1, 1, 512, 512, device="cuda")
        mask[..., 28:-28, 28:-28] = 1
        k = torch.exp(-torch.arange(-40, 41, device="cuda", dtype=torch.float32) ** 2 / (2 * 14.0**2))
        k = (k / k.sum()).view(1, 1, 1, -1)
        mask = F.conv2d(F.conv2d(mask, k, padding=(0, 40)), k.transpose(2, 3), padding=(40, 0))
        self.mask = mask.clamp(0, 1)
        self.prev: list = []
        self.faces = 0

    def landmarks(self, rgb) -> list:
        """5-point landmarks per face on the input frame, smoothed with the previous frame's (no jitter)."""
        found = self.det.detect(self.np.ascontiguousarray(rgb[..., ::-1]))[1]
        out = []
        for f in found if found is not None else []:
            if f[2] < MIN_FACE:
                continue
            lm = f[4:14].reshape(5, 2).astype(self.np.float32)
            c = lm.mean(0)
            near = [q for q in self.prev if self.np.linalg.norm(q.mean(0) - c) < 0.25 * f[2]]
            out.append(0.55 * lm + 0.45 * near[0] if near else lm)
        self.prev = out
        return out

    def apply(self, y: torch.Tensor, lms: list, k: float) -> torch.Tensor:
        """y: (1,3,H,W) 0..1 upscaled frame; landmarks scaled by k into it. Restored faces are blended back in."""
        np = self.np
        H, W = y.shape[2:]
        for lm in lms:
            A, _ = self.cv2.estimateAffinePartial2D(lm * k, self.template, method=self.cv2.LMEDS)  # frame -> face
            if A is None:
                continue
            inv = self.cv2.invertAffineTransform(A)
            scale = float(np.sqrt(abs(np.linalg.det(inv[:, :2]))))  # frame px per face px
            src, M = y, inv
            if scale > 1.4:  # the face is bigger than 512 px here: sample from an anti-aliased smaller copy
                src = F.interpolate(y, scale_factor=1 / scale, mode="bilinear", antialias=True)
                M = inv / scale
            face = F.grid_sample(src, _grid(M, 512, 512, src.shape[2], src.shape[3]), mode="bilinear",
                                 padding_mode="reflection", align_corners=True)
            with torch.autocast("cuda", dtype=torch.float16):
                r = self.net(face * 2 - 1, return_rgb=False)[0]
            r = (r.float().clamp(-1, 1) + 1) / 2
            corners = np.array([[0, 0, 1], [511, 0, 1], [0, 511, 1], [511, 511, 1]], np.float32) @ inv.T
            x0, y0 = (int(max(0, v)) for v in corners.min(0))
            x1, y1 = (int(min(lim, v + 1)) for v, lim in zip(corners.max(0), (W, H), strict=True))
            if x1 - x0 < 8 or y1 - y0 < 8:
                continue
            Ar = A.copy()
            Ar[:, 2] += A[:, 0] * x0 + A[:, 1] * y0  # ROI pixel (u, v) -> face pixel
            g = _grid(Ar, y1 - y0, x1 - x0, 512, 512)
            back = F.grid_sample(r, g, mode="bilinear", align_corners=True)
            m = F.grid_sample(self.mask, g, mode="bilinear", align_corners=True) * self.strength
            y[..., y0:y1, x0:x1] = y[..., y0:y1, x0:x1] * (1 - m) + back * m
            self.faces += 1
        return y


def probe(path: str) -> tuple[int, int, int]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                          "stream=width,height,nb_read_packets", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout.strip().split(",")
    return int(out[0]), int(out[1]), int(out[2])


def main() -> None:
    job = json.loads(open(sys.argv[1], encoding="utf-8").read())
    torch.backends.cudnn.benchmark = True
    w, h, total = probe(job["input"])
    W, H = job["width"], job["height"]
    net = load(job["models"], job.get("denoise", 0.5))
    faces = Faces(job["faces"], w, h) if job.get("faces") else None
    # the intermediate is untagged: read it as BT.709 (FFmpeg's default for untagged video is BT.601, which shifted
    # and dulled reds and greens against the BT.709 output)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", job["input"], "-vf",
                            "scale=in_color_matrix=bt709:in_range=tv:out_range=pc,format=rgb24", "-f", "rawvideo", "-"],
                           stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-s", f"{W}x{H}",
                            "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-r", str(job["fps"]), "-i", "-", *job["encode"]], stdin=subprocess.PIPE,
                           cwd=job.get("cwd"), stderr=subprocess.PIPE)
    size, done, t0 = w * h * 3, 0, time.time()
    # decode, GPU and encode overlap: a reader thread fills `inq`, a writer thread drains `outq`
    inq: queue.Queue = queue.Queue(maxsize=8)
    outq: queue.Queue = queue.Queue(maxsize=4)

    def reader():
        while (buf := dec.stdout.read(size)) and len(buf) == size:
            inq.put(buf)
        inq.put(None)

    def writer():
        while (b := outq.get()) is not None:
            enc.stdin.write(b)

    threads = [threading.Thread(target=reader, daemon=True), threading.Thread(target=writer, daemon=True)]
    for t in threads:
        t.start()
    last_in, last_out = None, None
    with torch.inference_mode():
        while (buf := inq.get()) is not None:
            if buf == last_in:  # a repeated frame (24/25 fps film in a 30 fps reel): same output, no GPU work
                outq.put(last_out)
            else:
                raw = torch.frombuffer(bytearray(buf), dtype=torch.uint8)
                lms = faces.landmarks(raw.view(h, w, 3).numpy()) if faces else []
                x = raw.cuda().view(1, h, w, 3).permute(0, 3, 1, 2)
                y = net((x.half() / 255).contiguous(memory_format=torch.channels_last))
                if (y.shape[2], y.shape[3]) != (H, W):
                    y = F.interpolate(y.float(), size=(H, W), mode="bicubic", antialias=True)
                y = y.float().clamp(0, 1)
                if lms:
                    y = faces.apply(y, lms, W / w)
                last_in, last_out = buf, yuv420(y.clamp(0, 1)).cpu().numpy().tobytes()
                outq.put(last_out)
            done += 1
            if done % 30 == 0 or done == total:
                print(f"progress {done} {total} {done / max(time.time() - t0, 1e-6):.1f}", flush=True)
    outq.put(None)
    threads[1].join()
    dec.wait()
    enc.stdin.close()
    err = enc.stderr.read().decode("utf-8", "replace")
    if enc.wait() != 0 or dec.returncode != 0:
        sys.stderr.write(f"ffmpeg failed: {err[-2000:]}")
        sys.exit(1)
    print(json.dumps({"frames": done, "fps": round(done / max(time.time() - t0, 1e-6), 1),
                      "faces_restored": faces.faces if faces else 0}), flush=True)


if __name__ == "__main__":
    main()
