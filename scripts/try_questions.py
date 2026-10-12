"""Developer helper: run questions through Marshie's brain from the command line.
Usage:  python scripts/try_questions.py "what is a noun" "who is Yaa Asantewaa"
"""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="marshie_try_"))
from app.store import Store
from app.brain import Brain

brain = Brain(Store())
questions = sys.argv[1:] or ["hi", "what is the capital of Ghana", "what is photosynthesis"]
for q in questions:
    r = brain.ask(q)
    print(f"{q!r:50} [{r['source']:9} {r['confidence']:.2f}] {r['answer'][:110]}")
