.PHONY: test

test:
	QT_QPA_PLATFORM=offscreen uv run --no-sync python -m unittest discover -s tests -v

run:
	uv run --locked tofu-eq
