from conans import ConanFile
import os, shutil
from conans.tools import download, unzip, replace_in_file, check_md5
from conans import CMake


class GnutlsConan(ConanFile):
    name = "gnutls"
    version = "3.4.16"
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
    requires = 'libiconv/1.15@bincrafters/stable', 'nettle/3.3@DEGoodmanWilson/testing', 'gmp/6.1.1@DEGoodmanWilson/testing', 'zlib/1.2.8@conan/stable'
    # TODO add p11-kit http://p11-glue.freedesktop.org/p11-kit.html and libidn and libdane

    url = "http://github.com/DEGoodmanWilson/conan-gnutls"
    default_options = "shared=False", "enable_m_guard=False", "disable_asm=False", \
                      "enable_ld_version_script=False", "disable_endian_check=False", \
                      "enable_random_daemon=False", "disable_aesni_support=False", \
		      "enable_hmac_binary_check=False", "disable_padlock_support=False", "disable_O_flag_munging=False"

    def source(self):
        zip_name = "gnutls-%s.tar.gz" % self.version
        # download("http://ftp.heanet.ie/mirrors/ftp.gnupg.org/gcrypt/gnutls/v3.4/%s" % zip_name, zip_name)
        download("https://www.dropbox.com/s/njds242a0mk62wu/%s?dl=1" % zip_name, zip_name)
        check_md5(zip_name, "b4b58ca69bf58029553e0e3eac09f5b9")
        unzip(zip_name)
        os.unlink(zip_name)

    def config(self):
        del self.settings.compiler.libcxx

    def generic_env_configure_vars(self, verbose=False):
        """Reusable in any lib with configure!!"""
	
        # find nettle and hogweed paths
        nettle_lib_path = ""
        nettle_include_path = ""
        gmp_lib_path = ""
        gmp_include_path = ""
        for path in self.deps_cpp_info.lib_paths:
            if "nettle" in path:
                nettle_lib_path = path
            elif "gmp" in path:
                gmp_lib_path = path

        for path in self.deps_cpp_info.include_paths:
            if "nettle" in path:
                nettle_include_path = path
            elif "gmp" in path:
                gmp_include_path = path


        if self.settings.os == "Linux" or self.settings.os == "Macos":
            libs = 'LIBS="%s"' % " ".join(["-l%s" % lib for lib in self.deps_cpp_info.libs])
            ldflags = 'LDFLAGS="%s -liconv"' % " ".join(["-L%s" % lib for lib in self.deps_cpp_info.lib_paths]) 
            archflag = "-m32" if self.settings.arch == "x86" else ""
            cflags = 'CFLAGS="-fPIC %s %s %s"' % (archflag, " ".join(self.deps_cpp_info.cflags), " ".join(['-I"%s"' % lib for lib in self.deps_cpp_info.include_paths]))
            cpp_flags = 'CPPFLAGS="%s %s %s"' % (archflag, " ".join(self.deps_cpp_info.cppflags), " ".join(['-I"%s"' % lib for lib in self.deps_cpp_info.include_paths]))
            package_flags = 'NETTLE_CFLAGS="-I%s" NETTLE_LIBS="-L%s -lnettle" HOGWEED_CFLAGS="-I%s" HOGWEED_LIBS="-L%s -lhogweed" GMP_CFLAGS="-I%s" GMP_LIBS="-L%s -lgmp"' % (nettle_include_path, nettle_lib_path, nettle_include_path, nettle_lib_path, gmp_include_path, gmp_lib_path)
            command = "env %s %s %s %s %s" % (libs, ldflags, cflags, cpp_flags, package_flags)
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

        iconv_prefix = ""
        for path in self.deps_cpp_info.lib_paths:
            if "iconv" in path:
                iconv_prefix = '/lib'.join(path.split("/lib")[0:-1]) #remove the final /lib. There are probably better ways to do this.
                break

	# TODO remove --without-p11-kit
        configure_command = "cd %s && %s ./configure --enable-static --enable-shared --without-p11-kit --without-idn --with-included-libtasn1 --enable-local-libopts --with-libiconv-prefix=%s %s" % (self.ZIP_FOLDER_NAME, self.generic_env_configure_vars(), iconv_prefix, config_options_string)
        self.output.warn(configure_command)
        self.run(configure_command)
        self.run("cd %s && make" % self.ZIP_FOLDER_NAME)
       

    def package(self):
        if self.settings.os == "Windows":
            self.output.fatal("Cannot build on Windows, sorry!")
            return

        self.copy("*.h", dst="include", src="%s/src" % (self.ZIP_FOLDER_NAME), keep_path=True)
        self.copy("*.h", dst="include", src="%s/lib/includes" % (self.ZIP_FOLDER_NAME), keep_path=True)
        if self.options.shared:
            self.copy(pattern="*.so*", dst="lib", src=self.ZIP_FOLDER_NAME, keep_path=False)
            self.copy(pattern="*.dll*", dst="bin", src=self.ZIP_FOLDER_NAME, keep_path=False)
        else:
            self.copy(pattern="*.a", dst="lib", src="%s" % self.ZIP_FOLDER_NAME, keep_path=False)
        
        self.copy(pattern="*.lib", dst="lib", src="%s" % self.ZIP_FOLDER_NAME, keep_path=False)
        
    def package_info(self):
        self.cpp_info.libs = ['gnutls']


