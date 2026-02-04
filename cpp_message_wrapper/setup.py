from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext
import os

here = os.path.abspath(os.path.dirname(__file__))

ext_modules = [
    Pybind11Extension(
        "message_wrapper",
        ["src/bindings.cpp", "src/message_wrapper.cpp"],
        include_dirs=[
            os.path.join(here, "include"),
            os.path.join(here, "..", "my_lib")
        ],
        cxx_std=17,
        extra_compile_args=["-Wall", "-Wextra", "-Werror"],
    ),
]

setup(
    name="message_wrapper",
    version="1.0.0",
    description="C++ message parser with shared_ptr for Surf Lamp",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
)
