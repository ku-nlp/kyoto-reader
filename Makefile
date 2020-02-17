.PHONY: deploy
deploy: build
	twine upload dist/*

.PHONY: test-deploy
test-deploy: build
	twine upload -r pypitest dist/*

.PHONY: build
build:
	python setup.py sdist --formats=zip

.PHONY: build-doc
build-doc:
	sphinx-apidoc -ef -o docs/source src/kyoto_reader
	cd docs && make html
