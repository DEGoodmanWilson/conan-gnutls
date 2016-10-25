from conans import ConanFile
import os, shutil
from conans.tools import download, unzip, replace_in_file, check_md5
from conans import CMake


class GnutlsConan(ConanFile):
    name = "gnutls"
    version = "1.7.3"
    branch = "master"
    ZIP_FOLDER_NAME = "gnutls-%s" % version
    generators = "cmake"
    settings =  "os", "compiler", "arch", "build_type"
    options = {"shared": [True, False],
               "enable_m_guard": [True, False],
               "disable_asm": [True, False],
               "enable_ld_version_script": [True, False],
               "disable_endian_check": [True, False],
               "enable_random_daemon": [True, False],
               "enable_hmac_binary_check": [True, False],
               "disable_padlock_support": [True, False],
               "disable_aesni_support": [True, False],
               "disable_O_flag_munging": [True, False]}
               #TODO add in non-binary flags
    requires = 'nettle/1.24@DEGoodmanWilson/testing', 'gmp/6.1.1@DEGoodmanWilson/testing', 'zlib/1.2.8@lasote/stable'

    url = "http://github.com/DEGoodmanWilson/conan-gnutls"
    default_options = "shared=False", "enable_m_guard=False", "disable_asm=False", \
                      "enable_ld_version_script=False", "disable_endian_check=False", \
                      "enable_random_daemon=False", "disable_aesni_support=False", \
		      "enable_hmac_binary_check=False", "disable_padlock_support=False", "disable_O_flag_munging=False"

    def source(self):
        zip_name = "gnutls-%s.tar.gz" % self.version
        download("https://ftp.gnu.org/gnu/gnutls//%s" % zip_name, zip_name)
        check_md5(zip_name, "bb5b00cb70b1215833857fd690080fbb")
        unzip(zip_name)
        os.unlink(zip_name)

    def config(self):
        del self.settings.compiler.libcxx

    def generic_env_configure_vars(self, verbose=False):
        """Reusable in any lib with configure!!"""

        if self.settings.os == "Windows":
            self.output.fatal("Cannot build on Windows, sorry!")
            return

        if self.settings.os == "Linux" or self.settings.os == "Macos":
            libs = 'LIBS="%s"' % " ".join(["-l%s" % lib for lib in self.deps_cpp_info.libs])
            ldflags = 'LDFLAGS="%s"' % " ".join(["-L%s" % lib for lib in self.deps_cpp_info.lib_paths]) 
            archflag = "-m32" if self.settings.arch == "x86" else ""
            cflags = 'CFLAGS="-fPIC %s %s %s"' % (archflag, " ".join(self.deps_cpp_info.cflags), " ".join(['-I"%s"' % lib for lib in self.deps_cpp_info.include_paths]))
            cpp_flags = 'CPPFLAGS="%s %s %s"' % (archflag, " ".join(self.deps_cpp_info.cppflags), " ".join(['-I"%s"' % lib for lib in self.deps_cpp_info.include_paths]))
            command = "env %s %s %s %s" % (libs, ldflags, cflags, cpp_flags)
        elif self.settings.os == "Windows" and self.settings.compiler == "Visual Studio":
            cl_args = " ".join(['/I"%s"' % lib for lib in self.deps_cpp_info.include_paths])
            lib_paths= ";".join(['"%s"' % lib for lib in self.deps_cpp_info.lib_paths])
            command = "SET LIB=%s;%%LIB%% && SET CL=%s" % (lib_paths, cl_args)
            if verbose:
                command += " && SET LINK=/VERBOSE"
        
        return command
       
    def build(self):
        if self.settings.os == "Windows":
            self.output.fatal("Cannot build on Windows, sorry!")
            return # no can do boss!

        self.build_with_configure()
            
        
    def build_with_configure(self):
        config_options_string = ""

        for option_name in self.options.values.fields:
            activated = getattr(self.options, option_name)
            if activated:
                self.output.info("Activated option! %s" % option_name)
                config_options_string += " --%s" % option_name.replace("_", "-")

        # find the libgpg-error folder, so we can set the binary path for configuring it
        gpg_error_path = ""
        for path in self.deps_cpp_info.lib_paths:
            if "libgpg-error" in path:
                gpg_error_path = '/lib'.join(path.split("/lib")[0:-1]) #remove the final /lib. There are probably better ways to do this.
                break

        configure_command = "cd %s && %s ./configure --enable-static --enable-shared --with-libgpg-error-prefix=%s %s" % (self.ZIP_FOLDER_NAME, self.generic_env_configure_vars(), gpg_error_path, config_options_string)
        self.output.warn(configure_command)
        self.run(configure_command)
        self.run("cd %s && make" % self.ZIP_FOLDER_NAME)
       

    def package(self):
        if self.settings.os == "Windows":
            self.output.fatal("Cannot build on Windows, sorry!")
            return

        self.copy("*.h", dst="include", src="%s/src" % (self.ZIP_FOLDER_NAME), keep_path=True)
        if self.options.shared:
            self.copy(pattern="*.so*", dst="lib", src=self.ZIP_FOLDER_NAME, keep_path=False)
            self.copy(pattern="*.dll*", dst="bin", src=self.ZIP_FOLDER_NAME, keep_path=False)
        else:
            self.copy(pattern="*.a", dst="lib", src="%s" % self.ZIP_FOLDER_NAME, keep_path=False)
        
        self.copy(pattern="*.lib", dst="lib", src="%s" % self.ZIP_FOLDER_NAME, keep_path=False)
        
    def package_info(self):
        self.cpp_info.libs = ['gnutls']


