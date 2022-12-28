.PHONY: deploy
deploy: build
	twine upload --skip-existing dist/*

.PHONY: test-deploy
test-deploy: build
	twine upload --skip-existing -r pypitest dist/*

.PHONY: build
build:
	python setup.py sdist --formats=zip

.PHONY: build-doc
build-doc:
	sphinx-apidoc -efT -o docs/source src/kyoto_reader
	cd docs && make html
