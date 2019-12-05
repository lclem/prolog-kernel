.PHONY: clean all build install kernel-install test

PIP=pip3
PYTHON=python3
SITE-PACKAGES = $(shell $(PIP) show notebook | grep Location | cut -d ' ' -f 2)

all: build install kernel-install

#test: build install kernel-install codemirror-install
	#jupyter nbconvert --to notebook --execute example/Example.ipynb  --output Example-output.ipynb
	
test: install
	pytest

build: dist/prolog_kernel-0.1-py3-none-any.whl

dist/prolog_kernel-0.1-py3-none-any.whl: setup.py src/prolog_kernel/install.py src/prolog_kernel/kernel.py
#	pylint src/prolog_kernel/kernel.py
	$(PYTHON) setup.py bdist_wheel

install: build
	$(PIP) install .

# run after the prolog_kernel module is installed
kernel-install: install
	$(PYTHON) -m prolog_kernel.install

pip-upload: build
	$(PYTHON) -m twine upload dist/*

pip-install:
	$(PIP) install prolog_kernel

commit:
	git add 

clean:
	rm -rf prolog_kernel.egg-info build dust