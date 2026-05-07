.PHONY: all exe dist test clean

all: dist

exe:
	pyinstaller --onefile --windowed --add-data wacb/wacb.css:wacb wacb.py

dist:
	python -m build

test:
	pytest --cov=wacb --cov-report html

clean:
	rm -rf __pycache__ */__pycache__
	rm -rf .pytest_cache .coverage htmlcov
	rm -rf dist build wacb.egg-info wacb.spec
	find . -name '*~' -exec rm {} \;
