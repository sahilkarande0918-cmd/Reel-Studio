"""Local speech recognition with faster-whisper (CTranslate2). One model kept in memory at a time."""

import logging
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings

log = logging.getLogger(__name__)
_model = None
_model_key: tuple | None = None
# batched decoding is ~5x faster but repeated lines on a real podcast ("It's not an option" x6): off unless asked for
BATCH = int(os.environ.get("WHISPER_BATCH", "0"))
# The Hinglish-tuned model (settings.whisper_model) writes Roman Hinglish but cannot transcribe plain English (it
# printed "nan" for a whole English podcast). English and every other language use Whisper large-v3-turbo (MIT).
GENERAL_MODEL = os.environ.get("WHISPER_GENERAL_MODEL", r"D:\ReelStudio\models\whisper-large-v3-turbo")
HINGLISH = {"hi", "ur"}  # spoken Hindi/Urdu → the Hinglish model (Roman script, as Mode A expects)


def choose_model(audio: Path, language: str | None) -> tuple[str | None, str | None]:
    """(model name or None for the configured Hinglish model, language to decode with).
    language: None = detect; "hinglish"/"hi" = Hinglish model; anything else = the general model."""
    if language in ("hinglish", "hi"):
        return None, "hi"
    if not Path(GENERAL_MODEL).is_dir():
        return None, language  # general model not installed: previous behaviour
    if language:
        return GENERAL_MODEL, language
    from faster_whisper import decode_audio

    model = load(GENERAL_MODEL)
    lang, prob, _ = model.detect_language(audio=decode_audio(str(audio))[: 16000 * 30 * 4])  # up to 4 windows
    log.info("detected spoken language %s (%.2f)", lang, prob)
    return (None, "hi") if lang in HINGLISH else (GENERAL_MODEL, lang)


def _add_cuda_dlls() -> None:
    """pip's nvidia-cublas/cudnn wheels put DLLs in site-packages/nvidia/*/bin; Windows needs them on the path."""
    # Blackwell GPUs JIT-compile CTranslate2 kernels on first use (minutes); keep them cached on disk.
    os.environ.setdefault("CUDA_CACHE_MAXSIZE", str(4 * 1024**3))
    if sys.platform != "win32":
        return
    import site

    for sp in site.getsitepackages():
        for sub in ("cublas", "cudnn", "cuda_runtime", "cuda_nvrtc"):
            d = Path(sp) / "nvidia" / sub / "bin"
            if d.is_dir():
                os.add_dll_directory(str(d))
                os.environ["PATH"] = f"{d};{os.environ['PATH']}"


def load(model_name: str | None = None):
    global _model, _model_key
    s = get_settings()
    name = model_name or s.whisper_model
    key = (name, s.whisper_device, s.whisper_compute_type)
    if _model is not None and _model_key == key:
        return _model
    _add_cuda_dlls()
    from faster_whisper import WhisperModel

    t = time.perf_counter()
    try:
        _model = WhisperModel(
            name,
            device=s.whisper_device,
            compute_type=s.whisper_compute_type,
            download_root=str(s.data_dir / "models"),
        )
    except Exception as e:  # GPU unavailable / OOM -> CPU so jobs still complete (slowly)
        log.warning("GPU load failed (%s); falling back to CPU int8", e)
        _model = WhisperModel(
            name, device="cpu", compute_type="int8", download_root=str(s.data_dir / "models")
        )
        key = (name, "cpu", "int8")
    _model_key = key
    log.info("loaded whisper %s on %s in %.1fs", name, key[1], time.perf_counter() - t)
    return _model


def unload() -> None:
    """Free VRAM before another GPU model (LLM, renderer) runs."""
    global _model, _model_key
    _model, _model_key = None, None
    import gc

    gc.collect()


@dataclass
class Result:
    language: str
    language_probability: float
    duration_s: float
    segments: list[dict]
    words: list[dict]
    model: str
    device: str


def transcribe(
    audio: Path,
    hotwords: str = "",
    language: str | None = None,
    on_progress: Callable[[float], None] | None = None,
    auto_model: bool = False,
) -> Result:
    """auto_model: pick the speech model for the spoken language (see choose_model); otherwise the configured
    Hinglish model with `language` (Mode A's original behaviour)."""
    s = get_settings()
    name = None
    if auto_model:
        name, language = choose_model(audio, language)
    model = load(name)
    args = dict(
        language=language or s.whisper_language or None,
        task="transcribe",  # never "translate": Hinglish stays Hinglish
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        condition_on_previous_text=False,  # avoids repetition loops on long lectures
        hotwords=hotwords or None,
    )
    seg_iter = info = None
    if BATCH and _model_key[1] == "cuda":
        # same model, same beam, Silero-VAD chunks decoded 8 at a time: ~3-4x faster on long recordings (faster-whisper
        # benchmark: 1m03s → 17s); falls back to sequential decoding if the GPU runs out of memory
        from faster_whisper import BatchedInferencePipeline

        try:
            seg_iter, info = BatchedInferencePipeline(model=model).transcribe(str(audio), batch_size=BATCH, **args)
            seg_iter = list(seg_iter)
        except RuntimeError as e:  # CUDA out of memory
            log.warning("batched transcription failed (%s); decoding sequentially", e)
            seg_iter = info = None
    if seg_iter is None:
        seg_iter, info = model.transcribe(str(audio), **args)
    segments, words = [], []
    last = 0.0
    for seg in seg_iter:
        si = len(segments)
        segments.append(
            {
                "idx": si,
                "start_s": seg.start,
                "end_s": seg.end,
                "raw_text": seg.text.strip(),
                "avg_logprob": seg.avg_logprob,
                "no_speech_prob": seg.no_speech_prob,
            }
        )
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                words.append(
                    {
                        "idx": len(words),
                        "segment_idx": si,
                        "start_s": w.start,
                        "end_s": w.end,
                        "raw_text": text,
                        "confidence": w.probability,
                    }
                )
        if on_progress and info.duration and seg.end - last > 15:
            last = seg.end
            on_progress(seg.end / info.duration)
    return Result(
        info.language,
        info.language_probability,
        info.duration,
        segments,
        words,
        model=_model_key[0],
        device=_model_key[1],
    )
