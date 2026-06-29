from pathlib import Path

from app.scanner.source_detector import SourceRootDetector

detector = SourceRootDetector()

roots = detector.detect(Path("."))

print("\nDetected Source Roots\n")

for root in roots:
    print(root)