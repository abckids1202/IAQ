import os


# Keep the legacy unit fixtures deterministic. Integration tests that exercise
# the imported Dataset Lab catalog opt into it explicitly with environment
# variables, while manual local runs use the staged catalog by default.
os.environ.setdefault("IAQ_ASSESSMENT_SOURCE", "authored")
os.environ.setdefault("IAQ_ALLOW_STAGED_ITEMS", "false")
