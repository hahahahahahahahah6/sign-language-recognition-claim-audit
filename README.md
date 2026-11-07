# Documentation claim auditor

An offline, deterministic, standard-library-only CLI for comparing documentation
claims about signed-video labelling with static Python evidence. Python 3.9 or
later is required. No network, telemetry, or file writes are performed.

Install and run:

```sh
python3 -m pip install .
sign-language-recognition-claim-audit audit .
python3 -m sign_language_recognition_claim_audit audit . --json
sign-language-recognition-claim-audit --version
python3 -m unittest discover
```

The repository defaults to the current directory. The scope is the root README,
Markdown below docs, and Markdown fixtures below tests directories. Python files
are scanned recursively, excluding Git metadata, caches and virtual environments.
Triple-backtick fences are excluded; inline code counts as prose. Repeat
`--ignore PREFIX` to skip paths by their repository-relative prefix. Use
`--verbose` for scope and per-file decisions on stderr. JSON output is a list of
findings, each carrying an identifier, severity, path, phrase, verdict and message.

Findings use these identifiers:

```text
documented-sign-language-recognition-claim-false
documented-no-sign-language-recognition-claim-false
```

Contradicted assertions and denials are high severity. Assertions found in test
fixtures alone are medium severity. Exit status is 0 below the selected threshold,
2 for findings at or above it, and 1 for usage or IO errors. The default threshold
is high; `--fail-on medium` includes test fixtures. A denial without contradictory
source evidence passes.

## Differentiation

```text
gesture-recognition-claim-audit
```

Checks generic hand movements; this auditor checks mapping to linguistic signs.

```text
pose-claim-audit
```

Checks body pose tracking; this auditor checks sign vocabulary.

```text
face-claim-audit
```

Checks finding faces; this auditor checks reading signs.

```text
translation-claim-audit
```

Checks text between spoken languages; this auditor checks signed video to text.

```text
speech-recognition-claim-audit
```

Checks spoken audio transcription; this auditor checks signed video.

```text
image-classification-claim-audit
```

Checks one label for a still image; this auditor checks a sign in video.

## Limitations

Static patterns are not semantic judgement. Exact substring phrases are matched
case-insensitively without stemming, fuzzy matching, or hyphen normalization.
Denial spans are removed first. Longest-first matching blanks each span, so each
occurrence is counted once under its longest matching phrase. Restatements can
be missed. Syntax-invalid Python provides no evidence. All parts of an evidence
route must occur in a single module; imports and uncalled constructions alone
provide none. Local function and class definitions shadow imported route names.

A video-classification pipeline whose model string contains “sign”, paired with
an instance call, counts even though that pair does not prove a correct label.
A landmark extraction and processing stage paired with a classifier prediction
also counts, although the prediction alone does not establish a linguistic label.
A generic method name on an unrelated object counts too:

```python
unrelated.recognize_sign_language()
```

A gesture recognizer deliberately does not count: labelling a hand movement is
not mapping it to a linguistic sign. Hand tracking, pose estimation, face work,
spoken text translation and speech processing alone provide no evidence.

These exact phrases can describe human interpreters, human translation services,
or reading road signs aloud respectively. Such prose still matches; this is a
known ambiguity, not a semantic distinction the auditor can resolve:

```text
sign language interpreter
sign language translation
sign to text
we provide a sign language interpreter for meetings
```

Licensed under MIT. Tests are included in the source distribution.
