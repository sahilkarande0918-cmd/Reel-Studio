"""AI 4K upscaler, run as a subprocess in the torch environment (VIDEO_PYTHON), like video_worker.py.

    python upscale_worker.py job.json

job: {"input", "width", "height", "fps", "models": [general, wdn], "denoise", "encode": [ffmpeg args], "cwd"}
FFmpeg decodes the input to raw RGB frames → Real-ESRGAN realesr-general-x4v3 (BSD-3, xinntao/Real-ESRGAN; the compact
SRVGG network, fp16 on the GPU, the "wdn" weights blended in for denoising like Real-ESRGAN's -dn option) → resize to
the target size on the GPU → raw frames into a second FFmpeg that adds the overlays and encodes. No frame files on
disk. Prints "progress <done> <total>" lines; exits non-zero with the error on stderr.
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
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", job["input"], "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
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
                x = torch.frombuffer(bytearray(buf), dtype=torch.uint8).cuda().view(1, h, w, 3).permute(0, 3, 1, 2)
                y = net((x.half() / 255).contiguous(memory_format=torch.channels_last))
                if (y.shape[2], y.shape[3]) != (H, W):
                    y = F.interpolate(y.float(), size=(H, W), mode="bicubic", antialias=True)
                last_in, last_out = buf, yuv420(y.float().clamp(0, 1)).cpu().numpy().tobytes()
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
    print(json.dumps({"frames": done, "fps": round(done / max(time.time() - t0, 1e-6), 1)}), flush=True)


if __name__ == "__main__":
    main()
