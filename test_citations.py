
from rag import extract_citations
from rag import hint_builder
from rag import answer_with_retry
# 1. Three different sources
assert extract_citations("Text [1], [2], [3].", 3) == (
    [1, 2, 3], []
)

# 2. Preserve order and remove duplicates
assert extract_citations("Text [2]. Mehr [2] und [1].", 3) == (
    [2, 1], []
)

# 3. Invalid citation
assert extract_citations("Text [4].", 3) == (
    [], [4]
)

# 4. Multiple citations in one bracket
assert extract_citations("Text [1, 2].", 3) == (
    [1, 2], []
)

# 5. Refusal sentence has no citations
refusal = (
    "Diese Information finde ich nicht in den vorliegenden Dokumenten."
)
assert extract_citations(refusal, 3) == ([], [])

hint = hint_builder([4], 3 )
assert "[4]" in hint 
assert "[1] bis [3]" in hint


def make_fake_generate(answers):
    calls = []

    def generate(query, context, hint=None):
        calls.append({
            "query": query,
            "context": context,
            "hint": hint,
        })
        return answers[len(calls) - 1]

    return generate, calls

fake, calls = make_fake_generate(["Eine Antwort [1]."])

answer, valid, invalid, attempts = answer_with_retry(
    generate=fake,
    query="Testfrage",
    context="[1] Testquelle",
    n_sources=3,
)

assert len(calls) == 1
assert invalid == []
assert attempts == 1
assert calls[0]["hint"] is None

print("Case A passed!")

# B: 1st invalid, 2nd valid
fake, calls = make_fake_generate([
    "Eine Antwort [4].",
    "Eine Antwort [1].",
])

answer, valid, invalid, attempts = answer_with_retry(
    generate=fake,
    query="Testfrage",
    context="[1] Testquelle",
    n_sources=3,
)

assert len(calls) == 2
assert attempts == 2
assert invalid == []
assert calls[0]["hint"] is None
assert "[4]" in calls[1]["hint"]

print("Case B passed!")


# C: always invalid
fake, calls = make_fake_generate([
    "Eine Antwort [4].",
    "Eine Antwort [4].",
    "Eine Antwort [4].",
])

answer, valid, invalid, attempts = answer_with_retry(
    generate=fake,
    query="Testfrage",
    context="[1] Testquelle",
    n_sources=3,
)

assert len(calls) == 3
assert attempts == 3
assert invalid == [4]

print("Case C passed!")


# D: refusal
fake, calls = make_fake_generate([refusal])

answer, valid, invalid, attempts = answer_with_retry(
    generate=fake,
    query="Testfrage",
    context="[1] Testquelle",
    n_sources=3,
)

assert len(calls) == 1
assert valid == []
assert invalid == []

print("Case D passed!")


# E: max_attempts=2
fake, calls = make_fake_generate([
    "Eine Antwort [4].",
    "Eine Antwort [4].",
])

answer, valid, invalid, attempts = answer_with_retry(
    generate=fake,
    query="Testfrage",
    context="[1] Testquelle",
    n_sources=3,
    max_attempts=2,
)

assert len(calls) == 2
assert attempts == 2

print("Case E passed!")
print("All citation tests passed.")
