"""SYNTHETIC test fixture: a two-voice business interview (original script, local Kokoro TTS, no real people).

It has a filler intro, a sponsor read, 12 distinct question→answer insights, one insight repeated later in other words
(near-duplicate test), an unfinished tangent and a filler outro. The video is two labelled colour panels (no faces), so
it tests conversation understanding, selection, cuts and captions, NOT face framing (that needs real footage).

    python tests/podcast_fixture.py OUT_DIR [--short]     # --short: only 5 insights (shortfall test)
"""

import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

HOST, GUEST = "am_adam", "af_heart"
INTRO = [
    (HOST, "Hey everyone, welcome back to the show. How are you doing today?"),
    (GUEST, "I'm doing great, thanks for having me. Really happy to be here."),
    (HOST, "Yeah, great to have you. Okay, let's get into it."),
]
SPONSOR = [(HOST, "Quick word from our sponsor. This episode is brought to you by Cloud Notes, the notebook app "
                  "that syncs everywhere. Use the code SHOW for twenty percent off your first year. Okay, back to it.")]
QA = [
    ("Why did your first startup fail?",
     "Honestly, we built a product nobody asked for. We spent eleven months writing code before we talked to a single "
     "customer. When we finally launched, we had three users, and two of them were my parents. The lesson I took from "
     "that is simple. Talk to twenty customers before you write one line of code. If you cannot find twenty people who "
     "describe the problem in their own words, you do not have a business yet, you have a hobby."),
    ("How do you decide what price to charge?",
     "Most founders price based on their costs, and that is the biggest mistake. Customers do not care what it costs "
     "you. They care what the problem costs them. We raised our price from nine dollars to forty nine dollars a month, "
     "and our sales actually went up, because the higher price told people we were serious. So price on the value you "
     "create, not on the hours you spend."),
    ("What is the one metric you watch every week?",
     "Retention. Not sign ups, not revenue, retention. If people use your product in week one and they are gone by week "
     "four, every dollar you spend on marketing is poured into a leaking bucket. We fixed our week four retention from "
     "twenty percent to fifty five percent before we spent anything on ads. That is why our growth later was cheap. Fix "
     "the bucket before you pour more water in."),
    ("How did you get your first hundred customers?",
     "We did things that do not scale. I personally emailed every person who signed up and asked them for a fifteen "
     "minute call. Out of three hundred emails, about eighty people said yes. Those calls gave us our roadmap and our "
     "first case studies. My advice is to do the manual work first. Automation is for later, once you know exactly what "
     "works."),
    ("What does an investor really look for in a pitch?",
     "From the investor side, the first thing I check is whether the founder understands the customer better than "
     "anyone else in the room. A great slide deck means nothing if you cannot tell me the exact moment your customer "
     "feels the pain. The second thing is speed. If you shipped three meaningful updates since our last meeting, that "
     "tells me more than any projection. So show evidence of learning, not just a big market number."),
    ("How do you hire your first employees?",
     "I hire for slope, not for intercept. Intercept is what someone knows today. Slope is how fast they learn. In a "
     "startup the job changes every three months, so the person who learns fastest wins. In interviews I ask people to "
     "teach me something they learned last month. If they light up and explain it clearly, that is a strong signal."),
    ("What is the most common financial mistake you see?",
     "Founders confuse revenue with cash. You can have a record month of sales and still run out of money, because "
     "your customers pay you in ninety days and your suppliers want payment in thirty. We almost died that way in our "
     "second year. Now I tell every founder to look at their cash runway every Monday. Revenue is vanity, cash is "
     "survival."),
    ("How do you handle a bad month?",
     "I write down three things. What happened, what we controlled, and what we will change. Then I share it with the "
     "whole team. Hiding bad news is what kills trust. When people see the numbers honestly, they come up with better "
     "ideas than I ever would alone. A bad month is information, not a verdict."),
    ("Should founders raise money early?",
     "Only if money is the bottleneck. Most early companies do not have a money problem, they have a learning problem. "
     "If you raise two million dollars before you know what customers want, you just make expensive mistakes faster. "
     "We bootstrapped until we had fifty paying customers, and then we raised on much better terms. Raise when money "
     "speeds up something that already works."),
    ("How do you build a sales process from scratch?",
     "Start by writing down every step a customer takes from first hearing about you to paying you. Then measure the "
     "drop at each step. When we did this, we saw that sixty percent of people disappeared right after the demo. The "
     "demo was too long. We cut it from forty minutes to twelve and our close rate doubled. You cannot fix a process you "
     "have never written down."),
    ("What is your view on competition?",
     "Competition is mostly a distraction. In five years I have never lost a customer because a competitor launched a "
     "feature. I lost customers because we were slow to answer support tickets. So I spend my energy on response time. "
     "We answer every ticket within two hours now. Watch your customers, not your competitors."),
    ("What would you tell yourself on day one?",
     "Pick a problem you are willing to work on for ten years. The first idea is almost never the final product, and "
     "the only thing that keeps you going through the pivots is caring about the problem itself. If you are only in it "
     "for the money, you will quit at the first hard year. Choose the problem first, then the product."),
]
# said again later in other words: a near-duplicate of the first insight
REPEAT = ("Coming back to customers for a second.",
          "Like I said earlier, really the main thing is talking to customers before building. Before you write any "
          "code, go and talk to around twenty customers and listen to how they describe the problem. If you cannot find "
          "them, it is a hobby and not a business.")
