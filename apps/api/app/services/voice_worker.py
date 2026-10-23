"""Runs in the isolated voice environment (torch + Chatterbox), never in the API process:

    voice-venv/python voice_worker.py job.json

job.json: {"sample": path, "items": [{"text": ..., "language": "en"|"hi", "out": path}], "exaggeration": 0.5}
Writes result.json next to job.json: per item duration and whether the Perth watermark is detectable.
Plain data in, audio out; no code from the job is executed. One process per job, so VRAM is released afterwards.
"""

import json
import sys
from pathlib import Path


def main() -> None:
    job_path = Path(sys.argv[1])
    job = json.loads(job_path.read_text(encoding="utf-8"))
    import torch
    import torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = ChatterboxMultilingualTTS.from_pretrained(device=device)
    out = []
    try:
        import perth

        detector = perth.PerthImplicitWatermarker()
    except Exception:  # noqa: BLE001 — identification is reported as unknown, never assumed
        detector = None
    for it in job["items"]:
        wav = model.generate(it["text"], language_id=it.get("language", "en"), audio_prompt_path=job["sample"],
                             exaggeration=job.get("exaggeration", 0.5), cfg_weight=job.get("cfg_weight", 0.5))
        torchaudio.save(it["out"], wav, model.sr)
        marked = None
        if detector is not None:
            try:
                marked = float(detector.get_watermark(wav.squeeze(0).cpu().numpy(), sample_rate=model.sr)) > 0.5
            except Exception:  # noqa: BLE001
                marked = None
        out.append({"out": it["out"], "seconds": round(wav.shape[-1] / model.sr, 2), "watermarked": marked})
    (job_path.parent / "result.json").write_text(json.dumps({"device": device, "items": out}), encoding="utf-8")


if __name__ == "__main__":
    main()
