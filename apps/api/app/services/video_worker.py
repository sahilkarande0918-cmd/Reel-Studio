"""Runs in the isolated video environment (torch + diffusers + LTX-Video 2B distilled), never in the API process:

    video-venv/python video_worker.py job.json

job.json: {"model_dir": path, "items": [{"image": path, "prompt": str, "out": path, "seed": int}],
           "width": 448, "height": 800, "frames": 97, "fps": 24}
Writes result.json next to job.json: per item seconds and frame count. Plain data in, video out; one process per job, so
VRAM is released afterwards. Weights: LTX-Video 2B 0.9.8 distilled (LTXV Open Weights License: free under US$10M annual
revenue; outputs must be disclosed as machine-generated) + a bf16 copy of the T5-XXL encoder.
"""

import json
import sys
from pathlib import Path

NEGATIVE = "worst quality, inconsistent motion, blurry, jittery, distorted, warped face, extra limbs, watermark, text artifacts"
# distilled schedule published for the LTX 0.9.7/0.9.8 distilled checkpoints (8 steps, no CFG)
TIMESTEPS = [1000, 993, 987, 981, 975, 909, 725, 0.03]


def main() -> None:
    job_path = Path(sys.argv[1])
    job = json.loads(job_path.read_text(encoding="utf-8"))
    import torch
    from diffusers import AutoencoderKLLTXVideo, FlowMatchEulerDiscreteScheduler, LTXConditionPipeline, LTXVideoTransformer3DModel
    from diffusers.pipelines.ltx.pipeline_ltx_condition import LTXVideoCondition
    from diffusers.utils import export_to_video
    from PIL import Image, ImageOps
    from transformers import T5EncoderModel, T5Tokenizer

    d = Path(job["model_dir"])
    ckpt = str(d / "ltxv-2b-0.9.8-distilled.safetensors")
    dt = torch.bfloat16
    # the single-file checkpoint is the 0.9.5+ 2B architecture; its diffusers configs are kept locally (configs/) so
    # loading never reaches the network (HF_HUB_OFFLINE)
    cfg = str(d / "configs")
    pipe = LTXConditionPipeline(
        # the distilled model runs the fixed TIMESTEPS schedule: no resolution-dependent shift
        scheduler=FlowMatchEulerDiscreteScheduler.from_pretrained(d / "scheduler", use_dynamic_shifting=False),
        vae=AutoencoderKLLTXVideo.from_single_file(ckpt, config=cfg, subfolder="vae", torch_dtype=dt),
        text_encoder=T5EncoderModel.from_pretrained(d / "text_encoder", torch_dtype=dt),
        tokenizer=T5Tokenizer.from_pretrained(d / "tokenizer"),
        transformer=LTXVideoTransformer3DModel.from_single_file(ckpt, config=cfg, subfolder="transformer", torch_dtype=dt),
    )
    pipe.enable_model_cpu_offload()  # T5-XXL (9.5 GB) never sits on an 8 GB GPU with the transformer
    pipe.vae.enable_tiling()
    w, h, n, fps = job.get("width", 448), job.get("height", 800), job.get("frames", 97), job.get("fps", 24)
    out = []
    for it in job["items"]:
        image = ImageOps.fit(Image.open(it["image"]).convert("RGB"), (w, h), Image.LANCZOS)
        frames = pipe(
            # the photo pins both ends: the subject stays in frame and the motion stays gentle (a single first-frame
            # condition let the model walk the person out of shot)
            conditions=[LTXVideoCondition(image=image, frame_index=0), LTXVideoCondition(image=image, frame_index=n - 1)],
            prompt=it["prompt"], negative_prompt=NEGATIVE,
            width=w, height=h, num_frames=n, timesteps=TIMESTEPS, decode_timestep=0.05, decode_noise_scale=0.025,
            image_cond_noise_scale=0.0, guidance_scale=1.0, guidance_rescale=0.7,
            generator=torch.Generator().manual_seed(int(it.get("seed", 0))), output_type="pil",
        ).frames[0]
        export_to_video(frames, it["out"], fps=fps)
        out.append({"out": it["out"], "frames": len(frames), "seconds": round(len(frames) / fps, 3)})
    (job_path.parent / "result.json").write_text(json.dumps({"device": "cuda" if torch.cuda.is_available() else "cpu",
                                                             "items": out}), encoding="utf-8")


if __name__ == "__main__":
    main()