TANGENT = [(HOST, "By the way, did you see the match last night?"),
           (GUEST, "Oh I did, that last over was crazy, but anyway, we can talk about that some other time.")]
OUTRO = [(HOST, "This was amazing. Thank you so much for coming on."), (GUEST, "Thank you, this was really fun.")]


def script(short: bool = False) -> list[tuple[str, str]]:
    qa = QA[:5] if short else QA
    turns = list(INTRO)
    for i, (q, a) in enumerate(qa):
        turns += [(HOST, q), (GUEST, a)]
        if i == 2:
            turns += SPONSOR
        if i == 6 and not short:
            turns += TANGENT
    if not short:
        turns += [(HOST, REPEAT[0]), (GUEST, REPEAT[1])]
    return turns + OUTRO


def build(out: Path, short: bool = False) -> Path:
    from app.services.generation.narration import _synthesize

    out.mkdir(parents=True, exist_ok=True)
    parts, labels = [], []
    for n, (voice, text) in enumerate(script(short)):
        wav = out / f"turn-{n:03d}.wav"
        if not wav.exists():
            _synthesize(text, voice, wav)
        parts.append(wav)
        labels.append("HOST" if voice == HOST else "GUEST")
    # each turn → 16 kHz mono with 0.6 s of silence after it, then one file
    lst = out / "list.txt"
    norm = []
    for p in parts:
        q = p.with_suffix(".16k.wav")
        if not q.exists():
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(p), "-af", "apad=pad_dur=0.6", "-ar", "16000",
                            "-ac", "1", str(q)], check=True)
        norm.append(q)
    lst.write_text("".join(f"file '{q.name}'\n" for q in norm), encoding="utf-8")
    audio = out / "interview.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                    str(audio)], check=True, cwd=out)
    with wave.open(str(audio)) as w:
        dur = w.getnframes() / w.getframerate()
    video = out / ("interview-short.mp4" if short else "interview.mp4")
    font = "C\\:/Windows/Fonts/arial.ttf"
    vf = (f"drawbox=x=0:y=0:w=960:h=1080:color=0x1f3a2e:t=fill,drawbox=x=960:y=0:w=960:h=1080:color=0x2e2a1f:t=fill,"
          f"drawtext=fontfile='{font}':text='HOST (synthetic voice)':x=180:y=520:fontsize=48:fontcolor=white,"
          f"drawtext=fontfile='{font}':text='GUEST (synthetic voice)':x=1130:y=520:fontsize=48:fontcolor=white,"
          f"drawtext=fontfile='{font}':text='SYNTHETIC TEST FIXTURE':x=(w-tw)/2:y=60:fontsize=36:fontcolor=0xffd43b")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=black:s=1920x1080:r=30:d={dur:.2f}",
                    "-i", str(audio), "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", str(video)], check=True)
    (out / "labels.txt").write_text("\n".join(labels), encoding="utf-8")
    return video


if __name__ == "__main__":
    print(build(Path(sys.argv[1]), short="--short" in sys.argv))
