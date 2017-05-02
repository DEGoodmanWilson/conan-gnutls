#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, CMake
import os
from os import path
from shutil import copyfile

username = os.getenv("CONAN_USERNAME", "paulobrizolara")
channel = os.getenv("CONAN_CHANNEL", "testing")
library = "gnutls"
version = "3.5.11"

class PackageTest(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    requires = "%s/%s@%s/%s" % (library, version, username, channel)
    generators = "cmake"
    default_options = ""

    def build(self):
        #Make build dir
        build_dir = os.path.join(".", "build")
        self._try_make_dir(build_dir)

        #Copy
        build_info = "conanbuildinfo.cmake"
        copyfile(build_info, os.path.join(build_dir, build_info))

        cmake = CMake(self.settings)

        self.run('cmake "%s" %s' % (self.conanfile_directory, cmake.command_line), cwd=build_dir)
        self.run('cmake --build . %s' % cmake.build_config, cwd=build_dir)

    def test(self):
        self.output.info("test cwd: " + os.getcwd())
        self.run(path.join("build", "bin", "example"))

    def _try_make_dir(self, dir):
        try:
            os.mkdir(dir)
        except OSError:
            #dir already exist
            pass
