from conans import ConanFile, AutoToolsBuildEnvironment, tools
from conans.errors import ConanInvalidConfiguration

import os


class XtrConan(ConanFile):
    name = "xtr"
    description = \
        "C++ Logging Library for Low-latency or Real-time Environments"
    topics = ("xtr", "logging", "logger")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/choll/xtr"
    license = "MIT"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
        "enable_exceptions": [True, False],
        "enable_lto": [True, False],
    }
    default_options = {
        "fPIC": True,
        "enable_exceptions": True,
        "enable_lto": False,
    }
    generators = "make"

    def requirements(self):
        self.requires("fmt/7.1.3")
        # Require liburing on any Linux system as a run-time check will be
        # done to detect if the host kernel supports io_uring.
        if self.settings.os == "Linux":
            self.requires("liburing/2.1")

    def validate(self):
        if self.settings.os not in ("FreeBSD", "Linux"):
            raise ConanInvalidConfiguration(f"Unsupported os={self.settings.os}")
        if self.settings.compiler not in ("gcc", "clang"):
            raise ConanInvalidConfiguration(f"Unsupported compiler={self.settings.compiler}")
        if self.settings.arch not in ("x86_64", ):
            raise ConanInvalidConfiguration(f"Unsupported arch={self.settings.arch}")

        minimal_cpp_standard = 20
        if self.settings.compiler.cppstd:
            tools.check_min_cppstd(self, minimal_cpp_standard)

        minimum_version = {"gcc": 10, "clang": 12}
        compiler = str(self.settings.compiler)
        version = tools.Version(self.settings.compiler.version)

        if version < minimum_version[compiler]:
            raise ConanInvalidConfiguration(
                f"{self.name} requires {self.settings.compiler} version {minimum_version[compiler]} or later")

    def source(self):
        tools.get(**self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # FIXME: should be done in validate (but version is not yet available there)
        if tools.Version(self.deps_cpp_info["fmt"].version) < 6:
            raise ConanInvalidConfiguration("The version of fmt must >= 6.0.0")
        if tools.Version(self.deps_cpp_info["fmt"].version) == "8.0.0" and self.settings.compiler == "clang":
            raise ConanInvalidConfiguration("fmt/8.0.0 is known to not work with clang (https://github.com/fmtlib/fmt/issues/2377)")

        autotools = AutoToolsBuildEnvironment(self)
        env_build_vars = autotools.vars
        # Conan uses LIBS, presumably following autotools conventions, while
        # the XTR makefile follows GNU make conventions and uses LDLIBS
        env_build_vars["LDLIBS"] = env_build_vars["LIBS"]
        # fPIC and Release/Debug/RelWithDebInfo etc are set via CXXFLAGS,
        # CPPFLAGS etc.
        env_build_vars["EXCEPTIONS"] = \
            str(int(bool(self.options.enable_exceptions)))
        env_build_vars["LTO"] = str(int(bool(self.options.enable_lto)))
        autotools.make(vars=env_build_vars)
        autotools.make(vars=env_build_vars, target="xtrctl")

    def package(self):
        self.copy("LICENSE", dst="licenses")
        self.copy("*.hpp", src="include", dst="include")
        self.copy("*/libxtr.a", src="build", dst="lib", keep_path=False)
        self.copy("*/xtrctl", src="build", dst="bin", keep_path=False)

        tools.rmdir(os.path.join(self.package_folder, "man"))

    def package_info(self):
        self.cpp_info.libs = ["xtr"]
        self.cpp_info.system_libs = ["pthread"]
        bin_path = os.path.join(self.package_folder, "bin")
        self.output.info(f"Appending PATH environment variable: {bin_path}")
        self.env_info.PATH.append(bin_path)
