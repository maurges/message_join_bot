TESTDIR = test
TESTFILES = decide_test

.PHONY: test
test:
	python3 -m unittest $(addprefix $(TESTDIR).,$(TESTFILES))
