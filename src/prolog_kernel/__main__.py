from ipykernel.kernelapp import IPKernelApp
from .kernel import PrologKernel

IPKernelApp.launch_instance(kernel_class=PrologKernel)