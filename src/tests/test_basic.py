import pytest
from prolog_kernel.kernel import PrologKernel

@pytest.fixture
def kernel():
    return PrologKernel()

#def test_get_expression_12(kernel): # cursor at the end of the word
#    kernel.code = "module test5 where\nproj1 : ∀ {A B : Set} → A → B → A\nproj1 x y = {! y !}\n\nproj' : ∀ {A B : Set} → A → B → A\nproj' = proj1\n\nproj'' : ∀ {A B : Set} → A → B → A\nproj'' = proj1"
#    assert (167, 172, "proj1") == kernel.get_expression(kernel.code, 172)

def test_responseParser(kernel):
    input = """Warning: /Users/lorenzo/Google Drive/dev/jupyterlab-prolog/examples/test.pl:7:
	Singleton variables: [Y]
    ERROR: /Users/lorenzo/Google Drive/dev/jupyterlab-prolog/examples/test.pl:8:9: Syntax error: Operator priority clash"""

    errors, warnings = kernel.responseParser(input)

    assert warnings[0] == 7
    assert errors[0] == (8, 9)


